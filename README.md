# MuJoCo Skydio X2 Ping-Pong Window-Gate Policy

Analytical (non-learning) closed-loop policy for the MuJoCo Skydio X2 quadrotor ping-pong window-gate task. It commands the four rotor thrusts using a deterministic launch sequence, a delayed-measurement ball-state filter, geometric gate planning, and cascaded PID-style control. No reinforcement learning, no neural networks, numpy only.

## Rollout render (plays in the browser)

GitHub Pages player (recommended, always plays in-browser): **https://lucronn.github.io/mujoco-skydio-pingpong-policy/**

Inline preview:

https://github.com/lucronn/mujoco-skydio-pingpong-policy/assets/nominal_actuated_rollout.mp4

<video src="https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/nominal_actuated_rollout.mp4" controls muted playsinline width="720">
  Your browser can not play this embed. Direct link: https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/nominal_actuated_rollout.mp4
</video>

Direct MP4: [assets/nominal_actuated_rollout.mp4](https://github.com/lucronn/mujoco-skydio-pingpong-policy/raw/main/assets/nominal_actuated_rollout.mp4)

> If the inline player above does not render on the repo front page, use the GitHub Pages link (https://lucronn.github.io/mujoco-skydio-pingpong-policy/) or the direct MP4 link, both of which play in the browser.

## Files

- `policy_one.py` - final policy candidate (numpy-only `Policy` with `reset()` / `act()`).
- `assets/nominal_actuated_rollout.mp4` - native MuJoCo render (generated on this host with `xvfb-run`).
- `index.html` - browser-playable render page (served by GitHub Pages).
- `render_summary.json` - metrics + checksums for the rendered rollout.

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

The high-energy launch that reliably earns gates 1-2 also sends the ball to ~3.9 m; it then descends too fast for the current back-half planner to convert into gates 3-4. Reduced-energy launches break gates 1-2, and recovery/descent/estimator-reset variants did not improve the hidden-like suite. A stronger candidate likely needs a redesigned lower, controlled multi-bounce launch rather than back-half tuning.

## Checksums (sha256)

- policy_one.py: `28e9136d0b20ef51e9603c1221c4add46d84d80e5d9fdeaa8717f7ddb447290f`
- assets/nominal_actuated_rollout.mp4: `a89ca3170eb09d83b0be35bcf47b01b2fdd1d8ed5df38d4550d3df52abcd484b`
