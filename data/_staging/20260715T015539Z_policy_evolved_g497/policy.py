# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.6332893474108953,
  "quiet_vy_hot": 2.0924699273659333,
  "quiet_ym_mod": 0.5015230297355586,
  "quiet_mod_dt": 0.2835779981979061,
  "race_ym_arm": 0.6728316520627402,
  "race_meet_back": 0.5546424948506296,
  "race_far_y": 0.31626962435525213,
  "race_dxy_lo": 0.24900121344130316,
  "race_dxy_hi": 0.7267710730832904,
  "race_far_off": 0.06981299168254304,
  "race_mix": 31.20646976377314,
  "race_ty_far": 0.9164467875160214,
  "race_ty_vy": 0.7539081701001937,
  "race_ty_g": 0.6016426842009022,
  "race_sep": 0.6233692831475222,
  "coast_after_contact": 0.3788962106732111,
  "early_tip_mix": 34.70897630639125,
  "early_tip_ty_far": 1.2,
  "early_tip_ty_vy": 0.1,
  "band2_tend_base": 0.7753966391090402,
  "band2_tend_span": 0.06027917746388824,
  "b1_ym": 0.8592198903703241,
  "b1_vy_max": 2.544102949155968,
  "b1_by_min": 0.13257043002522167,
  "b1_t0": 0.48670622188833457,
  "b1_t1": 0.6004585805293741,
  "cold_ym": 0.6274646963704815,
  "cold_vy_max": 1.6289045866414893,
  "cold_by_abs_max": 0.25,
  "cold_t0": 0.5484540809719024,
  "cold_t1": 0.651284322036787,
  "cold_tend": 0.8599462266944992,
  "cold_inside": 0.4
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260715T015539Z_policy_evolved_g497/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
