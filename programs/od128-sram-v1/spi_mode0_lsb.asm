; SPDX-License-Identifier: Apache-2.0
; Versioned G3 example; see README.md for pin ownership and timing limits.
.target od128-sram-v1
.const PERIOD 434
.const HALF 25
.const CLOCK_TIMEOUT 49999
.data TX0 0x96
.data TX1 0x00
.idle 0x02

entry:
    SET mask=0x0c value=0x08 oe=0x0c
    LOOP count=8 end=loop_end_1
    DRIVE tx=0 rx=1 order=lsb mask=0x0c value=0x00
    WAIT cycles=HALF-2
    SET mask=0x04 value=0x04 oe=0x04
    SAMPLE tx=0 rx=1 order=lsb delay=HALF-2
loop_end_1:
    SET mask=0x0c value=0x08 oe=0x0c
    HALT
