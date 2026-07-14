# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.7115292903489737,
  "quiet_vy_hot": 1.891276457624525,
  "quiet_ym_mod": 0.7783994925567334,
  "quiet_mod_dt": 0.16049224634008696,
  "race_ym_arm": 0.8970788189171699,
  "race_meet_back": 0.39403372094114253,
  "race_far_y": 0.28818743563474886,
  "race_dxy_lo": 0.4,
  "race_dxy_hi": 0.6338763141894261,
  "race_far_off": 0.022528582692583662,
  "race_mix": 26.009389695374143,
  "race_ty_far": 0.7946114643744883,
  "race_ty_vy": 0.5240456333495461,
  "race_ty_g": 0.7749554075798997,
  "race_sep": 0.30630121594178616,
  "coast_after_contact": 0.3772268788334456,
  "early_tip_mix": 34.64056577219839,
  "early_tip_ty_far": 0.9031081311727072,
  "early_tip_ty_vy": 0.4458472101293353,
  "band2_tend_base": 0.8745030242598852,
  "band2_tend_span": 0.06450668694104875,
  "b1_ym": 0.9295001749248636,
  "b1_vy_max": 2.115715753257249,
  "b1_by_min": 0.23796203204032598,
  "b1_t0": 0.5186146002243335,
  "b1_t1": 0.5638253007638571,
  "cold_ym": 0.9925761720798766,
  "cold_vy_max": 1.6232214410387142,
  "cold_by_abs_max": 0.540099740581993,
  "cold_t0": 0.4947228541528873,
  "cold_t1": 0.7454797804538097,
  "cold_tend": 0.8855661252064909,
  "cold_inside": 0.23556876536631557
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260714T201030Z_policy_evolved_g12/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
