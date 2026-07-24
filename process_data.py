#!/usr/bin/env python3
"""
Rebuild data/scanned_progression.json — the single index index.html fetches.

Run from repair_work/dashboard_sync.py (or by hand: `python3 process_data.py`).

SCHEMA 2 (2026-07-22). The old schema listed every media file as an object with
a `filename` and a `rel_path`; with 70 packs that was 4119 objects and a 2.2 MB
download whose paths were all derivable from the pack/case name. Schema 2 emits
a bitmap of which artifacts exist and lets the page build paths, which also lets
the UI grey out a case that is genuinely missing a render instead of mounting a
<video> on a 404.

SCHEMA 2.1 (2026-07-24): each case also carries `rank` — a task-aligned episode
score derived from instruction.md (bounce gates + matching windows + target-box
settle + safety). Champions on the dashboard rank by this, NOT by legacy
held-out raw_score_100 from reward-hack policies (raw≈25 fling/lap).

    {
      "schema": 2,
      "generated_utc": "20260722T...Z",
      "artifacts": ["render_3d.mp4", ...],
      "ranking": { "method": "...", "top_episodes": [ ... ] },
      "runs": [ ... ]
    }

`have` is one char per entry of `artifacts`, '1' present / '0' missing.
Paths are always  data/<dir>/cases/<name>/<artifact>.
"""
from __future__ import annotations

import json
import os
import re
import time

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_DIR, "data")

# Order is load-bearing: it defines the "have" bit string consumed by index.html.
ARTIFACTS = [
    # index 0-4: the render contract. index.html treats have[:5] as "complete".
    "render_3d.mp4",
    "render_3d.gif",
    "render_2d.mp4",
    "render_2d.gif",
    "trajectory_2d.png",
    # index 5+: optional extras. Append here, never insert.
    "summary.md",
    "render_3d.jpg",   # ~5 KB card poster, so the page can preload="none"
]

PACK_RE = re.compile(r"^(\d{8}T\d{6}Z)_(.*)$")

# Legacy reward-hack / fling-lap policies. Their plant case_score and suite raw
# look high but violate the interleaved bounce→window choreography required by
# the task (instruction.md + user CHAIN rule). Do not promote them as champs.
_INVALID_PACK_RE = re.compile(
    r"(policy_v230|policy_evolved|evolved_g\d+|detach_smoke|soft_hi|win011|"
    r"catch_(mild|near)|remo_|byp_|g12_best|v229|win2_focus|win_retro|"
    r"policy_soft|policy_catch|policy_remo|policy_byp|policy_win)",
    re.I,
)


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _prefix_pairs(metrics: dict) -> int | None:
    """Longest gate-1-anchored run of (bounce AND window). Needs per-gate lists."""
    bg = metrics.get("bounced_gate_pass")
    wp = metrics.get("drone_window_pass")
    if not isinstance(bg, list) or not isinstance(wp, list):
        return None
    n = 0
    for i in range(min(4, len(bg), len(wp))):
        if bool(bg[i]) and bool(wp[i]):
            n += 1
        else:
            break
    return n


def episode_rank(metrics: dict) -> dict:
    """Task-aligned rank for one rollout (instruction.md).

    Primary levers (in order):
      1. paired depth — min(bg, wins) as proxy when per-gate window bits missing;
         prefer true gate-1-anchored prefix when drone_window_pass[] is present
      2. target-box settle (required for full score / hard_success)
      3. no crash / safety
      4. hard_success
      5. plant case_score (0..1)

    Returns a dict with a sortable `key` list (higher better) and a scalar
    `score` for UI badges.
    """
    m = metrics or {}
    bg = int(m.get("bounced_gate_passes") or 0)
    wins = int(m.get("drone_windows_passed") or 0)
    tbox = float(m.get("target_box_score") or 0.0)
    crash = int(m.get("drone_crash") or 0)
    safety = float(m.get("safety_score") or 0.0)
    hard = int(m.get("hard_success") or 0)
    case = float(m.get("score") or 0.0)

    prefix = _prefix_pairs(m)
    paired = int(prefix) if prefix is not None else int(min(bg, wins))

    # Lexicographic key — must stay comparable as a JSON list.
    key = [
        paired,                          # interleaved bounce+window depth
        1 if tbox > 0.5 else 0,          # ball settled in target box
        0 if crash else 1,               # survive
        1 if safety > 0.5 else 0,        # safety credit
        hard,                            # full hard_success
        round(tbox, 5),
        round(case, 5),
        bg,
        wins,
    ]
    # Compact scalar for badges (not used for ordering when key is present).
    score = (
        paired * 1000.0
        + (100.0 if tbox > 0.5 else 0.0)
        + (50.0 if not crash else 0.0)
        + (20.0 if safety > 0.5 else 0.0)
        + (10.0 if hard else 0.0)
        + case * 10.0
    )
    return {
        "paired": paired,
        "prefix": prefix,
        "bg": bg,
        "wins": wins,
        "tbox": tbox,
        "crash": bool(crash),
        "safety": safety,
        "hard": bool(hard),
        "case_score": case,
        "key": key,
        "score": round(score, 3),
    }


def pack_is_invalid(dir_name: str, aggregate: dict) -> bool:
    """True for reward-hack / fling-lap packs that must not lead the board."""
    if _INVALID_PACK_RE.search(dir_name or ""):
        if "juggle" in (dir_name or "").lower():
            return False
        return True
    raw = aggregate.get("raw_score_100")
    try:
        if raw is not None and float(raw) > 15.0 and "juggle" not in (dir_name or "").lower():
            return True
    except (TypeError, ValueError):
        pass
    return False


