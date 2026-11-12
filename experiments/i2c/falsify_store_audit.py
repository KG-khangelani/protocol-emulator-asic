# SPDX-License-Identifier: Apache-2.0
"""Attempt to make the memory-proof auditor accept corrupted real summaries."""
import argparse
import copy
import json
from pathlib import Path

from audit_store_proofs import audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "preserve earlier controls"
    original = json.loads(args.snapshot.read_bytes())
    assert audit(args.positive, args.controls, "od128", args.snapshot.read_bytes())["status"] == "PASS_COMPLETE_VARIANT_STORE_PROOF"
    results = []
    for mutation in ("missing_state_group", "missing_read_group", "duplicate_group", "missing_assertion",
                     "missing_cover", "incomplete_word_coverage", "wrong_source", "failed_proof", "missing_cover_witness"):
        changed = copy.deepcopy(original)
        tasks = changed["tasks"]
        state = next(t for t in tasks if t["variant"] == "od128" and t["name"] == "state")
        read = next(t for t in tasks if t["variant"] == "od128" and t["name"] == "read")
        cover = next(t for t in tasks if t["variant"] == "od128" and t["name"] == "cover")
        if mutation == "missing_state_group":
            tasks.remove(state)
        elif mutation == "missing_read_group":
            tasks.remove(read)
        elif mutation == "duplicate_group":
            tasks.append(copy.deepcopy(state))
        elif mutation == "missing_assertion":
            state["selected_assertions"].pop()
        elif mutation == "missing_cover":
            tasks.remove(cover)
        elif mutation == "incomplete_word_coverage":
            state["word_indices"].pop()
        elif mutation == "wrong_source":
            changed["sources"]["od128"] = "0" * 64
        elif mutation == "failed_proof":
            state["status"] = "FAIL"
        elif mutation == "missing_cover_witness":
            cover["witnesses"].pop(next(iter(cover["witnesses"])))
        try:
            audit(args.positive, args.controls, "od128", json.dumps(changed).encode())
        except AssertionError:
            results.append({"mutation": mutation, "rejected": True})
        else:
            raise AssertionError("corrupted summary accepted: " + mutation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps({"status": "PASS_AUDITOR_NEGATIVE_CONTROLS", "controls": results,
                                       "scope": "Evidence-checker falsification, not additional RTL coverage"}, indent=2) + "\n").encode())
    print("PASS:", len(results), "corrupted proof summaries rejected")


if __name__ == "__main__":
    main()
