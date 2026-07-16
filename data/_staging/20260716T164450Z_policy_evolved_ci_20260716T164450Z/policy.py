# auto CI candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.8682255005676511,
  "quiet_vy_hot": 2.289412944901186,
  "quiet_ym_mod": 0.5502061838909239,
  "quiet_mod_dt": 0.07840490107868801,
  "race_ym_arm": 0.7268679106530013,
  "race_meet_back": 0.49623056296565987,
  "race_far_y": 0.26470603431423484,
  "race_dxy_lo": 0.06,
  "race_dxy_hi": 0.6586976289052761,
  "race_far_off": 0.012534944913171225,
  "race_mix": 53.66726520377184,
  "race_ty_far": 0.8044785837121229,
  "race_ty_vy": 0.7746109021729634,
  "race_ty_g": 0.4184377003922424,
  "race_sep": 0.4126039250054476,
  "race_bvz_max": 1.8687895790457767,
  "coast_after_contact": 0.4448535548863865,
  "early_tip_mix": 30.196234515766545,
  "early_tip_ty_far": 0.7697951686973045,
  "early_tip_ty_vy": 0.3249543647096565,
  "band2_tend_base": 0.8883223333005917,
  "band2_tend_span": 0.01285213016983205,
  "b1_ym": 0.9046155522646308,
  "b1_vy_max": 1.9502608072193333,
  "b1_by_min": 0.12611369999187508,
  "b1_t0": 0.5006234287517138,
  "b1_t1": 0.5796200187311379,
  "cold_ym_lo": 1.2,
  "cold_ym_hi": 1.25,
  "cold_ym_mid": 0.771077151091583,
  "cold_ym_mid_hi": 1.05,
  "cold_ym": 0.771077151091583,
  "cold_vy_max": 1.170512444468784,
  "cold_by_abs_max": 0.8765191862422826,
  "cold_t0": 0.5398475096810477,
  "cold_t1": 0.7124173605689329,
  "cold_tend": 0.9113292570196927,
  "cold_inside": 0.1742851454580974,
  "lag_chase_x": 0.3474153356189007,
  "lag_chase_z": 0.13557102260428094,
  "lag_dz_lo": -0.0016550297585156415,
  "lag_dxy_hi_cap": 0.34081614185137055,
  "lag_up": 0.1596224294584148,
  "lag_mix_boost": 13.414903463011534,
  "lag_arm_bx": 1.7863135911469064,
  "lag_behind_eps": 0.07568071105494764,
  "hot_far_soft": -0.2143025322753545,
  "launch1_tx": -0.1,
  "launch1_ty": 0.20668423533793084,
  "launch2_scale": 1.0,
  "launch2_tx": 0.004337874157701538,
  "launch2_ty": 0.05,
  "race_lim_span": 0.4,
  "dive_vz_kp": 5.0,
  "dive_vz_kd": 1.3,
  "dive_vz_max_down": -6.2
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260716T164450Z_policy_evolved_ci_20260716T164450Z/policy_v230.py').resolve().parent / "policy_v230.py"
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
