# SPDX-License-Identifier: Apache-2.0
"""Public-pin screen of E0027 EXACT firmware on the production 0x22 core."""
import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def word_vector(ui, data, *, host, target, enable, reset_n, run):
    return (ui | data << 8 | int(host) << 16 | int(target) << 17 |
            enable << 18 | reset_n << 19 | int(run) << 20)


def load_step(step):
    return word_vector(step["ui_in"], step["uio_in"], host=step["host_drives_uio"],
                       target=step["action"] == "flush_idle", enable=step["ena"],
                       reset_n=step["rst_n"], run=False)


def programs(root, assemble):
    folder = root / "programs/od128-sram-v1"
    catalog = json.loads((folder / "examples.json").read_bytes())
    indexed = {entry["name"]: entry for entry in catalog["examples"]}
    old = root / "evidence/E0027-four-mode-schedule-screen/reference-witnesses.json.gz"
    witnesses = json.loads(gzip.decompress(old.read_bytes()))
    historical = {(c["mode"], c["order"]): c["encoded_words"] for w in witnesses
                  if (c := w["case"])["family"] == "exact"}
    result = {}
    for mode in range(4):
        for order, suffix in enumerate(("lsb", "msb")):
            name = f"spi_mode{mode}_{suffix}"
            text = (folder / (name + ".asm")).read_text(encoding="utf-8")
            check(text.count("delay=HALF-2") == 1, f"unexpected SAMPLE in {name}")
            variants = {
                "held": text,
                "exact": text.replace("delay=HALF-2", "delay=1\n    WAIT cycles=HALF-4"),
                "early": text.replace("delay=HALF-2", "delay=0\n    WAIT cycles=HALF-3"),
            }
            encoded = {kind: assemble(source) for kind, source in variants.items()}
            check(encoded["held"]["words"] == indexed[name]["expected_words"], name + " catalog")
            check(encoded["exact"]["words"] == historical[mode, order], name + " E0027 bytes")
            check(len(encoded["exact"]["words"]) == (11 if mode & 1 else 9), name + " length")
            result.update({(mode, order, kind): program for kind, program in encoded.items()})
    return result


def make_cases(images, timing, raw_at, load_plan):
    cases = []
    tests = [("exact", "edge_only", rx, 96) for rx in (0x69, *(1 << j for j in range(8)))]
    tests += [("exact", "held", 0x69, 1), ("exact", "held", 0x69, 96),
              ("held", "held", 0x69, 96), ("held", "edge_only", 0x69, 96),
              ("early", "edge_only", 0x69, 96)]
    for mode in range(4):
        for order in (0, 1):
            schedule = timing(mode, 2 if mode & 1 else 3)
            for kind, profile, rx, delay in tests:
                image = images[mode, order, kind]
                name = f"m{mode}-o{order}-{kind}-{profile}-r{rx:02x}-d{delay}"
                script = load_plan(image)["steps"]
                levels = [raw_at(edge, schedule, rx, order, profile, [delay] * 8)
                          for edge in range(1, schedule["halt"] + 1)]
                cases.append((name, mode, order, kind, profile, rx, delay, image, schedule, script, levels))
    return cases


def observe(root, out, image, prepared, vendor):
    def docker_run(label, command):
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False, timeout=150)
        (out / (label + ".log")).write_bytes(result.stdout)
        check(result.returncode == 0, f"{label} failed; see {label}.log")
        return result.stdout.decode("utf-8", errors="replace")

    identity = docker_run("inspect", ["docker", "image", "inspect", image, "--format", "{{.Id}}"]).strip()
    base = ["docker", "run", "--pull=never", "--rm", "--network", "none", "--read-only",
            "--env", "TMPDIR=/work", "--mount", f"type=bind,source={root},target=/repo,readonly",
            "--mount", f"type=bind,source={out},target=/work", "--workdir", "/work", identity]
    version = docker_run("version", [*base, "iverilog", "-V"]).splitlines()[0]
    rtl = ["/repo/src/" + name for name in prepared]
    docker_run("build", [*base, "iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS",
                         "-s", "spi_trace_tb", "-o", "spi.vvp", "spi_trace_tb.sv",
                         *rtl, *vendor])
    docker_run("run", [*base, "vvp", "spi.vvp"])
    return identity, version


