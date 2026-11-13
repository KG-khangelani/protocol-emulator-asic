; SPDX-License-Identifier: Apache-2.0
; Versioned G3 example; see README.md for pin ownership and timing limits.
.target od128-sram-v1
.const PERIOD 434
.const HALF 25
.const CLOCK_TIMEOUT 49999
.data TX0 0xa5
.data TX1 0x96
.idle 0x03

entry:
    SET mask=0x1f value=0x00 oe=0x1c
    WAIT cycles=235
    SET mask=0x02 value=0x00 oe=0x02
    WAIT cycles=200
    SET mask=0x01 value=0x00 oe=0x01
    LOOP count=8 end=loop_end_5
    DRIVE tx=1 rx=5 order=msb mask=0x01 value=0x00 drive=open_drain
    WAIT cycles=260
    SET mask=0x01 value=0x00 oe=0x00
    WAIT_PIN pin=0 level=1 timeout=CLOCK_TIMEOUT on_timeout=timeout
    SAMPLE tx=1 rx=5 order=msb delay=240
    SET mask=0x01 value=0x00 oe=0x01
loop_end_5:
    SET mask=0x02 value=0x00 oe=0x00
    WAIT cycles=260
    SET mask=0x01 value=0x00 oe=0x00
    WAIT_PIN pin=0 level=1 timeout=CLOCK_TIMEOUT on_timeout=timeout
    WAIT cycles=240
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=nack
    SET mask=0x01 value=0x00 oe=0x01
    LOOP count=8 end=loop_end_19
    WAIT cycles=260
    SET mask=0x01 value=0x00 oe=0x00
    WAIT_PIN pin=0 level=1 timeout=CLOCK_TIMEOUT on_timeout=timeout
    WAIT cycles=240
    SHIFT_STEP tx=0 rx=1 order=msb drive=open_drain
    SET mask=0x01 value=0x00 oe=0x01
loop_end_19:
    SET mask=0x02 value=0x00 oe=0x00
    WAIT cycles=260
    SET mask=0x01 value=0x00 oe=0x00
    WAIT_PIN pin=0 level=1 timeout=CLOCK_TIMEOUT on_timeout=timeout
    WAIT cycles=240
    SET mask=0x01 value=0x00 oe=0x01
    SET mask=0x02 value=0x00 oe=0x02
    WAIT cycles=260
    SET mask=0x01 value=0x00 oe=0x00
    WAIT_PIN pin=0 level=1 timeout=CLOCK_TIMEOUT on_timeout=timeout
    WAIT cycles=200
    SET mask=0x02 value=0x00 oe=0x00
    WAIT cycles=235
    SET mask=0x1f value=0x04 oe=0x1c
    HALT
nack:
    SET mask=0x01 value=0x00 oe=0x01
    SET mask=0x02 value=0x00 oe=0x02
    WAIT cycles=260
    SET mask=0x01 value=0x00 oe=0x00
    WAIT_PIN pin=0 level=1 timeout=CLOCK_TIMEOUT on_timeout=timeout
    WAIT cycles=200
    SET mask=0x02 value=0x00 oe=0x00
    WAIT cycles=235
    SET mask=0x1f value=0x08 oe=0x1c
    HALT
timeout:
    SET mask=0x1f value=0x0c oe=0x1c
    HALT
