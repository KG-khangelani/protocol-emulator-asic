# SPDX-License-Identifier: Apache-2.0
"""Build a readable RP2040 PIO source for one SPI phase and sample time."""


def spi_source(cpha, sample_kind):
    if cpha not in (0, 1) or sample_kind not in ("exact", "late", "early", "mapped_exact", "mapped_early", "bypass_exact"):
        raise ValueError("unsupported SPI phase or sample time")
    mapped = sample_kind.startswith(("mapped_", "bypass_"))
    lines = ["; SPDX-License-Identifier: Apache-2.0", ".program council_spi", ".side_set 2", ".wrap_target"]

    def emit(instruction, sides, duration=1):
        if not 1 <= duration <= 8:
            raise ValueError("two side-set bits leave three delay bits")
        delay = f" [{duration - 1}]" if duration > 1 else ""
        lines.append(f"    {instruction:<26} side {sides}{delay}")

    # Side bit 0 controls SCK, bit 1 controls CS. The host can invert SCK
    # at the GPIO output for modes 2 and 3. SET covers GPIOs 0..3.
    launch, sample = (0, 1) if cpha == 0 else (1, 0)
    if not mapped:
        emit("set pindirs, 12", 2)  # Otherwise done by a host force after program verification.
    if cpha == 0:
        emit("out pins, 1", 2)  # Load first MOSI bit behind its disabled output.
    else:
        emit("out pins, 1", 0, 8)  # CS assertion; first MOSI value still hidden.
        emit("nop", 0, 8)
        emit("nop", 0, 8)
        emit("nop", 0)

    # First and later launches each spend exactly 25 ticks to the sample edge.
    emit("set pindirs, 13", launch, 8)
    emit("jmp launch_tail", launch, 8)
    if sample_kind == "late":
        lines.append("capture_before_next_bit:")
        emit("in pins, 1", sample)
    lines.append("next_bit:")
    emit("out pins, 1", launch, 8)
    emit("nop", launch, 8)
    lines.append("launch_tail:")
    emit("nop", launch, 8)
    if sample_kind == "bypass_exact":
        emit("jmp !y final_capture", launch)
    else:
        emit("nop", launch)

    if sample_kind == "late":
        # IN occurs at S+24 on both iteration paths. Branch beforehand so
        # the final half-period can proceed directly to CS release.
        emit("nop", sample, 8)
        emit("nop", sample, 8)
        emit("jmp y-- capture_before_next_bit", sample, 8)
        emit("in pins, 1", sample)
    elif sample_kind == "bypass_exact":
        # IN consumes physical S through the one remaining mapping register.
        # The explicit last-bit branch avoids relying on Wokwi's IFFULL.
        emit("nop", sample, 2)
        emit("in pins, 1", sample, 8)
        emit("nop", sample, 8)
        emit("jmp y-- next_bit", sample, 7)
        lines.append("final_capture:")
        emit("nop", sample, 2)
        emit("in pins, 1", sample)
        emit("push block", sample, 8)
        emit("nop", sample, 8)
        emit("nop", sample, 6)
    else:
        offset = {"exact": 2, "early": 1, "mapped_exact": 4, "mapped_early": 3}[sample_kind]
        emit("nop", sample, offset)
        emit("in pins, 1", sample, 8)
        emit("nop", sample, 8)
        emit("jmp y-- next_bit", sample, 25 - offset - 16)

    emit("nop", 2)  # CS releases at Q, SCK returns to or holds its idle value.
    if mapped:
        emit("nop", 2)  # Account for the registered physical propagation of CS release.
    emit("irq 0", 2)  # A non-destructive host completion flag at Q+1.
    lines.append("hold:")
    emit("jmp hold", 2)
    lines.append(".wrap")
    return "\n".join(lines) + "\n"


def resident_source():
    """Share the last three operations of two synchronized phase-specific paths."""
    lines = ["; SPDX-License-Identifier: Apache-2.0", ".program council_spi_resident", ".side_set 2", ".wrap_target"]
    entries = []
    address = 0
    for phase in (0, 1):
        entries.append(address)
        lines.append(f"phase{phase}_entry:")
        body = spi_source(phase, "mapped_exact").splitlines()
        body = body[body.index(".wrap_target") + 1:body.index(".wrap")]
        if [s.strip().split(" side")[0].strip() for s in body[-5:]] != ["nop", "nop", "irq 0", "hold:", "jmp hold"]:
            raise ValueError("phase termination cannot be safely shared")
        for line in body[:-5]:
            lines.append(line.replace("next_bit", f"p{phase}_next_bit").replace("launch_tail", f"p{phase}_launch_tail"))
            if not line.endswith(":"):
                address += 1
        lines.append("    jmp complete               side 2")
        address += 1
    lines.extend(["complete:", "    nop                        side 2", "    irq 0                      side 2",
                  "hold:", "    jmp hold                   side 2", ".wrap"])
    return "\n".join(lines) + "\n", entries
