# SPDX-License-Identifier: Apache-2.0
"""Capture actual Linux physical replays or release packaging on the isolated branch.

Docker is used only when main() runs. Physical proof omits reconstructed bulk.
Package proof retains the seventeen actual assets without changing their bytes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time
import zipfile


ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / "build/g4-ci-proof"
SCRATCH = ROOT / "build/g4-linux-verification-work"
CONTAINER_SCRATCH = "/workspace/build/g4-linux-verification-work"
E47 = Path("evidence/E0047-g4-submission-candidate")
IMAGE_RECORD = Path("evidence/E0046-program-toolchain/publication/release-verification.json")
WORKFLOW = Path(".github/workflows/g4-linux-verification.yaml")
PACKAGER = E47 / "release-tools/package.py"
PHYSICAL_SOURCE = "45c55f7cd95db2a883b0ffb5e864decd62d53601"
PUBLIC_IMAGE = "ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:f487aaf03906535a3187690557ff97ca1707e966b48ae8a99362683b5f68e307"
PUBLIC_CONFIG = "sha256:6f45e71162641466c4e9e08601a383c8a081c06b263114903a181d5f8f971451"
RUNS = (("candidate", 43543626249, False), ("reproduction", 43543629839, True))
ARCHIVES = ("GDS_logs", "tt_submission", "sram-physical-candidate",
            "precheck_reports", "gatelevel_test_results", "sram-netlist-check")
ASSET_NAMES = {"g4-submission-bundle.zip", "g4-public-programs.zip", "g4-windows-programs.zip",
               "g4-submission.json", "g4-SHA256SUMS"} | {
    f"g4-{run_id}-{name}.zip" for _, run_id, _ in RUNS for name in ARCHIVES
}
PACKAGE_RUNTIME_PREFIX = "G4_PACKAGE_RUNTIME "
PACKAGE_DRIVER = """import json, platform, runpy, sys
runtime = {'python': sys.version, 'platform': platform.platform(),
           'machine': platform.machine(), 'executable': sys.executable}
