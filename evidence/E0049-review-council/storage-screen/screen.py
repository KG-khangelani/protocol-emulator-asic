# SPDX-License-Identifier: Apache-2.0
"""Measure a per-image word dictionary on the exact G4 and G5 program releases."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT))
from tools.assembler import assemble, program_bytes


def check(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(raw):
    check(4 <= len(raw) <= 512 and len(raw) % 4 == 0, "invalid word count")
    words = [raw[pos:pos + 4] for pos in range(0, len(raw), 4)]
    dictionary = list(dict.fromkeys(words))
    indexes = {word: index for index, word in enumerate(dictionary)}
    width = (len(dictionary) - 1).bit_length()
    packed = sum(indexes[word] << (width * pc) for pc, word in enumerate(words))
    payload = packed.to_bytes((width * len(words) + 7) // 8, "little")
    header = bytes((1, len(words), len(dictionary), width))
    return header + b"".join(dictionary) + payload


def decode(blob):
    check(len(blob) >= 4, "short header")
    version, size, count, width = blob[:4]
    check(version == 1 and 1 <= count <= size <= 128, "invalid header")
    check(width == (count - 1).bit_length(), "noncanonical width")
    start = 4 + 4 * count
    check(len(blob) == start + (size * width + 7) // 8, "incorrect encoded size")
    words = [blob[p:p + 4] for p in range(4, start, 4)]
    check(len(set(words)) == count, "repeated dictionary entry")
    packed = int.from_bytes(blob[start:], "little")
    decoded = bytearray()
    for pc in range(size):
        index = (packed >> (pc * width)) & ((1 << width) - 1)
        check(index < count, "unused dictionary index")
        decoded.extend(words[index])
    check(packed >> (size * width) == 0, "nonzero padding")
    return bytes(decoded)


def measure(raw):
    blob = encode(raw)
    check(decode(blob) == raw, "decoded program mismatch")
    return {"words": len(raw) // 4, "distinct_words": blob[2], "index_bits": blob[3],
            "original_bytes": len(raw), "dictionary_bytes": len(blob),
            "change_bytes": len(blob) - len(raw), "fraction_of_original": round(len(blob) / len(raw), 6),
            "original_sha256": sha(raw), "dictionary_sha256": sha(blob)}


def read_artifact(directory, archive_id, prefix):
    path = directory / f"{archive_id}.zip"
    row = next(a for a in json.loads((directory / "artifacts.json").read_bytes())["artifacts"]
               if a["id"] == archive_id)
    digest = sha(path.read_bytes())
    check(row["digest"] == "sha256:" + digest and row["size_in_bytes"] == path.stat().st_size, path.name)
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.startswith(prefix) and n.endswith("/program.bin")]
        return digest, {n[len(prefix):-len("/program.bin")]: archive.read(n) for n in names}


def controls():
    def program(lines):
        return program_bytes(assemble(".target od128-sram-v1\n" + "\n".join(lines) + "\n"))

    cases = {"three_words_partial_byte": program(["WAIT cycles=0", "WAIT cycles=1", "HALT"] * 7),
             "two_values_cross_byte": program(["WAIT cycles=1", "HALT"] * 11),
             "one_word": program(["HALT"]), "all_equal_128": program(["HALT"] * 128),
             "all_distinct_128": program([f"WAIT cycles={n}" for n in range(127)] + ["HALT"])}
    good = encode(cases["three_words_partial_byte"])
    damaged = {"out_of_range_index": good[:-1] + bytes([3]),
               "short_stream": good[:-1], "extra_data": good + b"\0",
               "wrong_width": good[:3] + bytes([3]) + good[4:],
               "nonzero_padding": good[:-1] + bytes([good[-1] | 128])}
    rejected = {}
    for name, blob in damaged.items():
        try:
            decode(blob)
        except ValueError as exc:
            rejected[name] = str(exc)
        else:
            raise ValueError("accepted damaged dictionary: " + name)
    return {name: measure(raw) for name, raw in cases.items()}, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    output = parser.parse_args().output.resolve()
    check(output.is_relative_to(ROOT / "build") and not output.exists(), "use a new file under build")
    started = datetime.now(timezone.utc).isoformat()
    g4 = ROOT / "evidence/E0047-g4-submission-candidate/program-tools"
    g5 = ROOT / "evidence/E0048-waveform-replay"
    first, originals = read_artifact(g4, 14094030144, "examples/")
    second, continuous = read_artifact(g5 / "ci-66743b6", 14155007514, "g3-continuity/examples/")
    _, wave = read_artifact(g5 / "ci-66743b6", 14155007514, "primary/programs/")
    _, wave_replay = read_artifact(g5 / "ci-66743b6", 14155007514, "reproduction/programs/")
    check(len(originals) == 13 and originals == continuous, "G3 continuity")
    check(len(wave) == 2 and wave == wave_replay and not set(wave) & set(originals), "G5 continuity")
    for name, raw in wave.items():
        check(raw == (g5 / "windows-build-66743b6/programs" / name / "program.bin").read_bytes(),
              "cross-platform identity " + name)
    programs = {name: measure(raw) for name, raw in (originals | wave).items()}
    synthetic, rejected = controls()
    values = list(programs.values())
    totals = {field: sum(item[field] for item in values) for field in ("original_bytes", "dictionary_bytes")}
    maximum = {field: max(item[field] for item in values) for field in totals}
    result = {"started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
              "artifacts_sha256": {"14094030144": first, "14155007514": second}, "images": programs,
              "collection_bytes": totals, "peak_single_image_bytes": maximum,
              "images_shrunk": sum(item["change_bytes"] < 0 for item in values),
              "images_equal": sum(item["change_bytes"] == 0 for item in values),
              "images_grown": sum(item["change_bytes"] > 0 for item in values),
              "synthetic": synthetic, "rejected": rejected}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(totals, maximum, result["images_shrunk"], "of", len(programs), "smaller")


if __name__ == "__main__":
    main()
