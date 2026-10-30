#include "tauCellHistogram.H"
#include "volFields.H"
#include "OFstream.H"
#include "OSspecific.H"
#include "addToRunTimeSelectionTable.H"

namespace Foam
{
namespace functionObjects
{
    defineTypeNameAndDebug(tauCellHistogram, 0);
    addToRunTimeSelectionTable(functionObject, tauCellHistogram, dictionary);
}
}


Foam::label Foam::functionObjects::tauCellHistogram::bin(const scalar x)
{
    return min(79, max(0, label(floor((log10(max(x, 1e-30)) + 8.0)/0.1))));
}


Foam::functionObjects::tauCellHistogram::tauCellHistogram
(
    const word& name,
    const Time& runTime,
    const dictionary& dict
)
:
    fvMeshFunctionObject(name, runTime, dict),
    every_(50),
    wedgeAngle_(5),
    Tsplit_(600),
    hist_(160, Zero),
    dtHist_(160, Zero),
    nSamples_(0)
{
    read(dict);
}


bool Foam::functionObjects::tauCellHistogram::read(const dictionary& dict)
{
    fvMeshFunctionObject::read(dict);
    every_ = dict.getOrDefault<label>("every", 50);
    wedgeAngle_ = dict.getOrDefault<scalar>("wedgeAngle", 5);
    Tsplit_ = dict.getOrDefault<scalar>("Tsplit", 600);
    return true;
}


bool Foam::functionObjects::tauCellHistogram::execute()
{
    if (time_.timeIndex() % every_ != 0) return true;

    const auto& T = mesh_.lookupObject<volScalarField>("T");
    const auto& U = mesh_.lookupObject<volVectorField>("U");
    const auto& rho = mesh_.lookupObject<volScalarField>("rho");
    const auto& alpha = mesh_.lookupObject<volScalarField>("thermo:alpha");
    const volScalarField* alphat = mesh_.findObject<volScalarField>("alphat");
    const scalarField& V = mesh_.V();
    const vectorField& C = mesh_.C();
    const scalar theta = wedgeAngle_*constant::mathematical::pi/180.0;
    const scalar dt = time_.deltaTValue();

    forAll(T, i)
    {
        scalar dx;
        if (theta > 0)
        {
            const scalar r = max(sqrt(sqr(C[i].y()) + sqr(C[i].z())), 1e-6);
            dx = sqrt(V[i]/(r*theta));
        }
        else
        {
            dx = cbrt(V[i]);
        }
        const scalar D = (alpha[i] + (alphat ? (*alphat)[i] : 0.0))/max(rho[i], VSMALL);
        const scalar tConv = dx/max(mag(U[i]), 1e-12);
        const scalar tDiff = sqr(dx)/max(D, 1e-12);
        const label hot = (T[i] >= Tsplit_ ? 80 : 0);
        hist_[hot + bin(0.1*min(tConv, tDiff))]++;
        dtHist_[hot + bin(dt)]++;
    }
    nSamples_++;

    labelList h(hist_), hd(dtHist_);
    Pstream::listCombineReduce(h, plusEqOp<label>());
    Pstream::listCombineReduce(hd, plusEqOp<label>());
    if (Pstream::master())
    {
        const fileName dir(time_.globalPath()/"postProcessing"/"tauCellHistogram");
        mkDir(dir);
        OFstream f(dir/"histogram.csv");
        f << "# tau_cell = 0.1 min(dx/|U|, dx^2/D); " << nSamples_
          << " samples, last at t = " << time_.value() << nl
          << "log10_lo,log10_hi,tau_cold,tau_hot,dt_cold,dt_hot" << nl;
        for (label b=0; b<80; b++)
        {
            f << -8 + 0.1*b << ',' << -8 + 0.1*(b + 1) << ',' << h[b] << ','
              << h[80 + b] << ',' << hd[b] << ',' << hd[80 + b] << nl;
        }
    }
    return true;
}


bool Foam::functionObjects::tauCellHistogram::write()
{
    return true;
}