def main() -> int:
    if not os.path.isdir(DATA_DIR):
        print(f"Error: data directory not found at {DATA_DIR}")
        return 1

    run_dirs = sorted(
        (d for d in os.listdir(DATA_DIR)
         if PACK_RE.match(d) and os.path.isdir(os.path.join(DATA_DIR, d))),
        reverse=True,
    )

    runs = []
    top_episodes = []
    for dir_name in run_dirs:
        run_path = os.path.join(DATA_DIR, dir_name)
        m = PACK_RE.match(dir_name)
        stamp, tail = m.group(1), m.group(2)

        meta = read_json(os.path.join(run_path, "meta.json"))
        aggregate = read_json(os.path.join(run_path, "aggregate.json"))

        # Older packs never wrote created_utc, which left the UI printing empty
        # timestamps like "juggle_close ()" in the run picker. The directory name
        # is authoritative, so always backfill from it.
        if not meta.get("created_utc"):
            meta["created_utc"] = stamp
        if not meta.get("label"):
            meta["label"] = aggregate.get("label") or tail

        invalid = pack_is_invalid(dir_name, aggregate)
        aggregate = dict(aggregate)
        aggregate["ranking_invalid"] = invalid
        # Valid held-out raw only (CHAIN-compliant / non-hack era).
        raw = aggregate.get("raw_score_100")
        try:
            raw_f = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            raw_f = None
        if invalid or raw_f is None:
            aggregate["valid_raw_score_100"] = None
        else:
            aggregate["valid_raw_score_100"] = raw_f

        # Staged policy freeze, if this pack recorded one (used by the modal to
        # link the exact controller source that produced the rollouts).
        rel_policy = None
        if meta.get("policy_path") and "_staging/" in meta["policy_path"]:
            rel_policy = "data/_staging/" + meta["policy_path"].split("_staging/")[1]
        meta["rel_policy_path"] = rel_policy

        cases = []
        cases_dir = os.path.join(run_path, "cases")
        best_rank = None
        if os.path.isdir(cases_dir):
            for case_name in sorted(os.listdir(cases_dir)):
                case_path = os.path.join(cases_dir, case_name)
                # macOS drops AppleDouble "._foo" files on this NFS mount. They
                # once leaked into the index as 2067 phantom media entries that
                # all 404'd in the browser.
                if case_name.startswith(".") or not os.path.isdir(case_path):
                    continue
                have = "".join(
                    "1" if os.path.isfile(os.path.join(case_path, a)) else "0"
                    for a in ARTIFACTS
                )
                metrics = read_json(os.path.join(case_path, "metrics.json"))
                rank = episode_rank(metrics)
                cases.append({
                    "name": case_name,
                    "metrics": metrics,
                    "have": have,
                    "rank": rank,
                })
                if have[0] != "1":
                    continue  # no 3D render — skip champion board
                if best_rank is None or rank["key"] > best_rank["key"]:
                    best_rank = rank
                top_episodes.append({
                    "dir": dir_name,
                    "stamp": stamp,
                    "label": meta["label"],
                    "case": case_name,
                    "invalid": invalid,
                    "rank": rank,
                    "have": have,
                })

        runs.append({
            "dir": dir_name,
            "stamp": stamp,
            "label": meta["label"],
            "meta": meta,
            "aggregate": aggregate,
            "grid": os.path.isfile(os.path.join(run_path, "grid_renders.mp4")),
            "cases": cases,
            "best_rank": best_rank,
            "ranking_invalid": invalid,
        })

    # Champions: valid packs first, then by episode rank key.
    top_episodes.sort(
        key=lambda e: (e["invalid"], [-x for x in e["rank"]["key"]]),
    )
    top10 = top_episodes[:10]

    out = {
        "schema": 2,
        "generated_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "artifacts": ARTIFACTS,
        "ranking": {
            "method": (
                "instruction.md episode quality: paired bounce+window depth "
                "(min(bg,wins) or gate-1 prefix), then target-box settle, "
                "no-crash/safety, hard_success, case_score. Legacy fling/lap "
                "packs (raw>15 / evolved FSM) are demoted."
            ),
            "top_episodes": top10,
        },
        "runs": runs,
    }

    out_path = os.path.join(DATA_DIR, "scanned_progression.json")
    with open(out_path, "w") as f:
        # Compact separators: this file is downloaded on every page load.
        json.dump(out, f, separators=(",", ":"))

    n_cases = sum(len(r["cases"]) for r in runs)
    n_incomplete = sum(
        1 for r in runs for c in r["cases"] if "0" in c["have"][:5]
    )
    size_kb = os.path.getsize(out_path) / 1024
    print(f"Indexed {len(runs)} runs / {n_cases} cases -> {out_path} ({size_kb:.0f} KB)")
    if n_incomplete:
        print(f"  NOTE: {n_incomplete} case(s) missing at least one artifact "
              f"(run: python3 repair_work/dashboard_sync.py --audit)")
    print("Top champions (task-aligned):")
    for i, e in enumerate(top10, 1):
        rk = e["rank"]
        print(
            f"  #{i} paired={rk['paired']} tbox={rk['tbox']:.2f} "
            f"crash={int(rk['crash'])} sc={rk['case_score']:.3f} "
            f"{'[INV] ' if e['invalid'] else ''}"
            f"{e['dir']}/{e['case']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
