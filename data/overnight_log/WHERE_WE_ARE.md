# Where we are now — ping-pong window gate

**Updated:** 2026-07-16 ~00:10 local  
**Goal:** held-out `raw_score_100 > 50` on 28 cases  

---

## Bottom line

| | |
|---|---|
| **Ship** | `near_gate_1.55` md5 `e6219107…` |
| **Held-out raw** | **≈19.2–19.3** (was ~18.68 on pure win2; prior “20.4” was stale vs live body) |
| **hist** | `{1:7, 2:16, 3:4, 4:1}` — **bg3+ = 5** (was 4) |
| **Nominal** | bg=4 score **0.774** win=2 (protected) |
| **Focus** | raw≈29 mbg=2.6 |
| **hard** | 0 |

First rematch hist gain: **`range_424242_005` → bg=3**. Soft score also up via nearer smash window (1.55 m).

---

## Why we were stuck (and what changed)

1. **Score formula caps incomplete bounce** — bg=2 ≈ case score 0.21; need mass bg≥3 for raw→50  
2. **CEM was dead** — thousands of gens with all focus FAIL; hard-reset patched in `evolve_volley.py`  
3. **Wrong lever** — tip/window search on nominal; g3 smash only under `fast_midcourse`  
4. **False smash bug** — tip at bx≪gate then **zeros** killed rematch; fixed with near-gate + abort  

**Working rematch patch:**
- Arm `fast_midcourse` when ymiss>0.55 or severe z-deficit after g2 cross (skips nominal)  
- Smash only within **1.25 m** of gate 3  
- Abort smash if no new contact in 0.14 s (no false zero-coast)

---

## Autonomy

- CI daemon + cron watchdog restored  
- `window_cycle` now runs **bg23** rematch search and restores `ship_bg23_best` (not tip thrash)  
- Vultr pushed with new `policy_v230` + rebased `best.json`  
- Pristine pre-rematch backup: `/tmp/policy_v230_ship_win2_ORIG.py`

---

## Path to 50

Still need ~16 more cases from bg=2→≥3, then windows + target. Soft CEM alone will not do it — keep rematch mechanism search as primary.
