import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS=JuggleParams(**{'dz_under': 0.55, 'xy_kp': 3.776704275380355, 'xy_kd': 3.3999550618340817, 'z_kp': 5.94389225615628, 'z_kd': 1.9911285273831894, 'coll_bias': -0.17843606885015592, 'tip_flat_y': 0.6484889445827702, 'tip_flat_x': 0.041209491445341306, 'face_gain': 0.46249507578623966, 'max_xy_acc': 5.48953023194303, 'blend': 0.5859188210435244, 'center_x': 0.007025529126069595, 'center_y': 0.016293160798153607, 'sep_s': 0.2932400059571707, 'sep_coll': 1.118582935137814, 'remount_dz': 0.16784099725996518, 'sep_drop': 0.2620437641216399, 'punch_gain': 1.95})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
