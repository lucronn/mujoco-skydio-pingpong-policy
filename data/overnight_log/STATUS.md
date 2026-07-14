# Overnight status

**Champ:** `policy_evolved_g10` — raw **17.99** — `/tmp/output`  
hist `{1:9, 2:10, 3:6, 4:3}` mbg≈2.11

## Continuous solve (locked)
CEM runs until **raw≥50** via `repair_work/keep_evolve_running.sh`  
Log: `progression/overnight_log/evolve_continuous.log`  
Driver: `evolve_volley.py --until-raw 50 --resume` (install gate +0.005)  
**θ expanded to 33-D** (b1 thresholds + cold/lateral band3, cold off by default until CEM lowers `cold_ym`)

## Strategy lock
**Hybrid volley FSM + CEM** on `policy_v230` θ.
Plateau risk: rematch θ only moves soft/mean; still **9 bg=1**. Secondary if stall: deeper FSM / cold-arm θ expand.

## Not primary
Hand multiagent bands / cold tip grids / finite `--gens` batches / autodriver

## Progression pack 20260714T194605Z
- `20260714T194442Z_v229_focus_smoke` suite=focus raw=25.24 mbg=2.60
- policy `policy_v229.py`

## Progression pack 20260714T194710Z
- `20260714T194624Z_detach_smoke_v229` suite=focus raw=25.24 mbg=2.60
- policy `policy_v229.py` (rendered from staging snapshot)

## Progression pack 20260714T194731Z
- `20260714T194647Z_evolved_g3_focus` suite=focus raw=25.72 mbg=2.80
- policy `policy_evolved_g3.py` (rendered from staging snapshot)

## Progression pack 20260714T195349Z
- `20260714T195252Z_policy_evolved_g5_focus` suite=focus raw=28.00 mbg=3.00
- policy `policy_evolved_g5.py` (rendered from staging snapshot)

## Progression pack 20260714T195932Z
- `20260714T195745Z_policy_evolved_g10_focus` suite=focus raw=28.10 mbg=3.00
- policy `policy_evolved_g10.py` (rendered from staging snapshot)

## Progression pack 20260714T200541Z
- `20260714T200420Z_policy_evolved_g5_focus` suite=focus raw=28.00 mbg=3.00
- policy `policy_evolved_g5.py` (rendered from staging snapshot)

## Progression pack 20260714T200734Z
- `20260714T200611Z_policy_evolved_g7_focus` suite=focus raw=28.11 mbg=3.00
- policy `policy_evolved_g7.py` (rendered from staging snapshot)

## Progression pack 20260714T200925Z
- `20260714T200804Z_policy_evolved_g9_focus` suite=focus raw=28.11 mbg=3.00
- policy `policy_evolved_g9.py` (rendered from staging snapshot)

## Progression pack 20260714T201152Z
- `20260714T201031Z_policy_evolved_g12_focus` suite=focus raw=28.20 mbg=3.00
- policy `policy_evolved_g12.py` (rendered from staging snapshot)