def check_case(case, observations, assess):
    name, mode, order, kind, profile, rx, delay, image, schedule, script, levels = case
    for step in script:
        status, out_byte, oe, resolved, _, _ = next(observations)
        actual = {"uo_out": status, "uio_out": out_byte, "uio_oe": oe}
        check(all(actual[k] == v for k, v in step["expected"].items()), name + " " + step["action"])
        if "uio_out" in step["expected"]:
            check(resolved == step["expected"]["uio_out"], name + " physical readback")
    rows = [{"edge": 0, "out": out_byte, "oe": oe, "miso": 1, "rx": 0,
             "rx_valid": 0, "state": "RUN"}]
    driven = bytearray([out_byte, oe])
    for edge, miso in enumerate(levels, 1):
        status, out_byte, oe, pins, value, valid = next(observations)
        check((status & 0x20) != 0, name + " ready dropped")
        check(pins == (out_byte & oe) | ((8 | (miso << 1)) & ~oe), name + " resolved pins")
        rows.append({"edge": edge, "out": out_byte, "oe": oe, "miso": (pins >> 1) & 1,
                     "rx": value, "rx_valid": valid, "state": ("RUN", "WAIT", "HALT", "FAULT")[status >> 6]})
        driven.extend([out_byte, oe])
    delta = {"exact": 2, "held": 24, "early": 1}[kind]
    capture = [n + delta for n in schedule["sample"]]
    errors = assess(rows, schedule, 0x96, rx, order, capture)
    expected_ok = kind == "exact" or profile == "held"
    errors_found = sorted({e["kind"] for e in errors})
    check(errors_found == ([] if expected_ok else ["received_byte"]), f"{name} {errors[:2]}")
    check(value == (rx if expected_ok else rx ^ 255), name + " byte control")
    expected_pc = len(image["words"]) - 1
    check(status == 0xa0 | expected_pc, name + " terminal PC")
    return {"case": name, "mode": mode, "order": order, "family": kind, "profile": profile,
            "tx": 0x96, "expected_rx": rx, "observed_rx": value, "error_kinds": errors_found,
            "first_valid_edge": next(r["edge"] for r in rows if r["rx_valid"]),
            "halt_edge": rows[-1]["edge"], "halt_pc": expected_pc, "load_steps": len(script),
            "driven_and_oe_sha256": digest(driven), "binary_sha256": image["binary_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True, help="new isolated output directory")
    parser.add_argument("--image", required=True, help="installed Docker image with Icarus")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(root))
    from tools.assembler import assemble, load_plan
    from tools.spi_four_mode_oracle import assess, raw_at, timing
    src = json.loads((root / "evidence/E0042-sram-prefetch-screen/candidate.json").read_bytes())
    for name, h in src["source_sha256"].items():
        check(digest((root / "src" / name).read_bytes()) == h, name)
    models = root / "evidence/E0042-sram-prefetch-screen/feasibility/verilog"
    for name, h in src["model_sha256"].items():
        raw = gzip.decompress((models / (name + ".gz")).read_bytes())
        check(digest(raw) == h, name)
        (out / name).write_bytes(raw)
    tb = Path(__file__).with_name("spi_trace_tb.sv")
    shutil.copyfile(tb, out / tb.name)
    images = programs(root, assemble)
    cases = make_cases(images, timing, raw_at, load_plan)
    with (out / "stimulus.hex").open("w", encoding="ascii", newline="\n") as stream:
        for case in cases:
            script, levels = case[-2:]
            for step in script:
                stream.write(f"{load_step(step):06x}\n")
            for miso in levels:
                vector = word_vector(0, miso << 1, host=False, target=True, enable=1, reset_n=1, run=True)
                stream.write(f"{vector:06x}\n")
    identity, version = observe(root, out, args.image, src["source_sha256"], src["model_sha256"])
    with (out / "observed.txt").open(encoding="ascii") as stream:
        records = (tuple(int(n, 16) for n in line.split()) for line in stream)
        results = [check_case(case, records, assess) for case in cases]
        check(next(records, None) is None, "extra observations")
    # These three families drive the same complete output pin and OE sequence.
    for mode in range(4):
        for order in (0, 1):
            traces = {r["driven_and_oe_sha256"] for r in results if r["mode"] == mode and r["order"] == order}
            check(len(traces) == 1, f"pin schedule differs for m{mode}-o{order}")
    count_reject = sum(bool(r["error_kinds"]) for r in results)
    check(len(results) == 112 and count_reject == 16, "case inventory")
    summary = {"scope": "public RTL pin equations with discrete raw MISO sampling",
               "cases": len(results), "accepted": len(results) - count_reject, "expected_rejections": count_reject,
               "historical_exact_images_byte_equal": 8, "image_id": identity, "simulator": version,
               "rtl_sha256": src["source_sha256"], "sram_sha256": src["model_sha256"],
               "bench_sha256": digest(tb.read_bytes()), "checker_sha256": digest(Path(__file__).read_bytes()),
               "observed_edges_sha256": digest((out / "observed.txt").read_bytes()), "observations": results}
    (out / "results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{len(results)} cases: {len(results) - count_reject} accepted, {count_reject} expected wrong-byte rejections.")
    print("All eight EXACT binaries match the archived E0027 words. Every output/OE trace agrees across families.")


if __name__ == "__main__":
    main()
