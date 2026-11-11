# SPDX-License-Identifier: Apache-2.0
"""Declared schedule families, including explicitly non-loadable references."""
from experiments.spi_phase.phase_programs import PhaseMachine, encode
from tools.m1_contract_model import Instruction


class ReferenceOnlyMachine(PhaseMachine):
    """Only the reference model has 16 words; actual compact hardware has eight."""
    @property
    def capacity(self):
        return 16


def image(mode, order, family, half=25):
    if mode not in range(4) or order not in (0, 1) or half < 4:
        raise ValueError("invalid mode/order/half period")
    if family not in ("exact", "held", "naive"):
        raise ValueError("invalid schedule family")
    cpol, cpha = mode >> 1, mode & 1
    first = cpol ^ cpha
    drive = Instruction("DRIVE", mask=12, value=first << 2, tx_pin=0, rx_pin=1, msb_first=order)
    body = [drive, Instruction("WAIT", count=half-2),
            Instruction("SET", mask=4, value=(1-first) << 2, oe=4),
            Instruction("SAMPLE", count=half-2 if family == "held" else 1,
                        tx_pin=0, rx_pin=1, msb_first=order)]
    if family != "held":
        body.append(Instruction("WAIT", count=half-4))
    prefix = []
    if family != "naive":
        prefix.append(Instruction("SET", mask=12, value=8 | (cpol << 2), oe=12))
        if cpha:
            prefix += [Instruction("SET", mask=12, value=cpol << 2, oe=12),
                       Instruction("WAIT", count=half-3)]
    program = prefix+[Instruction("LOOP", length=len(body), count=8)]+body+[
        Instruction("SET", mask=12, value=8 | (cpol << 2), oe=12), Instruction("HALT")]
    cs = 2 if family == "naive" or cpha else 3
    return program, cs


def execute_reference(program, *, tx, raw, steps):
    machine = ReferenceOnlyMachine()
    machine.edge(program, rst_n=False, ena=False)
    result, valid = 0, 0
    trace = [{"edge": 0, "out": 0, "oe": 0, "miso": raw(0),
              "rx": 0, "rx_valid": 0, "state": "RUN"}]
    commits = []
    for n in range(1, steps+1):
        machine.edge(program, sampled_inputs=raw(n-2) << 1, tx_payload=tx)
        if machine.shift_result_write:
            result, valid = machine.shift_result_data, 1
            commits.append([n, result])
        trace.append({"edge": n, "out": machine.gpio_value, "oe": machine.gpio_oe,
                      "miso": raw(n), "rx": result, "rx_valid": valid,
                      "state": machine.state.name})
    return trace, commits


def describe(program):
    return {"words": len(program), "used_bits": 32*len(program), "actual_capacity_words": 8,
            "fits_eight_word_store": len(program) <= 8, "rtl_execution": "NOT_EVALUATED",
            "encoded_words": [f"{encode(w):08x}" for w in program]}
