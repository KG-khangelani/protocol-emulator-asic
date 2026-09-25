"""Compare GDSII records while isolating standard timestamp fields."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


TIMESTAMP_RECORDS = {0x01: "BGNLIB", 0x05: "BGNSTR"}
RECORD_NAMES = {
    0x00: "HEADER",
    0x01: "BGNLIB",
    0x02: "LIBNAME",
    0x03: "UNITS",
    0x04: "ENDLIB",
    0x05: "BGNSTR",
    0x06: "STRNAME",
    0x07: "ENDSTR",
}


def parse_records(path: Path) -> tuple[bytes, list[tuple[int, int, int, bytes]]]:
    data = path.read_bytes()
    records: list[tuple[int, int, int, bytes]] = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < 4:
            raise ValueError(f"{path}: truncated GDS record header at byte {offset}")
        length = int.from_bytes(data[offset : offset + 2], "big")
        record_type = data[offset + 2]
        data_type = data[offset + 3]
        if length < 4 or length % 2:
            raise ValueError(f"{path}: invalid record length {length} at byte {offset}")
        end = offset + length
        if end > len(data):
            raise ValueError(f"{path}: record at byte {offset} extends past end of file")
        records.append((length, record_type, data_type, data[offset:end]))
        offset = end
    return data, records


def normalized_hash(records: list[tuple[int, int, int, bytes]]) -> str:
    digest = hashlib.sha256()
    for length, record_type, data_type, raw in records:
        digest.update(length.to_bytes(2, "big"))
        digest.update(bytes((record_type, data_type)))
        if record_type in TIMESTAMP_RECORDS:
            digest.update(bytes(length - 4))
        else:
            digest.update(raw[4:])
    return digest.hexdigest()


def file_identity(path: Path, data: bytes, records: list[tuple[int, int, int, bytes]]) -> dict[str, object]:
    return {
        "path": str(path),
        "size_in_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "record_count": len(records),
        "timestamp_normalized_sha256": normalized_hash(records),
    }


def compare(left_path: Path, right_path: Path) -> dict[str, object]:
    left_data, left_records = parse_records(left_path)
    right_data, right_records = parse_records(right_path)
    left_shape = [(length, record_type, data_type) for length, record_type, data_type, _ in left_records]
    right_shape = [(length, record_type, data_type) for length, record_type, data_type, _ in right_records]
    structure_equal = left_shape == right_shape

    different_bytes = sum(a != b for a, b in zip(left_data, right_data))
    different_bytes += abs(len(left_data) - len(right_data))
    timestamp_differences: Counter[str] = Counter()
    non_timestamp_differences: Counter[str] = Counter()
    different_records = 0

    if structure_equal:
        for left, right in zip(left_records, right_records):
            _, record_type, _, left_raw = left
            _, _, _, right_raw = right
            if left_raw == right_raw:
                continue
            different_records += 1
            name = RECORD_NAMES.get(record_type, f"RECORD_0x{record_type:02X}")
            if record_type in TIMESTAMP_RECORDS:
                timestamp_differences[name] += 1
            else:
                non_timestamp_differences[name] += 1

    left_identity = file_identity(left_path, left_data, left_records)
    right_identity = file_identity(right_path, right_data, right_records)
    equivalent = (
        structure_equal
        and not non_timestamp_differences
        and left_identity["timestamp_normalized_sha256"]
        == right_identity["timestamp_normalized_sha256"]
    )
    return {
        "schema": "gds-record-comparison-v1",
        "left": left_identity,
        "right": right_identity,
        "record_structure_equal": structure_equal,
        "different_records": different_records if structure_equal else None,
        "different_bytes": different_bytes,
        "timestamp_record_differences": dict(sorted(timestamp_differences.items())),
        "non_timestamp_record_differences": dict(sorted(non_timestamp_differences.items())),
        "equivalent_except_timestamps": equivalent,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two GDSII files and report whether only BGNLIB/BGNSTR timestamps differ."
    )
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = compare(args.left, args.right)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["equivalent_except_timestamps"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
