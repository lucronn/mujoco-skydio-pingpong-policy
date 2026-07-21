import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS=JuggleParams(**{'dz_under': 0.49059131771018155, 'xy_kp': 5.220540739238121, 'xy_kd': 3.4297497269503747, 'z_kp': 5.935044548987432, 'z_kd': 2.5828554957791052, 'coll_bias': -0.1703181122076914, 'tip_flat_y': 0.6946500591586484, 'tip_flat_x': 0.3415555527956377, 'face_gain': 0.607420435159231, 'max_xy_acc': 5.710372873225455, 'blend': 0.8399419631387092, 'center_x': 0.025147576873610307, 'center_y': 0.0007417595636460324, 'sep_s': 0.16638151698816905, 'sep_coll': 1.1949948694932964, 'remount_dz': 0.10151470257345871, 'sep_drop': 0.2686253387111756, 'punch_gain': 2.1747459430756875})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
