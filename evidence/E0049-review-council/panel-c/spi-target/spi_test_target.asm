; SPDX-License-Identifier: Apache-2.0
; Mode-0 emulator test device. SPI requester drives clock 0, MOSI 1, CS_n 2.
; MISO 3 is released throughout the opcode. Pins 5:4 carry terminal markers.
.target od128-sram-v1
.idle 0x04
.data TX0 0x3c
.data TX1 0xa7
.const DEADLINE 80

    WAIT_PIN pin=2 level=0 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=bad
; The two recognized command bytes share their first seven MSB-first bits.
; Bit 7 is one.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=1 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
; Bit 6 is zero.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
; Bit 5 is one.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=1 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
; Bit 4 is zero.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
; Bit 3 is zero.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
; Bit 2 is one.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=1 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
; Bit 1 is zero.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
; Last bit zero takes TX0, one takes TX1 through the immediate branch.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=reply_b

reply_a:
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
    LOOP count=8 end=finish_a
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    SHIFT_STEP tx=3 rx=1 order=msb payload=TX0
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
finish_a:
    SET mask=8 value=0 oe=0
    WAIT_PIN pin=2 level=1 timeout=DEADLINE on_timeout=timeout
    SET mask=0x30 value=0x10 oe=0x30
    HALT

reply_b:
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
    LOOP count=8 end=finish_b
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    SHIFT_STEP tx=3 rx=1 order=msb payload=TX1
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
finish_b:
    SET mask=8 value=0 oe=0
    WAIT_PIN pin=2 level=1 timeout=DEADLINE on_timeout=timeout
    SET mask=0x30 value=0x10 oe=0x30
    HALT

bad:
    SET mask=0x38 value=0x20 oe=0x30
    HALT
timeout:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
