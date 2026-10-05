"""UART-RX stimulus/schedule oracle and proposed firmware; no production RTL.

Times use quarter-clock ticks so sub-cycle input phase is explicit. The waveform
and expected schedule are mathematical frame definitions, not Machine.edge.
"""

from dataclasses import dataclass

if __package__:
    from .m1_contract_model import Instruction
else:
    from m1_contract_model import Instruction


@dataclass(frozen=True)
class Frame:
    payload: int
    stop: int = 1

    def __post_init__(self):
        if not 0 <= self.payload <= 255 or self.stop not in (0, 1):
            raise ValueError("frame requires an eight-bit payload and binary stop")


def rx_program(period=434):
    """Eight words; both TX payload registers must contain 0xff separately."""
    if not 4 <= period <= 32766 or period % 2:
        raise ValueError("RX period must be even, 4..32766 (2P timeout fits 16 bits)")
    return [
        Instruction("LOOP", length=6, count=2),
        Instruction("WAIT_PIN", pin=1, level=0, count=2 * period),
        Instruction("WAIT", count=period // 2 - 2),
        Instruction("WAIT_PIN", pin=1, level=0, count=0),
        Instruction("WAIT", count=period - 2),
        Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1, burst=1, period=period),
        Instruction("WAIT_PIN", pin=1, level=1, count=0),
        Instruction("HALT"),
    ]


def line_level(quarter_tick, frames, *, start_quarter=17, period=434):
    """Idle/start/eight LSB-first data/stop; frames have no intervening idle."""
    elapsed = quarter_tick - start_quarter
    if elapsed < 0:
        return 1
    cell = elapsed // (4 * period)
    frame_index, cell_index = divmod(cell, 10)
    if frame_index >= len(frames):
        return 1
    frame = frames[frame_index]
    if cell_index == 0:
        return 0
    if cell_index == 9:
        return frame.stop
    return (frame.payload >> (cell_index - 1)) & 1


def expected_schedule(*, start_quarter=17, period=434):
    """Derived from fixed instruction latencies and the two-stage input path.

    A transition on an integer clock is applied before that edge in this digital
    oracle. This ordering is not a metastability assumption for real hardware.
    """
    rx_program(period)  # Check operand bounds before calculating a schedule.
    event = (start_quarter + 3) // 4 + 2
    starts = [event, event + 10 * period]
    return {
        "detected_start": starts,
        "checked_start": [edge + period // 2 for edge in starts],
        "first_data": [edge + 3 * period // 2 for edge in starts],
        "raw_capture": [edge + 17 * period // 2 for edge in starts],
        "checked_stop": [edge + 19 * period // 2 for edge in starts],
        "halt": event + 39 * period // 2 + 1,
    }
