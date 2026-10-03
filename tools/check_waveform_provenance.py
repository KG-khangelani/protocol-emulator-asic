"""Bind each retained Icarus waveform to its actual regression and checksum."""

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "build/rtl-icarus-waveform-checkpoint.json"
MANIFEST = ROOT / "build/waveform-provenance.json"
RTL_WAVEFORM = ROOT / "test/tb.fst"
RTL_JUNIT = ROOT / "test/results.xml"
GL_WAVEFORM = ROOT / "test/tb-gl-harness.fst"
GL_JUNIT = ROOT / "test/results-gl-harness.xml"
SCHEMA = "protocol-emulator-waveform-provenance-v1"


class ProvenanceError(RuntimeError):
    """Raised when an artifact cannot support its claimed simulation label."""


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path):
    path = path.resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _require_file(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise ProvenanceError(f"missing or empty artifact: {_display_path(path)}")


def _junit_summary(path):
    _require_file(path)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ProvenanceError(f"invalid JUnit XML: {_display_path(path)}") from exc
    cases = list(root.iter("testcase"))
    if not cases:
        raise ProvenanceError(f"JUnit has no cases: {_display_path(path)}")
    for tag in ("failure", "error", "skipped"):
        if list(root.iter(tag)):
            raise ProvenanceError(f"JUnit contains {tag}: {_display_path(path)}")
    return {
        "modules": sorted({case.get("classname", "") for case in cases}),
        "tests": [case.get("name", "") for case in cases],
        "total_sim_time_ns": sum(float(case.get("sim_time_ns", "0")) for case in cases),
    }


def _fingerprint(label, waveform, junit):
    _require_file(waveform)
    summary = _junit_summary(junit)
    return {
        "label": label,
        "waveform": {
            "path": _display_path(waveform),
            "bytes": waveform.stat().st_size,
            "sha256": _sha256(waveform),
        },
        "junit": {
            "path": _display_path(junit),
            "bytes": junit.stat().st_size,
            "sha256": _sha256(junit),
            **summary,
        },
    }


def create_checkpoint(waveform=RTL_WAVEFORM, junit=RTL_JUNIT):
    return {"schema": SCHEMA, "simulation": _fingerprint("rtl_icarus", waveform, junit)}


def build_manifest(
    checkpoint,
    rtl_waveform=RTL_WAVEFORM,
    rtl_junit=RTL_JUNIT,
    gl_waveform=GL_WAVEFORM,
    gl_junit=GL_JUNIT,
):
    if checkpoint.get("schema") != SCHEMA:
        raise ProvenanceError("unexpected waveform checkpoint schema")
    rtl = _fingerprint("rtl_icarus", rtl_waveform, rtl_junit)
    if checkpoint.get("simulation") != rtl:
        raise ProvenanceError("rtl_icarus artifacts changed after their checkpoint")
    gl = _fingerprint("gl_harness_smoke", gl_waveform, gl_junit)
    if rtl["junit"]["modules"] != ["test"]:
        raise ProvenanceError("rtl_icarus label does not point to the full test module")
    if gl["junit"]["modules"] != ["test_gate_harness_smoke"]:
        raise ProvenanceError("gl_harness_smoke label does not point to its smoke module")
    if gl["junit"]["tests"] != ["public_handles_reset_without_direct_engine"]:
        raise ProvenanceError("unexpected GL-shaped harness test set")
    if rtl["waveform"]["sha256"] == gl["waveform"]["sha256"]:
        raise ProvenanceError("distinct simulations produced indistinguishable waveform files")
    if rtl["junit"]["total_sim_time_ns"] <= gl["junit"]["total_sim_time_ns"]:
        raise ProvenanceError("rtl_icarus and GL-shaped smoke labels appear swapped")
    return {
        "schema": SCHEMA,
        "simulations": {
            "rtl_icarus": rtl,
            "gl_harness_smoke": gl,
        },
    }


def validate_saved_manifest(path=MANIFEST):
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"cannot read provenance manifest: {_display_path(path)}") from exc
    expected = build_manifest(json.loads(CHECKPOINT.read_text()))
    if manifest != expected:
        raise ProvenanceError("saved waveform provenance does not match current artifacts")
    expected_paths = {
        "rtl_icarus": ("test/tb.fst", "test/results.xml"),
        "gl_harness_smoke": ("test/tb-gl-harness.fst", "test/results-gl-harness.xml"),
    }
    for label, (waveform, junit) in expected_paths.items():
        record = manifest["simulations"][label]
        if (record["waveform"]["path"], record["junit"]["path"]) != (waveform, junit):
            raise ProvenanceError(f"{label} uses an unexpected artifact path")
    return manifest


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("checkpoint", "verify", "validate"))
    args = parser.parse_args()
    try:
        if args.command == "checkpoint":
            _write_json(CHECKPOINT, create_checkpoint())
            print("PASS: checkpointed rtl_icarus waveform and JUnit checksums")
        elif args.command == "verify":
            checkpoint = json.loads(CHECKPOINT.read_text())
            _write_json(MANIFEST, build_manifest(checkpoint))
            validate_saved_manifest()
            print("PASS: rtl_icarus and gl_harness_smoke artifacts retain distinct labels and checksums")
        else:
            validate_saved_manifest()
            print("PASS: saved waveform provenance matches current artifacts")
    except (OSError, json.JSONDecodeError, ProvenanceError) as exc:
        raise SystemExit(f"FAIL: {exc}") from exc


if __name__ == "__main__":
    main()
