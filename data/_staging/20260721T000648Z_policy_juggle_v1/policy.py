import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from juggle_autodrive import JuggleParams, JugglePolicy
_PARAMS = JuggleParams(**{'dz_under': 0.28274696618150563, 'xy_kp': 7.561180452734798, 'xy_kd': 2.1848765705191, 'z_kp': 12.0, 'z_kd': 5.930488513105702, 'coll_bias': 0.25739589907131744, 'tip_flat_y': -0.5005285090832932, 'tip_flat_x': 0.638498077065116, 'face_gain': 1.7457874354625316, 'max_xy_acc': 5.155531965268159, 'blend': 0.4217476774648611, 'center_x': 0.004692620305786695, 'center_y': 0.005959107627303426, 'sep_s': 0.32, 'sep_coll': 1.1707922703135598, 'remount_dz': 0.22, 'sep_drop': 0.30391977152086924})
class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
