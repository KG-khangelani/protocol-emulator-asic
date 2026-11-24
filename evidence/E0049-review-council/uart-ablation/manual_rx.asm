; SPDX-License-Identifier: Apache-2.0
.target od128-sram-v1
.const PERIOD 434
.data TX0 0xff
.data TX1 0xff
.idle 2

    WAIT cycles=0
    WAIT_PIN pin=1 level=0 timeout=PERIOD*2
    WAIT cycles=PERIOD//2-2
    WAIT_PIN pin=1 level=0 timeout=0
    WAIT cycles=PERIOD-3
    LOOP count=8 end=first_stop
    SHIFT_STEP tx=0 rx=1 order=lsb payload=TX0
    WAIT cycles=PERIOD-2
first_stop:
    WAIT_PIN pin=1 level=1 timeout=0
    WAIT_PIN pin=1 level=0 timeout=PERIOD*2
    WAIT cycles=PERIOD//2-2
    WAIT_PIN pin=1 level=0 timeout=0
    WAIT cycles=PERIOD-3
    LOOP count=8 end=second_stop
    SHIFT_STEP tx=0 rx=1 order=lsb payload=TX1
    WAIT cycles=PERIOD-2
second_stop:
    WAIT_PIN pin=1 level=1 timeout=0
    HALT
