# SPDX-License-Identifier: Apache-2.0
"""Independent SPI pin mathematics and explicit eight-word feasibility images.

Quarter ticks describe raw MISO response; no Machine/RTL state computes the
expected SCK, CS or rising-edge word. This is a partial mode-0 seed.
"""

from .m1_contract_model import Instruction

MOSI, MISO, SCK, CS = 0, 1, 2, 3


def check_half_period(half_period):
    if type(half_period) is not int or not 4 <= half_period <= 65535:
        raise ValueError("half-period must be an integer in 4..65535")


def bits(payload, msb_first=1):
    if type(payload) is not int or not 0 <= payload <= 255:
        raise ValueError("payload must be a byte")
    if msb_first not in (0, 1):
        raise ValueError("bit order must be binary")
    return [(payload >> i) & 1 for i in (range(7, -1, -1) if msb_first else range(8))]


def assemble(samples, msb_first=1):
    if len(samples) != 8 or any(bit not in (0, 1) for bit in samples):
        raise ValueError("eight binary samples required")
    return sum(bit << i for bit, i in zip(
        samples, range(7, -1, -1) if msb_first else range(8)))


def schedule(half_period=25, *, late=True):
    check_half_period(half_period)
    lows = [2 + 2 * half_period * j for j in range(8)]
    rising = [edge + half_period for edge in lows]
    shifts = [edge - 1 for edge in rising] if late else [edge + 1 for edge in lows]
    return {"low": lows, "rising": rising,
            "falling": [edge + 2 * half_period for edge in lows],
            "shift": shifts, "raw_capture": shifts[-1],
            "release": 2 + 16 * half_period, "halt": 3 + 16 * half_period}


def coupled_program(half_period=25, *, msb_first=1, late=True):
    check_half_period(half_period)
    bits(0, msb_first)
    step = Instruction("SHIFT_STEP", tx_pin=MOSI, rx_pin=MISO, msb_first=msb_first)
    low_wait = Instruction("WAIT", count=half_period - 3)
    return [Instruction("LOOP", length=5, count=8),
            Instruction("SET", mask=12, value=0, oe=12),
            *([low_wait, step] if late else [step, low_wait]),
            Instruction("SET", mask=4, value=4, oe=4),
            Instruction("WAIT", count=half_period - 2),
            Instruction("SET", mask=12, value=8, oe=12),
            Instruction("HALT")]


def miso_level(quarter_tick, payload, *, half_period=25, response_quarters=1,
               msb_first=1, idle=1):
    """Target changes only after CS assertion/falling edges and holds otherwise."""
    check_half_period(half_period)
    word = bits(payload, msb_first)
    if type(response_quarters) is not int or not 1 <= response_quarters <= 4 * half_period - 4:
        raise ValueError("response must leave at least one clock of input setup")
    if idle not in (0, 1):
        raise ValueError("idle must be binary")
    # Hold the last bit through the clock edge that deasserts CS; release at
    # the next quarter tick, after the host output has actually settled.
    if quarter_tick < 8 or quarter_tick > 4 * (2 + 16 * half_period):
        return idle
    index = (quarter_tick - 8 - response_quarters) // (8 * half_period)
    return word[index] if 0 <= index < 8 else idle


def expected_gpio(edge, payload, *, half_period=25, msb_first=1, late=True):
    """Raw post-edge output and enable, not values of externally pulled pins."""
    timing = schedule(half_period, late=late)
    if edge < 2:
        return 0, 0
    clock = int(edge < timing["release"] and (edge - 2) % (2 * half_period) >= half_period)
    selected = [j for j, when in enumerate(timing["shift"]) if when <= edge]
    tx = bits(payload, msb_first)[selected[-1]] if selected else 0
    return tx | (clock << SCK) | (int(edge >= timing["release"]) << CS), 12 | int(bool(selected))


def coupled_result(payload, *, half_period=25, response_quarters=1,
                   msb_first=1, late=True):
    """Predict the existing coupling failure without executing Machine.edge."""
    return assemble([miso_level(4 * (edge - 2), payload, half_period=half_period,
                               response_quarters=response_quarters, msb_first=msb_first)
                     for edge in schedule(half_period, late=late)["shift"]], msb_first)
