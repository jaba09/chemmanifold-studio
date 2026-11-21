# Running the simulations on a rented server

Written 2026-11-03 (Spain time). This guide takes you, from a Windows PC, through renting a Linux
server, installing everything, copying the files, launching the long runs so they keep going when you
close the window, watching them, bringing the results home, and switching the server off so it stops
costing money.

Everything you type is in a grey box. Boxes marked **PowerShell (your PC)** are typed on Windows;
boxes marked **server** are typed in the server window after you have logged in.

What can run on the server:

| Run | What it is | Cores | Rough time |
|---|---|---|---|
| Exploration + training (`run_pipeline.py`) | Cantera exploration of the thermochemical space, then training of one network | 4 | 1-2 h |
| Seeds (`scripts/train_seeds.py`) | the same training with 3 random seeds | 2 per seed | 1.5-2 h for 3 seeds side by side |
| Offline benchmark (stage 18) | each model against Cantera on 440 states | 4 | ~15 min per model |
| CFD protocol, DI reference (GA18) | burner, 100 ms, GA18 in every cell | 2 | 8-11 h |
| CFD protocol, one model, pure or hybrid | burner, 100 ms, the network in the cells | 2 | 3-6 h |
| ISANN | burner, 50 ms, network trained during the run | 2 CFD + 2 training | 4-5 h |
| ITERML iteration (PR #19) | collection run, seeds, exploration, training, CFD test | 4 | most of a day |
| Ensemble CFD test (PR #21) | protocol run of each seed / ensemble | 2 per run | 3-6 h each |

The CFD times are from the 2-rank runs in the cloud containers (2-8 s per time step, 2500 steps per
50 ms). A server does not make one run much faster; what it gives you is **no 2-hour cut**, and room
to run several runs at the same time (one per 2 cores).

---

## 1. Which server to rent

**Recommendation: Hetzner Cloud, a "Dedicated vCPU" server (CCX line), in an EU location.**
It is simple, billed by the hour, and the cheapest of the big providers for this kind of work.

| Server | vCPU / memory / disk | Use it for | Approx. price |
|---|---|---|---|
| **CCX33** | 8 / 32 GB / 240 GB | one ISANN run, or two protocol runs at once, or training | ~€0.20-0.25 per hour (~€5-6 per day) |
| CCX43 | 16 / 64 GB / 360 GB | four protocol runs at once (e.g. the 3-seed ensemble test + DI) | ~€0.40-0.45 per hour |
| CCX53 | 32 / 128 GB / 600 GB | a whole queue of runs at once | ~€0.80-0.90 per hour |

Hetzner raised its prices twice in 2026, so check the price on the order page before you buy.
Choose **Dedicated vCPU (CCX)**, not "Shared vCPU" (CX/CPX): on shared servers other customers slow
your cores down, which ruins the seconds-per-step comparisons.

**Important about cost: on Hetzner a switched-off server is still billed.** Only deleting it stops
the bill. Section 9 shows how to keep a copy (a snapshot) and delete the server.

Alternatives, if you prefer:

- **AWS** (region *Europe (Spain)*, `eu-south-2`), instance `c7a.2xlarge` (8 real cores, 16 GB),
  about $0.45 per hour. A *stopped* AWS instance does not pay for the processor (only for its disk),
  which is handier if you start and stop often. The AWS console is more complicated.
- **Your university's or RES's HPC cluster** (no rental cost, but a queue and a time limit per job):
  see section 11.

Everything below is written for Hetzner. On AWS the only differences are how you create the server
(section 2) and the login name (`ubuntu@` instead of `root@`).

---

## 2. Create the server (once)

### 2.1 Make an SSH key on your PC

An SSH key is a pair of files that lets your PC log into the server without a password. Windows 10
and 11 already have the tools.

**PowerShell (your PC)** (Start menu, type *PowerShell*, open *Windows PowerShell*):

```powershell
ssh-keygen -t ed25519
```

Press **Enter** three times (default place, no passphrase). Then show the public half of the key:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub
```

Select the whole line it prints (it starts with `ssh-ed25519`) and copy it (right-click copies in
PowerShell).

### 2.2 Order the server

1. Go to <https://console.hetzner.com>, create an account (needs a card), and click **New project**
   (call it `chemmanifold`). Open the project.
2. Click **Add Server** (or **Create Resource → Servers**).
3. **Location:** Falkenstein or Nuremberg (Germany) or Helsinki.
4. **Image:** Ubuntu **24.04**.
5. **Type:** **Dedicated vCPU** → **x86 (Intel/AMD)** → **CCX33**. (Not Arm: OpenFOAM's package has no Arm build.)
6. **Networking:** leave **Public IPv4** ticked.
7. **SSH keys:** **Add SSH key**, paste the line you copied, give it a name, **Add SSH key**.
8. **Name:** `chem1`. Click **Create & Buy now**.

After about a minute the server shows a green dot and an IP address such as `65.108.12.34`. Copy it.
Below it is written `<IP>`; type your own number instead.

### 2.3 Log in

**PowerShell (your PC):**

```powershell
ssh root@<IP>
```

The first time it asks *Are you sure you want to continue connecting?*: type `yes` and Enter. The
prompt changes to `root@chem1:~#`. You are now typing on the server. `exit` logs out (the server keeps
running).

---

## 3. Install the software (once per server, 10-20 minutes)

**server:**

```bash
apt-get update && apt-get install -y git
git clone https://github.com/jaba09/chemmanifold-studio.git
cd chemmanifold-studio
bash server/setup_server.sh
```

If `git clone` asks for a username and password (the repository is private): the username is
`jaba09`, and the password is a **token**, not your GitHub password. Make one at
<https://github.com/settings/personal-access-tokens/new>: *Repository access → Only select
repositories → chemmanifold-studio*, *Permissions → Contents → Read-only*, **Generate token**, copy it
and paste it as the password (nothing appears on the screen while you paste; press Enter).

`setup_server.sh` installs, in `/opt/ofb`:

- OpenFOAM v2412 (the version all the burner runs used), from conda-forge, no system changes;
- a separate Python 3.12 with Cantera, PyTorch (CPU), numpy, scipy, pandas, scikit-learn, matplotlib,
  and this repository (`/opt/ofb/ml/bin/python`);
- `/opt/ofb/ofenv.sh`, the file that "switches on" OpenFOAM in a window;
- the compiled `userChemStep` library (surrogate, hybrid, ISANN, shadow DI checks) and
  `tauCellHistogram`.

It ends with a check like:

```
  OpenFOAM:        OK (/opt/ofb/env/bin/rhoReactingBuoyantFoam)
  userChemStep:    OK (/root/OpenFOAM/user-v2412/platforms/linux64GccDPInt32Opt/lib/libuserChemStep.so)
  Python ML:       OK (Cantera 3.x / torch 2.x)
```

It uses the same folders (`/opt/ofb/...`) as the cloud containers where the runs were developed, so
the commands in `openfoam/*/README.md` and the paths in `configs/iterml/*.yaml` work unchanged.

**Two Pythons, which one when:** after `. /opt/ofb/ofenv.sh`, plain `python3` is OpenFOAM's own Python
(numpy and h5py only; the OpenFOAM scripts use it). For anything with Cantera or PyTorch (training,
benchmark, scoring, ISANN daemon, ITERML) type `/opt/ofb/ml/bin/python`.

---

## 4. Copy the project files to the server

The runs need files that are not in the repository (base case of the burner, trained models, parent
data, DI reference snapshots). They are packed in two files in the project's Library, folder
`chemmanifold/servidor/`:

| File | Size | Holds | Needed for |
|---|---|---|---|
| `server-inputs.tgz` | 396 MB | burner base case (mesh, GA18, lit start, dt 2e-5 s); all models of `benchmark/modelos` and `benchmark/semillas`; the data of ood7 (ISANN parent) and ood8 (ITERML parent); benchmark states | every run |
| `server-di-reference.tgz` | 326 MB | GA18 DI reference snapshots 0-67.5 ms and the resumable DI states | **scoring** protocol, ITERML and ensemble runs (not for running them) |

1. Download both from the Library to your PC (they land in `Downloads`).
2. **PowerShell (your PC):**

   ```powershell
   ssh root@<IP> "mkdir -p /root/uploads"
   scp $env:USERPROFILE\Downloads\server-inputs.tgz $env:USERPROFILE\Downloads\server-di-reference.tgz root@<IP>:/root/uploads/
   ```

   It shows a progress bar; 700 MB take 5-20 minutes depending on your upload speed.

3. **server:**

   ```bash
   cd ~/chemmanifold-studio
   bash server/unpack_inputs.sh /root/uploads
   ```

After it, the files are in:

| Where | What |
|---|---|
| `/opt/ofb/files/chemmanifold/...` | the project files, same tree as the Library (also reachable as `/mnt/project-files/chemmanifold/...`) |
| `/opt/ofb/files/chemmanifold/benchmark/modelos/<name>/` | each model (`chemmanifold_model.txt`): ood1 ... ood8, chemnode, unityle, strain |
| `/opt/ofb/base/base` | the burner base case for every CFD run |
| `/opt/ofb/isann/parent_ood7` | ISANN's parent (as `openfoam/isann/isann.yaml` expects) |
| `/opt/ofb/iterml/data/iter0`, `/opt/ofb/iterml/base/base` | ITERML's parent data and base case (as `configs/iterml/*.yaml` expect) |

If you prefer drag and drop to `scp`, install **WinSCP** (<https://winscp.net>), log in with *File
protocol SFTP*, *Host name* `<IP>`, *User name* `root`, and under *Advanced → SSH → Authentication*
pick your key file `C:\Users\<you>\.ssh\id_ed25519` (WinSCP offers to convert it; say yes).

---

## 5. Keep runs alive when you close the window: tmux

If you start a run in the plain SSH window and then close it (or your PC sleeps), the run dies.
**tmux** keeps a window open on the server for you. Always start long runs inside tmux.

| You want to | Type |
|---|---|
| open a new tmux window called `isann` | `tmux new -s isann` |
| leave it running and go back to the normal window | press **Ctrl+B**, release, then press **D** |
| list the tmux windows | `tmux ls` |
| go back into one | `tmux attach -t isann` |
| scroll up inside tmux | **Ctrl+B** then **[**, arrows / PageUp; **q** to stop scrolling |
| close it (when the run has finished) | `exit` inside it |

Every runner in this repository is **resumable**: if the server restarts or a run is stopped, typing
the same command again continues from the last saved time. Nothing here has the 2-hour limit of the
chat's background jobs.

Before any OpenFOAM command in a new window, switch OpenFOAM on:

```bash
. /opt/ofb/ofenv.sh
cd ~/chemmanifold-studio
```

---

## 6. The runs

How many at the same time: one 2-rank CFD run per 2 vCPU, leaving 2 vCPU free for the system and
the plots. On a CCX33 (8 vCPU): 2-3 protocol runs, or 1 ISANN run (which uses 4) plus 1 protocol run.
`htop` shows how busy the cores are (**q** to quit).

### 6.1 Exploration + training of a network

```bash
tmux new -s train
cd ~/chemmanifold-studio
/opt/ofb/ml/bin/python run_pipeline.py --config configs/burner_fluent_strain.yaml --arch resnet_film
```

Outputs go to `data/<config name>/` (stage 12 writes the exported model, ready for OpenFOAM, into
`data/<config name>/08_fluent/`). The configs use 4 training threads (`training.threads: 4`); on a
CCX33 you can set it to 6. If it stops, restart from the stage that was running, e.g. `--from 7`
(training) — each stage reads the previous stage's files from `data/`.

Seeds (three trainings side by side, 2 threads each):

```bash
/opt/ofb/ml/bin/python scripts/train_seeds.py --config configs/burner_fluent_strain.yaml \
    --seeds 0 1 2 --parallel 3 --threads 2 --dest /opt/ofb/seeds
```

Offline benchmark (stage 18): `/opt/ofb/ml/bin/python scripts/18_offline_benchmark.py --help` lists
the options; models are given as `label=path/to/chemmanifold_model.txt`, e.g.
`ood8=/opt/ofb/files/chemmanifold/benchmark/modelos/ood8/chemmanifold_model.txt`.

### 6.2 CFD protocol (DI reference, a model in pure or hybrid mode)

The protocol is described in `openfoam/protocol/PROTOCOL.md` (100 ms from the lit start, start-up
and flame phases scored apart). One window per run:

```bash
tmux new -s ood8pure
. /opt/ofb/ofenv.sh && cd ~/chemmanifold-studio
mkdir -p /opt/ofb/runs
M=/opt/ofb/files/chemmanifold/benchmark/modelos
openfoam/protocol/run_protocol.sh /opt/ofb/base/base /opt/ofb/runs/ood8_pure pure $M/ood8
```

- `pure` = network everywhere (as in Fluent); `hybrid` = GA18 in the cells the network flags as
  outside its data; `di` = GA18 everywhere (the reference; `LABEL=di openfoam/protocol/run_protocol.sh /opt/ofb/base/base /opt/ofb/runs/di di`).
  The DI reference 0-67.5 ms is already in `server-di-reference.tgz`, so you only need a new DI run to
  go beyond 67.5 ms.
- Other models: replace `ood8` by any folder name in `$M` (or a seed:
  `/opt/ofb/files/chemmanifold/benchmark/semillas/ood1/seed1`, or a newly trained
  `~/chemmanifold-studio/data/<config>/08_fluent`).
- To stop early at 50 ms: put `T_END=0.05` before the command.
- Resume after a stop: type the same command again.
- `cat /opt/ofb/runs/ood8_pure/protocol_status` says `completed <time>` or `failed <time>`.

Score it against the DI reference:

```bash
D=/opt/ofb/files/chemmanifold/protocolo-cfd
/opt/ofb/ml/bin/python openfoam/protocol/score_protocol.py \
    --di $D/de-bucle-ood/snap_di $D/snap_di_ext \
    --run /opt/ofb/runs/ood8_pure/snap --label ood8_pure \
    --run-dir /opt/ofb/runs/ood8_pure --out /opt/ofb/reports
```

The report is `/opt/ofb/reports/ood8_pure/protocol_report.md` (+ `.json`, `protocol_timeseries.png`).
Several reports in one table:
`/opt/ofb/ml/bin/python openfoam/protocol/score_protocol.py --compare /opt/ofb/reports/*/protocol_report.json --out /opt/ofb/reports`.

### 6.3 ISANN

```bash
tmux new -s isann
cd ~/chemmanifold-studio
bash server/run_isann.sh isann1
```

This makes `/opt/ofb/run/isann1` from the base case and the ood7 parent, starts the trainer daemon
(2 threads) and the CFD (2 ranks), and runs to 50 ms. If it stops, run the same command again. The
daemon's diary is `/opt/ofb/run/isann1/isann/daemon.out`; the accepted networks are listed in
`/opt/ofb/run/isann1/isann/control`. Other parent or settings:
`bash server/run_isann.sh <name> <parent dir> 2 <your isann.yaml>` (the dY/dT parent `parent_ood7dy.tgz`
is in the Library under `chemmanifold/isann/delta-output/`; unpack it next to `parent_ood7` and give its
folder, with `isann_dy.yaml` from the same place as the settings file).

ISANN report: `/opt/ofb/ml/bin/python openfoam/isann/isann_report.py --help`.

### 6.4 ITERML and the ensemble tests (code still in open pull requests)

The ITERML driver is in PR #19 (branch `claude/project-thread-d8k91y`) and the ensemble code in PR #21
(branch `claude/project-thread-04fho7`); they are not in `main` yet. Both change `userChemStep`, so
after switching branch **rebuild it**:

```bash
cd ~/chemmanifold-studio
git fetch origin
git checkout claude/project-thread-d8k91y          # ITERML  (or claude/project-thread-04fho7 for the ensemble)
. /opt/ofb/ofenv.sh && (cd openfoam/userChemStep && ./Allwmake)
```

ITERML (one iteration, resumable; run the short test `--dry` first):

```bash
tmux new -s iterml
. /opt/ofb/ofenv.sh && cd ~/chemmanifold-studio
export OFENV=/opt/ofb/ofenv.sh
/opt/ofb/ml/bin/python openfoam/iterml/iterml.py --settings configs/iterml/iterml.yaml --root /opt/ofb/iterml --dry run --iter 1
/opt/ofb/ml/bin/python openfoam/iterml/iterml.py --settings configs/iterml/iterml.yaml --root /opt/ofb/iterml run --iter 1
```

Everything goes to `/opt/ofb/iterml/iter1/` (`ITER-REPORT.md` at the end, `iterml.log` in Spain time).
If it stops, the same command skips the finished steps and continues.

Ensemble: follow `docs/ENSEMBLE-ROADMAP.md` on that branch (it is a plan; its heavy stages wait for
your go-ahead). Its CFD tests are protocol runs in pure mode (section 6.2), one per seed, so on a
CCX43 the 3 seeds + the baseline run side by side in about the time of one.

Go back to `main` afterwards with `git checkout main` and rebuild `userChemStep` again the same way.

---

## 7. Watching a run

```bash
tmux ls                                              # which runs are open
tmux attach -t ood8pure                              # look at one (Ctrl+B then D to leave)
tail -f /opt/ofb/runs/ood8_pure/log.run              # live solver output (Ctrl+C stops watching, not the run)
grep "^Time = " /opt/ofb/runs/ood8_pure/log.run | tail -1     # simulated time reached (s)
grep ExecutionTime /opt/ofb/runs/ood8_pure/log.run | tail -2  # wall time; the difference = seconds per step
ls /opt/ofb/runs/ood8_pure/snap                      # snapshots written so far
htop                                                 # how busy the cores are (q to quit)
df -h /opt                                           # free disk
```

For ISANN the log is `/opt/ofb/run/<name>/log.run.<n>` (one per restart).

---

## 8. Bring the results home

Pack the light parts on the server (reports, snapshots, logs; not the big processor folders):

```bash
cd /opt/ofb
tar czf ~/results_$(date +%Y%m%d).tgz reports runs/*/snap runs/*/log.run runs/*/protocol_status \
    runs/*/processor0/shadowDI.csv run/*/isann run/*/log.run.* run/*/server.log iterml/*/ITER-REPORT.md 2>/dev/null
ls -lh ~/results_*.tgz
```

**PowerShell (your PC):**

```powershell
scp root@<IP>:/root/results_*.tgz $env:USERPROFILE\Downloads\
```

Then drop the `.tgz` into the project chat, and I can read and analyse it. For ParaView, reconstruct
the latest time first (`. /opt/ofb/ofenv.sh; cd /opt/ofb/runs/ood8_pure; reconstructPar -latestTime; touch run.foam`)
and copy the whole run folder.

---

## 9. Switch off to stop paying

When nothing is running (`tmux ls` shows nothing you still need, `htop` is quiet) and the results are
on your PC:

1. In the Hetzner console, open the server → **Snapshots** → **Take snapshot** (keeps everything:
   software, runs, data; costs roughly €0.01 per GB per month, a few euros at most). Wait until it is
   listed.
2. Server → **Delete** (top right, or the *Delete* tab) → confirm.

The bill for the server stops at that moment. **Power off is not enough** on Hetzner.

To work again: **Add Server** → under **Image** choose the **Snapshots** tab → your snapshot → same
type → create. Everything is as you left it (the IP address changes; use the new one). If you do not
need the old runs, skip the snapshot: a fresh server plus sections 3-4 takes about 30 minutes.

On AWS: **Instance state → Stop** stops the processor bill (the disk keeps costing ~€0.08 per GB per
month); **Terminate** deletes it.

---

## 10. When something goes wrong

| What you see | What to do |
|---|---|
| `rhoReactingBuoyantFoam: command not found` | type `. /opt/ofb/ofenv.sh` in that window |
| `ModuleNotFoundError: torch` / `cantera` | you used `python3`; use `/opt/ofb/ml/bin/python` |
| `Could not load "libuserChemStep.so"` | rebuild: `. /opt/ofb/ofenv.sh && (cd ~/chemmanifold-studio/openfoam/userChemStep && ./Allwmake)` |
| a run stopped (server restart, Ctrl+C) | type the same command again; it resumes |
| `protocol_status` says `failed`, log ends with `Floating point exception` | the run diverged (happens with some pure-mode models); it is scored up to where it got; send me the log |
| `No space left on device` | `df -h /opt`; delete old `processor*` folders of finished, already-scored runs |
| `ssh: connect to host ... timed out` | the server is off or was deleted; check the console |
| `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` (new server, same IP) | `ssh-keygen -R <IP>` in PowerShell, then log in again |

Everything printed in red by `setup_server.sh` or `unpack_inputs.sh` says what failed; running them
again is safe.

---

## 11. On a university / RES HPC cluster instead

Clusters have no hourly bill but use a queue (SLURM) and a time limit per job (often 24-72 h). The
same setup works without `sudo` if you change `OFB=/opt/ofb` to a folder in your home or project space
in `server/setup_server.sh` and `server/unpack_inputs.sh` (and the `/opt/ofb` paths in
`openfoam/isann/isann.yaml` and `configs/iterml/*.yaml`). Compute nodes often have no internet: run
`setup_server.sh` on the login node. Then submit runs as jobs instead of tmux, e.g. `protocol.sbatch`:

```bash
#!/bin/bash
#SBATCH --job-name=ood8pure
#SBATCH --ntasks=2
#SBATCH --time=24:00:00
. $HOME/ofb/ofenv.sh
cd $HOME/chemmanifold-studio
openfoam/protocol/run_protocol.sh $HOME/ofb/base/base $HOME/ofb/runs/ood8_pure pure $HOME/ofb/files/chemmanifold/benchmark/modelos/ood8
```

`sbatch protocol.sbatch` submits it, `squeue -u $USER` shows it, and if the time limit stops it,
`sbatch protocol.sbatch` again resumes it. Ask the cluster's support which partition and module
names to use; the MPI used is the one inside `ofb/env`, so no cluster MPI module is needed for 2-4
ranks on one node.
