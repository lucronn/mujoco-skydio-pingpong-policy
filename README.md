# MuJoCo Skydio X2 Ping-Pong Window-Gate Policy
<img width="400" height="225" alt="low_fast_actuated_rollout" src="https://github.com/user-attachments/assets/673777fd-5afe-4521-bc78-3e991f61a5c7" />

Analytical (non-learning) closed-loop policy for the MuJoCo Skydio X2 quadrotor ping-pong window-gate task. It commands the four rotor thrusts using a deterministic launch sequence, a delayed-measurement ball-state filter, geometric gate planning, and cascaded PID-style control. No reinforcement learning, no neural networks, numpy only.

## Visualize and compare

Browser comparison gallery (all videos play in-browser):

**https://lucronn.github.io/mujoco-skydio-pingpong-policy/**

The gallery shows native MuJoCo renders of the **same policy** across all four public scenarios side by side, a per-scenario metrics table, and the trajectory diagnostic.

### Native rollout renders (four public scenarios)

| Scenario | Score | Raw gates | Bounced | Windows | Crash | MP4 |
|---|---:|---:|---:|---:|:--:|---|
| nominal | 0.195 | 2 | 2 | 0 | yes | [mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/nominal_actuated_rollout.mp4) |
| ball_x_pos | 0.207 | 3 | 2 | 1 | yes | [mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/ball_x_pos_actuated_rollout.mp4) |
| ball_y_pos | 0.126 | 1 | 1 | 0 | no | [mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/ball_y_pos_actuated_rollout.mp4) |
| low_fast | 0.190 | 3 | 2 | 1 | yes | [mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/low_fast_actuated_rollout.mp4) |

### Trajectory diagnostic

Plot-based side/top trajectory render (ball, drone, gates, windows, target):

- Video: [assets/policy_one_trajectory_diagnostic.mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/policy_one_trajectory_diagnostic.mp4)
- Static summary: ![Trajectory diagnostic summary](assets/policy_one_trajectory_summary.png)

## Files

- `policy_one.py` - final policy candidate (numpy-only `Policy` with `reset()` / `act()`).
- `assets/nominal_actuated_rollout.mp4` - native MuJoCo render, nominal scenario.
- `assets/ball_x_pos_actuated_rollout.mp4` - native render, ball_x_pos scenario.
- `assets/ball_y_pos_actuated_rollout.mp4` - native render, ball_y_pos scenario.
- `assets/low_fast_actuated_rollout.mp4` - native render, low_fast scenario.
- `assets/policy_one_trajectory_diagnostic.mp4` - diagnostic plot-based render.
- `assets/policy_one_trajectory_summary.png` - final-frame trajectory summary.
- `index.html` - browser comparison gallery served by GitHub Pages.
- `render_summary.json` - metrics + checksums.

## Documented-range local validation (28 hidden-like cases)

| Metric | Value |
|---|---:|
| Public smoke average | 0.17952 |
| Hidden-like average | 0.15079 |
| Hidden-like suite estimate | 12.576 |
| Raw gates average | 2.14286 |
| Bounced gates average | 1.25 |
| Windows average | 0.25 |
| Safety average | 0.03571 |
| Target-box average | 0.03559 |

## Known limitation

This is a verified partial-credit policy, not a full solution. Across all four public scenarios it clears at most 3 raw gates and never completes the full course (four bounced gates + windows + target dwell). The high-energy launch that reliably earns the early gates sends the ball to roughly 3.9 m; it then descends too fast for the current back-half planner to convert into gates 3-4. Reduced-energy launches break gates 1-2, and recovery/descent/estimator-reset variants did not robustly improve the hidden-like suite.
