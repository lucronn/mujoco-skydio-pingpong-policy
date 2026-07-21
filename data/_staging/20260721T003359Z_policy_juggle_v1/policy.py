import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS=JuggleParams(**{'dz_under': 0.5112338171904333, 'xy_kp': 2.090015563414363, 'xy_kd': 4.939154472366236, 'z_kp': 7.954517881002876, 'z_kd': 1.8899892701004402, 'coll_bias': -0.036216979322120285, 'tip_flat_y': -0.18899981745689703, 'tip_flat_x': 0.06413815299274753, 'face_gain': 0.9204607823815587, 'max_xy_acc': 6.22304014338062, 'blend': 0.44687268492091525, 'center_x': 0.016341621939792265, 'center_y': 0.01297437510123116, 'sep_s': 0.12, 'sep_coll': 1.1604529736281972, 'remount_dz': 0.041033948624108724, 'sep_drop': 0.23657829339367042, 'punch_gain': 1.95})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
