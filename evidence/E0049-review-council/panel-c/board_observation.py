"""Check the result again using dedicated output and resolved pads; omit debug OE."""
import argparse
import collections
import gzip
import json
from pathlib import Path


def pad_view(path):
    edges = []
    for line in gzip.decompress(path.read_bytes()).splitlines():
        if line.startswith(b"EDGE "):
            _, index, status, _macro_oe, pads = line.split()
            if int(index) != len(edges):
                raise ValueError(f"record discontinuity in {path}")
            edges.append((int(status, 16), int(pads, 16)))
    return edges


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run
    result = json.loads((run / "result.json").read_bytes())
    if result["status"] != "PASS_BOUNDED_DIGITAL_SCREEN":
        raise ValueError("an incomplete run cannot supply the positive screen")
    flush_patterns = collections.Counter()
    summary = {"released_programs": 0, "load_steps_per_positive_profile": 0,
               "released_ena_low_requests": 0, "runtime_edges_per_positive_profile": 0,
               "powered_identical_after_run": 0, "naive_different_after_run": 0}
    for name, example in result["examples"].items():
        steps, words = example["load_steps"], example["words"]
        bank_count = (words + 7) // 8
        if steps != 8 * words + 2 * bank_count + 10 or example["requests_ena_low"] != 4 * words + 7:
            raise ValueError(f"unexpected protocol counts for {name}")
        reference, naive, powered = [pad_view(run / "traces" / f"{name}-{v}.trace.gz")
                                    for v in ("reference", "naive", "powered")]
        if any(len(trace) != steps + example["runtime_edges"] for trace in (reference, naive, powered)):
            raise ValueError(f"incomplete trial for {name}")
        flush_patterns[tuple(f"{trace[steps - 2][0]:02x}" for trace in (reference, naive, powered))] += 1
        summary["released_programs"] += 1
        summary["load_steps_per_positive_profile"] += steps
        summary["released_ena_low_requests"] += example["requests_ena_low"]
        summary["runtime_edges_per_positive_profile"] += example["runtime_edges"]
        summary["powered_identical_after_run"] += int(reference[steps:] == powered[steps:])
        summary["naive_different_after_run"] += int(reference[steps:] != naive[steps:])
    summary["first_flush_dedicated_status_reference_naive_powered_hex"] = [
        {"status": list(pattern), "examples": count} for pattern, count in flush_patterns.items()]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
