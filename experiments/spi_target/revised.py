"""Generate a literal-reply program for the released VM instruction set."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "evidence/E0049-review-council/panel-c/spi-target/spi_test_target.asm"


def source():
    original = ORIGINAL.read_text(encoding="utf-8")
    prefix, _ = original.split("\nreply_a:\n")
    entry = "    WAIT_PIN pin=2 level=0 timeout=DEADLINE on_timeout=timeout"
    prefix = prefix.replace(entry, "rearm:\n    SET mask=8 value=0 oe=0\n" + entry, 1)
    lines = [prefix]
    for label, reply in (("a", 0x3C), ("b", 0xA7)):
        lines += [f"reply_{label}:", "    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout"]
        previous = None
        for index in range(8):
            bit = (reply >> (7 - index)) & 1
            if bit != previous:
                lines.append(f"    SET mask=8 value={bit << 3} oe=8")
            previous = bit
            for level in (1, 0):
                poll = f"{label}{index}_await_{level}"
                lines += [poll + ":", "    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm",
                          f"    WAIT_PIN pin=0 level={level} timeout=0 on_timeout={poll}"]
        lines += ["    SET mask=8 value=0 oe=0", "    WAIT_PIN pin=2 level=1 timeout=DEADLINE on_timeout=timeout",
                  "    SET mask=0x30 value=0x10 oe=0x30", "    HALT"]
    lines += ["bad:", "    SET mask=0x38 value=0x20 oe=0x30", "    HALT",
              "timeout:", "    SET mask=0x38 value=0x30 oe=0x30", "    HALT"]
    return "\n".join(lines) + "\n"
