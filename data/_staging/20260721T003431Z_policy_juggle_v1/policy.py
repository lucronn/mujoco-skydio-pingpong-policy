import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS=JuggleParams(**{'dz_under': 0.55, 'xy_kp': 2.090015563414363, 'xy_kd': 4.939154472366236, 'z_kp': 8.423832994452694, 'z_kd': 1.8899892701004402, 'coll_bias': -0.12527308172860507, 'tip_flat_y': -0.2965251526052794, 'tip_flat_x': 0.06413815299274753, 'face_gain': 1.0319394675426359, 'max_xy_acc': 5.659979875729479, 'blend': 0.41824412266613664, 'center_x': 0.016341621939792265, 'center_y': 0.015425944514083837, 'sep_s': 0.15335176363538242, 'sep_coll': 1.0994819167576406, 'remount_dz': 0.041033948624108724, 'sep_drop': 0.23657829339367042, 'punch_gain': 1.8706646851769722})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
