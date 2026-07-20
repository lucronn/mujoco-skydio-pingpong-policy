#!/usr/bin/env python3
"""Frozen phase-1 vertical juggle policy (N>=4 in-cylinder, no crash)."""
from juggle_autodrive import JuggleParams, JugglePolicy

_PARAMS = JuggleParams(**{'dz_under': 0.33405893075524323, 'xy_kp': 6.0, 'xy_kd': 3.209751249341733, 'z_kp': 9.908820369445786, 'z_kd': 1.4041667425544953, 'coll_bias': 0.10405889021839003, 'tip_flat_y': 0.056490083938235396, 'tip_flat_x': -0.11009560086794191, 'face_gain': 0.5689785402339267, 'max_xy_acc': 4.5, 'blend': 0.6369024471176995, 'center_x': 0.014431110013921375, 'center_y': 0.008375336627078227, 'sep_s': 0.4, 'sep_coll': 1.108742473018421, 'remount_dz': 0.12426925635847742, 'sep_drop': 0.1465124306527301})

class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
