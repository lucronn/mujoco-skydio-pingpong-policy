import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS=JuggleParams(**{'dz_under': 0.5407523975180364, 'xy_kp': 4.251449857746069, 'xy_kd': 4.489230108959308, 'z_kp': 6.591922049685816, 'z_kd': 1.6514850067197815, 'coll_bias': -0.16378356794612386, 'tip_flat_y': 0.39669793280423454, 'tip_flat_x': -0.2226855973197102, 'face_gain': 1.1131250267466106, 'max_xy_acc': 5.92849569498652, 'blend': 0.34302859738193053, 'center_x': 0.02266974270342351, 'center_y': 0.016293160798153607, 'sep_s': 0.23253758556672632, 'sep_coll': 1.1604529736281972, 'remount_dz': 0.18701803296192726, 'sep_drop': 0.2317823523075494, 'punch_gain': 1.95})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
