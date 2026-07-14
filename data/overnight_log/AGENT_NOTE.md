# Debug note 2026-07-14

## Why raw ~16 not ~50

1. **Wrong metric on progression packs**: `--random 0` evals (12 cases) give raw ~19.5; full held-out (28 cases) is ~16.6. Progression videos look good on public cases; 16 random cases dominate aggregate.

2. **Score caps**: partial bounced_gate_progress caps case score at `0.12 + 0.38*bg/4`. bg=1 → ~0.21, bg=2 → ~0.31. Random suite: 9× bg=1, 6× bg=2 → q25≈0.14, mean≈0.21 → raw≈16.

3. **Nominal ceiling**: if all 28 scored like nominal (0.712), raw≈62.7. Only 3/28 get 4 gates today.

4. **Failure mode**: open-loop smash credits gates 1–2 on lucky trajectories; gate 3+ needs rematch. Lateral y drift (yerr>0.7 at gate 3) with carry/chatter instead of SEPARATE→strike.

5. **Bug found**: post-g1 rescue waited for `cross_seen_t[1]` (x≥2.85) before rematching for `gates[2]` — after gate 2 already crossed. v113 retimed raw-ball window; same bg hist (no gain).

6. **Autodriver v2**: sep/win4/ty_gain grid cannot fix gate-1/2 rematch; plateau 16.42–16.63.

## v113 attempt
- Raw 16.34 (regression vs 16.63), nominal 4 bg preserved.

## Next autonomous work
- Hybrid: v85 warm-start → policy_named belief/strike for gate_idx 0–2 → existing g3/g4 fast path.
- Stop overnight param grid; eval on full 28-case suite only.
