# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.7443131728030475,
  "quiet_vy_hot": 1.916637712186536,
  "quiet_ym_mod": 0.7892706523524358,
  "quiet_mod_dt": 0.15411436635747505,
  "race_ym_arm": 0.8508988933365512,
  "race_meet_back": 0.4555889292548041,
  "race_far_y": 0.29230588645876115,
  "race_dxy_lo": 0.4,
  "race_dxy_hi": 0.6468257070581628,
  "race_far_off": 0.02,
  "race_mix": 23.887264471017232,
  "race_ty_far": 0.9377690788750349,
  "race_ty_vy": 0.592161314798748,
  "race_ty_g": 0.7049169774758611,
  "race_sep": 0.36642791494901705,
  "coast_after_contact": 0.31779189053788154,
  "early_tip_mix": 34.30933658723318,
  "early_tip_ty_far": 1.03807688591016,
  "early_tip_ty_vy": 0.40866709391006234,
  "band2_tend_base": 0.8746790641495473,
  "band2_tend_span": 0.06351874044345396,
  "b1_ym": 0.9453411936050755,
  "b1_vy_max": 2.1736382161450574,
  "b1_by_min": 0.2468168867745605,
  "b1_t0": 0.5174331461635138,
  "b1_t1": 0.5571912182761186,
  "cold_ym": 0.9537667699106851,
  "cold_vy_max": 1.6206649105472803,
  "cold_by_abs_max": 0.570285232896395,
  "cold_t0": 0.4813707751536728,
  "cold_t1": 0.7145773296804782,
  "cold_tend": 0.908216055832647,
  "cold_inside": 0.25534977800357883
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260714T200611Z_policy_evolved_g7/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
