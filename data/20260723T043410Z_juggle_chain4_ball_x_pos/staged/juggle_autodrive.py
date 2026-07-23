#!/usr/bin/env python3
"""Phase-2: forward juggle rally — bounce ball OVER each gate, dash drone THROUGH the window.

Fitness re-aimed at the real scorer (user directive 2026-07-21):
  primary   bounced_gate_passes (bg)     — ball over each gate lintel after a distinct bounce
  then      drone_windows_passed (wins)  — drone body inside each gate's window box
  then      no-crash, plant case score, shaped progress (reach/clearance/loft/travel), -chatter

Geometry (actuated_plant):
  gate_top_z(h) = h + 1.90  -> ball must clear z ~= 2.59..2.73 m at the gate plane
  window center z = h + 1.10 (box |dx|<0.18, |dy|<0.64, |dz|<0.44) -> drone threads at ~1.3..2.1 m
  bounce -> gate-cross credit window 0.65 s -> contact ~0.5..0.9 m before the plane, vx ~1.2..2.0

Compat: Phase-1 `score_contacts` retained; ALL new JuggleParams fields default to
Phase-1-neutral values so frozen demos (policy_juggle_v1.py, juggle_winners/policy_juggle_*.py)
behave exactly as before. Forward behavior comes from seeds/mutation, not defaults.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import math
import os
import random
import sys
import time
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "q1-pingpong-window-gate-kit" / "data"))
sys.path.insert(0, str(REPO / "repair_work"))

from actuated_plant import run_episode, scenario_to_arrays  # noqa: E402
import parallel_suite as ps  # noqa: E402

OUT_DIR = REPO / "repair_work" / "juggle_winners"
LOG = REPO / "progression" / "overnight_log"
STATUS = LOG / "JUGGLE_STATUS.md"
JSONL = LOG / "juggle_autodrive.jsonl"

# Phase-1 legacy targets (kept for score_contacts compat)
N_BOUNCE = 4
PARK_AFTER = 4  # neutral default for park_hits; Phase-2 seeds raise it
CYL_R = 0.30
EPISODE_T = 4.0  # legacy contact-scoring window (score_contacts only)
VZ_MIN = 0.30
UP_MIN = 0.65
VXY_MAX = 1.10

# Phase-2 constants
DEFAULT_GATES = [[1.45, 0.50, 0.62], [2.85, 1.00, 0.72], [4.20, 1.55, 0.68], [5.55, 2.05, 0.76]]
WIN_ZOFF_DEFAULT = 1.10  # window center z = gate h + this (WINDOW_Z_GAP + WINDOW_HALF_HEIGHT)
P2_VZ_LOFT = 1.2  # contact counts as a loft if vz_out >= this
P2_UP_MIN = 0.35  # ... and upward ratio >= this (forward bounces are deliberately non-vertical)
# Drone window box (actuated_plant L763-768): |dx|<0.18, |dy|<WHW-0.28, |dz|<WHH-0.28
GATE_TOP_OFF = 1.90     # gate_top_z(h) = h + GATE_TOP_OFF (actuated_plant)
BALL_R = 0.06
WIN_BOX_DX = 0.18
WIN_BOX_DY = 0.64
WIN_BOX_DZ = 0.44
# A window thread only counts as RALLY progression if it happens within this many
# seconds of that gate's credited bounce contact — kills the fling-then-lap hack.
PAIR_MAX_LAG_S = 1.20
# ===== CURRICULUM (user directive 2026-07-22) =====
# STAGE A ("bounce"): master the motion FIRST — sustained HIGH bounces from hard
# opposing impact, drifting only SLIGHTLY forward. Gates and windows are ignored
# entirely. STAGE B ("rally"): once the motion is solid, thread the gate while the
# ball flies over (the CHAIN hard rule). Select with env JUGGLE_STAGE=bounce|rally.
JUGGLE_STAGE = os.environ.get("JUGGLE_STAGE", "rally").strip().lower()
# STAGE A rewards VERTICAL bounces off HARD impact. Forward travel is deliberately
# NOT rewarded — the user's point is that translation is trivially obtained later with
# a slight paddle tilt, so making the search chase it just corrupts the bounce.
# A Stage-A bounce only counts if it reaches LINTEL-CLEARING HEIGHT and is vertical.
# MEASURED 2026-07-22: the old bar (vz >= 3.20) was far too low — it rewarded SUSTAINING
# mediocre bounces (apex 1.90-2.34 m) when clearing a lintel needs ball-centre apex
# 2.58-2.72 m, i.e. vz ~4.7-4.9 m/s off a contact at z~1.4. The search optimised exactly
# the stated bar and plateaued 0.4 m short of usable, so the height-armed launch could
# never arm. vz 5.43 was observed once (apex ~2.9 m), so the target IS reachable.
HIGH_VZ = 4.60          # floor on vz_out
VERT_UP_MIN = 0.80      # ... and only counts as VERTICAL if vz/|v| >= this (near-straight-up)
APEX_CLEAR_MARGIN = 0.0 # extra height above the lintel required to count


@dataclass
class JuggleParams:
    dz_under: float = 0.34
    xy_kp: float = 5.0
    xy_kd: float = 2.8
    z_kp: float = 7.0
    z_kd: float = 3.5
    coll_bias: float = 0.0
    tip_flat_y: float = 0.0
    tip_flat_x: float = 0.0
    face_gain: float = 0.8
    max_xy_acc: float = 4.5
    blend: float = 0.60
    center_x: float = 0.0
    center_y: float = 0.0
    sep_s: float = 0.36
    sep_coll: float = 1.05  # ~hover during SEP (must not free-fall)
    remount_dz: float = 0.12  # extra drop during remount after sep
    sep_drop: float = 0.28  # target drop below hit altitude during SEP
    punch_gain: float = 1.55  # collective multiplier into the ball (visible loft)
    # --- Phase-2 fields. Defaults are Phase-1-NEUTRAL (behavior identical to old module). ---
    fwd_tip: float = 0.0      # paddle tip toward next-gate aim during punch (0 = pure vertical)
    adv_frac: float = 0.0     # per-hit advance of juggle center toward next-gate aim (0 = in place)
    loft_lead: float = 0.0    # aim this far beyond the gate x-plane
    dash_gain: float = 0.0    # SEP window-dash aggressiveness (0 = no dash)
    dash_z: float = 0.0       # RETIRED for altitude: thread/dash use window centre only (kept for JSON compat)
    punch_cap: float = 2.30   # collective cap multiplier during punch (2.30 = legacy clip)
    park_hits: float = 4.0    # park after this many hits (4 = legacy PARK_AFTER)
    fwd_after: float = 0.0    # forward mechanics (tip/advance/dash) arm only after this many hits
    # --- Per-gate CYCLE choreography (user directive 2026-07-22). Neutral defaults (cycle
    # off) so frozen demos are unchanged; the seed pool switches it on.
    #   settle taps (small forward advance, drone steps DOWN each impact) x (launch_hit-1),
    #   then a LAUNCH punch over the lintel on impact `launch_hit` (3rd or 4th),
    #   then thread that gate's window immediately, catch on the far side, repeat.
    cycle_on: float = 0.0     # >0.5 enables the per-gate cycle choreography
    launch_hit: float = 3.0   # which impact of the cycle is the LAUNCH (3rd or 4th)
    tap_adv: float = 0.10     # forward advance of the rally centre per SETTLE tap (small)
    tap_frac: float = 0.86    # settle-tap punch as a fraction of the launch punch (>=0.70; below that it dribbles)
    drop_per_hit: float = 0.12  # drone descends this much per impact -> arrives at window height
    catch_lead: float = 0.40  # how far past the gate plane to set up the far-side catch
    thread_s: float = 0.55    # seconds after the launch during which threading is forced
    # --- HARD-IMPACT rule (user directive 2026-07-22): the drone may only drive UP into
    # the ball while the ball is coming DOWN. Punching while the ball still rises makes
    # the racket follow it -> push / steady contact / dribble (measured: 385 contacts).
    base_z: float = 1.05       # ABSOLUTE ready altitude the drone returns to between bounces.
                               # Critical: the old hold anchored to `_hit_z` (the drone's z at the
                               # LAST impact), so it RATCHETED UPWARD — measured 1.34 -> 2.66 over
                               # 6 contacts, drone vz never negative between bounces, until it met
                               # the ball at its apex while the ball was still RISING and vz_out
                               # decayed 4.58 -> 0.00. Anchor the rest height absolutely instead.
    min_taps: float = 2.0        # at least this many settle taps before a launch is allowed
    launch_margin: float = 0.12  # ball apex must exceed the lintel by this much to ARM the launch
    launch_tip: float = 0.22     # forward paddle tilt applied on the LAUNCH impact only
    track_gain: float = 0.0    # LATERAL PURSUIT (ballistic intercept xy) — DEFAULT OFF.
                               # HYPOTHESIS DISPROVED 2026-07-22: swept 0.0/0.35/0.60/0.85 and
                               # `min n_high` stayed 1 at EVERY value; total went 16/14/12/16, i.e.
                               # tracking never fixed the two failing cases and 0.60 made things
                               # worse. It DID help nominal (3 -> 6 bounces at 0.85), so it is kept
                               # as a searchable DOF, but it is NOT the lost-ball fix.
                               # ACTUAL measured cause on edge_crosswind_a: the ball barely moves
                               # (x 0.00 -> 0.12, y 0.04 -> 0.16, wind only 0.05) — it is the DRONE
                               # that flies away, from (0.04,0.05) at t=0.82 to (-1.15,1.66) at
                               # t=1.44, abandoning a nearly STATIONARY ball. Chase that, not drift.
                               # how strongly the drone flies to where the
                               # ball will actually COME DOWN (ballistic intercept xy) instead of
                               # holding a slowly-advancing rally centre. Measured need: on
                               # edge_crosswind_a the drone lands ONE perfect 5.43 m/s strike then
                               # the crosswind carries the ball laterally out of reach and it is
                               # never touched again — a lost-ball failure, not a bad bounce.
    arrest_coll: float = 0.32  # collective (x hover) used to ARREST the drone's own upward
                               # coast right after a punch. MEASURED: the punch drives the DRONE
                               # to +1.89 m/s; the hold's 0.88*hs floor only decelerates at 0.12g
                               # (1.6 s to stop) but the ball returns in 0.64 s — so the drone was
                               # still climbing at every subsequent contact and ratcheted from
                               # racket_z 1.34 -> 2.66, vz_out decaying 4.58 -> 0.00.
                               # 0.32*hs gives ~0.68g down: kills 1.9 m/s in ~0.28 s.
    impact_bvz: float = -0.15  # ball vz must be BELOW this (descending) to allow a punch
    fall_away: float = 0.0     # drop-away on a rising ball. MEASURED HARMFUL at 0.55:
                               # the drone plummets after each hit and is FALLING at the
                               # next contact — the opposite of 'drone up while ball down'.
                               # Left searchable but defaults OFF; timing is the real lever.


class JugglePolicy:
    """Flat-face hover-under-ball juggler; Phase-2 adds forward rally over the gate line."""

    def __init__(self, params: JuggleParams | None = None):
        self.p = params or JuggleParams()
        self.g = 9.81
        self.rot_min = 0.0
        self.rot_max = 13.0
        self.hover = np.ones(4) * 3.25
        self.mass = 1.5
        self.last_cmd = self.hover.copy()
        self.int_xy = np.zeros(2)
        self._ball = np.array([0.0, 0.0, 1.72])
        self._ball_v = np.zeros(3)
        self._sep_until = -1e9
        self._prev_close = False
        self._hit_count = 0
        self._last_hit_t = -1e9
        self._hit_z = 1.0
        self._parked = False
        self._want_park = False
        self._punch_until = -1e9
        self._cycle_hits = 0
        self._launched = False
        self._launch_pending = False
        self._thread_until = -1e9
        self.gates = np.asarray(DEFAULT_GATES, float)
        self.tgt = np.array([6.9, 2.55, 0.0])
        self.gi = 0
        self._window_seen = [False, False, False, False]
        self._win_zoff = WIN_ZOFF_DEFAULT
        self._touch_since = -1e9
        self._p2 = False
        xs = np.array([-0.14, -0.14, 0.14, 0.14])
        ys = np.array([-0.18, 0.18, 0.18, -0.18])
        yaw = np.array([-0.0201, 0.0201, -0.0201, 0.0201])
        A = np.zeros((4, 4))
        A[0, :] = 1.0
        A[1, :] = ys
        A[2, :] = -xs
        A[3, :] = yaw
        self.Ainv = np.linalg.inv(A)

    def reset(self, info=None):
        info = info or {}
        self.hover = np.clip(np.asarray(info.get("hover_rotor_thrusts", self.hover), float).reshape(4), 0.5, 12.0)
        self.mass = float(np.clip(np.sum(self.hover) / self.g, 0.8, 2.2))
        self.last_cmd = self.hover.copy()
        self.int_xy = np.zeros(2)
        self._ball = np.array([0.0, 0.0, 1.72])
        self._ball_v = np.zeros(3)
        self.cx = float(self.p.center_x)
        self.cy = float(self.p.center_y)
        self._sep_until = -1e9
        self._prev_close = False
        self._hit_count = 0
        self._last_hit_t = -1e9
        self._hit_z = 1.0
        self._parked = False
        self._want_park = False
        self._punch_until = -1e9
        self._cycle_hits = 0
        self._launched = False
        self._launch_pending = False
        self._thread_until = -1e9
        self.gi = 0
        self._window_seen = [False, False, False, False]
        try:
            g = info.get("gates")
            if g is not None:
                self.gates = np.asarray(g, float).reshape(4, 3)
        except Exception:
            pass
        try:
            t = info.get("target")
            if t is not None:
                tv = np.asarray(t, float).reshape(-1)
                if tv.size >= 2:
                    self.tgt = np.array([float(tv[0]), float(tv[1]), 0.0])
        except Exception:
            pass
        try:
            self._win_zoff = float(info.get("window_center_z_offset") or WIN_ZOFF_DEFAULT)
        except Exception:
            self._win_zoff = WIN_ZOFF_DEFAULT
        self._touch_since = -1e9
        p = self.p
        self._p2 = bool(
            float(p.adv_frac) > 1e-6
            or float(p.fwd_tip) > 1e-6
            or float(p.dash_gain) > 0.05
            or float(p.park_hits) > 4.5
        )

    def _vec(self, x, n, d):
        try:
            a = np.asarray(x, float).reshape(-1)
            if a.size != n or not np.all(np.isfinite(a)):
                return np.asarray(d, float).reshape(n).copy()
            return a.copy()
        except Exception:
            return np.asarray(d, float).reshape(n).copy()

    def _quat_to_R(self, q):
        q = self._vec(q, 4, np.array([1.0, 0.0, 0.0, 0.0]))
        n = float(np.linalg.norm(q))
        w, x, y, z = (1.0, 0.0, 0.0, 0.0) if n < 1e-9 else tuple(q / n)
        return np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ],
            float,
        )

    def _vee(self, Rd, Rmat):
        E = Rd.T @ Rmat - Rmat.T @ Rd
        return 0.5 * np.array([E[2, 1], E[0, 2], E[1, 0]], float)

    def _mix(self, coll, torq):
        u = self.Ainv @ np.array([float(coll), float(torq[0]), float(torq[1]), float(torq[2])])
        if not np.all(np.isfinite(u)):
            u = self.hover.copy()
        return np.clip(u, self.rot_min, self.rot_max)

    def _clip_norm(self, v, m):
        v = np.asarray(v, float)
        n = float(np.linalg.norm(v))
        return v * (m / n) if n > m > 0 else v

    def _aim_xy(self):
        if self.gi < 4:
            return (
                float(self.gates[self.gi][0]) + float(self.p.loft_lead),
                float(self.gates[self.gi][1]),
            )
        return float(self.tgt[0]), float(self.tgt[1])

    def act(self, obs):
        p = self.p
        dp = self._vec(obs.get("drone_pos", [0, 0, 1]), 3, np.array([0.0, 0.0, 1.0]))
        dv = self._vec(obs.get("drone_linvel", [0, 0, 0]), 3, np.zeros(3))
        q = self._vec(obs.get("drone_quat", [1, 0, 0, 0]), 4, np.array([1.0, 0.0, 0.0, 0.0]))
        om = self._vec(obs.get("drone_angvel", [0, 0, 0]), 3, np.zeros(3))
        dt = float(np.clip(float(obs.get("dt", 0.01) or 0.01), 0.002, 0.05))
        rp = self._vec(obs.get("racket_pos", dp + np.array([0, 0, 0.2])), 3, dp + np.array([0.0, 0.0, 0.2]))
        rn = self._vec(obs.get("racket_normal", [0, 0, 1]), 3, np.array([0.0, 0.0, 1.0]))

        if bool(obs.get("ball_visible", False)):
            self._ball = self._vec(obs.get("ball_pos", self._ball), 3, self._ball)
            self._ball_v = self._vec(obs.get("ball_vel", self._ball_v), 3, self._ball_v)
            age = float(obs.get("ball_observation_age_s", 0.0) or 0.0)
            # Lead delayed ball so proximity SEP isn't late.
            bp = self._ball + self._ball_v * max(0.0, age + 0.02)
            bv = self._ball_v
        else:
            self._ball = self._ball + self._ball_v * dt + np.array([0.0, 0.0, -0.5 * self.g * dt * dt])
            self._ball_v = self._ball_v + np.array([0.0, 0.0, -self.g * dt])
            bp, bv = self._ball, self._ball_v

        t = float(obs.get("time", 0.0))
        hs = float(np.sum(self.hover))

        # Policy-local window state drives the compliant gate FSM even when telemetry
        # is disabled (for example, a directly instantiated policy outside search).
        for i in range(4):
            gx, gy, gh = [float(v) for v in self.gates[i]]
            zc = gh + float(self._win_zoff)
            if (
                abs(float(dp[0]) - gx) < WIN_BOX_DX
                and abs(float(dp[1]) - gy) < WIN_BOX_DY
                and abs(float(dp[2]) - zc) < WIN_BOX_DZ
            ):
                self._window_seen[i] = True

        # Phase-2 telemetry (only present on search-generated subclasses; frozen demos skip).
        tel = getattr(type(self), "_telem", None)
        if tel is not None:
            if float(dp[0]) > tel["max_dx"]:
                tel["max_dx"] = float(dp[0])
            wm = tel["win_miss"]
            for i in range(4):
                gx, gy, gh = float(self.gates[i][0]), float(self.gates[i][1]), float(self.gates[i][2])
                zc = gh + float(self._win_zoff)
                d = math.sqrt(
                    (float(dp[0]) - gx) ** 2
                    + (float(dp[1]) - gy) ** 2
                    + (float(dp[2]) - zc) ** 2
                )
                if d < wm[i]:
                    wm[i] = d
                inside = (
                    abs(float(dp[0]) - gx) < WIN_BOX_DX
                    and abs(float(dp[1]) - gy) < WIN_BOX_DY
                    and abs(float(dp[2]) - zc) < WIN_BOX_DZ
                )
                # Record every distinct entry. A pre-bounce entry cannot satisfy a
                # causal pair, but a later legitimate re-entry still can.
                if tel.get("win_times") is not None and tel.get("win_inside") is not None:
                    if inside and not tel["win_inside"][i]:
                        self._window_seen[i] = True
                        tel["win_t"][i] = t
                        tel["win_times"][i].append(t)
                    tel["win_inside"][i] = inside
                elif inside and tel.get("win_t") is not None and tel["win_t"][i] is None:
                    self._window_seen[i] = True
                    tel["win_t"][i] = t

        # In cycle mode, the active gate is not complete when the ball crosses it:
        # the drone must still thread THAT SAME window. Advancing immediately made
        # the thread branch target gate i+1 and reset the launch state, structurally
        # preventing the intended launch -> same-window -> far-side catch sequence.
        while self.gi < 4 and float(bp[0]) > float(self.gates[self.gi][0]) + 0.08:
            if float(p.cycle_on) > 0.5 and not self._window_seen[self.gi]:
                break
            self.gi += 1
            # New gate cycle: settle taps restart, launch re-arms, drone re-climbs.
            self._cycle_hits = 0
            self._launched = False
            self._launch_pending = False
            self._thread_until = -1e9

        def _hold_xy_z(z_des: float, tip_scale: float = 1.0):
            tip = np.array([
                float(np.clip(tip_scale * 1.4 * (self.cx - dp[0]), -0.55, 0.55)),
                float(np.clip(tip_scale * 1.4 * (self.cy - dp[1]), -0.55, 0.55)),
                0.0,
            ])
            z_des = max(0.78, float(z_des))
            coll = float(p.sep_coll) * hs + 5.5 * (z_des - float(dp[2])) - 2.2 * float(dv[2])
            coll = float(np.clip(coll, 0.88 * hs, 1.55 * hs))
            u = self._mix(coll, tip)
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]

        def _hold_at(x_des, y_des, z_des, tip_lim=0.35):
            tip = np.array([
                float(np.clip(1.2 * (float(x_des) - dp[0]), -tip_lim, tip_lim)),
                float(np.clip(1.2 * (float(y_des) - dp[1]), -tip_lim, tip_lim)),
                0.0,
            ])
            z_des = max(0.85, float(z_des))
            coll = 1.10 * hs + 6.5 * (z_des - float(dp[2])) - 2.5 * float(dv[2])
            coll = float(np.clip(coll, 0.98 * hs, 1.55 * hs))
            u = self._mix(coll, tip)
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]

        def _intercept_xy(strike_z):
            # Where will the ball be when it descends to strike height? Under wind/offsets the
            # ball drifts, so holding a static rally centre loses it. Predict and go there.
            try:
                dzb = float(bp[2]) - float(strike_z)
                vzb = float(bv[2])
                disc = vzb * vzb + 2.0 * self.g * max(0.0, dzb)
                if disc <= 0.0:
                    return float(bp[0]), float(bp[1])
                tf = (vzb + math.sqrt(disc)) / self.g
                tf = float(np.clip(tf, 0.0, 1.50))
                return float(bp[0]) + float(bv[0]) * tf, float(bp[1]) + float(bv[1]) * tf
            except Exception:
                return float(bp[0]), float(bp[1])

        def _track_xy(strike_z, base_x, base_y):
            g_ = float(np.clip(p.track_gain, 0.0, 1.0))
            if g_ <= 1e-6:
                return float(base_x), float(base_y)
            ix, iy = _intercept_xy(strike_z)
            return (1.0 - g_) * float(base_x) + g_ * ix, (1.0 - g_) * float(base_y) + g_ * iy

        def _cyc():
            return float(p.cycle_on) > 0.5

        def _win_zc(gi=None):
            # Natural window-centre altitude only. After settle-tap step-downs the
            # drone is already at this height; the thread is a forward tilt/thrust
            # with NO altitude change. Do not add dash_z — that caused an unnecessary
            # climb during the gate thread (user directive 2026-07-22).
            k = int(self.gi if gi is None else gi)
            if k >= 4:
                return None
            return float(self.gates[k][2]) + float(self._win_zoff)

        def _lintel_need():
            # Ball-centre height required to clear the next gate's lintel.
            if self.gi >= 4:
                return None
            return float(self.gates[int(self.gi)][2]) + GATE_TOP_OFF + BALL_R + float(p.launch_margin)

        def _ball_apex():
            # Apex the ball will reach on its CURRENT flight.
            return float(bp[2]) + (max(0.0, float(bv[2])) ** 2) / (2.0 * self.g)

        def _launch_now():
            # HEIGHT-ARMED LAUNCH (user directive 2026-07-22): keep bouncing VERTICALLY until
            # the ball is already flying high enough to clear the lintel, and only THEN convert
            # that height into forward travel with a slight paddle tilt on the next impact.
            # This is why the launch does not need a bigger hit — the height is already paid for
            # by the vertical rally; the tilt only redirects it.
            if not _cyc() or self._launched:
                return False
            if self._cycle_hits < int(round(float(np.clip(p.min_taps, 1.0, 6.0)))):
                return False      # "bounce at least twice" first
            need = _lintel_need()
            if need is None:
                return False
            if _ball_apex() >= need:
                # Only launch if the ball is at least partway toward the gate — launching
                # when the ball has zero forward position (e.g. edge_crosswind_a: x=0.09
                # vs gate at x=1.45) makes the drone thread a window the ball will never
                # reach, wasting the rally.
                gx = float(self.gates[int(self.gi)][0]) if int(self.gi) < 4 else 5.55
                if float(bp[0]) < gx * 0.20:
                    return False
                return True
            # fallback: don't stall forever if height is never reached
            n = int(round(float(np.clip(p.launch_hit, 2.0, 6.0))))
            return (self._cycle_hits + 1) >= n

        def _fwd_armed():
            # Rally must stabilize before forward play (handoff: "tip only after bounce looks solid").
            return self._hit_count >= max(0, int(round(float(p.fwd_after))))

        def _next_frame_ahead():
            # First gate frame whose x-plane lies ahead of the DRONE (drone may lag the ball's gi).
            for k in range(4):
                if float(dp[0]) < float(self.gates[k][0]) - 0.02:
                    return k
            return 4

        def _dash_cmd():
            # During ball free-flight: fly forward through the window of the frame ahead of the drone.
            dg = float(p.dash_gain)
            if dg <= 0.05 or self._want_park or not _fwd_armed():
                return None
            ki = _next_frame_ahead()
            if ki >= 4 or self.gi >= 4:
                return None
            gx, gy, gh = [float(v) for v in self.gates[ki]]
            if float(bp[0]) < gx - 0.15:
                return None  # ball not past the frame yet — dashing now would intercept its arc (carry crash)
            ahead = gx - float(dp[0])
            if ahead >= 1.6:
                return None  # too far to make it this flight
            zc = gh + float(self._win_zoff)  # window centre; no dash_z climb
            tx = min(gx + 0.35, float(dp[0]) + 1.25)
            return _hold_at(tx, gy, zc, tip_lim=0.18 + 0.30 * float(np.clip(dg, 0.0, 1.0)))

        def _cross_guard(x_tgt):
            # Never chase forward through a gate frame at low altitude: any pending x-crossing
            # is routed through that frame's window box (the only safe opening).
            if not _fwd_armed():
                return None
            ki = _next_frame_ahead()
            if ki >= 4:
                return None
            gx, gy, gh = [float(v) for v in self.gates[ki]]
            if float(bp[0]) < gx - 0.15 or float(x_tgt) <= gx - 0.30:
                return None  # only thread once the BALL is past the plane; drone follows under its arc
            zc = gh + float(self._win_zoff)  # window centre; no dash_z climb
            if (gx - float(dp[0])) < 0.60:
                return _hold_at(gx + 0.35, gy, zc, tip_lim=0.30)  # thread it
            return _hold_at(min(gx - 0.10, float(dp[0]) + 1.0), gy, zc, tip_lim=0.26)  # approach at window height

        # PREDICTIVE ANTI-DIVE: if the drone will be below 0.65m within 0.40s at
        # current descent rate, arrest immediately. Catches crash trajectories early
        # (from post-thread descent or failed-catch dive) without blocking the normal
        # descent needed to reach base_z after threading a window.
        _z_pred = float(dp[2]) + float(dv[2]) * 0.40
        if _z_pred < 0.65 and float(dv[2]) < -0.3:
            return _hold_at(float(self.cx), float(self.cy), max(0.95, float(dp[2]) + 0.10), tip_lim=0.10)

        # BALL-GROUNDED SAFETY (last resort): ball on the ground, hover safely.
        if float(bp[2]) < 0.15 and self._hit_count >= 1 and not self._parked:
            return _hold_at(float(self.cx), float(self.cy), max(0.95, float(dp[2])), tip_lim=0.10)

        # Permanent park after park_hits bounces — drop clear then hold.
        if self._parked:
            return _hold_at(float(self.cx), float(self.cy), 0.92, tip_lim=0.08)

        # If we're done juggling, finish SEP then park — never re-engage.
        if getattr(self, "_want_park", False) and t >= float(self._sep_until):
            self._parked = True
            return _hold_at(float(self.cx), float(self.cy), 0.95, tip_lim=0.08)

        # Proximity-based contact → SEP.
        dxy = float(math.hypot(float(bp[0]) - float(rp[0]), float(bp[1]) - float(rp[1])))
        dz = float(bp[2] - rp[2])
        contactish = dxy < 0.30 and -0.05 < dz < 0.28
        # Phase-2 anti-carry: a ball riding the racket destabilizes the drone (asymmetric
        # load → sideways drift → flip). If contact persists, shake off decisively.
        if contactish:
            if self._touch_since < -1e8:
                self._touch_since = t
        else:
            self._touch_since = -1e9
        if self._p2 and self._touch_since > -1e8 and (t - self._touch_since) > 0.30 and not self._want_park and not self._parked:
            self._touch_since = -1e9
            self._sep_until = t + 0.40
            self._hit_z = float(dp[2]) - 0.15  # bias the SEP hold lower — get out from under the ball
            tip = np.zeros(3)
            coll = 0.80 * hs
            u = self._mix(coll, tip)
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]
        if (not getattr(self, "_want_park", False)) and contactish and (t - float(self._last_hit_t)) > 0.34 and t > float(self._sep_until):
            self._sep_until = t + max(0.30, float(p.sep_s))
            self._hit_z = float(dp[2])
            self._hit_count += 1
            self._cycle_hits += 1
            self._last_hit_t = t
            if _cyc():
                n_launch = int(round(float(np.clip(p.launch_hit, 2.0, 5.0))))
                if (not self._launched) and (self._launch_pending or self._cycle_hits >= n_launch):
                    # That impact WAS the launch -> thread this gate's window immediately.
                    self._launched = True
                    self._launch_pending = False
                    self._thread_until = t + max(0.20, float(p.thread_s))
            # Phase-2: walk the rally center toward (then past) the next gate, or to the target.
            _adv = float(p.adv_frac)
            if _cyc():
                # Settle taps creep forward; the launch tap commits toward the gate.
                _adv = float(p.tap_adv) if not self._launched else max(float(p.adv_frac), 0.35)
            if _adv > 1e-6 and self._hit_count >= max(0, int(round(float(p.fwd_after)))):
                ax, ay = self._aim_xy()
                a = float(np.clip(_adv, 0.0, 0.9))
                self.cx += a * float(np.clip(ax - self.cx, -1.0, 1.0))
                self.cy += a * float(np.clip(ay - self.cy, -0.8, 0.8))
            park_n = max(1, int(round(float(p.park_hits))))
            if self._hit_count >= park_n:
                self._want_park = True
            # Cut thrust immediately — create visible air gap under rising ball.
            tip = np.zeros(3)
            coll = 0.88 * hs + 4.0 * (0.80 - float(dp[2]))
            coll = float(np.clip(coll, 0.75 * hs, 1.30 * hs))
            u = self._mix(coll, tip)
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]

        # Immediately after the launch tap, thread THIS gate's window while the ball
        # arcs over the lintel above — then continue to the far side to catch it.
        if _cyc() and self._launched and t < float(self._thread_until) and self.gi < 4:
            _gx, _gy, _gh = [float(v) for v in self.gates[int(self.gi)]]
            _zc = _win_zc()
            if _zc is not None:
                return _hold_at(_gx + float(p.catch_lead), _gy, _zc, tip_lim=0.34)

        if t < float(self._sep_until):
            # ARREST: the punch launches the DRONE upward too, and it must shed that before the
            # ball comes back or the next contact happens while it is still climbing (push, not
            # impact). Cut collective hard until the upward coast is killed.
            if float(dv[2]) > 0.15:
                coll = float(np.clip(float(p.arrest_coll), 0.10, 0.95)) * hs
                u = self._mix(coll, np.zeros(3))
                self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
                return [float(x) for x in self.last_cmd]
            age = t - (float(self._sep_until) - max(0.30, float(p.sep_s)))
            # Return to the ABSOLUTE ready altitude (never a delta off the last hit — that
            # ratchets the drone up until it is at the ball's apex and cannot impact hard).
            z_hold = max(0.82, min(float(p.base_z),
                                   float(getattr(self, "_hit_z", float(dp[2]))) - max(0.22, float(p.sep_drop))))
            if age < 0.14:
                tip = np.zeros(3)
                coll = 0.90 * hs + 5.0 * (z_hold - float(dp[2]))
                coll = float(np.clip(coll, 0.80 * hs, 1.35 * hs))
                u = self._mix(coll, tip)
                self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
                return [float(x) for x in self.last_cmd]
            c = _dash_cmd()
            if c is not None:
                return c
            _tx, _ty = _track_xy(float(p.base_z) + float(p.dz_under), float(self.cx), float(self.cy))
            self.cx += 0.35 * float(np.clip(_tx - self.cx, -0.6, 0.6))
            self.cy += 0.35 * float(np.clip(_ty - self.cy, -0.6, 0.6))
            return _hold_xy_z(z_hold, tip_scale=0.05)

        # Ball RISING while close overhead -> never climb with it; sink clear so the next
        # contact is a fresh opposing impact rather than a carry.
        if float(p.fall_away) > 0.02 and float(bv[2]) > 0.05 and dz < 0.75 and not self._parked:
            coll = float(np.clip(1.0 - float(np.clip(p.fall_away, 0.0, 0.9)), 0.15, 1.0)) * hs
            u = self._mix(coll, np.zeros(3))
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]

        # Wait for clear separation + falling ball before remount.
        if float(bv[2]) > 0.0 or dz < 0.38:
            c = _dash_cmd()
            if c is None:
                c = _cross_guard(max(float(self.cx), float(bp[0])))
            if c is not None:
                return c
            z_hold = min(float(bp[2]) - 0.65, float(p.base_z),
                         float(getattr(self, "_hit_z", 1.0)) - max(0.32, float(p.sep_drop)))
            return _hold_xy_z(z_hold, tip_scale=0.08)

        # Remount under ball.
        _bx = 0.50 * float(bp[0]) + 0.50 * float(self.cx)
        _by = 0.50 * float(bp[1]) + 0.50 * float(self.cy)
        # LATERAL PURSUIT: fly to where the ball will actually come down.
        x_des, y_des = _track_xy(float(dp[2]) + float(p.dz_under), _bx, _by)
        extra = float(p.remount_dz) if (t < float(self._sep_until) + 0.40) else 0.0
        z_des = float(bp[2]) - float(p.dz_under) - extra - (float(rp[2]) - float(dp[2]))
        # Cap the remount at the ready altitude while the ball is still high: rise to MEET
        # the descending ball from below rather than climbing to follow it up.
        if float(bv[2]) > -0.05 and float(bp[2]) > float(p.base_z) + float(p.dz_under):
            z_des = min(z_des, float(p.base_z))
        z_des = max(0.82, z_des)
        if _cyc():
            # Drone steps DOWN a little on each impact of the cycle so that by the launch
            # tap it is already level with the open window and threads it as a continuation
            # of the motion. TWO HARD CONSTRAINTS (learned the hard way — violating either
            # turns the rally into a 385-contact dribble):
            #   (a) the step-down is BOUNDED (cycle_hits is unbounded when no gate clears);
            #   (b) it may never raise the racket to/above the ball — the racket must stay
            #       UNDER the ball or contact becomes a continuous carry instead of a bounce.
            _zc = _win_zc()
            _steps = int(np.clip(self._cycle_hits, 0, max(1, int(round(float(p.launch_hit))))))
            z_des = z_des - float(p.drop_per_hit) * float(_steps)
            if _zc is not None:
                z_des = max(z_des, _zc - 0.10)
            # never above the safe under-ball altitude
            _z_safe = float(bp[2]) - float(p.dz_under) - (float(rp[2]) - float(dp[2]))
            z_des = min(z_des, _z_safe)
            z_des = max(0.82, z_des)

        # Rising punch into the ball — tall loft (Phase-2: tipped toward the next gate for +vx).
        # HARD IMPACT ONLY: ball must be DESCENDING. The old threshold (+0.40) allowed a
        # punch while the ball was still RISING, so the racket chased it upward and rode
        # it — that is the push/steady-contact dribble. Opposing motion = clean impulse.
        _ibvz = float(np.clip(float(p.impact_bvz), -1.20, -0.02))
        approaching = 0.12 < dz < 0.58 and float(bv[2]) < _ibvz and dxy < 0.32
        if approaching or t < float(getattr(self, "_punch_until", -1e9)):
            if approaching and t >= float(getattr(self, "_punch_until", -1e9)):
                self._punch_until = t + 0.12
            tipx = float(np.clip(0.9 * (x_des - dp[0]), -0.14, 0.14))
            tipy = float(np.clip(0.9 * (y_des - dp[1]), -0.14, 0.14))
            ft = float(p.fwd_tip)
            if _cyc() and _launch_now():
                # LAUNCH impact: tilt forward to send the (already high enough) ball over the
                # lintel. Settle taps deliberately keep ft small so they stay vertical.
                ft = max(ft, float(np.clip(p.launch_tip, 0.0, 0.60)))
            if ft > 1e-6 and self._hit_count >= max(0, int(round(float(p.fwd_after)))):
                ax, ay = self._aim_xy()
                vx_, vy_ = ax - float(dp[0]), ay - float(dp[1])
                nrm = math.hypot(vx_, vy_) + 1e-9
                tipx += float(np.clip(ft * vx_ / nrm, -0.42, 0.42))
                tipy += float(np.clip(ft * vy_ / nrm, -0.42, 0.42))
            tip = np.array([tipx, tipy, 0.0])
            cap = float(np.clip(float(p.punch_cap), 2.30, 2.90))
            pg_hi = 2.25 if cap <= 2.3000001 else cap
            pg = float(np.clip(float(p.punch_gain), 1.25, pg_hi))
            _is_launch = _launch_now()
            if approaching and _is_launch:
                # Preserve the height-armed decision across the few control ticks
                # between punch initiation and physics contact.
                self._launch_pending = True
            _lo = 1.25 * hs   # NEVER go below this or the tap dribbles instead of bouncing
            if _cyc() and not _is_launch:
                # SETTLE TAP: a REAL bounce (distinct contact, clean separation) that is
                # simply lower than the launch — enough to keep the ball alive and creeping
                # forward, not enough to clear the lintel. Scaling the punch below ~1.25*hs
                # makes the racket ride the ball (385-contact dribble), so tap_frac only
                # trims the punch, it never softens it into a carry.
                pg = pg * float(np.clip(p.tap_frac, 0.70, 0.97))
                tip = np.array([tipx * 0.55, tipy * 0.55, 0.0])
            coll = pg * hs + 6.0 * max(0.0, 0.25 - float(dv[2]))
            _cap_eff = cap if (not _cyc() or _is_launch) else cap * float(np.clip(p.tap_frac, 0.70, 0.97))
            coll = float(np.clip(coll, _lo, max(_cap_eff, 1.30) * hs))
            u = self._mix(coll, tip)
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]
        c = _cross_guard(x_des)
        if c is not None:
            return c
        # Never ram a frame while the ball is still on this side of it.
        if _fwd_armed():
            ki = _next_frame_ahead()
            if ki < 4:
                gxk = float(self.gates[ki][0])
                if float(bp[0]) < gxk - 0.15:
                    x_des = min(x_des, gxk - 0.45)
        return _hold_at(x_des, y_des, z_des, tip_lim=0.12)


def score_contacts(result: dict, cx: float, cy: float) -> dict:
    """Legacy Phase-1 in-place scoring (kept for frozen-demo / old-snippet compat)."""
    evs = result.get("contact_events_debug") or []
    verts = []
    max_r = 0.0
    for e in evs:
        t = float(e.get("end", e.get("start", 0.0)))
        if t > EPISODE_T:
            continue
        vo = np.asarray(e.get("vel_out", [0, 0, 0]), float)
        po = np.asarray(e.get("pos_out", [0, 0, 0]), float)
        vz = float(e.get("vz_out", vo[2] if vo.size >= 3 else 0.0))
        vxy = float(np.linalg.norm(vo[:2]))
        sp = float(np.linalg.norm(vo)) + 1e-9
        up = max(0.0, vz) / sp
        r = float(math.hypot(float(po[0]) - cx, float(po[1]) - cy))
        ok = vz >= VZ_MIN and up >= UP_MIN and vxy <= VXY_MAX and r <= CYL_R
        if ok:
            if verts and (t - verts[-1]["t"]) < 0.12:
                continue  # debounce chatter into one bounce
            max_r = max(max_r, r)
            verts.append({"t": t, "vz": vz, "up": up, "vxy": vxy, "r": r})
    n = len(verts)
    mean_up = float(np.mean([v["up"] for v in verts])) if verts else 0.0
    mean_vz = float(np.mean([v["vz"] for v in verts])) if verts else 0.0
    crash = 1 if result.get("drone_crash") else 0
    t_cut = (verts[-1]["t"] + 0.45) if verts else EPISODE_T
    n_all = len([e for e in evs if float(e.get("end", 0)) <= t_cut])
    chatter_pen = max(0, n_all - 10) * 0.05
    succ = 1 if (n >= N_BOUNCE and crash == 0 and n_all <= 48 and max_r <= CYL_R) else 0
    fit = (
        succ,
        (mean_vz if crash == 0 else -1.0),
        (n if crash == 0 else -1),
        mean_up,
        -max_r - chatter_pen,
        -n_all,
    )
    return {
        "fit": fit,
        "n_vert": n,
        "mean_up": mean_up,
        "mean_vz": mean_vz,
        "max_r": max_r,
        "verts": verts,
        "n_contact": n_all,
        "success": bool(succ),
    }


def score_phase2(result: dict, telem: dict | None, gates=None) -> dict:
    """Rank by the real scorer's levers: bg, wins, then no-crash, plant score, shaped progress.

    gates: true per-episode 4x3 gate array (from scenario_to_arrays). The summary's
    "scenario" dict holds jitter magnitudes, NOT resolved gates. Gate x is never
    jittered, so the DEFAULT_GATES fallback is safe for the x-based shaping.
    """
    bg = int(result.get("bounced_gate_passes") or 0)
    wins = int(result.get("drone_windows_passed") or 0)
    plant = float(result.get("score") or 0.0)
    crash = 1 if result.get("drone_crash") else 0
    try:
        gates = np.asarray(gates if gates is not None else DEFAULT_GATES, float).reshape(4, 3)
    except Exception:
        gates = np.asarray(DEFAULT_GATES, float)

    bp_list = list(result.get("bounced_gate_pass") or [False] * 4)[:4]
    while len(bp_list) < 4:
        bp_list.append(False)
    wp_list = list(result.get("drone_window_pass") or [False] * 4)[:4]
    while len(wp_list) < 4:
        wp_list.append(False)
    win_t = list((telem or {}).get("win_t") or [None] * 4)[:4]
    while len(win_t) < 4:
        win_t.append(None)
    win_times = list((telem or {}).get("win_times") or [[] for _ in range(4)])[:4]
    while len(win_times) < 4:
        win_times.append([])
    bt = list(result.get("gate_bounce_contact_times_s") or [None] * 4)[:4]
    while len(bt) < 4:
        bt.append(None)

    # ===== HARD RULE (user directive 2026-07-22) =====
    # A gate counts ONLY if BOTH its lintel was bounced AND the drone threaded THAT
    # SAME gate's window (time-coupled within PAIR_MAX_LAG_S). Credit is a STRICT
    # SEQUENTIAL PREFIX anchored at gate 1: if gate k's bounce OR window is skipped
    # or missed, NOTHING from gate k onward earns any reward. No out-of-order credit.
    # Harsher than a plain pair-count: the render at 20260722T054500Z paired gate 2
    # but never threaded gate 1's window -> chain=0 despite pairs=1.
    def _pair_ok(i):
        if not (bool(bp_list[i]) and bool(wp_list[i])):
            return False
        if bt[i] is None:
            return False
        candidates = list(win_times[i] or [])
        if win_t[i] is not None:
            candidates.append(win_t[i])
        return any(0.0 <= float(wt) - float(bt[i]) <= PAIR_MAX_LAG_S for wt in candidates)

    chain = 0
    for i in range(4):
        if _pair_ok(i):
            chain += 1
        else:
            break
    pairs = chain  # only prefix-anchored progress is ever reported/rewarded
    # Shaping targets the FIRST INCOMPLETE PAIR, so the search is pushed to finish
    # gate `chain`'s bounce AND window before it gets any credit for later gates.
    next_gi = chain

    evs = result.get("contact_events_debug") or []
    lofts = []
    max_bx = 0.0
    for e in evs:
        vo = np.asarray(e.get("vel_out", [0, 0, 0]), float).reshape(-1)
        po = np.asarray(e.get("pos_out", [0, 0, 0]), float).reshape(-1)
        vz = float(e.get("vz_out", vo[2] if vo.size >= 3 else 0.0))
        sp = float(np.linalg.norm(vo)) + 1e-9
        up = max(0.0, vz) / sp
        if po.size >= 1:
            max_bx = max(max_bx, float(po[0]))
        t = float(e.get("end", e.get("start", 0.0)))
        if vz >= P2_VZ_LOFT and up >= P2_UP_MIN:
            if lofts and (t - lofts[-1]["t"]) < 0.12:
                continue
            _cz = float(po[2]) if po.size >= 3 else 1.40
            lofts.append({"t": t, "vz": vz, "up": up, "apex": _cz + (vz * vz) / (2.0 * 9.81)})
    fb = result.get("final_ball_pos") or [0, 0, 0]
    max_bx = max(max_bx, float(fb[0]))
    n_all = len(evs)
    best_vz = max([l["vz"] for l in lofts], default=0.0)

    wm_all = [round(float(x), 3) for x in ((telem or {}).get("win_miss") or [9.0] * 4)]
    if next_gi >= 4:
        s_gate = 1.0
        s_win = 1.0
    else:
        gx = float(gates[next_gi][0])
        gcl = result.get("gate_closest") or [None] * 4
        gc = gcl[next_gi] if next_gi < len(gcl) else None
        if gc:
            xdist = abs(float(gc.get("ball_x", 0.0)) - gx)
            clear = float(gc.get("over_top_clearance_m", gc.get("ball_bottom_over_gate_top_clearance_m", -2.2)))
        else:
            xdist, clear = gx, -2.2
        s_reach = 1.0 - float(np.clip(xdist / 2.0, 0.0, 1.0))
        s_clear = float(np.clip((clear + 2.2) / 2.3, 0.0, 1.0))
        s_gate = 0.6 * s_reach + 0.4 * s_clear * s_reach
        s_win = 1.0 - float(np.clip(float(wm_all[next_gi]) / 2.5, 0.0, 1.0))
    s_loft = float(np.clip(best_vz / 5.6, 0.0, 1.0))
    # HARD RULE: do NOT reward raw forward travel — flinging the ball down the course
    # past unpaired gates is precisely the policy_v230 dead end. Travel only counts up
    # to just beyond the CURRENT chain gate; anything further is worth nothing.
    _travel_cap = float(gates[min(next_gi, 3)][0]) + 0.60 if next_gi < 4 else 5.85
    s_travel = float(np.clip(max_bx / max(_travel_cap, 1e-6), 0.0, 1.0))
    s_nb = float(np.clip(len(lofts) / 6.0, 0.0, 1.0))
    # Weight the pair components (gate clearance + window proximity) most heavily.
    shape = 0.34 * s_gate + 0.34 * s_win + 0.14 * s_loft + 0.08 * s_travel + 0.10 * s_nb

    # PAIRED PROGRESSION (2026-07-22) — the fingerprint of a REAL rally: gate i's
    # lintel bounced AND gate i's window threaded. policy_v230 (raw 25) games the
    # scorer by flinging the ball over all 4 gates, letting it settle, then flying
    # BACKWARDS through the windows (verified: windows at t=4.87/6.67/7.88 vs ball
    # down at t=3.61) — bg and wins are both nonzero yet `pairs` stays ~0. Ranking
    # on pairs is what separates a genuine interleaved rally from that dead end.

    # ---- STAGE A: the MOTION only. Gates/windows/forward travel contribute nothing. ----
    # A qualifying bounce must be BOTH hard (vz) and VERTICAL (up-ratio) — a fast but
    # diagonal fling is not the motion we want and must not out-rank a clean vertical.
    # apex the bounce actually achieves, vs the height needed to clear gate 1's lintel
    _need_apex = float(gates[0][2]) + GATE_TOP_OFF + BALL_R + APEX_CLEAR_MARGIN
    highs = [
        l for l in lofts
        if float(l["vz"]) >= HIGH_VZ
        and float(l["up"]) >= VERT_UP_MIN
        and float(l.get("apex", 0.0)) >= _need_apex
    ]
    n_high = len(highs)
    mean_high_vz = float(np.mean([l["vz"] for l in highs])) if highs else 0.0
    mean_high_up = float(np.mean([l["up"] for l in highs])) if highs else 0.0
    fwd = float(np.clip(max_bx / 2.60, 0.0, 1.0))  # diagnostic only — NOT in the fitness
    # Dribble guard: a clean rally has ~1 contact per bounce. Chatter is heavily penalised
    # by ranking on FEWER total contacts once the high-bounce count ties.
    if JUGGLE_STAGE == "bounce":
        succ = 1 if (n_high >= 3 and not crash) else 0
        fit = (
            n_high,                       # sustained HARD VERTICAL bounces = the objective
            (0 if crash else 1),          # never flip
            -n_all,                       # fewer contacts -> no push/steady contact
            round(mean_high_vz, 3),       # hit them HARD
            round(mean_high_up, 4),       # ... and STRAIGHT UP (forward is not rewarded)
        )
        return {
            "fit": fit, "success": bool(succ), "pairs": pairs, "chain": chain,
            "bg": bg, "wins": wins, "crash": bool(crash), "shape": round(shape, 5),
            "n_vert": len(lofts), "n_high": n_high, "mean_up": float(np.mean([l["up"] for l in lofts])) if lofts else 0.0,
            "mean_vz": float(np.mean([l["vz"] for l in lofts])) if lofts else 0.0,
            "mean_high_vz": mean_high_vz, "mean_high_up": mean_high_up, "fwd": round(fwd, 4),
            "best_apex": round(float(max([l.get("apex", 0.0) for l in lofts], default=0.0)), 3),
            "need_apex": round(_need_apex, 3),
            "max_r": round(max_bx, 3), "verts": lofts, "n_contact": n_all,
            "win_miss": wm_all, "max_dx": round(float((telem or {}).get("max_dx", 0.0)), 3),
            "next_gate": next_gi,
        }

    # HARD RULE: bg/wins are NOT rewarded — only the sequential paired chain is.
    # They remain in the output dict purely as diagnostics.
    succ = 1 if chain >= 1 else 0
    fit = (chain, (0 if crash else 1), round(plant, 5), round(shape, 5), -n_all)
    mean_vz = float(np.mean([l["vz"] for l in lofts])) if lofts else 0.0
    mean_up = float(np.mean([l["up"] for l in lofts])) if lofts else 0.0
    return {
        "fit": fit,
        "success": bool(succ),
        "pairs": pairs,
        "chain": chain,
        "bg": bg,
        "wins": wins,
        "crash": bool(crash),
        "shape": round(shape, 5),
        "n_vert": len(lofts),
        "mean_up": mean_up,
        "mean_vz": mean_vz,
        "max_r": round(max_bx, 3),  # REPURPOSED in Phase-2: max ball x (forward travel); key kept for compat
        "verts": lofts,
        "n_contact": n_all,
        "win_miss": wm_all,
        "max_dx": round(float((telem or {}).get("max_dx", 0.0)), 3),
        "next_gate": next_gi,
    }


def make_policy_cls(params: JuggleParams):
    class Policy(JugglePolicy):
        _telem = {
            "win_miss": [9.0, 9.0, 9.0, 9.0],
            "max_dx": 0.0,
            "win_t": [None, None, None, None],
            "win_times": [[], [], [], []],
            "win_inside": [False, False, False, False],
        }

        def __init__(self):
            super().__init__(params)
            type(self)._telem = {
                "win_miss": [9.0, 9.0, 9.0, 9.0],
                "max_dx": 0.0,
                "win_t": [None, None, None, None],
                "win_times": [[], [], [], []],
                "win_inside": [False, False, False, False],
            }

    return Policy


def evaluate(params: JuggleParams) -> dict:
    names = [s.strip() for s in os.environ.get("JUGGLE_CASES", "nominal").split(",") if s.strip()]
    cases = {c.name: c for c in ps.held_out_cases()}
    per = []
    for nm in names:
        Policy = make_policy_cls(params)
        scen = cases[nm]
        r = run_episode(Policy, scen, observation_mode="partial")
        true_gates, _tgt = scenario_to_arrays(scen)
        s = score_phase2(r, getattr(Policy, "_telem", None), gates=true_gates)
        s["case"] = nm
        s["score"] = float(r.get("score") or 0.0)
        s["final_ball"] = [float(x) for x in (r.get("final_ball_pos") or [0, 0, 0])]
        s["final_drone"] = [float(x) for x in (r.get("final_drone_pos") or [0, 0, 0])]
        per.append(s)
    if len(per) == 1:
        out = dict(per[0])
        out["params"] = asdict(params)
        return out
    # PHASE-3 ROBUSTNESS FITNESS (2026-07-22 rewrite).
    # The previous aggregate led with sum_bg, which a SINGLE-case specialist maxes
    # out: the seeded nominal champ scored sum_bg=4 entirely from `nominal`, and any
    # mutation that helped the other cases first had to perturb the razor-edge
    # nominal rally -> sum_bg dropped -> rejected. Result: 11.8k generations with
    # ZERO improvement (a hard local optimum the lexicographic order cannot escape).
    # Fix: lead with the REAL objective (mean plant case_score across the training
    # cases, i.e. a direct proxy for the suite mean), then breadth (how many cases
    # bounce at least one gate). A specialist scoring 0.34 on one case and ~0 on five
    # has mean~0.06; a generalist scoring 0.15 everywhere has mean 0.15 and wins.
    if JUGGLE_STAGE == "bounce":
        # per-case fit is (n_high, nocrash, -contacts, mean_high_vz, fwd)
        nh = [int(p_["fit"][0]) for p_ in per]
        agg_fit = (
            int(min(nh)),                                                  # must bounce on EVERY case
            int(min(p_["fit"][1] for p_ in per)),                          # never flip, anywhere
            int(sum(nh)),
            -int(round(float(np.mean([-p_["fit"][2] for p_ in per])))),    # fewer contacts
            round(float(np.mean([p_["fit"][3] for p_ in per])), 3),        # mean high vz
            round(float(np.mean([p_["fit"][4] for p_ in per])), 4),        # verticality
        )
        return {
            "fit": agg_fit,
            "success": all(p_["success"] for p_ in per),
            "n_high": int(sum(p_.get("n_high", 0) for p_ in per)),
            "min_n_high": int(min(p_.get("n_high", 0) for p_ in per)),
            "crash": any(p_["crash"] for p_ in per),
            "score": float(np.mean([p_["score"] for p_ in per])),
            "mean_vz": float(np.mean([p_["mean_vz"] for p_ in per])),
            "mean_high_vz": float(np.mean([p_.get("mean_high_vz", 0.0) for p_ in per])),
            "fwd": float(np.mean([p_.get("fwd", 0.0) for p_ in per])),
            "mean_high_up": float(np.mean([p_.get("mean_high_up", 0.0) for p_ in per])),
            "best_apex": float(max([p_.get("best_apex", 0.0) for p_ in per], default=0.0)),
            "min_best_apex": float(min([p_.get("best_apex", 0.0) for p_ in per], default=0.0)),
            "need_apex": float(max([p_.get("need_apex", 0.0) for p_ in per], default=0.0)),
            "n_vert": int(sum(p_["n_vert"] for p_ in per)),
            "chain": int(sum(p_.get("chain", 0) for p_ in per)),
            "bg": int(sum(p_["bg"] for p_ in per)),
            "wins": int(sum(p_["wins"] for p_ in per)),
            "max_r": max(p_["max_r"] for p_ in per),
            "mean_up": float(np.mean([p_["mean_up"] for p_ in per])),
            "verts": [],
            "cases": [{k: v for k, v in p_.items() if k != "verts"} for p_ in per],
            "params": asdict(params),
        }

    # Per-case fit is (chain, nocrash, plant, shape, -contacts) — HARD RULE:
    # only the gate-1-anchored paired chain is rewarded; bg/wins are diagnostics.
    # Across cases, breadth leads. Leading with sum_chain recreates the old sum_bg
    # specialist trap: CHAIN=4 on one case would outrank CHAIN=1 on three cases.
    chains = [int(p_["fit"][0]) for p_ in per]
    sum_chain = int(sum(chains))
    min_chain = int(min(chains))
    breadth = int(sum(1 for c in chains if c >= 1))
    mean_plant = float(np.mean([p_["fit"][2] for p_ in per]))
    agg_fit = (
        breadth,                                      # paired progress on as many cases as possible
        min_chain,                                    # then raise the worst training case
        sum_chain,                                    # then deepen the paired chain
        int(min(p_["fit"][1] for p_ in per)),         # no-crash
        round(float(np.mean([p_["fit"][3] for p_ in per])), 5),
        -int(round(float(np.mean([-p_["fit"][4] for p_ in per])))),
        round(mean_plant, 5),                         # diagnostic scorer only; never progression
    )
    return {
        "fit": agg_fit,
        "success": any(p_["success"] for p_ in per),
        "pairs": int(sum(p_.get("pairs", 0) for p_ in per)),
        "chain": int(sum(p_.get("chain", 0) for p_ in per)),
        "min_chain": int(min(p_.get("chain", 0) for p_ in per)),
        "bg": int(sum(p_["bg"] for p_ in per)),
        "wins": int(sum(p_["wins"] for p_ in per)),
        "crash": any(p_["crash"] for p_ in per),
        "score": float(np.mean([p_["score"] for p_ in per])),
        "shape": float(np.mean([p_["shape"] for p_ in per])),
        "n_vert": int(sum(p_["n_vert"] for p_ in per)),
        "mean_up": float(np.mean([p_["mean_up"] for p_ in per])),
        "mean_vz": float(np.mean([p_["mean_vz"] for p_ in per])),
        "max_r": max(p_["max_r"] for p_ in per),
        "verts": [],
        "cases": [{k: v for k, v in p_.items() if k != "verts"} for p_ in per],
        "params": asdict(params),
    }


def mutate(p: JuggleParams, rng: random.Random) -> JuggleParams:
    q = JuggleParams(**asdict(p))
    specs = [
        ("dz_under", 0.04, 0.18, 0.55),
        ("center_x", 0.05, -0.15, 0.35),
        ("center_y", 0.05, -0.25, 0.25),
        ("sep_s", 0.04, 0.12, 0.45),
        ("sep_coll", 0.04, 0.90, 1.20),
        ("remount_dz", 0.03, 0.0, 0.22),
        ("sep_drop", 0.04, 0.20, 0.45),
        ("punch_gain", 0.10, 1.25, 2.85),
        # Phase-2 dims
        ("fwd_tip", 0.05, 0.0, 0.45),
        ("adv_frac", 0.08, 0.0, 0.85),
        ("loft_lead", 0.08, 0.0, 0.70),
        ("dash_gain", 0.15, 0.0, 1.0),
        # dash_z retired — altitude during thread is fixed at window centre
        ("punch_cap", 0.10, 2.30, 2.90),
        ("park_hits", 1.5, 4.0, 16.0),
        ("fwd_after", 0.8, 0.0, 5.0),
        # per-gate cycle choreography
        ("cycle_on", 1.0, 0.0, 1.0),
        ("launch_hit", 0.6, 2.0, 4.49),
        ("tap_adv", 0.05, 0.0, 0.45),
        ("tap_frac", 0.05, 0.70, 0.97),
        ("drop_per_hit", 0.04, 0.0, 0.30),
        ("catch_lead", 0.08, 0.15, 0.80),
        ("thread_s", 0.10, 0.20, 1.00),
        ("impact_bvz", 0.10, -1.20, -0.02),
        ("base_z", 0.08, 0.85, 1.60),
        ("arrest_coll", 0.06, 0.10, 0.95),
        ("track_gain", 0.10, 0.0, 1.0),
        ("min_taps", 0.6, 1.0, 4.0),
        ("launch_margin", 0.06, 0.0, 0.60),
        ("launch_tip", 0.06, 0.0, 0.60),
        ("fall_away", 0.08, 0.0, 0.85),
    ]
    if JUGGLE_STAGE == "bounce":
        # Retained only as an optional diagnostic curriculum. The rally search does not
        # gate on a minimum bounce count.
        active = {
            "dz_under", "center_x", "center_y",
            "sep_s", "sep_coll", "remount_dz", "sep_drop", "punch_gain",
            "punch_cap", "park_hits", "base_z", "arrest_coll", "impact_bvz",
            "track_gain",
        }
        specs = [spec for spec in specs if spec[0] in active]

    # The old "local" mutation changed ~22 of 40 dimensions in every child. That
    # repeatedly destroyed useful bounce/window timing and made refinement almost
    # impossible. Most children now make a surgical 1-4 parameter move; a small
    # fraction remain broad explorers so the search can still leave a local basin.
    if rng.random() < 0.12:
        chosen = [spec for spec in specs if rng.random() < 0.32]
        if not chosen:
            chosen = [rng.choice(specs)]
    else:
        chosen = rng.sample(specs, k=min(len(specs), rng.randint(1, 4)))
    for attr, scale, lo, hi in chosen:
        if attr == "cycle_on":
            if JUGGLE_STAGE == "rally":
                # User-mandated per-gate launch/thread/catch choreography. Do not
                # allow cycle_off specialists to reclaim the frontier (they were
                # dominating every winner JSON while leaving launch_latch dead).
                setattr(q, attr, 1.0)
            else:
                # Diagnostic bounce stage: categorical architecture switch.
                setattr(q, attr, 0.0 if float(getattr(q, attr)) > 0.5 else 1.0)
        else:
            v = getattr(q, attr) + rng.gauss(0, scale)
            setattr(q, attr, float(np.clip(v, lo, hi)))
    if JUGGLE_STAGE == "rally":
        q.cycle_on = 1.0
    return canonicalize(q)


def _ensure_cycle(p: JuggleParams) -> JuggleParams:
    """Rally search always uses the per-gate cycle choreography."""
    if JUGGLE_STAGE == "rally" and float(p.cycle_on) <= 0.5:
        d = asdict(p)
        d["cycle_on"] = 1.0
        return JuggleParams(**d)
    return p


# Fields the live controller never reads in rally mode — keep them out of cache keys
# so mutations that only touch dead dims do not burn six-case evaluations.
_DEAD_KEY_FIELDS = frozenset({
    "xy_kp", "xy_kd", "z_kp", "z_kd", "coll_bias",
    "tip_flat_y", "tip_flat_x", "face_gain", "max_xy_acc", "blend",
    "dash_z",  # retired altitude offset; always 0 in rally canonicalize
})
_INT_RUNTIME_FIELDS = ("park_hits", "fwd_after", "launch_hit", "min_taps")


def canonicalize(p: JuggleParams) -> JuggleParams:
    """Clamp / quantize params to the values the controller actually uses."""
    d = asdict(_ensure_cycle(p))
    d["tap_frac"] = float(np.clip(float(d.get("tap_frac", 0.85)), 0.70, 0.97))
    d["punch_cap"] = float(np.clip(float(d.get("punch_cap", 2.40)), 2.30, 2.90))
    d["punch_gain"] = float(np.clip(float(d.get("punch_gain", 2.0)), 1.25, 2.85))
    for attr in _INT_RUNTIME_FIELDS:
        d[attr] = float(int(round(float(d.get(attr, 0.0)))))
    if JUGGLE_STAGE == "rally":
        d["cycle_on"] = 1.0
        d["dash_z"] = 0.0  # altitude offset retired; thread at window centre
    elif float(d.get("cycle_on", 0.0)) <= 0.5:
        # Cycle-only dims are behaviorally dead when the FSM is off.
        d["cycle_on"] = 0.0
        d["launch_hit"] = 3.0
        d["tap_adv"] = 0.0
        d["tap_frac"] = 0.85
        d["drop_per_hit"] = 0.0
        d["catch_lead"] = 0.40
        d["thread_s"] = 0.55
        d["min_taps"] = 1.0
        d["launch_margin"] = 0.0
        d["launch_tip"] = 0.0
    return JuggleParams(**d)


def behavior_key(p: JuggleParams) -> tuple:
    """Deterministic phenotype key used for eval cache and submission dedupe."""
    d = asdict(canonicalize(p))
    items = tuple(
        (k, round(float(v), 6) if isinstance(v, (int, float)) else v)
        for k, v in sorted(d.items())
        if k not in _DEAD_KEY_FIELDS
    )
    return items


def crossover(primary: JuggleParams, donor: JuggleParams, rng: random.Random) -> JuggleParams:
    """Transfer a small subset of live controls from a per-case specialist."""
    data = asdict(primary)
    donor_data = asdict(donor)
    live_fields = (
        "dz_under", "center_x", "center_y", "sep_s", "sep_coll", "remount_dz",
        "sep_drop", "punch_gain", "fwd_tip", "adv_frac", "loft_lead",
        "dash_gain", "punch_cap", "park_hits", "fwd_after",
        "cycle_on", "launch_hit", "tap_adv", "tap_frac", "drop_per_hit",
        "catch_lead", "thread_s", "impact_bvz", "base_z", "arrest_coll",
        "track_gain", "min_taps", "launch_margin", "launch_tip", "fall_away",
    )
    transferred = 0
    for attr in live_fields:
        if rng.random() < 0.18:
            data[attr] = donor_data[attr]
            transferred += 1
    if transferred == 0:
        attr = rng.choice(live_fields)
        data[attr] = donor_data[attr]
    child = JuggleParams(**data)
    return _ensure_cycle(child)


# Phase-1 Vultr champ (mean_vz≈4.17, winner_ok_20260721T032246Z) — proven bounce core.
CHAMP = {
    "dz_under": 0.36909717892025523,
    "xy_kp": 3.6761815343365454,
    "xy_kd": 3.1879301275619354,
    "z_kp": 4.413401576246235,
    "z_kd": 2.5524514878527937,
    "coll_bias": -0.1648740304082072,
    "tip_flat_y": -0.2192784937627698,
    "tip_flat_x": -0.6425485094322069,
    "face_gain": 1.1989428086131497,
    "max_xy_acc": 2.9391313700471686,
    "blend": 0.2821154001671811,
    "center_x": 0.017743878753631998,
    "center_y": 0.0007417595636460324,
    "sep_s": 0.18103932495813646,
    "sep_coll": 1.1949948694932964,
    "remount_dz": 0.03810466993221,
    "sep_drop": 0.25718069282872247,
    "punch_gain": 2.2385948879778192,
}


def _fw(**kw) -> JuggleParams:
    d = dict(CHAMP)
    d.update(kw)
    return JuggleParams(**d)


def seed_pool(rng: random.Random) -> list:
    # CYCLE seeds (user-specified choreography 2026-07-22): >=2 settle taps creeping
    # forward with the drone stepping DOWN each impact, a LAUNCH over the lintel on the
    # 3rd/4th impact, thread that window immediately, catch on the far side, repeat.
    def _cyc(**kw):
        d = dict(CHAMP)
        d.update(dict(cycle_on=1.0, park_hits=16.0, fwd_after=1.0, dash_gain=0.45,
                      adv_frac=0.30, fwd_tip=0.06, loft_lead=0.10))
        d.update(kw)
        return JuggleParams(**d)

    seeds = [
        _cyc(launch_hit=3.0, drop_per_hit=0.12, tap_adv=0.10, tap_frac=0.85, catch_lead=0.40, thread_s=0.55),
        _cyc(launch_hit=4.0, drop_per_hit=0.10, tap_adv=0.08, tap_frac=0.80, catch_lead=0.40, thread_s=0.60),
        _cyc(launch_hit=3.0, drop_per_hit=0.16, tap_adv=0.14, tap_frac=0.90, catch_lead=0.50, thread_s=0.50),
        _cyc(launch_hit=4.0, drop_per_hit=0.14, tap_adv=0.12, tap_frac=0.85, catch_lead=0.35, thread_s=0.65),
        _cyc(launch_hit=3.0, drop_per_hit=0.08, tap_adv=0.06, tap_frac=0.78, catch_lead=0.45, thread_s=0.45,
             punch_gain=2.30),
        _cyc(launch_hit=3.0, drop_per_hit=0.12, tap_adv=0.10, tap_frac=0.85, catch_lead=0.40, thread_s=0.55,
             dash_gain=0.70, dz_under=0.28),
        # GENTLE forward variants of the proven bounce champ. Smoke-tested 2026-07-21:
        # the champ rally is a razor-edge equilibrium — even punch_cap 2.30->2.40 collapses
        # the punch chain, so seeds keep punch_cap/punch_gain stock and nudge only the
        # forward params. GENTLE_A verified: 4 lofts mvz~3.95, drone to x~6.0, NO crash.
        _fw(fwd_tip=0.03, adv_frac=0.10, loft_lead=0.10, dash_gain=0.0, park_hits=8, fwd_after=3),   # GENTLE_A
        _fw(fwd_tip=0.05, adv_frac=0.15, loft_lead=0.15, dash_gain=0.20, park_hits=8, fwd_after=3),  # GENTLE_B
        _fw(fwd_tip=0.02, adv_frac=0.06, loft_lead=0.05, dash_gain=0.0, park_hits=6, fwd_after=2),   # GENTLE_C
        _fw(fwd_tip=0.08, adv_frac=0.20, loft_lead=0.20, dash_gain=0.35, park_hits=10, fwd_after=3), # GENTLE_D
        _fw(fwd_tip=0.03, adv_frac=0.10, loft_lead=0.10, dash_gain=0.50, park_hits=8, fwd_after=3),  # A + window dash
        _fw(fwd_tip=0.03, adv_frac=0.10, loft_lead=0.10, dash_gain=0.0, park_hits=8, fwd_after=3, punch_cap=2.45),  # A + taller punch headroom
        _fw(),  # champ, neutral (bounce anchor)
        JuggleParams(),  # stock neutral
    ]
    # Prefer frozen local/Vultr winners if present (Phase-2 winners carry forward params in JSON).
    for wp in sorted(OUT_DIR.glob("winner*.json"))[-8:]:
        try:
            d = json.loads(wp.read_text())
            if d.get("success") and d.get("params"):
                allowed = {f.name for f in fields(JuggleParams)}
                seeds.insert(
                    0,
                    _ensure_cycle(
                        JuggleParams(**{k: v for k, v in d["params"].items() if k in allowed})
                    ),
                )
        except Exception:
            pass

    # CHAIN candidates were historically logged but not saved as winner JSONs.
    # Preserve both the current aggregate frontier and the best specialist for each
    # training case; otherwise every relaunch collapses back to one lineage.
    if JUGGLE_STAGE == "rally" and JSONL.exists():
        allowed = {f.name for f in fields(JuggleParams)}
        chain_seeds = []
        seen = set()
        try:
            entries = [
                json.loads(line).get("best", {})
                for line in JSONL.read_text().splitlines()
            ]
            case_best = {}
            for best in entries:
                params = best.get("params")
                if not params:
                    continue
                for case in best.get("cases") or []:
                    name = case.get("case")
                    if not name:
                        continue
                    metric = (
                        int(case.get("chain") or 0),
                        0 if case.get("crash", True) else 1,
                        float(case.get("shape") or 0.0),
                        float(case.get("score") or 0.0),
                    )
                    if name not in case_best or metric > case_best[name][0]:
                        case_best[name] = (metric, params)
            for _metric, params in case_best.values():
                key = json.dumps(params, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                chain_seeds.append(
                    _ensure_cycle(JuggleParams(**{k: v for k, v in params.items() if k in allowed}))
                )
            for best in reversed(entries):
                params = best.get("params")
                if int(best.get("chain") or 0) < 1 or not params:
                    continue
                key = json.dumps(params, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                chain_seeds.append(
                    _ensure_cycle(JuggleParams(**{k: v for k, v in params.items() if k in allowed}))
                )
                if len(chain_seeds) >= len(case_best) + 4:
                    break
        except Exception:
            chain_seeds = []
        seeds[0:0] = chain_seeds
    while len(seeds) < 16:
        seeds.append(mutate(rng.choice(seeds[:8]), rng))
    return [canonicalize(s) for s in seeds[:16]]


def write_status(best: dict, gen: int):
    LOG.mkdir(parents=True, exist_ok=True)
    lines = [
        "# JUGGLE Autodrive STATUS — PHASE 2 (gate rally)",
        "",
        f"- updated: {datetime.now(timezone.utc).isoformat()}",
        f"- gen: {gen}",
        f"- fitness cases: {os.environ.get('JUGGLE_CASES', 'nominal')}",
        f"- STAGE: {JUGGLE_STAGE}  " + ("(A: sustained HIGH bounces, gates/windows IGNORED)" if JUGGLE_STAGE == "bounce" else "(B: CHAIN hard rule)"),
        (f"- n_high per case (min/total): {best.get('min_n_high')} / {best.get('n_high')}   mean_high_vz={best.get('mean_high_vz', 0):.2f}  up={best.get('mean_high_up', 0):.2f}  APEX best/min={best.get('best_apex', 0):.2f}/{best.get('min_best_apex', 0):.2f} need={best.get('need_apex', 0):.2f}  (fwd {best.get('fwd', 0):.2f} = diagnostic only)" if JUGGLE_STAGE == "bounce" else ""),
        (
            f"- best_fit (min_high, nocrash, sum_high, -contacts, mean_vz, mean_up): {best.get('fit')}"
            if JUGGLE_STAGE == "bounce"
            else f"- best_fit (breadth, min_CHAIN, sum_CHAIN, nocrash, shape, -contacts, mean_plant): {best.get('fit')}"
        ),
        f"- CHAIN (HARD RULE: gate-1-anchored run of bounce+window pairs; any skip = 0 beyond) = {best.get('chain')} (min per case {best.get('min_chain')})",
        f"- bg / wins / crash: {best.get('bg')} / {best.get('wins')} / {best.get('crash')}",
        f"- plant_score: {best.get('score', 0):.4f}",
        f"- lofts n / mean_vz / max ball x: {best.get('n_vert')} / {best.get('mean_vz', 0.0):.3f} / {best.get('max_r')}",
        f"- params: `{json.dumps(best.get('params'))}`",
        "",
        "Phase-2: bounce ball OVER each gate lintel, dash drone THROUGH the window.",
        "Fitness = real scorer levers first (bg, wins), then plant score + shaped progress.",
        "",
    ]
    STATUS.write_text("\n".join(lines))
    txt = REPO / "repair_work" / "autoloop" / "STATUS.txt"
    txt.parent.mkdir(parents=True, exist_ok=True)
    txt.write_text(
        f"JUGGLE-P2 gen={gen} bg={best.get('bg')} wins={best.get('wins')} fit={best.get('fit')} "
        f"bx={best.get('max_r')}\n"
        f"Target: ball over all 4 gate lintels + drone through all 4 windows (real scorer levers).\n"
    )


def save_winner(best: dict, tag: str):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"winner_{tag}_{stamp}.json"
    path.write_text(json.dumps(best, indent=2))
    pol = OUT_DIR / f"policy_juggle_{tag}_{stamp}.py"
    pol.write_text(
        "import sys\nimport dataclasses\nfrom pathlib import Path\n"
        f"_REPO = Path({str(REPO)!r})\n"
        'sys.path.insert(0, str(_REPO / "repair_work"))\n'
        "from juggle_autodrive import JuggleParams, make_policy_cls\n"
        f"_PARAMS = {best['params']!r}\n"
        "# Filter to the resolved module's fields so the stub loads even against an older\n"
        "# juggle_autodrive (e.g. pack-local staging copies) instead of raising TypeError.\n"
        "_allowed = {f.name for f in dataclasses.fields(JuggleParams)}\n"
        "Policy = make_policy_cls(JuggleParams(**{k: v for k, v in _PARAMS.items() if k in _allowed}))\n"
    )
    return path


def main():
    rng = random.Random(int(time.time()) ^ 0xB0A7)
    workers = int(os.environ.get("JUGGLE_WORKERS", os.environ.get("G12_WORKERS", "14")))
    print(
        f"JUGGLE_AUTODRIVE PHASE-2 start workers={workers} "
        f"cases={os.environ.get('JUGGLE_CASES', 'nominal')} "
        f"(stage={JUGGLE_STAGE}; fitness={'bounce diagnostics' if JUGGLE_STAGE == 'bounce' else 'CHAIN, plant, safety, shape'})",
        flush=True,
    )
    base = evaluate(canonicalize(JuggleParams()))
    print(f"SEED0 fit={base['fit']} bg={base['bg']} wins={base['wins']} success={base['success']}", flush=True)
    pool = seed_pool(rng)
    best = base
    write_status(best, 0)
    gen = 0
    eval_cache = {behavior_key(JuggleParams()): base}
    ex = cf.ProcessPoolExecutor(max_workers=workers)
    while True:
        gen += 1
        t0 = time.time()
        results = []
        pending = {}
        pending_keys = set()
        seen_keys = set()
        for params in pool:
            params = canonicalize(params)
            key = behavior_key(params)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            cached = eval_cache.get(key)
            if cached is not None:
                results.append(cached)
            elif key not in pending_keys:
                pending[ex.submit(evaluate, params)] = key
                pending_keys.add(key)
        for fut in cf.as_completed(pending):
            key = pending[fut]
            try:
                result = fut.result()
                eval_cache[key] = result
                results.append(result)
            except Exception as e:
                results.append({
                    "fit": (-1, 0, 0, 0.0), "error": str(e), "success": False, "params": {},
                    "n_vert": 0, "mean_up": 0.0, "mean_vz": 0.0, "max_r": 9.0,
                    "bg": 0, "wins": 0, "crash": True, "score": 0.0, "shape": 0.0,
                })
        if not results:
            results = [best]
        if len(eval_cache) > 20_000:
            # Keep the active population plus recent experiments. Without this cap,
            # deterministic result caching grows by ~14 full six-case results/gen.
            protected = {behavior_key(params) for params in pool}
            recent = set(list(eval_cache)[-10_000:])
            keep = protected | recent
            eval_cache = {key: value for key, value in eval_cache.items() if key in keep}
        results.sort(key=lambda r: r.get("fit", (-1,)), reverse=True)
        top = results[0]
        if top.get("fit", (-1,)) > best.get("fit", (-1,)):
            best = top
            write_status(best, gen)
            LOG.mkdir(parents=True, exist_ok=True)
            with open(JSONL, "a") as f:
                f.write(json.dumps({"gen": gen, "best": {k: best[k] for k in best if k != "verts"}, "ts": time.time()}) + "\n")
            if best.get("success"):
                wp = save_winner(best, "ok")
                print(f"JUGGLE_OK winner={wp} bg={best.get('bg')} wins={best.get('wins')}", flush=True)
        elif gen % 10 == 0:
            write_status(best, gen)
        print(
            f"GEN {gen} top={top.get('fit')} best={best.get('fit')} bg={top.get('bg')} wins={top.get('wins')} "
            f"success={best.get('success')} bx={top.get('max_r')} [{time.time()-t0:.1f}s]",
            flush=True,
        )
        elites = [
            _ensure_cycle(JuggleParams(**r["params"]))
            for r in results[:3] if r.get("params")
        ]
        if not elites:
            elites = [_ensure_cycle(JuggleParams())]

        # Preserve two necessary but temporarily dominated lineages:
        #   * cycle_on: explicit launch -> thread -> far-side catch choreography
        #   * safe: no-crash behavior that can continue to the next gate
        # A pure top-k population immediately discarded both after the first accidental
        # CHAIN=1 candidate, leaving only crashy cycle_off descendants.
        # Rally stage now forces cycle_on=1.0; this island is the whole population.
        cycle_results = [
            r for r in results
            if r.get("params") and float(r["params"].get("cycle_on", 0.0)) > 0.5
        ]
        # Within the architecture island, pair-directed shape and survival outrank
        # the trusted plant score. Plant score can rise from out-of-order gates or
        # windows, which is exactly the behavior CHAIN is meant to reject.
        cycle_results.sort(
            key=lambda r: (
                int(r.get("chain", 0)),
                0 if r.get("crash", True) else 1,
                float(r.get("shape", 0.0)),
                -int(r.get("n_contact", 9999)),
                float(r.get("score", 0.0)),
            ),
            reverse=True,
        )
        safe_results = [r for r in results if r.get("params") and not r.get("crash", True)]
        safe_results.sort(
            key=lambda r: (
                int(r.get("chain", 0)),
                float(r.get("shape", 0.0)),
                float(r.get("score", 0.0)),
            ),
            reverse=True,
        )
        cycle_elites = (
            [_ensure_cycle(JuggleParams(**cycle_results[0]["params"]))] if cycle_results else []
        )
        safe_elites = (
            [_ensure_cycle(JuggleParams(**safe_results[0]["params"]))] if safe_results else []
        )
        case_elites = []
        case_count = max([len(r.get("cases") or []) for r in results], default=0)
        for case_idx in range(case_count):
            candidates = [
                r for r in results
                if r.get("params") and len(r.get("cases") or []) > case_idx
            ]
            candidates.sort(
                key=lambda r: (
                    int(r["cases"][case_idx].get("chain", 0)),
                    0 if r["cases"][case_idx].get("crash", True) else 1,
                    float(r["cases"][case_idx].get("shape", 0.0)),
                    float(r["cases"][case_idx].get("score", 0.0)),
                ),
                reverse=True,
            )
            if candidates:
                case_elites.append(_ensure_cycle(JuggleParams(**candidates[0]["params"])))

        pool = []
        pool_keys = set()
        for candidate in elites + cycle_elites + safe_elites + case_elites:
            candidate = canonicalize(candidate)
            key = behavior_key(candidate)
            if key in pool_keys:
                continue
            pool_keys.add(key)
            pool.append(candidate)
        # Exact elites are served from the deterministic cache. Generate one fresh
        # child per worker so every core performs useful simulation in one wave.
        # Skip phenotype duplicates (cached or already queued) so workers are not idle.
        target_size = len(pool) + workers
        attempts = 0
        while len(pool) < target_size and attempts < workers * 8:
            attempts += 1
            pick = rng.random()
            if cycle_elites and pick < 0.15:
                parent = rng.choice(cycle_elites)
            elif safe_elites and pick < 0.25:
                parent = rng.choice(safe_elites)
            elif case_elites and pick < 0.65:
                donor = rng.choice(case_elites)
                parent = crossover(rng.choice(elites), donor, rng) if rng.random() < 0.65 else donor
            else:
                parent = rng.choice(elites)
            child = canonicalize(mutate(canonicalize(parent), rng))
            key = behavior_key(child)
            if key in pool_keys:
                continue
            pool_keys.add(key)
            pool.append(child)


if __name__ == "__main__":
    main()
