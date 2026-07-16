import os
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

repo_dir = "/mnt/openfoam/pingpong-venv/progression/mujoco-skydio-pingpong-policy"
data_dir = os.path.join(repo_dir, "data")
json_path = os.path.join(data_dir, "scanned_progression.json")

with open(json_path, "r") as f:
    runs = json.load(f)

# Collect all mp4 videos to convert
jobs = []
for run in runs:
    for case in run["cases"]:
        for video in case["videos"]:
            if video["filename"].endswith(".mp4"):
                mp4_path = os.path.join(repo_dir, video["rel_path"])
                gif_path = mp4_path.replace(".mp4", ".gif")
                jobs.append((mp4_path, gif_path))

print(f"Total videos to convert: {len(jobs)}")

def convert_one(job):
    mp4_path, gif_path = job
    if os.path.exists(gif_path):
        return True
    
    # Run ffmpeg command to convert to high-quality 360px wide GIF
    cmd = [
        "ffmpeg", "-y", "-i", mp4_path,
        "-vf", "fps=10,scale=360:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        gif_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {mp4_path}: {e}")
        return False

# Run in parallel using a ThreadPoolExecutor
max_workers = min(32, os.cpu_count() or 4)
print(f"Starting conversion using {max_workers} workers...")
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    results = list(executor.map(convert_one, jobs))

success_count = sum(1 for r in results if r)
print(f"Successfully converted {success_count}/{len(jobs)} videos to GIFs.")
