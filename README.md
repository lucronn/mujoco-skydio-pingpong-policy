# MuJoCo Skydio X2 Ping-Pong Window-Gate Policy Evolution

Closed-loop controller evolution logs and rollout visualizer database for the MuJoCo Skydio X2 quadrotor ping-pong window-gate task.

## 📊 Live Progression Dashboard & Archive

We have built a fully interactive progression dashboard served by GitHub Pages:

👉 **[Interactive Comparison Gallery & Progression Dashboard](https://lucronn.github.io/mujoco-skydio-pingpong-policy/)**

The dashboard features:
- **Timeline Analytics Chart**: Plot nominal score penalty cost curves, raw/bounced gate clearance counts, and overall crash rates plotted across all historical training runs via Chart.js.
- **Widescreen Double-Pane Modal**: On screens above 1400px, the detail views display the 3D Render Video and the 2D Trajectory Render side-by-side. Inside the 2D pane, toggles let you switch between the 2D trajectory plot and diagnostic video.
- **Single-File Grid Renders**: Pre-compiled grid videos (`grid_renders.mp4` / `grid_renders.gif`) consolidate up to 28 case renders into a single file. This drops browser CPU and video decoder overhead, avoiding hardware crashes.
- **Complete Rollouts Archive**: Search and filter through all 134 rollout videos. Toggle simultaneous playback, loop controls, and mute settings globally.

---

## 📈 Policy Evolution & Optimization Timeline

Across 52 training runs, the analytical policy's hyperparameters and constraints were iteratively optimized to navigate the trade-off between aggressive gate clearing and back-half drone safety.

```
[Phase 1: Early Exploration (Runs 12-14)] ---> [Phase 2: Safety & Capping (Runs 10-11)] ---> [Phase 3: Focused Optimization (Runs 1-52)]
- Initial Nominals (U1 - U4)                   - Attitude Safety Tuning                      - Focus Runs (g3 to g16223)
- High Collective Thrust                       - Restricted Roll/Pitch Tilt <70°             - Balanced Gate Clearance
- 100% Nominal Crash Rate (except U4)          - Lower Collisions, Stable Sweeps             - Window Threading Constraints
```

### Development Phases

#### 1. Early Exploration (U1 - U4)
- **Runs**: `U1_nominal`, `U3_public_smoke`, `U4_nominal_postsep`
- **Characteristics**: Focused on establishing stable geometric tracking and vertical racket-ball impulse timings.
- **Results**: High collective thrust secured rapid gate crossings but caused severe attitude tilt spikes (up to 180°), resulting in crashes. `U4_nominal_postsep` achieved the first crash-free nominal run by capping maximum attitude tilt.

#### 2. Expansion & Safety Tuning (flyaway_fix - U_overnight_v109)
- **Runs**: `flyaway_fix_public`, `U_overnight_v109_public`
- **Characteristics**: Implemented attitude limiters to restrict maximum roll/pitch angles below 70°, addressing flyaway control bugs and extending sweeps to test up to 12 cases per run.
- **Results**: Reduced high-speed collisions and stabilized average scoring.

#### 3. Continuous Optimization (v229 - evolved_g3 to g16223)
- **Runs**: Focus runs, continuous solving up to generation 16,604+
- **Characteristics**: Iteratively tuned parameters for vertical window traversing. Refined trajectory alignment to thread window targets rather than purely chasing raw gate speed.
- **Results**: Converged on stable controllers that navigate gate clearances and window threading across multiple environments.

---

## 🛠️ Local Development & Indexing

### Serving the Dashboard Locally
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
This script scans the `data` directory, parses their case summaries and metrics JSONs, and updates `data/scanned_progression.json`.

---

## 📂 Repository Layout

- `process_data.py` - Scanning and indexing script for run directories.
- `index.html` - HTML5/CSS3 progression dashboard with dynamic overlay.
- `policy_one.py` - Core analytical closed-loop policy.
- `policy_three.py` - Stricter tilt-constrained policy.
- `data/` - Consolidated database folder containing all runs, staging policies, and overnight logs.
