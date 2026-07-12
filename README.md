# MuJoCo Skydio X2 Ping-Pong Window-Gate Policy

Analytical (non-learning) closed-loop policy for the MuJoCo Skydio X2 quadrotor ping-pong window-gate task. It commands the four rotor thrusts using a deterministic launch sequence, a delayed-measurement ball-state filter, geometric gate planning, and cascaded PID-style control. No reinforcement learning, no neural networks, numpy only.

## Visual comparison

GitHub Pages comparison gallery, with both videos playable in-browser:

**https://lucronn.github.io/mujoco-skydio-pingpong-policy/**

### Native MuJoCo rollout render

Direct MP4: [assets/nominal_actuated_rollout.mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/nominal_actuated_rollout.mp4)

https://github.com/lucronn/mujoco-skydio-pingpong-policy/assets/nominal_actuated_rollout.mp4

### Trajectory diagnostic render

This is a generated diagnostic video showing side/top trajectory plots for the ball, drone, gates, windows, and target. It is useful for understanding why the policy earns early gate credit but fails to complete the back half.

Direct MP4: [assets/policy_one_trajectory_diagnostic.mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/policy_one_trajectory_diagnostic.mp4)

https://github.com/lucronn/mujoco-skydio-pingpong-policy/assets/policy_one_trajectory_diagnostic.mp4

### Static trajectory summary

![Trajectory diagnostic summary](assets/policy_one_trajectory_summary.png)

## Files

- `policy_one.py` - final policy candidate (numpy-only `Policy` with `reset()` / `act()`).
- `assets/nominal_actuated_rollout.mp4` - native MuJoCo render generated on Kali with `xvfb-run`.
- `assets/policy_one_trajectory_diagnostic.mp4` - diagnostic plot-based render showing ball/drone trajectories.
- `assets/policy_one_trajectory_summary.png` - final-frame trajectory summary image.
- `index.html` - browser-playable comparison gallery served by GitHub Pages.
- `render_summary.json` - metrics + checksums.

## Rendered nominal rollout metrics

| Metric | Value |
|---|---:|
| Score | 0.19488 |
| Raw gates passed | 2 |
| Bounced gates passed | 2 |
| Drone windows passed | 0 |
| Safety score | 0.0 |
| Target box score | 0.0 |
| Drone crash | true |
| Max tilt | 84.16 deg |

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

This is a verified partial-credit policy, not a full solution. The high-energy launch that reliably earns gates 1-2 also sends the ball to roughly 3.9 m; it then descends too fast for the current back-half planner to convert into gates 3-4. Reduced-energy launches break gates 1-2, and recovery/descent/estimator-reset variants did not robustly improve the hidden-like suite.
