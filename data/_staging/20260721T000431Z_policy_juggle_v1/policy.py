#!/usr/bin/env python3
"""Frozen phase-1 vertical juggle policy (N>=4 in-cylinder, no crash)."""
from juggle_autodrive import JuggleParams, JugglePolicy

_PARAMS = JuggleParams(**{'dz_under': 0.28274696618150563, 'xy_kp': 7.4001491796683325, 'xy_kd': 2.306581148676468, 'z_kp': 12.0, 'z_kd': 5.930488513105702, 'coll_bias': 0.25739589907131744, 'tip_flat_y': -0.5005285090832932, 'tip_flat_x': 0.6305914735729806, 'face_gain': 1.771017841727339, 'max_xy_acc': 5.250421113434598, 'blend': 0.2922231157482322, 'center_x': 0.004692620305786695, 'center_y': 0.005959107627303426, 'sep_s': 0.2837045131203723, 'sep_coll': 1.1612098231042578, 'remount_dz': 0.22, 'sep_drop': 0.2691171898124734})

class Policy(JugglePolicy):
    def __init__(self):
        super().__init__(_PARAMS)
