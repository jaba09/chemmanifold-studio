F2 (kinetic-theory diffusion + Soret, GRI-subset chemkin mechanism), transient
restart from simple_F2_it800: unsteady 1st order, dt = 1e-3 s, <=10 inner iterations,
state at flow time t = 0.300 s after the restart.

cells.csv  all 22192 cells. vol_per_rad_m3 is Fluent's axisymmetric cell volume per radian;
           vol_2pi_m3 = 2*pi * vol_per_rad_m3 (full revolution). Units SI, mass fractions.
axis.csv   cells with r < 1e-4 m, same columns.
balance.txt boundary flux reports (full 2*pi). The species flows there use net mdot *
           mass-weighted Y and are WRONG at the outlet because of backflow; use the signed
           last-row integration instead (CO2 out = 1.65e-5 kg/s, H2O 1.17e-5 kg/s at 0.3 s).
tmax_vs_time.out  Tmax per time step (time step, tmax, flow time) for 0-0.300 s.
