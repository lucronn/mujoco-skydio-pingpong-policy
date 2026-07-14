# Where we are now — ping-pong window gate

**Updated:** 2026-07-14 ~17:02 local  
**Goal:** held-out `raw_score_100 > 50` on 28 cases  
**Live solver:** continuous CEM (`keep_evolve_running.sh` → `evolve_volley.py --until-raw 50`)

---

## Bottom line

| | |
|---|---|
| **Champ** | `policy_evolved_g12` |
| **Held-out raw** | **18.14** / 50 needed (~**36%** of target) |
| **mean_bg** | **2.14** (need many more cases at bg≥3–4) |
| **Gate hist** | `{1: 8, 2: 11, 3: 6, 4: 3}` — **8 stuck at bg=1** |
| **Nominal** | bg=4, score≈0.712 (focus gate still held) |
| **Install path** | `/tmp/output/policy_one.py` + `repair_work/policy_evolved_g12.py` |
| **CEM** | Running (~gen 75+), ~50s/gen, stalled just under champ |

Progress since overnight start is real but **small**: raw ~16.7 → **18.14**. Soft/score gains and **one** bg1→2 conversion; not yet on a path that reaches 50 without more mechanism (or a lucky cold-band hit).

---

## Scoreboard trajectory

Official formula: `100 * (0.60*mean + 0.28*q25 + 0.12*hard_rate)` — **not** `100*mean_score`.

| Stamp (UTC) | Champ | raw | Notes |
|---|---|---:|---|
| overnight early | ~v116–v229 hand | ~16.7–17.77 | Hand / multiagent bands plateau |
| CEM g3 | `policy_evolved_g3` | 17.86 | First CEM install |
| CEM g5–g10 | evolved_g5…g10 | 17.98–18.09 | Soft climb |
| CEM g12 | **`policy_evolved_g12`** | **18.14** | Current; hist 9→**8** bg=1 |

Focus-suite (5 hard cases) packs sit ~25–28 raw / mbg~3 — easier than full 28; don’t confuse with held-out.

---

## What’s running

1. **Primary:** continuous CEM on **33-D θ** (`policy_v230` + cold/lateral band3, cold **off** until search lowers `cold_ym`)  
   - Log: `progression/overnight_log/evolve_continuous.log`  
   - Checkpoint: `evolve_volley_last.json`  
   - Pool: **6 policy × 2 case workers**, BLAS/OpenMP pinned to 1 thread (CPU use is intentional; was oversubscribed before)
2. **Watchdogs:** `overnight_loop.sh` + overnight wake every ~20 min re-shepherds CEM  
3. **Progression:** `--detach` snapshot renders on install (doesn’t block CEM)  
4. **Not running:** finite `--gens` batches, param autodriver, Cursor Task multiagents as main loop

---

## What’s working

- Continuous solve no longer dies after a short batch  
- Focus gate (nom bg4 / 000≥3 / 002·011≥2) protects regressions  
- CEM found a few installs; early-inside θ + rematch gains still dominate winners  
- Detached progression packs for each install  

## What’s stuck

- **8 bg=1** cold/lateral cases (014, crosswinds, offsets, …) — same failure mode as before  
- Gen bests hovering **17.9–18.1** under champ for dozens of gens → θ on rematch **soft-plateau**  
- Gap to **raw>50** is large: need mass promotion to bg≥3–4, not ±0.1 soft ticks  

## Locked strategy (unchanged)

**Hybrid volley FSM + CEM** on evolvable rematch/early-arm θ.  
If stall continues: deepen FSM (SEPARATE→approach→strike) and/or force cold-band exploration — not hand case-ID bands or cold-start RL yet.

---

## How to check live

```bash
bash repair_work/keep_evolve_running.sh 50          # already-running or restart
tail -f progression/overnight_log/evolve_continuous.log
python3 -c "import json;print(json.load(open('progression/overnight_log/best.json'))['raw_score_100'])"
```

**Pointers:** `best.json` · `STATUS.md` · `STRATEGY.md` · this file `WHERE_WE_ARE.md`
