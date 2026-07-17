# auto CI candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.8682255005676511,
  "quiet_vy_hot": 2.289412944901186,
  "quiet_ym_mod": 0.5502061838909239,
  "quiet_mod_dt": 0.07840490107868801,
  "race_ym_arm": 0.7268679106530013,
  "race_meet_back": 0.49702208291259703,
  "race_far_y": 0.26470603431423484,
  "race_dxy_lo": 0.06,
  "race_dxy_hi": 0.6586976289052761,
  "race_far_off": 0.012,
  "race_mix": 49.974774326528674,
  "race_ty_far": 0.8044785837121229,
  "race_ty_vy": 0.7746109021729632,
  "race_ty_g": 0.4184377003922424,
  "race_sep": 0.4126039250054476,
  "race_bvz_max": 2.427735167534775,
  "lag_chase_x": 0.45,
  "lag_chase_z": 0.11426804082051584,
  "lag_dz_lo": 0.09006095474051638,
  "lag_dxy_hi_cap": 0.17978829079794456,
  "lag_up": 0.28,
  "lag_mix_boost": 14.233274073044528,
  "lag_arm_bx": 2.0306729473141942,
  "lag_behind_eps": 0.012131363863020012,
  "hot_far_soft": -0.1760643100469142,
  "coast_after_contact": 0.44485355488638645,
  "early_tip_mix": 30.196234515766545,
  "early_tip_ty_far": 0.7697951686973044,
  "early_tip_ty_vy": 0.3249543647096565,
  "band2_tend_base": 0.8883223333005916,
  "band2_tend_span": 0.012852130169832048,
  "b1_ym": 0.9046155522646308,
  "b1_vy_max": 1.9502608072193333,
  "b1_by_min": 0.12611369999187508,
  "b1_t0": 0.5006234287517138,
  "b1_t1": 0.5796200187311379,
  "cold_ym_lo": 1.0425,
  "cold_ym_hi": 1.1105,
  "cold_ym_mid": 0.771077151091583,
  "cold_ym_mid_hi": 1.05,
  "cold_ym": 0.771077151091583,
  "cold_vy_max": 1.170512444468784,
  "cold_by_abs_max": 0.8765191862422825,
  "cold_t0": 0.5398475096810477,
  "cold_t1": 0.7124173605689328,
  "cold_tend": 0.9113292570196927,
  "cold_inside": 0.1742851454580974,
  "launch1_tx": -0.1,
  "launch1_ty": 0.20668423533793084,
  "launch2_scale": 1.0,
  "launch2_tx": 0.004346900444202017,
  "launch2_ty": 0.05,
  "race_lim_span": 0.4,
  "dive_vz_kp": 5.0,
  "dive_vz_kd": 1.3,
  "dive_vz_max_down": -6.199999999999999
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260717T155828Z_policy_evolved_ci_20260717T155828Z/policy_v230.py').resolve().parent / "policy_v230.py"
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