print('G4_PACKAGE_RUNTIME ' + json.dumps(runtime, sort_keys=True), flush=True)
packager, source, output = sys.argv[1:]
sys.argv = [packager, '--source', source, '--out', output]
print('G4_PACKAGE_ARGV ' + json.dumps(sys.argv), flush=True)
runpy.run_path(packager, run_name='__main__')
"""
CONTROL_ERRORS = {
    "pending-workflow": "physical workflow is not successfully complete",
    "wrong-archive-digest": "archive digest mismatch",
    "rehashed-port-count": "power-port selection differs",
    "rehashed-skipped-test": "required public test skipped",
    "rehashed-netlist": "submitted netlist differs",
    "wrong-job-source": "G4 job source differs",
    "rehashed-production": "production verification differs",
    "rehashed-stage-configuration": "G4 executed stage configuration differs",
    "rehashed-stage-skip": "configured G4 stage sequence differs",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout.decode("utf-8").strip()


def git_blob(source: str, name: Path) -> bytes:
    return subprocess.run(["git", "show", source + ":" + name.as_posix()], cwd=ROOT,
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def capture(argv: list[str], receipt_path: Path, log_path: Path, *, timeout: int,
            details: dict | None = None) -> tuple[dict, bytes]:
    """Record the actual combined output, return code, argv, and elapsed time."""
    started, timer = now(), time.monotonic()
    raw_path = SCRATCH / (receipt_path.relative_to(PROOF).as_posix().replace("/", "-") + ".raw")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    error = None
    returncode = None
    print("RUN " + json.dumps(argv), flush=True)
    with raw_path.open("wb") as output:
        try:
            completed = subprocess.run(argv, cwd=ROOT, stdout=output,
                                       stderr=subprocess.STDOUT, timeout=timeout)
            returncode = completed.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
    raw = raw_path.read_bytes()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes(gzip.compress(raw, mtime=0))
    receipt = {
        "schema": "protocol-emulator-g4-ci-command-invocation-v1",
        "command": argv,
        "working_directory": str(ROOT),
        "started_utc": started,
        "completed_utc": now(),
        "elapsed_seconds": round(time.monotonic() - timer, 6),
        "returncode": returncode,
        "log_path": log_path.relative_to(PROOF).as_posix(),
        "log_sha256": sha(raw),
        "compressed_log_sha256": file_sha(log_path),
        "output_capture": "stdout and stderr merged by subprocess.STDOUT, stored without text conversion",
        "runner_sha256": file_sha(Path(__file__)),
    }
    if details:
        receipt.update(details)
    if error:
        receipt["execution_error"] = error
    write(receipt_path, receipt)
    print(f"RETURN {returncode}: {receipt_path.relative_to(PROOF).as_posix()}", flush=True)
    return receipt, raw


def checked_capture(argv: list[str], label: str, *, timeout: int = 60) -> bytes:
    receipt, raw = capture(argv, PROOF / "commands" / (label + ".json"),
                           PROOF / "commands" / (label + ".log.gz"), timeout=timeout)
    require(receipt["returncode"] == 0, f"{label} failed; retained the actual command receipt and log")
    return raw


def validate_retained(run_id: int) -> dict:
    base = ROOT / E47 / f"ci-{run_id}"
    tracked = set(git("ls-files", "--", repo_path(base)).splitlines())
    require(repo_path(base / "SHA256SUMS") in tracked, f"uncommitted seal for run {run_id}")
    sealed = {}
    for line in (base / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        member = PurePosixPath(name)
        require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None and
                member.as_posix() == name and not member.is_absolute() and
                ".." not in member.parts and "\\" not in name and ":" not in name and
                name not in sealed, f"unsafe or duplicate seal member: {name}")
        path = base / name
        require(path.is_file() and not path.is_symlink() and repo_path(path) in tracked,
                f"seal member is not a committed regular file: {name}")
        require(file_sha(path) == expected, f"retained seal mismatch: {name}")
        sealed[name] = expected
    for required in ("verify.py", "audit.py", "controls.py", "producer.json", "producer.tar.gz",
                     "result.json", "zip-files.json", "storage.json", "verification-windows.json"):
        require(required in sealed, f"missing sealed dependency: {required}")
    result = read(base / "result.json")
    require(result["status"] == "PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES" and
            result["run_id"] == run_id and result["source_commit"] == PHYSICAL_SOURCE,
            f"run {run_id} has no complete frozen physical pass")
    require(result["precheck"]["test_count"] == 10 and
            result["netlist_tests"]["public_test_groups"] == 18,
            f"run {run_id} has incomplete precheck or netlist groups")
    require(len(result["archives"]) == len(read(base / "storage.json")) == 6,
            f"run {run_id} must retain six original archives")
    index = read(base / "zip-files.json")
    require(set(index) == set(result["archives"]) and sum(map(len, index.values())) == 1729,
            f"run {run_id} archive member coverage changed")
    require(len(read(base / "producer.json")["files"]) == 84,
            f"run {run_id} producing input count changed")
    return {"base": base, "result": result, "sealed": sealed}


def docker_command(image: str) -> list[str]:
    return ["docker", "run", "--rm", "--pull=never", "--network=none",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--env", "HOME=/tmp", "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "GIT_OPTIONAL_LOCKS=0",
            "--mount", f"type=bind,source={ROOT},target=/workspace,readonly",
            "--mount", f"type=bind,source={SCRATCH},target={CONTAINER_SCRATCH}",
            "--workdir", "/workspace", image]


def inspect_image(image: str, label: str) -> dict:
    raw = checked_capture(["docker", "image", "inspect", image], label)
    data = json.loads(raw)
    require(isinstance(data, list) and len(data) == 1, "expected one inspected image")
    inspected = data[0]
    require(inspected["Id"] == PUBLIC_CONFIG and image in inspected["RepoDigests"] and
            inspected["Os"] == "linux" and inspected["Architecture"] == "amd64",
            "pulled image config/platform differs from the E0046 public verification")
    (PROOF / (label + ".json")).write_bytes(raw)
    return inspected


def retain_controls(out: Path, dest: Path, retained: dict, replay_result_sha: str) -> dict:
    path = out / "controls/result.json"
    controls = read(path)
    (dest / "controls-result.json").write_bytes(path.read_bytes())
    require(controls["status"] == "PASS_NINE_COMPLETE_QUALIFICATION_FAULT_CONTROLS" and
            controls["source_commit"] == PHYSICAL_SOURCE and
            controls["run_id"] == retained["result"]["run_id"], "fault-control identity/status differs")
    require(controls["baseline_result_sha256"] == replay_result_sha and
            controls["audit_sha256"] == retained["sealed"]["audit.py"] and
            controls["runner_sha256"] == retained["sealed"]["controls.py"],
            "fault controls are not bound to the replay and frozen audit")
    cases = controls["cases"]
    require(len(cases) == 9 and {case["name"] for case in cases} == set(CONTROL_ERRORS),
            "expected exactly the nine named frozen corruption controls")
    (dest / "controls-logs").mkdir()
    for case in cases:
        name = case["name"]
        raw = (out / "controls" / name / "audit.log").read_bytes()
        (dest / "controls-logs" / (name + ".log.gz")).write_bytes(gzip.compress(raw, mtime=0))
        require(case["status"] == "PASS_REJECTED_CORRUPTION" and
                isinstance(case["returncode"], int) and case["returncode"] != 0 and
                case["expected_error"] == CONTROL_ERRORS[name] and
                case["observed"] == {"status": "NOT_QUALIFIED", "error": CONTROL_ERRORS[name]} and
                sha(raw) == case["log_sha256"], f"control did not reject its corruption: {name}")
    return {"count": 9, "result_sha256": file_sha(path), "names": sorted(CONTROL_ERRORS)}


def replay(role: str, run_id: int, controls: bool, retained: dict,
           image: str, runtime: dict, execution: dict) -> dict:
    base, result = retained["base"], retained["result"]
    out = SCRATCH / f"ci-{run_id}"
    dest = PROOF / f"ci-{run_id}"
    dest.mkdir()
    require(not out.exists(), "replay output must be fresh")
    command = docker_command(image) + ["python3", "-u", "/workspace/" + repo_path(base / "verify.py"),
                                      "--output", f"{CONTAINER_SCRATCH}/ci-{run_id}"]
    if controls:
        command.append("--controls")
    receipt_path = dest / "invocation-linux.json"
    invocation, _ = capture(command, receipt_path, dest / "replay-linux.log.gz", timeout=2400,
                            details={
                                "schema": "protocol-emulator-g4-physical-replay-invocation-v1",
                                "run_id": run_id, "host": "linux", "role": role,
                                "physical_source_commit": PHYSICAL_SOURCE,
                                "ci_execution": execution,
                                "runtime": runtime,
                                "verify_sha256": retained["sealed"]["verify.py"],
                                "verification_sha256": None,
                            })
    verification_path = out / "verification.json"
    if verification_path.is_file():
        (dest / "verification.json").write_bytes(verification_path.read_bytes())
        invocation["verification_sha256"] = file_sha(verification_path)
    audit_path = out / "audit/result.json"
    if audit_path.is_file():
        (dest / "audit").mkdir()
        (dest / "audit/result.json").write_bytes(audit_path.read_bytes())
        invocation["result_sha256"] = file_sha(audit_path)
    write(receipt_path, invocation)
    require(invocation["returncode"] == 0, f"{role} frozen replay failed; retained genuine receipt/log")
    expected = {
        "status": "PASS_RETAINED_COMPLETE_SRAM_QUALIFICATION",
        "source_commit": PHYSICAL_SOURCE, "run_id": run_id,
        "original_archive_files": 1729, "producing_inputs": 84,
        "gds_sha256": result["gds_sha256"], "netlist_sha256": result["netlist_sha256"],
        "controls_executed": controls,
    }
    require(read(verification_path) == expected, f"{role} replay report differs")
    windows = read(base / "verification-windows.json")
    require(windows == dict(expected, controls_executed=not controls),
            f"{role} retained Windows report differs beyond its planned controls flag")
    prior_linux = base / "verification-linux.json"
    if prior_linux.is_file():
        require(read(prior_linux) == expected, f"{role} prior retained Linux report differs")
    require(read(audit_path) == result and file_sha(audit_path) == retained["sealed"]["result.json"],
            f"{role} full audit result differs from the retained record")
    control_summary = retain_controls(out, dest, retained, file_sha(audit_path)) if controls else None
    require(controls or not (out / "controls").exists(), "candidate unexpectedly produced controls")
    return {
        "role": role, "run_id": run_id, "physical_source_commit": PHYSICAL_SOURCE,
        "directory": dest.relative_to(PROOF).as_posix(),
        "status": expected["status"], "original_archive_files": 1729, "producing_inputs": 84,
        "result_sha256": file_sha(audit_path), "verification_sha256": file_sha(verification_path),
        "verification_matches_retained_windows_except_controls_flag": True,
        "full_audit_result_identical_to_retained": True,
        "retained_seal_sha256": file_sha(base / "SHA256SUMS"),
        "retained_verify_sha256": retained["sealed"]["verify.py"],
        "controls_executed": controls, "controls": control_summary,
    }


def package_preflight(request: dict, head: str) -> dict:
    source = request.get("release_source_commit")
    require(isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source) is not None,
            "package request needs the actual final 40-hex main release_source_commit")
    require(git("rev-parse", "--verify", source + "^{commit}") == source,
            "release source does not identify the exact commit")
    main_snapshot = git("rev-parse", "--verify", "refs/remotes/origin/main^{commit}")
    checked_capture(["git", "merge-base", "--is-ancestor", source, head], "release-source-is-ci-ancestor")
    checked_capture(["git", "merge-base", "--is-ancestor", source, main_snapshot],
                    "release-source-is-main-ancestor")
    source_packager = git_blob(source, PACKAGER)
    require(source_packager == (ROOT / PACKAGER).read_bytes(),
            "checked-out packager differs from the selected release Git blob")
    require(git_blob(source, IMAGE_RECORD) == (ROOT / IMAGE_RECORD).read_bytes(),
            "public image evidence differs from the selected release Git blob")
    require(not git("status", "--porcelain", "--untracked-files=no"), "tracked checkout is dirty")
    return {
        "release_source_commit": source,
        "ci_checkout_commit": head,
        "ci_checkout_parents": git("rev-list", "--parents", "-n", "1", head).split()[1:],
        "origin_main_snapshot": main_snapshot,
        "release_source_is_ancestor_of_ci_checkout": True,
        "release_source_is_ancestor_of_origin_main": True,
        "ci_commits_after_release_source": int(git("rev-list", "--count", source + ".." + head)),
        "tracked_checkout_clean_before": True,
        "packager_path": PACKAGER.as_posix(),
        "packager_sha256": sha(source_packager),
        "executed_packager_identical_to_release_git_blob": True,
        "public_image_record_identical_to_release_git_blob": True,
    }


def package_inventory(directory: Path, source: str) -> tuple[dict, dict]:
    paths = list(directory.iterdir())
    require(len(paths) == 17 and {path.name for path in paths} == ASSET_NAMES and
            all(path.is_file() and not path.is_symlink() for path in paths),
            "package must contain exactly the seventeen declared regular asset files")
    files = {path.name: {"bytes": path.stat().st_size, "sha256": file_sha(path)}
             for path in sorted(paths)}
    manifest = read(directory / "g4-submission.json")
    require(manifest["schema"] == "protocol-emulator-g4-release-package-v1" and
            manifest["release_source_commit"] == source and manifest["tag"] == "v0.1.0" and
            manifest["target"] == "od128-sram-v1" and manifest["interface_id"] == "0x22",
            "release manifest source/version/interface differs")
    require(set(manifest["physical_runs"]) == {role for role, _, _ in RUNS} and
            all(manifest["physical_runs"][role]["run_id"] == run_id and
                manifest["physical_runs"][role]["source_commit"] == PHYSICAL_SOURCE
                for role, run_id, _ in RUNS), "package physical producer identity differs")
    require(manifest["artifacts"] == {name: item for name, item in files.items() if name.endswith(".zip")},
            "actual ZIP files differ from the package manifest")
    originals = manifest["original_archives"]
    require(len(originals) == 14 and
            {item["asset"] for item in originals} == set(manifest["artifacts"]) - {"g4-submission-bundle.zip"} and
            all(files[item["asset"]] == {"bytes": item["bytes"], "sha256": item["sha256"]}
                for item in originals), "original archive assets differ from their manifest identities")
    checksums = {}
    for line in (directory / "g4-SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None and name not in checksums,
                "malformed or duplicate package checksum entry")
        checksums[name] = digest
    require(checksums == {name: item["sha256"] for name, item in files.items() if name != "g4-SHA256SUMS"},
            "checksum file does not cover the exact sixteen other assets")
    for name in ("g4-submission.json", "g4-SHA256SUMS"):
        raw = (directory / name).read_bytes()
        raw.decode("utf-8")
        require(b"\r" not in raw and raw.endswith(b"\n"), f"asset is not UTF-8/LF: {name}")
    with zipfile.ZipFile(directory / "g4-submission-bundle.zip") as bundle:
        infos = bundle.infolist()
        require(len({item.filename for item in infos}) == len(infos) and
                {item.filename for item in infos} == set(manifest["bundle_members_sha256"]),
                "bundle member inventory differs from the manifest")
        for info in infos:
            member = PurePosixPath(info.filename)
            require(member.as_posix() == info.filename and not member.is_absolute() and
                    ".." not in member.parts and "\\" not in info.filename and not info.is_dir(),
                    "unsafe bundle member")
            require(info.compress_type == zipfile.ZIP_STORED and info.date_time == (1980, 1, 1, 0, 0, 0),
                    "bundle metadata differs from deterministic packaging")
            digest = hashlib.sha256()
            with bundle.open(info) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            require(digest.hexdigest() == manifest["bundle_members_sha256"][info.filename],
                    "bundle member hash differs: " + info.filename)
        inner = json.loads(bundle.read("g4-submission.json"))
        require(inner == {key: value for key, value in manifest.items()
                          if key not in ("bundle_members_sha256", "artifacts")},
                "embedded manifest differs from the external release manifest")
    return files, {"manifest_sha256": files["g4-submission.json"]["sha256"],
                   "checksums_sha256": files["g4-SHA256SUMS"]["sha256"],
                   "bundle_members_verified": len(manifest["bundle_members_sha256"]),
                   "original_archive_assets": len(originals),
                   "tag": manifest["tag"], "target": manifest["target"],
                   "interface_id": manifest["interface_id"]}


def package_release(bindings: dict, image: str, runtime: dict, execution: dict) -> dict:
    source = bindings["release_source_commit"]
    output = SCRATCH / "release-assets" / source
    destination = PROOF / "assets"
    require(output.resolve().is_relative_to((ROOT / "build").resolve()) and
            destination.resolve().is_relative_to(PROOF.resolve()) and
            not output.exists() and not destination.exists(), "package paths must be fresh and contained")
    container_output = f"{CONTAINER_SCRATCH}/release-assets/{source}"
    packager_argv = [PACKAGER.as_posix(), "--source", source, "--out", container_output]
    command = docker_command(image) + ["python3", "-u", "-c", PACKAGE_DRIVER,
                                      PACKAGER.as_posix(), source, container_output]
    receipt_path = PROOF / "package/invocation-linux.json"
    invocation, raw = capture(command, receipt_path, PROOF / "package/package-linux.log.gz", timeout=3600,
                              details={
                                  "schema": "protocol-emulator-g4-linux-package-invocation-v1",
                                  "host": "linux", "release_source_commit": source,
                                  "physical_source_commit": PHYSICAL_SOURCE,
                                  "ci_execution": execution, "runtime": runtime,
                                  "packager_sha256": bindings["packager_sha256"],
                                  "packager_argv": packager_argv,
                              })
    require(invocation["returncode"] == 0, "Linux packager failed; retained its actual receipt and log")
    lines = raw.decode("utf-8").splitlines()
    actual_runtimes = [json.loads(line[len(PACKAGE_RUNTIME_PREFIX):])
                       for line in lines if line.startswith(PACKAGE_RUNTIME_PREFIX)]
    actual_arguments = [json.loads(line[len("G4_PACKAGE_ARGV "):])
                        for line in lines if line.startswith("G4_PACKAGE_ARGV ")]
    require(len(actual_runtimes) == 1 and actual_arguments == [packager_argv],
            "actual packager process runtime/arguments are missing or ambiguous")
    require(actual_runtimes[0] == {key: runtime[key] for key in ("python", "platform", "machine", "executable")},
            "actual packager Python differs from the inspected image runtime")
    invocation["actual_packager_python_runtime"] = actual_runtimes[0]
    write(receipt_path, invocation)
    files, package_checks = package_inventory(output, source)
    require(not git("status", "--porcelain", "--untracked-files=no"),
            "tracked checkout changed during packaging")
    bindings["tracked_checkout_clean_after"] = True
    # Both paths are fresh ignored build paths on this Linux runner. Renaming the
    # directory retains the actual asset bytes rather than rebuilding any ZIP.
    output.rename(destination)
    result = {
        "schema": "protocol-emulator-g4-linux-release-package-v1",
        "status": "PASS_G4_LINUX_RELEASE_PACKAGE", "release_source_commit": source,
        "physical_source_commit": PHYSICAL_SOURCE, "asset_directory": "assets",
        "asset_count": len(files), "files": files, "manifest_checks": package_checks,
        "git_bindings": bindings, "ci_execution": execution,
        "image": image, "config_digest": runtime["container_image"]["Id"], "runtime": runtime,
        "invocation": receipt_path.relative_to(PROOF).as_posix(),
        "invocation_sha256": file_sha(receipt_path),
        "log_path": invocation["log_path"], "log_sha256": invocation["log_sha256"],
        "scope": "Actual Linux package assets only. Windows byte comparison, tag/publication, "
                 "anonymous downloads, and a matching release image remain separate gates.",
    }
    write(PROOF / "package/result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    require(not PROOF.exists() and not SCRATCH.exists(), "proof and replay directories must be fresh")
    PROOF.mkdir(parents=True)
    SCRATCH.mkdir(parents=True)
    summary = {
        "schema": "protocol-emulator-g4-linux-proof-v1", "status": "NOT_QUALIFIED",
        "started_utc": now(), "phase": None,
        "scope": "Actual requested verification work in the public Linux image. "
                 "This is not a new physical producer, release publication, or contest submission.",
    }
    exit_code = 1
    try:
        request = read(args.request)
        require(request.get("schema") == "protocol-emulator-g4-linux-request-v1" and
                request.get("phase") in ("physical", "package"),
                "only the physical and package request phases are implemented")
        phase = request["phase"]
        summary["phase"] = phase
        requested = request.get("source", "HEAD")
        require(isinstance(requested, str) and
                (requested == "HEAD" or re.fullmatch(r"[0-9a-f]{40}", requested) is not None),
                "request source must be HEAD or a full commit SHA")
        head = git("rev-parse", "--verify", "HEAD^{commit}")
        source = git("rev-parse", "--verify", requested + "^{commit}")
        require(source == head and re.fullmatch(r"[0-9a-f]{40}", source) is not None,
                "requested evidence source must be the checked-out commit")
        require(platform.system() == "Linux" and os.environ.get("GITHUB_ACTIONS") == "true",
                "this scaffold executes only on the isolated Linux GitHub Actions runner")
        require(os.environ.get("GITHUB_SHA") == head and
                os.environ.get("GITHUB_REF") == "refs/heads/codex/g4-linux-verification" and
                os.environ.get("GITHUB_REPOSITORY") == "KG-khangelani/protocol-emulator-asic",
                "CI execution identity differs from the isolated checkout")
        require(not git("status", "--porcelain", "--untracked-files=no"), "tracked checkout is dirty")
        execution = {
            "source_commit": source, "workflow_execution_commit": os.environ["GITHUB_SHA"],
            "repository": os.environ["GITHUB_REPOSITORY"], "ref": os.environ["GITHUB_REF"],
            "run_id": os.environ["GITHUB_RUN_ID"], "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
            "job": os.environ.get("G4_CI_JOB_ID", os.environ.get("GITHUB_JOB")),
            "event_name": os.environ.get("GITHUB_EVENT_NAME"),
            "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
            "workflow_sha": os.environ.get("GITHUB_WORKFLOW_SHA"),
            "runner_os": os.environ.get("RUNNER_OS"), "runner_arch": os.environ.get("RUNNER_ARCH"),
            "host_python": sys.version, "host_platform": platform.platform(),
            "host_machine": platform.machine(),
        }
        summary.update(source_commit=source, physical_source_commit=PHYSICAL_SOURCE,
                       ci_execution=execution, runner_sha256=file_sha(Path(__file__)))
        require(git_blob(source, Path(repo_path(Path(__file__).resolve()))) == Path(__file__).read_bytes(),
                "executed CI runner differs from its workflow source Git blob")
        require(args.request.resolve().is_relative_to(ROOT) and
                git_blob(source, Path(repo_path(args.request.resolve()))) == args.request.read_bytes(),
                "executed request differs from its workflow source Git blob")
        workflow_raw = git_blob(source, WORKFLOW)
        require(workflow_raw == (ROOT / WORKFLOW).read_bytes() and
                execution["workflow_sha"] == source, "workflow source identity differs")
        summary["workflow_binding"] = {
            "path": WORKFLOW.as_posix(), "source_commit": source, "sha256": sha(workflow_raw),
            "runner_path": repo_path(Path(__file__).resolve()), "runner_sha256": file_sha(Path(__file__)),
            "request_path": repo_path(args.request.resolve()), "request_sha256": file_sha(args.request),
        }
        write(PROOF / "request.json", request)
        if phase == "physical":
            summary["runs"] = {}
            retained = {run_id: validate_retained(run_id) for _, run_id, _ in RUNS}
        else:
            bindings = package_preflight(request, head)
            summary["release_source_commit"] = bindings["release_source_commit"]
            summary["git_bindings"] = bindings
        image_record = read(ROOT / IMAGE_RECORD)
        require(image_record["status"] == "PASS_G3_RELEASE_AND_PACKAGE" and
                image_record["tag"] == "v0.1.0-alpha.7" and
                image_record["image"] == PUBLIC_IMAGE and image_record["config_digest"] == PUBLIC_CONFIG,
                "E0046 record does not bind the expected public alpha.7 image")
        image = image_record["image"]
        summary["public_image_binding"] = {
            "record": IMAGE_RECORD.as_posix(), "record_sha256": file_sha(ROOT / IMAGE_RECORD),
            "record_commit": source if phase == "physical" else bindings["release_source_commit"],
            "tag": image_record["tag"], "source_commit": image_record["source_commit"],
            "image": image, "config_digest": image_record["config_digest"],
        }
        checked_capture(["docker", "version", "--format", "{{json .}}"], "docker-version")
        checked_capture(["docker", "pull", image], "image-pull", timeout=1200)
        inspected = inspect_image(image, "image-inspection-before")
        runtime_code = "import json,platform,sys; print(json.dumps({'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'executable':sys.executable},sort_keys=True))"
        container_runtime = json.loads(checked_capture(
            docker_command(image) + ["python3", "-c", runtime_code], "container-python-runtime"))
        require(container_runtime["platform"].startswith("Linux-") and
                container_runtime["machine"] == "x86_64", "unexpected actual container Python platform")
        runtime = dict(container_runtime, container_image={
            key: inspected[key] for key in ("Id", "RepoDigests", "Os", "Architecture")
        }, image_reference=image)
        write(PROOF / "runtime.json", {"ci_execution": execution, "container": runtime})
        if phase == "physical":
            for role, run_id, controls in RUNS:
                summary["runs"][role] = replay(role, run_id, controls, retained[run_id], image, runtime, execution)
        else:
            summary["package"] = package_release(bindings, image, runtime, execution)
        after = inspect_image(image, "image-inspection-after")
        require(all(after[key] == inspected[key] for key in ("Id", "RepoDigests", "Os", "Architecture")),
                "image identity changed during the actual replays")
        summary["status"] = ("PASS_G4_LINUX_PHYSICAL_REPLAYS" if phase == "physical"
                             else "PASS_G4_LINUX_RELEASE_PACKAGE")
        summary["runtime"] = runtime
        exit_code = 0
    except Exception as exc:
        summary["error"] = {"type": type(exc).__name__, "message": str(exc)}
        print(f"NOT_QUALIFIED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    finally:
        summary["completed_utc"] = now()
        summary["files"] = {p.relative_to(PROOF).as_posix(): {"bytes": p.stat().st_size, "sha256": file_sha(p)}
                            for p in sorted(PROOF.rglob("*")) if p.is_file()}
        write(PROOF / "run-summary.json", summary)
    print(summary["status"], flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
