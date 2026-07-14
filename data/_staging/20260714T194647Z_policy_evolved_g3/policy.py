# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.7036036723383623,
  "quiet_vy_hot": 1.887290144556357,
  "quiet_ym_mod": 0.6172132479576876,
  "quiet_mod_dt": 0.1763260891777483,
  "race_ym_arm": 0.8472583351860594,
  "race_meet_back": 0.4054432310114529,
  "race_far_y": 0.31301859197620496,
  "race_dxy_lo": 0.19314883873368097,
  "race_dxy_hi": 0.6774740861068199,
  "race_far_off": 0.06279302239237983,
  "race_mix": 38.184080635402964,
  "race_ty_far": 0.804473166898626,
  "race_ty_vy": 0.7439788342546984,
  "race_ty_g": 0.5929944306547776,
  "race_sep": 0.41683345120008974,
  "coast_after_contact": 0.33866858866888,
  "early_tip_mix": 30.86103059029285,
  "early_tip_ty_far": 0.9269941898901148,
  "early_tip_ty_vy": 0.433439222358672,
  "band2_tend_base": 0.880410723038655,
  "band2_tend_span": 0.09212563451013293
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260714T194647Z_policy_evolved_g3/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
