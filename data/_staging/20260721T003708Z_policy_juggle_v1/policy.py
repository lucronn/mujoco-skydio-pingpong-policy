import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS=JuggleParams(**{'dz_under': 0.55, 'xy_kp': 4.449911782357496, 'xy_kd': 3.5956830433452525, 'z_kp': 8.417236294185948, 'z_kd': 2.0823797022128416, 'coll_bias': -0.10939220240634939, 'tip_flat_y': 0.6043448951129068, 'tip_flat_x': 0.607408427362048, 'face_gain': 0.8730644426694172, 'max_xy_acc': 6.179211170293486, 'blend': 0.85, 'center_x': 0.025147576873610307, 'center_y': 0.0007417595636460324, 'sep_s': 0.25116040704248427, 'sep_coll': 1.1949948694932964, 'remount_dz': 0.09788654383964666, 'sep_drop': 0.26647332320450684, 'punch_gain': 2.1747459430756875})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
