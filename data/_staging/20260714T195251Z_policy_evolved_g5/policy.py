# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.6763564053073107,
  "quiet_vy_hot": 1.89204890895492,
  "quiet_ym_mod": 0.6871667816651983,
  "quiet_mod_dt": 0.1608546423964635,
  "race_ym_arm": 0.8687429023865993,
  "race_meet_back": 0.4081126380225411,
  "race_far_y": 0.29680938408113716,
  "race_dxy_lo": 0.23904028473111727,
  "race_dxy_hi": 0.6927192803485142,
  "race_far_off": 0.04792089616965171,
  "race_mix": 38.29585497856016,
  "race_ty_far": 0.8333076460821353,
  "race_ty_vy": 0.7282236828079178,
  "race_ty_g": 0.6134817386706338,
  "race_sep": 0.41550310479710145,
  "coast_after_contact": 0.3523777336119095,
  "early_tip_mix": 32.65918382986304,
  "early_tip_ty_far": 0.8932110773398322,
  "early_tip_ty_vy": 0.44106859527711617,
  "band2_tend_base": 0.8757776472732708,
  "band2_tend_span": 0.09444003389776305
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260714T195251Z_policy_evolved_g5/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
