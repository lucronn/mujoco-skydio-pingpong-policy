#!/usr/bin/env python3
"""Autonomous in-place vertical bounce (juggle) search.

Phase-1 success (user directive B):
  >= N near-vertical racket bounces with ball staying inside an xy cylinder.
  No gate/window/G12 reward. Forward tip comes later.

Flat paddle → vertical bounce. Search hover/face/PD params on Vultr.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import math
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "q1-pingpong-window-gate-kit" / "data"))
sys.path.insert(0, str(REPO / "repair_work"))

from actuated_plant import run_episode  # noqa: E402
import parallel_suite as ps  # noqa: E402

OUT_DIR = REPO / "repair_work" / "juggle_winners"
LOG = REPO / "progression" / "overnight_log"
STATUS = LOG / "JUGGLE_STATUS.md"
JSONL = LOG / "juggle_autodrive.jsonl"

# Target
N_BOUNCE = 4
CYL_R = 0.30
EPISODE_T = 4.0  # score contacts in this window
VZ_MIN = 0.30
UP_MIN = 0.65
VXY_MAX = 1.10


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


class JugglePolicy:
    """Dedicated flat-face hover-under-ball juggler (no smash / no gate chase)."""

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

        # Permanent park after N bounces — drop clear then hold.
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
        if (not getattr(self, "_want_park", False)) and contactish and (t - float(self._last_hit_t)) > 0.34 and t > float(self._sep_until):
            self._sep_until = t + max(0.30, float(p.sep_s))
            self._hit_z = float(dp[2])
            self._hit_count += 1
            self._last_hit_t = t
            if self._hit_count >= N_BOUNCE:
                self._want_park = True
            # Cut thrust immediately — create visible air gap under rising ball.
            tip = np.zeros(3)
            coll = 0.88 * hs + 4.0 * (0.80 - float(dp[2]))
            coll = float(np.clip(coll, 0.75 * hs, 1.30 * hs))
            u = self._mix(coll, tip)
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]

        if t < float(self._sep_until):
            age = t - (float(self._sep_until) - max(0.30, float(p.sep_s)))
            z_hold = max(0.82, float(getattr(self, "_hit_z", float(dp[2]))) - max(0.22, float(p.sep_drop)))
            if age < 0.14:
                tip = np.zeros(3)
                coll = 0.90 * hs + 5.0 * (z_hold - float(dp[2]))
                coll = float(np.clip(coll, 0.80 * hs, 1.35 * hs))
                u = self._mix(coll, tip)
                self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
                return [float(x) for x in self.last_cmd]
            return _hold_xy_z(z_hold, tip_scale=0.05)

        # Wait for clear separation + falling ball before remount.
        if float(bv[2]) > 0.0 or dz < 0.38:
            z_hold = min(float(bp[2]) - 0.65, float(getattr(self, "_hit_z", 1.0)) - max(0.32, float(p.sep_drop)))
            return _hold_xy_z(z_hold, tip_scale=0.08)

        # Remount under ball.
        x_des = 0.50 * float(bp[0]) + 0.50 * float(self.cx)
        y_des = 0.50 * float(bp[1]) + 0.50 * float(self.cy)
        extra = float(p.remount_dz) if (t < float(self._sep_until) + 0.40) else 0.0
        z_des = float(bp[2]) - float(p.dz_under) - extra - (float(rp[2]) - float(dp[2]))
        z_des = max(0.82, z_des)

        # Rising punch into the ball — tall visible loft.
        approaching = 0.12 < dz < 0.58 and float(bv[2]) < 0.40 and dxy < 0.32
        if approaching or t < float(getattr(self, "_punch_until", -1e9)):
            if approaching and t >= float(getattr(self, "_punch_until", -1e9)):
                self._punch_until = t + 0.12
            tip = np.array([
                float(np.clip(0.9 * (x_des - dp[0]), -0.14, 0.14)),
                float(np.clip(0.9 * (y_des - dp[1]), -0.14, 0.14)),
                0.0,
            ])
            pg = float(np.clip(getattr(p, "punch_gain", 1.55), 1.25, 2.25))
            coll = pg * hs + 6.0 * max(0.0, 0.25 - float(dv[2]))
            coll = float(np.clip(coll, 1.25 * hs, 2.30 * hs))
            u = self._mix(coll, tip)
            self.last_cmd = np.clip(np.asarray(u, float), self.rot_min, self.rot_max)
            return [float(x) for x in self.last_cmd]
        return _hold_at(x_des, y_des, z_des, tip_lim=0.12)



def score_contacts(result: dict, cx: float, cy: float) -> dict:
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
    # Count contacts only through last good vert + short settle (ignore post-park chatter/floor pin).
    t_cut = (verts[-1]["t"] + 0.45) if verts else EPISODE_T
    n_all = len([e for e in evs if float(e.get("end", 0)) <= t_cut])
    chatter_pen = max(0, n_all - 10) * 0.05
    # Success first; never let crashy high-n chatter beat a clean N=4.
    succ = 1 if (n >= N_BOUNCE and crash == 0 and n_all <= 48 and max_r <= CYL_R) else 0
    # Success first. Among successes prefer taller loft (mean_vz), then more bounces.
    # Never rank crashy one-hit loft as "best".
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


def make_policy_cls(params: JuggleParams):
    class Policy(JugglePolicy):
        def __init__(self):
            super().__init__(params)

    return Policy


def evaluate(params: JuggleParams) -> dict:
    cases = {c.name: c for c in ps.held_out_cases()}
    Policy = make_policy_cls(params)
    r = run_episode(Policy, cases["nominal"], observation_mode="partial")
    sc = score_contacts(r, params.center_x, params.center_y)
    return {
        **sc,
        "score": float(r.get("score") or 0.0),
        "bg": int(r.get("bounced_gate_passes") or 0),
        "crash": bool(r.get("drone_crash")),
        "params": asdict(params),
        "final_ball": [float(x) for x in (r.get("final_ball_pos") or [0, 0, 0])],
        "final_drone": [float(x) for x in (r.get("final_drone_pos") or [0, 0, 0])],
    }


def mutate(p: JuggleParams, rng: random.Random) -> JuggleParams:
    q = JuggleParams(**asdict(p))
    for attr, scale, lo, hi in [
        ("dz_under", 0.04, 0.18, 0.55),
        ("xy_kp", 0.8, 2.0, 10.0),
        ("xy_kd", 0.4, 0.8, 5.0),
        ("z_kp", 1.0, 3.0, 12.0),
        ("z_kd", 0.5, 1.0, 6.0),
        ("coll_bias", 0.05, -0.25, 0.35),
        ("tip_flat_y", 0.20, -1.2, 0.8),
        ("tip_flat_x", 0.12, -0.8, 0.8),
        ("face_gain", 0.25, 0.0, 2.0),
        ("max_xy_acc", 0.5, 2.0, 7.0),
        ("blend", 0.08, 0.25, 0.85),
        ("center_x", 0.05, -0.15, 0.35),
        ("center_y", 0.05, -0.25, 0.25),
        ("sep_s", 0.04, 0.12, 0.45),
        ("sep_coll", 0.04, 0.90, 1.20),
        ("remount_dz", 0.03, 0.0, 0.22),
        ("sep_drop", 0.04, 0.20, 0.45),
        ("punch_gain", 0.10, 1.25, 2.25),
    ]:
        if rng.random() < 0.55:
            v = getattr(q, attr) + rng.gauss(0, scale)
            setattr(q, attr, float(np.clip(v, lo, hi)))
    return q


def seed_pool(rng: random.Random) -> list:
    seeds = [
        JuggleParams(),
        JuggleParams(dz_under=0.34, sep_s=0.36, sep_drop=0.28, punch_gain=1.65, sep_coll=1.12, xy_kp=5.0, z_kp=8.0, remount_dz=0.12, blend=0.7),
        JuggleParams(dz_under=0.2893, xy_kp=6.0, xy_kd=2.80, z_kp=9.1, z_kd=2.62, tip_flat_y=0.06, face_gain=0.62, blend=0.65, center_x=0.08, sep_s=0.40, sep_coll=1.11, remount_dz=0.13, sep_drop=0.28, punch_gain=1.7),
        JuggleParams(dz_under=0.28, sep_s=0.40, sep_drop=0.30, punch_gain=1.75),
        JuggleParams(dz_under=0.40, xy_kp=6.5, sep_s=0.38, sep_drop=0.28, punch_gain=1.6),
        JuggleParams(dz_under=0.32, z_kp=9.0, sep_s=0.34, sep_drop=0.26, punch_gain=1.8),
        JuggleParams(dz_under=0.36, xy_kp=4.5, remount_dz=0.14, sep_s=0.42, sep_drop=0.32, punch_gain=1.7),
        JuggleParams(dz_under=0.30, tip_flat_y=-0.2, blend=0.7, sep_s=0.36, sep_coll=1.10, punch_gain=1.65),
        JuggleParams(dz_under=0.38, xy_kp=7.0, xy_kd=3.5, sep_coll=1.12, sep_drop=0.28, punch_gain=1.55),
        JuggleParams(dz_under=0.25, tip_flat_y=-0.3, face_gain=1.0, z_kp=8.0, sep_s=0.40, punch_gain=1.85),
        JuggleParams(dz_under=0.42, tip_flat_y=0.1, max_xy_acc=5.0, remount_dz=0.16, sep_s=0.32, punch_gain=1.6),
        JuggleParams(dz_under=0.34, tip_flat_y=0.0, face_gain=0.3, xy_kp=5.5, sep_s=0.45, sep_drop=0.30, punch_gain=1.7),
    ]
    # Prefer frozen local/Vultr winners if present.
    for wp in sorted(OUT_DIR.glob("winner*.json"))[-8:]:
        try:
            d = json.loads(wp.read_text())
            if d.get("success") and d.get("params"):
                allowed = {f.name for f in __import__("dataclasses").fields(JuggleParams)}
                seeds.insert(0, JuggleParams(**{k: v for k, v in d["params"].items() if k in allowed}))
        except Exception:
            pass
    while len(seeds) < 16:
        seeds.append(mutate(rng.choice(seeds[:8]), rng))
    return seeds[:16]


def write_status(best: dict, gen: int):
    LOG.mkdir(parents=True, exist_ok=True)
    lines = [
        "# JUGGLE Autodrive STATUS",
        "",
        f"- updated: {datetime.now(timezone.utc).isoformat()}",
        f"- gen: {gen}",
        f"- best_fit: {best.get('fit')}",
        f"- success (N>={N_BOUNCE} in R={CYL_R}): {best.get('success')}",
        f"- n_vert / mean_up / mean_vz / max_r: {best.get('n_vert')} / {best.get('mean_up'):.3f} / {best.get('mean_vz'):.3f} / {best.get('max_r'):.3f}",
        f"- plant_score/bg/crash: {best.get('score', 0):.4f} / {best.get('bg')} / {best.get('crash')}",
        f"- params: `{json.dumps(best.get('params'))}`",
        "",
        "Phase-1: vertical in-place juggle only. Gates/windows ignored.",
        "",
    ]
    STATUS.write_text("\n".join(lines))
    txt = REPO / "repair_work" / "autoloop" / "STATUS.txt"
    txt.parent.mkdir(parents=True, exist_ok=True)
    txt.write_text(
        f"JUGGLE gen={gen} success={best.get('success')} n_vert={best.get('n_vert')} "
        f"fit={best.get('fit')} max_r={best.get('max_r'):.3f}\n"
        f"Target: >={N_BOUNCE} vertical bounces inside R={CYL_R}m cylinder. No gate reward.\n"
    )


def save_winner(best: dict, tag: str):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"winner_{tag}_{stamp}.json"
    path.write_text(json.dumps(best, indent=2))
    pol = OUT_DIR / f"policy_juggle_{tag}_{stamp}.py"
    pol.write_text(
        "import sys\nfrom pathlib import Path\n"
        f"_REPO = Path({str(REPO)!r})\n"
        'sys.path.insert(0, str(_REPO / "repair_work"))\n'
        "from juggle_autodrive import JuggleParams, make_policy_cls\n"
        f"Policy = make_policy_cls(JuggleParams(**{best['params']!r}))\n"
    )
    return path


def main():
    rng = random.Random(int(time.time()) ^ 0xB0A7)
    workers = int(os.environ.get("JUGGLE_WORKERS", os.environ.get("G12_WORKERS", "14")))
    print(f"JUGGLE_AUTODRIVE start workers={workers} N={N_BOUNCE} R={CYL_R}", flush=True)
    # baseline smoke
    base = evaluate(JuggleParams())
    print(f"SEED0 fit={base['fit']} n_vert={base['n_vert']} success={base['success']}", flush=True)
    pool = seed_pool(rng)
    best = base
    write_status(best, 0)
    gen = 0
    while True:
        gen += 1
        t0 = time.time()
        results = []
        with cf.ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(evaluate, p) for p in pool]
            for fut in cf.as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as e:
                    results.append({"fit": (-1, 0.0, 0.0, 0.0), "error": str(e), "success": False, "params": {}, "n_vert": 0, "mean_up": 0.0, "mean_vz": 0.0, "max_r": 9.0})
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
                print(f"JUGGLE_OK winner={wp} n_vert={best.get('n_vert')}", flush=True)
        elif gen % 10 == 0:
            write_status(best, gen)
        print(
            f"GEN {gen} top={top.get('fit')} best={best.get('fit')} n={top.get('n_vert')} "
            f"success={best.get('success')} max_r={top.get('max_r'):.3f} [{time.time()-t0:.1f}s]",
            flush=True,
        )
        elites = [JuggleParams(**r["params"]) for r in results[:4] if r.get("params")]
        if not elites:
            elites = [JuggleParams()]
        pool = elites[:]
        while len(pool) < 16:
            pool.append(mutate(rng.choice(elites), rng))


if __name__ == "__main__":
    main()
