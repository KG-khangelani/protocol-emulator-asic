# SPDX-License-Identifier: Apache-2.0
"""Read small pinned primary sources, fingerprint them and count PIO instructions."""
import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen


PICO = "raspberrypi/pico-examples/0d62f75bafc2c8120d3276c3343d1a9195e909e9/"
PE = "Abagel-coder/protocol-emulator/f904d1fe3bfa3374ebb95d73f02feeaa09b14122/"
TEMPO = "satyaammu93/jane-street-asic-2026/65e0a742c1f91ac730c137afea5e154287267d67/protocol_emulator/"
FILES = {
    "pio_spi": PICO + "pio/spi/spi.pio",
    "pio_i2c": PICO + "pio/i2c/i2c.pio",
    "pio_i2c_host": PICO + "pio/i2c/pio_i2c.c",
    "peer_top": PE + "src/project.v",
    "peer_fifo": PE + "src/pe_fifo.v",
    "peer_imem": PE + "src/pe_imem.v",
    "tempo_top": TEMPO + "src/tt_um_protocol_emulator.v",
    "tempo_fifo": TEMPO + "src/tempo_fifo.v",
}


def fetch(item):
    key, path = item
    url = "https://raw.githubusercontent.com/" + path
    request = Request(url, headers={"User-Agent": "protocol-emulator-architecture-review"})
    with urlopen(request, timeout=15) as response:
        data = response.read()
    record = {"url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return key, record, data.decode("utf-8")


def count_instructions(text):
    current = None
    counts = {}
    opcodes = {"jmp", "wait", "in", "out", "push", "pull", "mov", "irq", "set", "nop"}
    for line in text.splitlines():
        code = line.split(";", 1)[0].split("//", 1)[0].strip()
        if code.startswith(".program "):
            current = code.split()[1]
            counts[current] = 0
        elif code.startswith("%"):
            current = None
        elif current and code and code.split()[0] in opcodes:
            counts[current] += 1
    return counts


def main(output):
    records = {}
    files = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for key, record, content in pool.map(fetch, FILES.items()):
            records[key], files[key] = record, content
    spi, i2c = count_instructions(files["pio_spi"]), count_instructions(files["pio_i2c"])
    assert spi == {"spi_cpha0": 2, "spi_cpha1": 3, "spi_cpha0_cs": 9, "spi_cpha1_cs": 9}
    assert i2c == {"i2c": 18, "set_scl_sda": 4}
    fifo_calls = {}
    for fn in ("start", "repstart", "stop"):
        body = files["pio_i2c_host"].split("void pio_i2c_" + fn + "(", 1)[1].split("}", 1)[0]
        fifo_calls[fn] = body.count("pio_i2c_put_or_err(")
    assert fifo_calls == {"start": 4, "repstart": 6, "stop": 4}
    result = {"source_files": records, "assembly_instruction_lines": {**spi, **i2c},
              "host_fifo_put_calls_per_function": fifo_calls,
              "boundary": "Resident source instruction counts and no-error host submission paths. "
                          "No competitor execution, gate cost or interoperability comparison."}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pio_instructions": {**spi, **i2c}, "host_fifo_calls": fifo_calls}))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
