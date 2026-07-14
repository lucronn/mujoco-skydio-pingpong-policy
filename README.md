# MuJoCo Skydio X2 Ping-Pong Window-Gate Policy Evolution

Analytical, closed-loop controller evolution logs and rollout visualizer database for the MuJoCo Skydio X2 quadrotor ping-pong window-gate task.

## 📊 Live Progression Dashboard & Archive

We have built a fully interactive progression dashboard served by GitHub Pages:

👉 **[Interactive Comparison Gallery & Progression Dashboard](https://lucronn.github.io/mujoco-skydio-pingpong-policy/)**

The dashboard features:
- **Timeline Analytics Chart**: Select between nominal score penalty cost curves, raw/bounced gate clearance counts, and overall crash rates plotted across all 14 historical training runs via Chart.js.
- **Simultaneous 3x3 Loop Grid**: Simultaneously plays and loops the nominal 3D rollout renders for the last 9 policy iterations. Clicking any card opens a diagnostic modal.
- **Detailed Evaluation Modal**: Drill down into specific cases (`nominal`, `range_424242_000`, etc.) to view side-by-side 2D/3D render videos, 2D trajectory snapshots, full metrics, and links to the staged controller code.
- **Complete Rollouts Archive**: Search and filter through all 134 rollout videos. Toggle simultaneous playback, loop controls, and mute settings globally.

---

## 📈 Policy Evolution & Optimization Timeline

Across 14 training runs, the analytical policy's hyperparameters and constraints were iteratively optimized to navigate the trade-off between aggressive gate clearing and back-half drone safety.

```
[Phase 1: Early Exploration (Runs 12-14)] ---> [Phase 2: Safety & Capping (Runs 10-11)] ---> [Phase 3: Focused Optimization (Runs 1-9)]
- Initial Nominals (U1 - U4)                   - Attitude Safety Tuning                      - Focus Runs (g3 to g12)
- High Collective Thrust                       - Restricted Roll/Pitch Tilt <70°             - Balanced Gate Clearance
- 100% Nominal Crash Rate (except U4)          - Lower Collisions, Stable Sweeps             - Window Threading Constraints
```

### Development Phases

#### 1. Early Exploration (U1 - U4)
- **Runs**: `U1_nominal`, `U3_public_smoke`, `U4_nominal_postsep`
- **Characteristics**: Focused on establishing stable geometric tracking and crisp racket-ball vertical impulse timings. 
- **Results**: High collective thrust secured rapid gate crossings but caused severe attitude tilt spikes (up to 180°), resulting in crashes. `U4_nominal_postsep` achieved the first crash-free nominal run by capping maximum attitude tilt.

#### 2. Expansion & Safety Tuning (flyaway_fix - U_overnight_v109)
- **Runs**: `flyaway_fix_public`, `U_overnight_v109_public`
- **Characteristics**: Implemented attitude limiters to restrict maximum roll/pitch angles below 70°, addressing flyaway control bugs and extending sweeps to test up to 12 cases per run.
- **Results**: Reduced high-speed collisions and stabilized average scoring.

#### 3. Focus Optimization (v229 - evolved_g3 to g12)
- **Runs**: `v229_focus_smoke`, `detach_smoke_v229`, `evolved_g3_focus`, `policy_evolved_g5_focus` (x2), `policy_evolved_g7_focus`, `policy_evolved_g9_focus`, `policy_evolved_g10_focus`, `policy_evolved_g12_focus`
- **Characteristics**: Iteratively tuned parameters for vertical window traversing. Refined trajectory alignment to thread window targets rather than purely chasing raw gate speed.
- **Results**: Achieved consistent gate crossings and window scores, converging on policy generation 12 (`g12_focus`).

---

## 📋 Progression Runs Directory Log

A total of 14 runs are cataloged in this repository under the `data/` folder:

| Run Label | Cases | Nominal Score | Nominal Crash | Avg Score | Avg Safety |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **policy_evolved_g12_focus** | 5 | 0.7120 | Yes | 0.3465 | 0.0000 |
| **policy_evolved_g9_focus** | 5 | 0.7120 | Yes | 0.3450 | 0.0000 |
| **policy_evolved_g7_focus** | 5 | 0.7120 | Yes | 0.3450 | 0.0000 |
| **policy_evolved_g5_focus** (Run 4) | 5 | 0.7120 | Yes | 0.3433 | 0.0000 |
| **policy_evolved_g10_focus** | 5 | 0.7120 | Yes | 0.3449 | 0.0000 |
| **policy_evolved_g5_focus** (Run 6) | 5 | 0.7120 | Yes | 0.3433 | 0.0000 |
| **evolved_g3_focus** | 5 | 0.7120 | Yes | 0.3319 | 0.0000 |
| **detach_smoke_v229** | 5 | 0.7120 | Yes | 0.3229 | 0.0000 |
| **v229_focus_smoke** | 5 | 0.7120 | Yes | 0.3229 | 0.0000 |
| **U_overnight_v109_public** | 12 | 0.7120 | Yes | 0.2554 | 0.2500 |
| **flyaway_fix_public** | 4 | 0.7119 | Yes | 0.4211 | 0.5000 |
| **U4_nominal_postsep** | 1 | 0.2492 | No | 0.2492 | 1.0000 |
| **U3_public_smoke** | 4 | 0.2502 | Yes | 0.2177 | 0.0000 |
| **U1_nominal** | 1 | 0.2076 | Yes | 0.2076 | 0.0000 |

---

## 🛠️ Local Development & Indexing

### serving the dashboard locally
To run the interactive comparison gallery locally, spin up a simple static web server from the repository root:

```bash
# Python 3
python3 -m http.server 8000
```
Then navigate to `http://localhost:8000` in your web browser.

### Re-indexing Progression Data
If you add new training runs to the `data/` directory, update the dashboard database index by executing:

```bash
python3 process_data.py
```
This script scans all folders starting with `20260714T` inside `data/`, parses their case summaries and metrics JSONs, and updates `data/scanned_progression.json`.

---

## 📂 Repository Layout

- `process_data.py` - Scanning and indexing script for run directories.
- `index.html` - HTML5/CSS3 progression dashboard with dynamic overlay.
- `policy_one.py` - Core analytical closed-loop policy.
- `policy_three.py` - Stricter tilt-constrained policy.
- `data/` - Consolidated database folder containing all runs, staging policies, and overnight logs.
