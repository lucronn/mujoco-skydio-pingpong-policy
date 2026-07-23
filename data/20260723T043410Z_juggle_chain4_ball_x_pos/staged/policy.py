import dataclasses
import sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from juggle_autodrive import JuggleParams, make_policy_cls
_PARAMS = {'dz_under': 0.3257451494184334, 'xy_kp': 5.219286702744909, 'xy_kd': 1.1207093340149004, 'z_kp': 3.0865273572677836, 'z_kd': 2.0877767864015224, 'coll_bias': -0.1469269726108805, 'tip_flat_y': -0.34405326697187893, 'tip_flat_x': -0.5895563912373578, 'face_gain': 0.6432407666063295, 'max_xy_acc': 3.2135577040900336, 'blend': 0.2690709371982089, 'center_x': -0.04168339215581768, 'center_y': 0.15895707367926887, 'sep_s': 0.1586053180978266, 'sep_coll': 1.2, 'remount_dz': 0.02888951829612994, 'sep_drop': 0.2839462574999707, 'punch_gain': 2.6789118125856946, 'fwd_tip': 0.45, 'adv_frac': 0.8329738588553, 'loft_lead': 0.31815701712589395, 'dash_gain': 1.0, 'dash_z': 0.0, 'punch_cap': 2.842806255625635, 'park_hits': 7.0, 'fwd_after': 4.0, 'cycle_on': 1.0, 'launch_hit': 4.0, 'tap_adv': 0.0, 'tap_frac': 0.9274113109666049, 'drop_per_hit': 0.10094245287760681, 'catch_lead': 0.15, 'thread_s': 0.6425987067219083, 'base_z': 1.2694831903246921, 'min_taps': 4.0, 'launch_margin': 0.1570671702442681, 'launch_tip': 0.2849598438061206, 'track_gain': 0.1794120603844856, 'arrest_coll': 0.3855964791174962, 'impact_bvz': -0.05157786832491394, 'fall_away': 0.0}
_allowed = {f.name for f in dataclasses.fields(JuggleParams)}
Policy = make_policy_cls(JuggleParams(**{k: v for k, v in _PARAMS.items() if k in _allowed}))
