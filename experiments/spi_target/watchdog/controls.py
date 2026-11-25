"""Execute faulty firmware and require a specific externally observable failure."""
import argparse
from pathlib import Path

from verify import (HERE, ROOT, assess, baseline, fresh_directory, json_gz, make_plan, observe,
                    prepare_sim)


# Each change uses original assembly syntax, the same cold loader, and real RTL.
MUTATIONS = {
    "watchdog_too_long": (".const POLLS 32", ".const POLLS 110", 1,
                          "missing_reply", "missing_reply_drive"),
    "watchdog_too_short": (".const POLLS 32", ".const POLLS 8", 1,
                           "normal-a4-1000-7", "reply_bit"),
    "halt_on_abort": ("on_timeout=rearm", "on_timeout=timeout_head", 21,
                      "reselect-a5-250-7-0-1", "reply_bit"),
    "wrong_reply_branch": ("pin=3 level=0 timeout=0 on_timeout=middle_first",
                           "pin=3 level=1 timeout=0 on_timeout=middle_first", 1,
                           "opcode-a4", "reply_bit"),
    "release_driven_zero": ("SET mask=8 value=0 oe=8\n    LOOP count=0 end=a_first",
                            "SET mask=8 value=0 oe=0\n    LOOP count=0 end=a_first", 1,
                            "opcode-a4", "reply_bit"),
    "premature_marker": ("rearm:\n    SET mask=8 value=0 oe=0",
                         "rearm:\n    SET mask=0x38 value=0x10 oe=0x30", 1,
                         "opcode-a5", "marker_without_terminal"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    out = fresh_directory(parser.parse_args().out)
    command, _ = prepare_sim(out, None)
    cases = baseline()
    original = (HERE / "target.asm").read_text(encoding="utf-8")
    records = {}
    for name, (old, new, expected_count, trial, reason) in MUTATIONS.items():
        if original.count(old) != expected_count:
            raise ValueError("mutation source anchor changed: " + name)
        image = make_plan(ROOT, original.replace(old, new), out, name)
        rows = observe(trial, cases[trial], out / (name + ".events"), command,
                       out / (name + ".plan"), image["clocked_load_steps"])
        verdict = assess(trial, cases[trial], rows)
        if reason not in {e["check"] for e in verdict["errors"]}:
            raise ValueError(f"{name} did not trigger {reason}: {verdict}")
        records[name] = dict(trial=trial, required_rejection=reason, image_sha256=image["binary_sha256"],
                             pins=rows, errors=verdict["errors"])
    json_gz(out / "controls.json.gz", records)
    print("Rejected", len(records), "firmware mutations at their specified observations")


if __name__ == "__main__":
    main()
