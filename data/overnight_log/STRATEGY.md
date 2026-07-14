# Overnight strategy (standing brief)

**Goal:** held-out `raw_score_100 > 50` on 28 cases.

**Primary approach (locked):** **Hybrid volley FSM + CEM on rematch θ**  
- Base: `repair_work/policy_v230.py` (`self.theta` gains for quiet / race / early tip / band2 tend)  
- Driver: `repair_work/evolve_volley.py`  
- Fitness: focus gate then full `raw_score_100` via `parallel_suite.py`  
- Why: highest success odds vs hand-tuning, rigid open-loop grids, or cold-start RL/MPC here.

**Champ:** `progression/overnight_log/best.json` + `/tmp/output`  
**Board:** `ma_board.json` still used to record evolve outcomes / failed regions.

## Secondary (only if CEM stalls)
- Deeper FSM (explicit SEPARATE→approach→strike states) with same θ loop  
- Not: case-ID bands, tip microgrids, full RL until θ search saturates

## Wake behavior
**Always keep continuous CEM running until raw>50.** Prefer:
```bash
nohup .venv/bin/python repair_work/evolve_volley.py --until-raw 50 --pop 12 --elite 3 --case-workers 4 --resume \
  >> progression/overnight_log/evolve_continuous.log 2>&1 &
```
Do **not** use finite `--gens N` as the overnight driver — that exits before the goal.
Check live: `tail -f progression/overnight_log/evolve_continuous.log`
Multiagent L1/L2/L3 = optional **proposal seeds** into θ means, not the main loop.
