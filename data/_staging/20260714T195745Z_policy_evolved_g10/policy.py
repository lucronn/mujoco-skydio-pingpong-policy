# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.6684848178484154,
  "quiet_vy_hot": 1.8810120384508329,
  "quiet_ym_mod": 0.69560678166742,
  "quiet_mod_dt": 0.15089860065232386,
  "race_ym_arm": 0.8557624293870388,
  "race_meet_back": 0.4382524478244932,
  "race_far_y": 0.28498263293813464,
  "race_dxy_lo": 0.24514208317897,
  "race_dxy_hi": 0.698714869390816,
  "race_far_off": 0.030031350195470898,
  "race_mix": 37.5579117864643,
  "race_ty_far": 0.850804951460267,
  "race_ty_vy": 0.7291072895239913,
  "race_ty_g": 0.6615459860691406,
  "race_sep": 0.4287582147376265,
  "coast_after_contact": 0.334614328097731,
  "early_tip_mix": 31.88966883123983,
  "early_tip_ty_far": 0.9055402327926981,
  "early_tip_ty_vy": 0.46971117397914564,
  "band2_tend_base": 0.8769076449828548,
  "band2_tend_span": 0.08789338325608455
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260714T195745Z_policy_evolved_g10/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
