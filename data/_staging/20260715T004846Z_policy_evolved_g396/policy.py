# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.7108568026926158,
  "quiet_vy_hot": 1.9353895874795903,
  "quiet_ym_mod": 0.4236085512290803,
  "quiet_mod_dt": 0.26642570675451305,
  "race_ym_arm": 0.7719263312464654,
  "race_meet_back": 0.43290999002103503,
  "race_far_y": 0.2420940826618462,
  "race_dxy_lo": 0.18120478392981068,
  "race_dxy_hi": 0.5682765770040907,
  "race_far_off": 0.10382740494282244,
  "race_mix": 40.047185796193745,
  "race_ty_far": 0.5942105254793287,
  "race_ty_vy": 0.9096703792051977,
  "race_ty_g": 0.3549856016201379,
  "race_sep": 0.5500951810280574,
  "coast_after_contact": 0.4965820027521402,
  "early_tip_mix": 32.055735414589186,
  "early_tip_ty_far": 0.9473381363909893,
  "early_tip_ty_vy": 0.29827839535269385,
  "band2_tend_base": 0.8990670179661083,
  "band2_tend_span": 0.13985656847750233,
  "b1_ym": 0.8811201515900109,
  "b1_vy_max": 2.144504193630363,
  "b1_by_min": 0.12629523585876953,
  "b1_t0": 0.4887668368120435,
  "b1_t1": 0.5903353267556196,
  "cold_ym": 0.8432316850603565,
  "cold_vy_max": 1.5299792518530275,
  "cold_by_abs_max": 0.25,
  "cold_t0": 0.5619804891831122,
  "cold_t1": 0.8446532458760527,
  "cold_tend": 0.860744978241036,
  "cold_inside": 0.15730524123002226
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260715T004846Z_policy_evolved_g396/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
