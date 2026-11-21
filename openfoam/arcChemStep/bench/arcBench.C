// bench: integrate states (T p Y22 per line) over dt with an OpenFOAM ODE solver, two steps per state
#include "argList.H"
#include "ODESolver.H"
#include "IFstream.H"
#include "OFstream.H"
#include "clockTime.H"
#include "arc_gri30_nox22.h"
#include <cstdlib>
using namespace Foam;
static long nRhs = 0, nJac = 0;
static double hFloor = 1e-9, hRel = 1e-7;
static void (*rhs)(double, const double*, double*) = arc_rhs_original;
class B : public ODESystem {
public:
    mutable scalar p_ = 1e5;
    label nEqns() const { return ARC_N_ODE + 1; }
    void derivatives(const scalar, const scalarField& y, scalarField& d) const {
        double yy[23], dd[23]; for (int k = 0; k < 23; k++) yy[k] = y[k]; if (yy[22] < 200) yy[22] = 200;
        rhs(p_, yy, dd); nRhs++; for (int k = 0; k < 23; k++) d[k] = dd[k]; }
    void jacobian(const scalar, const scalarField& y, scalarField& dfdx, scalarSquareMatrix& J) const {
        nJac++; double yy[23], f0[23], f1[23]; for (int k = 0; k < 23; k++) yy[k] = y[k]; if (yy[22] < 200) yy[22] = 200;
        rhs(p_, yy, f0); nRhs++;
        for (int j = 0; j < 23; j++) { double y0 = yy[j];
            double h = (j == 22) ? 1e-6*max(y0, 300.0) : hRel*max(fabs(y0), hFloor);
            yy[j] = y0 + h; rhs(p_, yy, f1); nRhs++; yy[j] = y0;
            for (int i = 0; i < 23; i++) J(i, j) = (f1[i] - f0[i])/h; }
        for (int i = 0; i < 23; i++) dfdx[i] = 0; }
};
int main(int argc, char* argv[]) {
    argList::noParallel(); argList::addArgument("states"); argList::addOption("relTol","1e-5");
    argList::addOption("absTol","1e-12"); argList::addOption("hFloor","1e-9"); argList::addOption("dt","2e-5");
    argList::addOption("solver","seulex"); argList::addOption("out","file"); argList::addOption("kernel","original|rebuilt");
    argList args(argc, argv, false, false, false);
    hFloor = args.getOrDefault<scalar>("hFloor", 1e-9);
    if (args.getOrDefault<word>("kernel", "original") == "rebuilt") rhs = arc_rhs;
    scalar dt = args.getOrDefault<scalar>("dt", 2e-5);
    dictionary d; d.add("solver", args.getOrDefault<word>("solver","seulex"));
    d.add("absTol", args.getOrDefault<scalar>("absTol", 1e-12)); d.add("relTol", args.getOrDefault<scalar>("relTol", 1e-5));
    B ode; autoPtr<ODESolver> s = ODESolver::New(ode, d);
    IFstream is(args.get<fileName>(1)); label n; is >> n;
    autoPtr<OFstream> os; if (args.found("out")) os.reset(new OFstream(args.get<fileName>("out")));
    scalarField y(23); double sumT = 0, maxdT = 0; clockTime ct; long r0 = 0;
    double tWarm = 0;
    for (label c = 0; c < n; c++) {
        scalar T, p; is >> T >> p; for (int k = 0; k < 22; k++) is >> y[k]; y[22] = T; ode.p_ = p;
        scalar dx = 1e-7; s->solve(0, dt, y, dx);            // warm-up step (as the first flow step)
        long rw = nRhs; double tw = ct.timeIncrement(); tWarm += tw; r0 += 0; (void)rw;
        scalarField y1(y); s->solve(0, dt, y1, dx);           // second step from the estimate
        sumT += ct.timeIncrement(); if (os) { os() << y1[22]; for (int k = 0; k < 22; k++) os() << " " << y1[k]; os() << nl; } maxdT = max(maxdT, mag(y1[22]-y[22]));
    }
    Info<< "cells " << n << " warm " << tWarm/n*1e3 << " ms/cell, steady " << sumT/n*1e3
        << " ms/cell; rhs " << nRhs << " jac " << nJac << " (" << double(nRhs)/n/2 << " rhs/cell/step)"
        << " max dT 2nd step " << maxdT << endl;
}
