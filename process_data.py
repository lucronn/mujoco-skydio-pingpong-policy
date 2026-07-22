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

    {
      "schema": 2,
      "generated_utc": "20260722T...Z",
      "artifacts": ["render_3d.mp4", ...],       # index order for the "have" string
      "runs": [
        {
          "dir": "20260722T131500Z_juggle_stageA_bounce",
          "stamp": "20260722T131500Z",
          "label": "juggle_stageA_bounce",
          "meta": {...},           # meta.json, with created_utc always filled in
          "aggregate": {...},      # aggregate.json (pack-level metrics/notes)
          "grid": true,            # grid_renders.mp4 present
          "cases": [
            {"name": "nominal", "metrics": {...}, "have": "111110"}
          ]
        }
      ]
    }

`have` is one char per entry of `artifacts`, '1' present / '0' missing:
    render_3d.mp4, render_3d.gif, render_2d.mp4, render_2d.gif,
    trajectory_2d.png, summary.md

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
    "render_3d.mp4",
    "render_3d.gif",
    "render_2d.mp4",
    "render_2d.gif",
    "trajectory_2d.png",
    "summary.md",
]

PACK_RE = re.compile(r"^(\d{8}T\d{6}Z)_(.*)$")


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


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

        # Staged policy freeze, if this pack recorded one (used by the modal to
        # link the exact controller source that produced the rollouts).
        rel_policy = None
        if meta.get("policy_path") and "_staging/" in meta["policy_path"]:
            rel_policy = "data/_staging/" + meta["policy_path"].split("_staging/")[1]
        meta["rel_policy_path"] = rel_policy

        cases = []
        cases_dir = os.path.join(run_path, "cases")
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
                cases.append({
                    "name": case_name,
                    "metrics": read_json(os.path.join(case_path, "metrics.json")),
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
        })

    out = {
        "schema": 2,
        "generated_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "artifacts": ARTIFACTS,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
