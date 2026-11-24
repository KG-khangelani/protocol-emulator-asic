; SPDX-License-Identifier: Apache-2.0
.target od128-sram-v1
.const PERIOD 434
.data TX0 0x55
.data TX1 0xaa
.idle 0

    SET mask=1 value=1 oe=1
    WAIT cycles=0
    SET mask=1 value=0 oe=1
    WAIT cycles=PERIOD-3
    LOOP count=8 end=first_stop
    SHIFT_STEP tx=0 rx=1 order=lsb payload=TX0
    WAIT cycles=PERIOD-2
first_stop:
    SET mask=1 value=1 oe=1
    WAIT cycles=PERIOD-2
    SET mask=1 value=0 oe=1
    WAIT cycles=PERIOD-3
    LOOP count=8 end=second_stop
    SHIFT_STEP tx=0 rx=1 order=lsb payload=TX1
    WAIT cycles=PERIOD-2
second_stop:
    SET mask=1 value=1 oe=1
    WAIT cycles=PERIOD-2
    HALT
