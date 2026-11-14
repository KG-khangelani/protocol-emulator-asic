# SPDX-License-Identifier: Apache-2.0
"""Capture genuine Linux replays; install beside request.json on the isolated branch.

Only the physical phase is implemented. Docker is used only when main() runs.
Original archives and reconstructed audit output stay outside the uploaded proof.
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


ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / "build/g4-ci-proof"
SCRATCH = ROOT / "build/g4-linux-physical-replays"
CONTAINER_SCRATCH = "/workspace/build/g4-linux-physical-replays"
E47 = Path("evidence/E0047-g4-submission-candidate")
IMAGE_RECORD = Path("evidence/E0046-program-toolchain/publication/release-verification.json")
PHYSICAL_SOURCE = "45c55f7cd95db2a883b0ffb5e864decd62d53601"
PUBLIC_IMAGE = "ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:f487aaf03906535a3187690557ff97ca1707e966b48ae8a99362683b5f68e307"
PUBLIC_CONFIG = "sha256:6f45e71162641466c4e9e08601a383c8a081c06b263114903a181d5f8f971451"
RUNS = (("candidate", 43543626249, False), ("reproduction", 43543629839, True))
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    require(not PROOF.exists() and not SCRATCH.exists(), "proof and replay directories must be fresh")
    PROOF.mkdir(parents=True)
    SCRATCH.mkdir(parents=True)
    summary = {
        "schema": "protocol-emulator-g4-linux-proof-v1", "status": "NOT_QUALIFIED",
        "started_utc": now(), "phase": "physical", "runs": {},
        "scope": "Replay of frozen retained physical qualification in the public Linux image. "
                 "This is not a new physical producer, release publication, or contest submission.",
    }
    exit_code = 1
    try:
        request = read(args.request)
        require(request.get("schema") == "protocol-emulator-g4-linux-request-v1" and
                request.get("phase") == "physical", "only the physical request phase is implemented")
        requested = request.get("source", "HEAD")
        require(requested == "HEAD" or re.fullmatch(r"[0-9a-f]{40}", requested) is not None,
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
        write(PROOF / "request.json", request)
        retained = {run_id: validate_retained(run_id) for _, run_id, _ in RUNS}
        image_record = read(ROOT / IMAGE_RECORD)
        require(image_record["status"] == "PASS_G3_RELEASE_AND_PACKAGE" and
                image_record["tag"] == "v0.1.0-alpha.7" and
                image_record["image"] == PUBLIC_IMAGE and image_record["config_digest"] == PUBLIC_CONFIG,
                "E0046 record does not bind the expected public alpha.7 image")
        image = image_record["image"]
        summary["public_image_binding"] = {
            "record": IMAGE_RECORD.as_posix(), "record_sha256": file_sha(ROOT / IMAGE_RECORD),
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
        for role, run_id, controls in RUNS:
            summary["runs"][role] = replay(role, run_id, controls, retained[run_id], image, runtime, execution)
        after = inspect_image(image, "image-inspection-after")
        require(all(after[key] == inspected[key] for key in ("Id", "RepoDigests", "Os", "Architecture")),
                "image identity changed during the actual replays")
        summary["status"] = "PASS_G4_LINUX_PHYSICAL_REPLAYS"
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
