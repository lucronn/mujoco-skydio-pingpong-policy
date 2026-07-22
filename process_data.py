import os
import json

# Script to scan the progression directories inside 'data' and rebuild the scanned_progression.json index
repo_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(repo_dir, "data")

if not os.path.exists(data_dir):
    print(f"Error: data directory not found at {data_dir}")
    exit(1)

import re

# Find run directories matching timestamp prefix in the data_dir
run_dirs = sorted([d for d in os.listdir(data_dir) if re.match(r"^\d{8}T\d{6}Z_", d) and os.path.isdir(os.path.join(data_dir, d))], reverse=True)

runs = []
for run_dir_name in run_dirs:
    run_path = os.path.join(data_dir, run_dir_name)
    meta_path = os.path.join(run_path, "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
            
    cases_dir = os.path.join(run_path, "cases")
    cases = []
    if os.path.exists(cases_dir):
        for case_name in sorted(os.listdir(cases_dir)):
            case_path = os.path.join(cases_dir, case_name)
            if not os.path.isdir(case_path):
                continue
            metrics_path = os.path.join(case_path, "metrics.json")
            metrics = {}
            if os.path.exists(metrics_path):
                with open(metrics_path, "r") as f:
                    metrics = json.load(f)
            
            videos = []
            for video_name in sorted(os.listdir(case_path)):
                if video_name.startswith("._"):
                    continue
                if video_name.endswith(".mp4") or video_name.endswith(".gif"):
                    rel_video_path = os.path.relpath(os.path.join(case_path, video_name), repo_dir)
                    videos.append({
                        "filename": video_name,
                        "rel_path": rel_video_path
                    })
                    
            snapshot_path = os.path.join(case_path, "trajectory_2d.png")
            rel_snapshot = None
            if os.path.exists(snapshot_path):
                rel_snapshot = os.path.relpath(snapshot_path, repo_dir)
                
            cases.append({
                "name": case_name,
                "metrics": metrics,
                "videos": videos,
                "snapshot": rel_snapshot
            })
            
    # Normalize staged policy path if possible
    if meta.get("policy_path"):
        local_path = meta["policy_path"]
        if "_staging/" in local_path:
            parts = local_path.split("_staging/")
            meta["rel_policy_path"] = "data/_staging/" + parts[1]
        else:
            meta["rel_policy_path"] = None
    else:
        meta["rel_policy_path"] = None
        
    runs.append({
        "dir_name": run_dir_name,
        "meta": meta,
        "cases": cases
    })

print(f"Generated data for {len(runs)} runs.")

output_json_path = os.path.join(data_dir, "scanned_progression.json")
with open(output_json_path, "w") as f:
    json.dump(runs, f, indent=2)
print(f"Saved metadata index to {output_json_path}")
