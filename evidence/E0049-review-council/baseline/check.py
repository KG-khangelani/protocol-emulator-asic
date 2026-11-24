# SPDX-License-Identifier: Apache-2.0
"""Recheck the council baseline using the retained archives. Optional live GETs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen
import zipfile

ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT / "tools"))
from compare_gds_records import compare
from production_sram import verify

BASE = "e90cca228490423a7fe7c4ae40f7e669200b4d0e"
G4 = ROOT / "evidence/E0047-g4-submission-candidate"
G5 = ROOT / "evidence/E0048-waveform-replay"
API = "https://api.github.com/repos/KG-khangelani/protocol-emulator-asic"
ANNOUNCEMENT = "https://blog.janestreet.com/protocol-emulator-asic-competition/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, label):
    if not condition:
        raise ValueError(label)


def read(path):
    return json.loads(path.read_bytes())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def get(url):
    request = Request(url, headers={"User-Agent": "asic-council-research", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=25) as response:
        require(response.status == 200, "HTTP status " + url)
        data = response.read(1_000_001)
    require(len(data) <= 1_000_000, "response size cap")
    return data


def archive(directory, name):
    entries = read(directory / "artifacts.json")["artifacts"]
    item, = [entry for entry in entries if entry["name"] == name]
    path = directory / (str(item["id"]) + ".zip")
    with path.open("rb") as stream:
        require("sha256:" + hashlib.file_digest(stream, "sha256").hexdigest() == item["digest"], name)
    return path


def physical():
    cases = [G4 / ("ci-" + n) for n in ("43543626249", "43543629839")]
    submitted = [archive(d, "tt_submission") for d in cases]
    member = "tt_submission/tt_um_khangelani_protocol_emulator"
    with zipfile.ZipFile(submitted[0]) as left, zipfile.ZipFile(submitted[1]) as right:
        pair = compare(zipfile.Path(left, member + ".gds"), zipfile.Path(right, member + ".gds"))
        nets = [sha(z.read(member + ".v")) for z in (left, right)]
        sizes = [[line.strip() for line in z.read(member + ".lef").decode().splitlines()
                  if line.lstrip().startswith("SIZE ")] for z in (left, right)]
    known = read(G4 / "reproduction.json")["comparisons"]
    for key in ("record_structure_equal", "different_bytes", "different_records",
                "timestamp_record_differences", "non_timestamp_record_differences", "equivalent_except_timestamps"):
        require(pair[key] == known["normalized_gds"][key], "GDS pair " + key)
    for side in ("left", "right"):
        for key in ("size_in_bytes", "sha256", "record_count", "timestamp_normalized_sha256"):
            require(pair[side][key] == known["normalized_gds"][side][key], "GDS identity " + key)
        pair[side].pop("path")
    require(nets == [known["netlist"]["sha256"]] * 2 and sizes[0] == sizes[1], "netlist or LEF differs")

    selected = []
    for directory in cases:
        # The archive name is frozen by the G4 producer.
        path = archive(directory, "GDS_logs")
        with zipfile.ZipFile(path) as z:
            metrics = json.loads(z.read("runs/wokwi/final/metrics.json"))
        selected.append({key: metrics[key] for key in (
            "design__die__bbox", "design__core__area", "design__instance__area__stdcell",
            "design__instance__area__macros", "design__instance__utilization",
            "design__instance__area__class:fill_cell", "timing__setup__ws", "timing__hold__ws")})
    require(selected[0] == selected[1], "metric pair differs")
    m = selected[0]
    occupied = m["design__instance__area__stdcell"] + m["design__instance__area__macros"]
    return {"gds_comparison": pair, "netlist_sha256": nets[0], "lef_size": sizes[0],
            "final_metrics": m, "occupied_logic_plus_macro_um2": occupied,
            "calculated_share_of_core_percent": 100 * occupied / m["design__core__area"]}


def assets(response):
    return sorted((item["name"], item["size"], item["digest"]) for item in response["assets"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(ROOT / "build") and not args.out.exists(),
            "use a new output file under build/")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    result = {"observed_utc": stamp, "baseline": BASE, "releases": {}}
    verify(ROOT)
    locked = read(ROOT / "tools/production-profile.json")["files_sha256"]
    for tag, directory in (("v0.1.0", G4), ("v0.1.1", G5)):
        local = git("rev-parse", tag + "^{commit}").decode().strip()
        for path, expected in locked.items():
            require(sha(git("show", tag + ":" + path)) == expected, tag + " " + path)
            require(sha(git("show", BASE + ":" + path)) == expected, BASE + " " + path)
        retained = read(directory / "publication/release.json")
        entry = {"tag_commit": local, "qualified_input_hashes_matched": len(locked),
                 "retained_asset_count": len(assets(retained))}
        if args.live:
            live = json.loads(get(API + "/releases/tags/" + tag))
            current_ref = json.loads(get(API + "/git/ref/tags/" + tag))["object"]["sha"]
            entry["live_asset_metadata_matches"] = assets(live) == assets(retained)
            title, body_sha = retained["name"], sha(retained["body"].encode())
            if tag == "v0.1.0":
                # The publisher appended an audited completion notice after the initial snapshot.
                notice = read(G4 / "release-notice.json")
                require(body_sha == notice["before_body_sha256"], "initial G4 release-body identity")
                title, body_sha = notice["title"], notice["after_body_sha256"]
                entry["title_body_reference"] = "G4 release-notice.json"
            entry["live_name_and_body_match"] = (live["name"], sha(live["body"].encode())) == (title, body_sha)
            entry["live_tag_ref_matches"] = current_ref == git("rev-parse", tag).decode().strip()
            require(all(v for k, v in entry.items() if k.startswith("live_")), "release metadata drift " + tag)
        result["releases"][tag] = entry
    result["physical"] = physical()
    if args.live:
        page = get(ANNOUNCEMENT)
        historical = read(ROOT / "docs/research/rule-reviews/2026-11-24.json")
        result["announcement"] = {"url": ANNOUNCEMENT, "bytes": len(page), "sha256": sha(page),
                                  "same_body_as_dated_recheck": sha(page) == historical["retrieval"]["sha256"]}
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Checked both release identities and G4 archives", args.out)


if __name__ == "__main__":
    main()
