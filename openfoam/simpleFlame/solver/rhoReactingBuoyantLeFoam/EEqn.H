{
    volScalarField& he = thermo.he();

    // enthalpy carried by species diffusion beyond the unity-Lewis part (zero for "stock")
    volScalarField speciesEnthalpyDiffusion
    (
        IOobject("speciesEnthalpyDiffusion", runTime.timeName(), mesh),
        mesh,
        dimensionedScalar(dimEnergy/dimTime/dimVolume, Zero)
    );
    if (diffModel != "stock")
    {
        const volScalarField alphaEff(turbulence->alphaEff());
        forAll(Y, i)
        {
            speciesEnthalpyDiffusion +=
                fvc::laplacian(speciesHs(i)*(rhoDEff[i] - alphaEff), Y[i]);
        }
    }

    fvScalarMatrix EEqn
    (
        fvm::ddt(rho, he) + mvConvection->fvmDiv(phi, he)
      + fvc::ddt(rho, K) + fvc::div(phi, K)
      + (
            he.name() == "e"
          ? fvc::div
            (
                fvc::absolute(phi/fvc::interpolate(rho), U),
                p,
                "div(phiv,p)"
            )
          : -dpdt
        )
      - fvm::laplacian(turbulence->alphaEff(), he)
      - speciesEnthalpyDiffusion
     ==
        Qdot
      + fvOptions(rho, he)
    );

    EEqn.relax();

    fvOptions.constrain(EEqn);

    EEqn.solve();

    fvOptions.correct(he);

    thermo.correct();

    Info<< "min/max(T) = "
        << min(T).value() << ", " << max(T).value() << endl;
}
