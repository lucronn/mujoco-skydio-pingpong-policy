# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.8933564873280517,
  "quiet_vy_hot": 2.376484620304717,
  "quiet_ym_mod": 0.5897996845757282,
  "quiet_mod_dt": 0.0869759420642773,
  "race_ym_arm": 0.7657548020110376,
  "race_meet_back": 0.4608079320518216,
  "race_far_y": 0.21843386304612292,
  "race_dxy_lo": 0.1321969039484466,
  "race_dxy_hi": 0.6848819408570909,
  "race_far_off": 0.044718150480158904,
  "race_mix": 54.095486955553596,
  "race_ty_far": 0.8996828081250319,
  "race_ty_vy": 0.6856752656882681,
  "race_ty_g": 0.44299784296041655,
  "race_sep": 0.39474556516436565,
  "coast_after_contact": 0.3939467843149883,
  "early_tip_mix": 27.51433287599564,
  "early_tip_ty_far": 0.7116173566822316,
  "early_tip_ty_vy": 0.36524850827600475,
  "band2_tend_base": 0.8654511896089824,
  "band2_tend_span": 0.036841818470017926,
  "b1_ym": 0.8895289720090322,
  "b1_vy_max": 1.9326216960417013,
  "b1_by_min": 0.12483496947574466,
  "b1_t0": 0.5042488633297817,
  "b1_t1": 0.5765146744757774,
  "cold_ym": 0.8266710748690492,
  "cold_vy_max": 1.158760201233805,
  "cold_by_abs_max": 0.8293047999982954,
  "cold_t0": 0.5430293121963732,
  "cold_t1": 0.7188336501297597,
  "cold_tend": 0.8710564367372595,
  "cold_inside": 0.15625374327507272
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260715T061844Z_policy_evolved_g883/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
