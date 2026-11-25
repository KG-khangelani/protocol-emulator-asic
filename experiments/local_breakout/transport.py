# SPDX-License-Identifier: Apache-2.0
"""Six-byte public loader rows on the stock Pico's local-breakout wiring (also runs on MicroPython)."""

def cold(io, packed, damage=False):
    returned = bytearray()
    registers = []
    for offset in range(0, len(packed), 6):
        reset, selector, data, flags, status, value = packed[offset:offset + 6]
        if flags & 1:
            io.set(reset, 1, data ^ int(damage and offset == 24))
            io.pulse()
        io.set(reset, 0, 0xe7 if flags & 8 else selector)
        io.pulse()
        if flags & 6:
            want = value if flags & 4 else status
            actual = io.check(want, offset // 6, selector)
            if actual != want:
                raise ValueError("cold readback", offset // 6, selector, want, actual)
            if flags & 4:
                if selector < 0xa0:
                    returned.append(actual)
                else:
                    registers.append((selector, actual))
    io.set(1, 0, 0)
    return returned, registers
