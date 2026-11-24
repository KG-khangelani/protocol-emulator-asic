"""Read cost indicators from immutable Git trees and retained release/job metadata."""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


def tree_sizes(repo, commit):
    raw = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-l", "-r", "-z", commit])
    totals = {"blob_paths": 0, "logical_file_bytes": 0, "evidence_paths": 0, "evidence_bytes": 0}
    unique = {}
    for record in raw.rstrip(b"\0").split(b"\0"):
        metadata, path = record.split(b"\t", 1)
        _, kind, oid, size = metadata.split()
        if kind != b"blob":
            continue
        size = int(size)
        totals["blob_paths"] += 1
        totals["logical_file_bytes"] += size
        unique[oid] = size
        if path.startswith(b"evidence/"):
            totals["evidence_paths"] += 1
            totals["evidence_bytes"] += size
    totals["unique_blob_bytes"] = sum(unique.values())
    return totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    evidence = args.repo / "evidence"
    g4 = evidence / "E0047-g4-submission-candidate"
    g5 = evidence / "E0048-waveform-replay"
    releases = {}
    for folder in (g4, g5):
        meta = json.loads((folder / "publication/release.json").read_bytes())
        sizes = {a["name"]: a["size"] for a in meta["assets"]}
        selected = ("g4-submission-bundle.zip", "g4-public-programs.zip", "g5-waveform-replay.zip")
        releases[meta["tag_name"]] = {"assets": len(sizes),
                                      "asset_sizes_bytes": {n: sizes[n] for n in selected if n in sizes}}
    physical = {}
    for run_id in (43543626249, 43543629839):
        jobs = json.loads((g4 / f"ci-{run_id}/jobs.json").read_bytes())["jobs"]
        starts = [datetime.fromisoformat(j["started_at"].replace("Z", "+00:00")) for j in jobs]
        ends = [datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00")) for j in jobs]
        durations = {job["name"]: int((end - start).total_seconds())
                     for job, start, end in zip(jobs, starts, ends, strict=True)}
        physical[run_id] = {"elapsed_first_job_start_to_last_completion_s":
                            int((max(ends) - min(starts)).total_seconds()),
                            "job_duration_s": durations, "sum_of_job_seconds": sum(durations.values())}
    commit = "5bdc0e6b6449a829a5da1f8f9a8060257e974843"
    print(json.dumps({"g4_release_commit": commit, "g4_tree": tree_sizes(args.repo, commit),
                      "retained_releases": releases, "retained_physical_jobs": physical}, indent=2))


if __name__ == "__main__":
    main()
