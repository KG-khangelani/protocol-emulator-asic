"""Test settled intermediate pin states against G4 RTL and the archived submitted netlist."""
import argparse
import gzip
import hashlib
import itertools
import json
import os
import subprocess
import time
from collections import Counter
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


ARCHIVE = "evidence/E0047-g4-submission-candidate/ci-43543626249/14094673928.zip"
ARCHIVE_SHA = "7348d2fc9e448ada84974b450801ee7cd5aa0b3065e1569fceefd6a154ad3ee2"
NETLIST_SHA = "2a0304aebbb2c9a287cc16ac0e61221116c4f2001420baa7df9c0ab1f035cd2e"
PDK_FILES = {
    "sg13cmos5l_io/verilog/sg13cmos5l_io.v": "ae986803821a9d6c3af9c221c33c3aa58ca23c283d3ad93ed4b3a2c45d6ccb4d",
    "sg13cmos5l_stdcell/verilog/sg13cmos5l_udp.v": "5491a3edf7468792b5222e7abe057e0583a407c01b2086d4fd44a55b6cf88055",
    "sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v": "485945f1b167daa68354548f46c95bdbff7d931516fc5b4edd47f2e2cd555735",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(raw, expected, name):
    if sha(raw) != expected:
        raise ValueError(f"hash mismatch for {name}")
    return raw


@contextmanager
def memory_file(name, data=b""):
    # The compiled gate image exceeds this panel's persistent scratch allowance.
    # Linux anonymous memory files give Icarus and vvp seekable process memory.
    with os.fdopen(os.memfd_create(name), "w+b") as source:
        source.write(data)
        source.flush()
        source.seek(0)
        yield f"/proc/{os.getpid()}/fd/{source.fileno()}"


def execute(argv, cwd):
    completed = subprocess.run([str(x) for x in argv], cwd=cwd, capture_output=True, timeout=90)
    if completed.returncode:
        raise RuntimeError((completed.stderr + completed.stdout)[-1800:].decode(errors="replace"))
    return completed.stdout


def score(raw, orders):
    rows = {}
    for line in raw.decode().splitlines():
        if line.startswith("P "):
            prefix, index, mode, step, selector, oe, status, pin6, pin0, out6 = line.split()
            key = int(index), int(mode), int(step)
            if key in rows:
                raise ValueError("duplicate sampled transition")
            rows[key] = int(selector, 16), int(oe, 16), int(status, 16), pin6, pin0, out6
    if len(rows) != 720 * 3 * 6 + 3 * 2:
        raise ValueError("incomplete selector matrix")
    summary = {}
    for mode, label in enumerate(("released", "peer_high", "peer_low")):
        histogram = Counter()
        conflicts, electrical_low, conflicting_steps, electrical_low_steps = 0, 0, 0, 0
        for index, order in enumerate(orders):
            expected_read = order.index(6) < order.index(7)
            expected_gap = order.index(7) - order.index(6) if expected_read else 0
            selector, exposed, lows, xs = 0xe7, 0, 0, 0
            for step, bit in enumerate(order):
                selector &= ~(1 << bit)
                observed, oe, _, pin6, pin0, out6 = rows[index, mode, step]
                if selector != observed or oe not in (0, 255):
                    raise ValueError(f"unexpected selector/OE in {label} order {order}")
                if oe == 255:
                    exposed += 1
                    if out6 != "0" or pin6 != ("x" if mode == 1 else "0"):
                        raise ValueError(f"fixture data-level witness failed with {label} order {order}")
                    lows += pin0 == "0"
                    xs += pin6 == "x"
                elif pin6 != ("1" if mode == 1 else "0") or pin0 != "1":
                    raise ValueError(f"released pad disagrees with fixture for {label} order {order}")
            if exposed != expected_gap:
                raise ValueError(f"unexpected drive count {exposed} for {order}")
            histogram[exposed] += 1
            conflicts += xs > 0
            electrical_low += lows > 0
            conflicting_steps += xs
            electrical_low_steps += lows
        for step, selector in enumerate((0x67, 0)):
            observed, oe, status, pin6, pin0, _ = rows[720, mode, step]
            if (observed, oe, status, pin6, pin0) != (selector, 0, (0x22, 0x20)[step],
                                                      "1" if mode == 1 else "0", "1"):
                raise ValueError(f"explicit staged transition failed for {label}")
        summary[label] = {"number_of_orders_by_count_of_read_dwells": dict(sorted(histogram.items())),
                          "opposed_bit6_X_orders": conflicts, "opposed_bit6_X_dwells": conflicting_steps,
                          "weak_pullup_bit0_low_orders": electrical_low,
                          "weak_pullup_bit0_low_dwells": electrical_low_steps,
                          "safe_bit7_first_tails": sum(x[0] == 7 for x in orders),
                          "explicit_staged_both_steps": "PASS"}
    # Exclude the simulator's terminal file:line message from binary equivalence.
    canonical = b"\n".join(row for row in raw.splitlines() if row.startswith(b"P ")) + b"\n"
    return canonical, summary


def screen(args, result):
    repo, out, libs = args.repo.resolve(), args.out.resolve(), args.pdk_libs.resolve()
    orders = list(itertools.permutations((7, 6, 5, 2, 1, 0)))
    order_file = out / "orders.hex"
    order_file.write_text("".join(f"{sum(bit << (4*i) for i,bit in enumerate(order)):06x}\n" for order in orders))
    bench = Path(__file__).resolve().with_name("selector_order_tb.v")
    result.update(bench_sha256=sha(bench.read_bytes()), runner_sha256=sha(Path(__file__).read_bytes()),
                  orders_sha256=sha(order_file.read_bytes()), archive_sha256=ARCHIVE_SHA,
                  netlist_sha256=NETLIST_SHA, pdk_library_sha256=PDK_FILES)
    for name, digest in PDK_FILES.items():
        checked((libs / name).read_bytes(), digest, name)
    lock = json.loads((repo / "tools/production-profile.json").read_bytes())
    archive = repo / ARCHIVE
    checked(archive.read_bytes(), ARCHIVE_SHA, ARCHIVE)
    result["simulator"] = execute(["iverilog", "-V"], out).decode().splitlines()[0]
    result["sampled"] = {}
    with ZipFile(archive) as source, ExitStack() as stack:
        def ram(name, raw):
            return stack.enter_context(memory_file(name, raw))

        rtl, models = [], []
        for name, expected in lock["files_sha256"].items():
            if name.startswith("src/") and name.endswith(".v"):
                rtl.append(ram(name.rsplit("/", 1)[1], checked(source.read(name), expected, name)))
        for name, expected in lock["model_sha256"].items():
            compressed = repo / "evidence/E0042-sram-prefetch-screen/feasibility/verilog" / (name + ".gz")
            models.append(ram(name, checked(gzip.decompress(compressed.read_bytes()), expected, name)))
        if len(rtl) != 5 or len(models) != 2:
            raise ValueError("production source set changed")
        netlist = ram("submitted.v", checked(source.read("tt_submission/tt_um_khangelani_protocol_emulator.v"),
                                           NETLIST_SHA, "submitted netlist"))
        canonical_records = {}
        implementations = {"rtl": rtl + models, "g4_netlist": [netlist, *models, *(libs / n for n in PDK_FILES)]}
        for name, inputs in implementations.items():
            with memory_file("compiled.vvp") as compiled:
                execute(["iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS", "-DSIM", "-s", "selector_order_tb",
                         "-o", compiled, bench, *inputs], out)
                raw = execute(["vvp", compiled, "+ORDERS=" + str(order_file)], out)
                (out / f"{name}-observed.gz").write_bytes(gzip.compress(raw, mtime=0))
                canonical, summary = score(raw, orders)
                result["sampled"][name] = {"rows": len(canonical.splitlines()), "sha256": sha(canonical),
                                           "modes": summary}
                canonical_records[name] = canonical
        if canonical_records["rtl"] != canonical_records["g4_netlist"]:
            raise ValueError("RTL and submitted-netlist public-port rows differ")
    result["status"] = "PASS_SETTLED_ORDER_SCREEN"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pdk-libs", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    result = {"status": "INCOMPLETE", "image_id_supplied_by_invoker": args.image_id,
              "started_utc": datetime.now(timezone.utc).isoformat()}
    start = time.monotonic()
    try:
        screen(args, result)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        result["ended_utc"] = datetime.now(timezone.utc).isoformat()
        result["runtime_seconds"] = round(time.monotonic() - start, 3)
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["runtime_seconds"])


if __name__ == "__main__":
    main()
