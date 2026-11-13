; SPDX-License-Identifier: Apache-2.0
; Versioned G3 example; see README.md for pin ownership and timing limits.
.target od128-sram-v1
.const PERIOD 434
.const HALF 25
.const CLOCK_TIMEOUT 49999
.data TX0 0x55
.data TX1 0xaa
.idle 0x00

entry:
    SET mask=0x01 value=0x01 oe=0x01
    LOOP count=2 end=loop_end_1
    SET mask=0x01 value=0x00 oe=0x01
    WAIT cycles=PERIOD-2
    SHIFT_BURST tx=0 rx=1 order=lsb period=PERIOD
    SET mask=0x01 value=0x01 oe=0x01
    WAIT cycles=PERIOD-2
loop_end_1:
    HALT
