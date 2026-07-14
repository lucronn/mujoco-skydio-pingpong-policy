# auto-generated evolvable candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.7261118130495798,
  "quiet_vy_hot": 1.8452176121378527,
  "quiet_ym_mod": 0.7964006874094021,
  "quiet_mod_dt": 0.15685914401456985,
  "race_ym_arm": 0.8482789484166662,
  "race_meet_back": 0.4506048701766919,
  "race_far_y": 0.29461528659776,
  "race_dxy_lo": 0.4,
  "race_dxy_hi": 0.6589533975534416,
  "race_far_off": 0.03281394852773938,
  "race_mix": 22.964641409215965,
  "race_ty_far": 0.8152946299740033,
  "race_ty_vy": 0.6011364171482811,
  "race_ty_g": 0.7514865086602955,
  "race_sep": 0.34882272481773186,
  "coast_after_contact": 0.3077487474107964,
  "early_tip_mix": 34.55762957272773,
  "early_tip_ty_far": 0.847862509143884,
  "early_tip_ty_vy": 0.40333366810206817,
  "band2_tend_base": 0.8708421116287347,
  "band2_tend_span": 0.08043770303684095,
  "b1_ym": 0.9596401101685397,
  "b1_vy_max": 2.235370205890854,
  "b1_by_min": 0.2486678415159536,
  "b1_t0": 0.5175160644476942,
  "b1_t1": 0.5565350559196418,
  "cold_ym": 0.9462083340053374,
  "cold_vy_max": 1.5993553777393037,
  "cold_by_abs_max": 0.6015632542121767,
  "cold_t0": 0.4747804755159185,
  "cold_t1": 0.7183753839616509,
  "cold_tend": 0.9006568559570509,
  "cold_inside": 0.263729563289477
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260714T200803Z_policy_evolved_g9/policy_v230.py')
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
