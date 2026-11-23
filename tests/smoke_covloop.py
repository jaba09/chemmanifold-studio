"""COVLOOP pipeline smoke (no OpenFOAM): train -> fake leg from general states -> coverage -> seed -> train -> decide.
The fake 'run' cells are general-sampling states with noise; it only checks that files flow between the steps."""
import sys, os, subprocess, shutil
import numpy as np
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, root)
from chemmanifold.moe import CPUFastMoE
R = "/tmp/claude-0/covloop_smoke"
shutil.rmtree(R, ignore_errors=True); os.makedirs(f"{R}/general")
shutil.copy("/tmp/claude-0/gs_smoke/pairs.npz", f"{R}/general/pairs.npz")
drv = [sys.executable, "-I", f"{root}/openfoam/covloop/covloop.py", "--root", R, "--np", "4", "--smoke"]
def run(*a):
    print(subprocess.run(drv + list(a), capture_output=True, text=True, check=True).stdout[-600:])
run("train", "0")
g = np.load(f"{R}/general/pairs.npz", allow_pickle=True)
m = CPUFastMoE.load(f"{R}/iter0/train_r0/moe.npz")
rng = np.random.default_rng(0)
i = rng.choice(len(g["T"]), 400)
T = g["T"][i] * (1 + 0.03 * rng.standard_normal(400)); Y = g["Y"][i]
_, fb = m.step(T, Y, np.full(400, 2e-5))
os.makedirs(f"{R}/iter0/runs/A_flame")
np.savez(f"{R}/iter0/runs/A_flame/cells.npz", T=T, Y=Y, species=g["species"], mass=np.ones(400), ood=fb)
np.savez(f"{R}/iter0/runs/A_flame/shadow.npz", T=np.repeat(T, 8), Y=np.repeat(Y, 8, 0), species=g["species"],
         **{"pass": rng.uniform(size=3200) > 0.05})
run("coverage", "0")
run("seed", "0")
run("train", "1")
assert os.path.exists(f"{R}/iter1/train_r1/chemmanifold_model.txt")
run("decide")
print(open(f"{R}/DECISIONS.md").read())
print("SMOKE OK")
