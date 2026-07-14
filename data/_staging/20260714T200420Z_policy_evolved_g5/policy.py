# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.6092532421942789,
  "quiet_vy_hot": 1.881668538853183,
  "quiet_ym_mod": 0.8,
  "quiet_mod_dt": 0.1467970398643097,
  "race_ym_arm": 0.8864326852814569,
  "race_meet_back": 0.40884152026742543,
  "race_far_y": 0.34261446662213063,
  "race_dxy_lo": 0.37802241622574173,
  "race_dxy_hi": 0.6489153209483179,
  "race_far_off": 0.029989986403131955,
  "race_mix": 24.359165106738292,
  "race_ty_far": 0.8915943369176684,
  "race_ty_vy": 0.6230967931085721,
  "race_ty_g": 0.6957135893401943,
  "race_sep": 0.21303961218536818,
  "coast_after_contact": 0.3142154533351098,
  "early_tip_mix": 35.4675203904148,
  "early_tip_ty_far": 1.133961395347765,
  "early_tip_ty_vy": 0.3964830742508442,
  "band2_tend_base": 0.8800879189344019,
  "band2_tend_span": 0.0628923984664116,
  "b1_ym": 0.9244121773285198,
  "b1_vy_max": 2.117530801464366,
  "b1_by_min": 0.23421165933566163,
  "b1_t0": 0.5221539316425403,
  "b1_t1": 0.555998203413102,
  "cold_ym": 0.9728702424742437,
  "cold_vy_max": 1.5359151151093382,
  "cold_by_abs_max": 0.4130373189903015,
  "cold_t0": 0.49731200544121984,
  "cold_t1": 0.6865951201394351,
  "cold_tend": 0.9218197423540032,
  "cold_inside": 0.24006956681373243
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260714T200420Z_policy_evolved_g5/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
