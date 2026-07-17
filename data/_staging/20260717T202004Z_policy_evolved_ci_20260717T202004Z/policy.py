# auto CI candidate
import importlib.util
from pathlib import Path
_THETA = {
  "quiet_ym_hot": 0.863797210184298,
  "quiet_vy_hot": 2.289412944901186,
  "quiet_ym_mod": 0.5437557719888343,
  "quiet_mod_dt": 0.07579162453983217,
  "race_ym_arm": 0.7268679106530013,
  "race_meet_back": 0.4941553462920987,
  "race_far_y": 0.2696607684509867,
  "race_dxy_lo": 0.09913855078942779,
  "race_dxy_hi": 0.6471414957068499,
  "race_far_off": 0.02674956861681908,
  "race_mix": 54.04332223773689,
  "race_ty_far": 0.7918871606248898,
  "race_ty_vy": 0.7760643474963798,
  "race_ty_g": 0.4268298974532272,
  "race_sep": 0.4126039250054476,
  "race_bvz_max": 2.3164113226565464,
  "lag_chase_x": 0.25149584664333297,
  "lag_chase_z": 0.21718297822917323,
  "lag_dz_lo": 0.04620057985038116,
  "lag_dxy_hi_cap": 0.3555422072631367,
  "lag_up": 0.20341439805489034,
  "lag_mix_boost": 5.741663408784509,
  "lag_arm_bx": 1.7491201363982054,
  "lag_behind_eps": 0.12634779464019372,
  "hot_far_soft": -0.1842982729077987,
  "coast_after_contact": 0.451352448374836,
  "early_tip_mix": 29.878455459483092,
  "early_tip_ty_far": 0.7647334727930255,
  "early_tip_ty_vy": 0.3249543647096565,
  "band2_tend_base": 0.8931118367043707,
  "band2_tend_span": 0.012852130169832048,
  "b1_ym": 0.894292913774426,
  "b1_vy_max": 1.9459644584262847,
  "b1_by_min": 0.12972311204363607,
  "b1_t0": 0.4900338243479108,
  "b1_t1": 0.5790581674883284,
  "cold_ym_lo": 1.0401870714333525,
  "cold_ym_hi": 1.1093420656652118,
  "cold_ym_mid": 0.7720295017255383,
  "cold_ym_mid_hi": 1.0448433989989965,
  "cold_ym": 0.7720295017255383,
  "cold_vy_max": 1.1762902040824676,
  "cold_by_abs_max": 0.8753385363589897,
  "cold_t0": 0.540217785428264,
  "cold_t1": 0.7124173605689328,
  "cold_tend": 0.9169227174365542,
  "cold_inside": 0.1742851454580974,
  "launch1_tx": -0.1,
  "launch1_ty": 0.20668423533793084,
  "launch2_scale": 1.0,
  "launch2_tx": 0.004346900444202017,
  "launch2_ty": 0.05,
  "race_lim_span": 0.4,
  "dive_vz_kp": 4.874252772921394,
  "dive_vz_kd": 1.354569368881074,
  "dive_vz_max_down": -6.174509623194963
}
_base_path = Path('/mnt/openfoam/pingpong-venv/progression/_staging/20260717T202004Z_policy_evolved_ci_20260717T202004Z/policy_v230.py').resolve().parent / "policy_v230.py"
_spec = importlib.util.spec_from_file_location("_volley_base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

class Policy(_base.Policy):
    def reset(self, info=None):
        super().reset(info)
        self.theta = dict(_THETA)
