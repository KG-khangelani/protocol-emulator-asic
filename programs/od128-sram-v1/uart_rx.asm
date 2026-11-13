; SPDX-License-Identifier: Apache-2.0
; Versioned G3 example; see README.md for pin ownership and timing limits.
.target od128-sram-v1
.const PERIOD 434
.const HALF 25
.const CLOCK_TIMEOUT 49999
.data TX0 0xff
.data TX1 0xff
.idle 0x02

entry:
    LOOP count=2 end=loop_end_0
    WAIT_PIN pin=1 level=0 timeout=PERIOD*2
    WAIT cycles=PERIOD//2-2
    WAIT_PIN pin=1 level=0 timeout=0
    WAIT cycles=PERIOD-2
    SHIFT_BURST tx=0 rx=1 order=lsb period=PERIOD
    WAIT_PIN pin=1 level=1 timeout=0
loop_end_0:
    HALT
