# SPDX-License-Identifier: Apache-2.0
"""Compare the already measured VM and common PIO MOSI/SCK/CS ports through terminal."""
import argparse
import gzip
import json
from pathlib import Path


def read_gzip(path):
    return gzip.decompress(path.read_bytes())


def resolved(port):
    output, enable = port
    return (output & enable) | (8 & ~enable)


def compare(vm_dir, pio_dir):
    vm_cases = json.loads(read_gzip(vm_dir / "results.json.gz"))["observations"]
    actual_vm = [tuple(int(field, 16) for field in row.split()) for row in
                 read_gzip(vm_dir / "final-row-trace.txt.gz").splitlines()]
    vm = {}
    start = 0
    for case in vm_cases:
        edge_zero = start + case["load_steps"] - 1
        end = edge_zero + case["halt_edge"] + 1
        if (case["family"], case["profile"], case["expected_rx"]) == ("exact", "edge_only", 0x69):
            vm[case["mode"], case["order"]] = [(row[1], row[2]) for row in actual_vm[edge_zero:end]]
        start = end
    if start != len(actual_vm):
        raise ValueError("unaccounted VM rows")
    pio_cases = json.loads(read_gzip(pio_dir / "stage-04.json.gz"))["observations"]
    actual_pio = read_gzip(pio_dir / "final-public-rows.bin.gz")
    start = 0
    checks = []
    for case in pio_cases:
        # H=25, eight complete bits, extra last half-cycle for CPHA1, one terminal clock.
        end_edge = case["cs_assumed_and_scored"] + 400 + 25 * (case["mode"] & 1) + 1
        end = start + 3 * (end_edge + 1)
        if (case["boundary"], case["control"], case["profile"], case["requested_rx"]) == (
                "gpio_resident", "pass", "edge_only", 0x69):
            reference = vm[case["mode"], case["order"]]
            alternate = [(actual_pio[i], actual_pio[i+1]) for i in range(start, end, 3)]
            if len(reference) != len(alternate) or case["tx"] != 0x96:
                raise ValueError("unmatched case")
            enable_diff = [i for i, (a, b) in enumerate(zip(reference, alternate)) if a[1] != b[1]]
            resolved_diff = [i for i, (a, b) in enumerate(zip(reference, alternate)) if resolved(a) != resolved(b)]
            if enable_diff != [0] or resolved_diff != ([0] if case["mode"] >= 2 else []):
                raise ValueError("startup phenotype differs")
            checks.append({"mode": case["mode"], "order": case["order"], "rows": len(reference),
                           "vm_edge0_output_enable": reference[0], "pio_edge0_output_enable": alternate[0],
                           "enable_difference_edges": enable_diff, "resolved_difference_edges": resolved_diff})
        start = end
    if start != len(actual_pio) or len(checks) != 8:
        raise ValueError("unaccounted PIO rows or missing matched cases")
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vm_records", type=Path)
    parser.add_argument("pio_records", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.vm_records, args.pio_records), indent=2))
