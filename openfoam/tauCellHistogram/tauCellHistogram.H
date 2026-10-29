/*---------------------------------------------------------------------------*\
    tauCellHistogram: histogram of Fluent's chemistry time scale per cell

    Fluent's laminar finite-rate stiff chemistry advances each cell over
    tau_cell = 0.1 min(t_conv, t_diff). OpenFOAM calls the chemistry with the
    flow time step instead, so this function object computes the equivalent
    per cell,
        t_conv = dx/|U|,  t_diff = dx^2/D,  D = (alpha + alphat)/rho,
    with dx the in-plane size of the cell (2D wedge: sqrt(V/(r theta))), and
    keeps only counts: log10(tau) bins of 0.1 from 1e-8 to 1 s, for cells
    colder / hotter than Tsplit. The counts accumulate every `every` time steps
    and postProcessing/tauCellHistogram/histogram.csv is rewritten each time.
    The flow time step of each call is counted too (columns dt_*), so the
    file also says what dt the chemistry really got.

    functions
    {
        tauCellHistogram
        {
            type    tauCellHistogram;
            libs    (tauCellHistogram);
            every   50;          // time steps between samples
            wedgeAngle 5;        // deg; 0 for a planar / 3D mesh (dx = V^(1/3))
            Tsplit  600;         // K
        }
    }
\*---------------------------------------------------------------------------*/

#ifndef functionObjects_tauCellHistogram_H
#define functionObjects_tauCellHistogram_H

#include "fvMeshFunctionObject.H"

namespace Foam
{
namespace functionObjects
{

class tauCellHistogram
:
    public fvMeshFunctionObject
{
    label every_;
    scalar wedgeAngle_;
    scalar Tsplit_;
    labelList hist_;
    labelList dtHist_;
    label nSamples_;

    static label bin(const scalar x);

public:

    TypeName("tauCellHistogram");

    tauCellHistogram(const word& name, const Time& runTime, const dictionary& dict);

    virtual ~tauCellHistogram() = default;

    virtual bool read(const dictionary& dict);
    virtual bool execute();
    virtual bool write();
};

} // End namespace functionObjects
} // End namespace Foam

#endif
