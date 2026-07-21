import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS=JuggleParams(**{'dz_under': 0.2556050121742397, 'xy_kp': 5.5, 'xy_kd': 2.8, 'z_kp': 8.252900184813482, 'z_kd': 3.5, 'coll_bias': -0.11372611270499484, 'tip_flat_y': 0.047249135790760934, 'tip_flat_x': -0.2298201499898013, 'face_gain': 0.6550201707814017, 'max_xy_acc': 4.5, 'blend': 0.789968614389558, 'center_x': 0.012519157094999053, 'center_y': 0.025166527235611327, 'sep_s': 0.34, 'sep_coll': 1.193584651024981, 'remount_dz': 0.16737567981076976, 'sep_drop': 0.34140322173469234, 'punch_gain': 1.4314389301634378})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
