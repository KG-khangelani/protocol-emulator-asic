"""JSON bridge to the independent decoded Python oracle; no RTL or device IO."""

import json
import sys

from m1_contract_model import Instruction, Machine


def predict(case):
    """The caller supplies separately decoded instructions, not JS decoder output."""
    program = [Instruction(**instruction) for instruction in case["decoded"]]
    machine = Machine()
    rows = []
    for inputs in case["inputs"]:
        machine.edge(program, rst_n=inputs["rstN"], ena=inputs["ena"])
        rows.append({
            "pc": machine.pc,
            "state": machine.state.name,
            "waitLeft": machine.wait_left,
            "gpio": machine.gpio_value,
            "oe": machine.gpio_oe,
        })
    return rows


if __name__ == "__main__":
    json.dump([predict(case) for case in json.load(sys.stdin)], sys.stdout)
