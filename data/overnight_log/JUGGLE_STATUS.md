# Juggle Autodrive Status

## Champ close-up (watch this)
https://lucronn.github.io/mujoco-skydio-pingpong-policy/data/20260721T003708Z_juggle_close/

- n=4 vertical bounces, mean_vz≈3.11
- vz_out: 4.26 → 3.83 → 2.86 → 1.51
- free-flight gaps: 0.63s / 0.57s / 0.48s
- punch_gain≈2.17; park after N=4 (safer)

## Active work
- Vultr: 1 parent + 14 workers, mean_vz-first fitness
- Pushing for higher loft / N≥5 without crash
- Frozen: repair_work/policy_juggle_v1.py
