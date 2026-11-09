// Species diffusion model, read from constant/speciesDiffusion (optional; default = stock)
//   model  stock;          rho D_k = mu + mu_t                     (stock reactingFoam: Sc = Sc_t = 1)
//   model  unityLewis;     rho D_k = kappa/cp + mu_t/Sct           (Le_k = 1)
//   model  constantLewis;  rho D_k = kappa/(cp Le_k) + mu_t/Sct    (Le from the Le sub-dictionary)
// For unityLewis/constantLewis the energy equation also gets the enthalpy flux carried by species
// diffusion that differs from heat diffusion, div( sum_k hs_k (rho D_k - alphaEff) grad Y_k ),
// as Fluent does (energy/species-diffusion on). The inert species absorbs the mass-conservation
// error (1 - sum Y), as in Fluent's dilute approximation.
IOdictionary speciesDiffusionDict
(
    IOobject
    (
        "speciesDiffusion",
        runTime.constant(),
        mesh,
        IOobject::READ_IF_PRESENT,
        IOobject::NO_WRITE
    )
);
const word diffModel(speciesDiffusionDict.getOrDefault<word>("model", "stock"));
const scalar Sct(speciesDiffusionDict.getOrDefault<scalar>("Sct", 1.0));
scalarList LeK(Y.size(), 1.0);
if (diffModel == "constantLewis")
{
    const dictionary& LeDict = speciesDiffusionDict.subDict("Le");
    const scalar LeDefault = LeDict.getOrDefault<scalar>("default", 1.0);
    forAll(Y, i)
    {
        LeK[i] = LeDict.getOrDefault<scalar>(Y[i].name(), LeDefault);
    }
}
else if (diffModel != "stock" && diffModel != "unityLewis")
{
    FatalErrorInFunction << "speciesDiffusion model " << diffModel
        << " unknown; use stock, unityLewis or constantLewis" << exit(FatalError);
}
Info<< "Species diffusion model " << diffModel << ", Sct " << Sct << nl;
forAll(Y, i)
{
    Info<< "    Le " << Y[i].name() << " " << LeK[i] << nl;
}
Info<< endl;

PtrList<volScalarField> rhoDEff(Y.size());
forAll(Y, i)
{
    rhoDEff.set
    (
        i,
        new volScalarField
        (
            IOobject("rhoDEff_" + Y[i].name(), runTime.timeName(), mesh),
            turbulence->muEff()
        )
    );
}

// sensible enthalpy of species i at the current p, T (cells and boundary faces)
auto speciesHs = [&](const label i)
{
    tmp<volScalarField> ths
    (
        new volScalarField
        (
            IOobject("hs_" + Y[i].name(), runTime.timeName(), mesh),
            mesh,
            dimensionedScalar(dimEnergy/dimMass, Zero)
        )
    );
    volScalarField& hs = ths.ref();
    forAll(hs, celli)
    {
        hs[celli] = composition.Hs(i, p[celli], T[celli]);
    }
    volScalarField::Boundary& hsb = hs.boundaryFieldRef();
    forAll(hsb, patchi)
    {
        forAll(hsb[patchi], facei)
        {
            hsb[patchi][facei] = composition.Hs
            (
                i,
                p.boundaryField()[patchi][facei],
                T.boundaryField()[patchi][facei]
            );
        }
    }
    return ths;
};
