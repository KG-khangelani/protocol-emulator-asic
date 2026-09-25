"""Validate and explain the project's human fluency checkpoint state."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "docs" / "learning" / "progress.json"
EXPECTED_MILESTONES = [f"M{number}" for number in range(6)]
EXPECTED_LEVELS = [
    "NOT_DEMONSTRATED",
    "DEMONSTRATED_WITH_SUPPORT",
    "INDEPENDENT",
]
EXPECTED_GATES = ["NOT_STARTED", "PENDING", "PASS"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def evidence_directory(evidence_id: str) -> Path:
    matches = list((ROOT / "evidence").glob(f"{evidence_id}-*"))
    require(len(matches) == 1, f"{evidence_id} must identify exactly one evidence directory")
    return matches[0]


def validate(progress: dict) -> dict:
    require(
        progress["schema"] == "protocol-emulator-learning-progress-v1",
        "unexpected learning-progress schema",
    )
    require(progress["level_order"] == EXPECTED_LEVELS, "unexpected learning-level order")
    require(progress["gate_statuses"] == EXPECTED_GATES, "unexpected learning gate vocabulary")
    try:
        date.fromisoformat(progress["updated_utc"])
    except (TypeError, ValueError) as error:
        raise SystemExit("FAIL: learning-progress date must be YYYY-MM-DD") from error
    require(bool(progress["privacy_boundary"]), "learning progress needs a privacy boundary")

    milestones = progress["milestones"]
    require([item["id"] for item in milestones] == EXPECTED_MILESTONES, "expected ordered M0-M5 milestones")
    milestone_by_id = {item["id"]: item for item in milestones}
    require(progress["active_milestone"] in milestone_by_id, "active learning milestone is missing")

    level_index = {level: index for index, level in enumerate(EXPECTED_LEVELS)}
    skill_ids: set[str] = set()
    for milestone in milestones:
        technical = milestone["technical_gate"]
        fluency = milestone["fluency_gate"]
        require(technical["status"] in EXPECTED_GATES, f"invalid technical gate: {milestone['id']}")
        require(fluency["status"] in EXPECTED_GATES, f"invalid fluency gate: {milestone['id']}")
        require(
            fluency["required_level"] in EXPECTED_LEVELS[1:],
            f"invalid required learning level: {milestone['id']}",
        )
        require(bool(milestone["skills"]), f"{milestone['id']} must define at least one fluency skill")

        for evidence_id in technical["evidence"]:
            require(re.fullmatch(r"E\d{4}", evidence_id) is not None, f"invalid evidence ID: {evidence_id}")
            evidence_directory(evidence_id)
        if technical["status"] == "PASS":
            require(bool(technical["evidence"]), f"{milestone['id']} technical PASS needs evidence")
        elif technical["status"] == "NOT_STARTED":
            require(not technical["evidence"], f"{milestone['id']} has evidence before technical work started")

        for skill in milestone["skills"]:
            require(skill["id"] not in skill_ids, f"duplicate learning skill: {skill['id']}")
            skill_ids.add(skill["id"])
            require(skill["status"] in EXPECTED_LEVELS, f"invalid skill level: {skill['id']}")
            require(bool(skill["description"]), f"missing skill description: {skill['id']}")
            require(bool(skill["resources"]), f"missing learning resource: {skill['id']}")
            for resource in skill["resources"]:
                require((ROOT / resource).is_file(), f"missing learning resource: {resource}")

        required_index = level_index[fluency["required_level"]]
        demonstrated = all(level_index[skill["status"]] >= required_index for skill in milestone["skills"])
        if fluency["status"] == "PASS":
            require(technical["status"] == "PASS", f"{milestone['id']} fluency cannot pass before technical work")
            require(demonstrated, f"{milestone['id']} fluency PASS lacks required demonstrations")
            require(isinstance(fluency["record"], dict), f"{milestone['id']} fluency PASS needs a record")
        else:
            require(fluency["record"] is None, f"{milestone['id']} non-pass gate must not claim a pass record")

    return progress


def load_and_validate() -> dict:
    return validate(json.loads(PROGRESS.read_text(encoding="utf-8")))


def reject_unearned_pass(progress: dict) -> None:
    corrupted = deepcopy(progress)
    active = next(
        item for item in corrupted["milestones"] if item["id"] == corrupted["active_milestone"]
    )
    active["fluency_gate"]["status"] = "PASS"
    active["fluency_gate"]["record"] = {
        "kind": "deliberately invalid self-test record"
    }
    try:
        validate(corrupted)
    except SystemExit as error:
        require(
            "fluency PASS lacks required demonstrations" in str(error),
            "invalid fluency promotion failed for an unexpected reason",
        )
        return
    require(False, "validator accepted an unearned fluency PASS")


def print_status(progress: dict) -> None:
    print("PROJECT LEARNING STATUS - technical proof and human understanding stay separate")
    print("=" * 78)
    for milestone in progress["milestones"]:
        print(
            f"{milestone['id']} {milestone['name']:<25} "
            f"technical={milestone['technical_gate']['status']:<11} "
            f"fluency={milestone['fluency_gate']['status']}"
        )

    active = next(item for item in progress["milestones"] if item["id"] == progress["active_milestone"])
    required = active["fluency_gate"]["required_level"]
    level_index = {level: index for index, level in enumerate(EXPECTED_LEVELS)}
    complete = sum(level_index[skill["status"]] >= level_index[required] for skill in active["skills"])
    print(f"\nACTIVE CHECKPOINT: {active['id']} - {active['name']}")
    print(f"Required this milestone: {required.replace('_', ' ').title()}")
    print(f"Demonstrated at that level: {complete}/{len(active['skills'])}")
    for skill in active["skills"]:
        mark = "x" if level_index[skill["status"]] >= level_index[required] else " "
        print(f"  [{mark}] {skill['description']} ({skill['status']})")

    print("\nAUTOMATION BOUNDARY")
    print("The repository can verify commands, artifacts, and this record's consistency.")
    print("It cannot infer understanding from green CI or promote the fluency gate automatically.")
    print(f"Privacy: {progress['privacy_boundary']}")

    if active["id"] == "M0" and active["fluency_gate"]["status"] != "PASS":
        print("\nNEXT SMALL TEACH-BACK")
        print("1. Complete: Generic synthesis establishes ____. It cannot establish ____. E0010 adds ____.")
        print("2. Choose the hold or reset-wins waveform row; name rst_n and ena, then explain the output.")
        print("An incomplete answer is expected evidence for what we should explain next, not a failure.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="validate the progress record without printing the full learning status",
    )
    args = parser.parse_args()
    progress = load_and_validate()
    if args.verify:
        reject_unearned_pass(progress)
        print("PASS: learning milestones, evidence references, resources, statuses, and gate rules agree.")
        print("FALSIFICATION: PASS - an unearned active-milestone fluency promotion was rejected.")
        print("LIMIT: structural consistency cannot demonstrate a person's understanding.")
        return
    print_status(progress)


if __name__ == "__main__":
    main()
