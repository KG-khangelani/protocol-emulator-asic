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
    SET mask=8 value=0 oe=8
    LOOP count=37 end=a0_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a0_1_seen
a0_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a0_1_seen:
    LOOP count=37 end=a0_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a0_0_seen
a0_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a0_0_seen:
    LOOP count=37 end=a1_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a1_1_seen
a1_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a1_1_seen:
    LOOP count=37 end=a1_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a1_0_seen
a1_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a1_0_seen:
    SET mask=8 value=8 oe=8
    LOOP count=37 end=a2_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a2_1_seen
a2_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a2_1_seen:
    LOOP count=37 end=a2_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a2_0_seen
a2_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a2_0_seen:
    LOOP count=37 end=a3_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a3_1_seen
a3_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a3_1_seen:
    LOOP count=37 end=a3_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a3_0_seen
a3_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a3_0_seen:
    LOOP count=37 end=a4_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a4_1_seen
a4_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a4_1_seen:
    LOOP count=37 end=a4_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a4_0_seen
a4_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a4_0_seen:
    LOOP count=37 end=a5_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a5_1_seen
a5_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a5_1_seen:
    LOOP count=37 end=a5_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a5_0_seen
a5_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a5_0_seen:
    SET mask=8 value=0 oe=8
    LOOP count=37 end=a6_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a6_1_seen
a6_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a6_1_seen:
    LOOP count=37 end=a6_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a6_0_seen
a6_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a6_0_seen:
    LOOP count=37 end=a7_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a7_1_seen
a7_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a7_1_seen:
    LOOP count=37 end=a7_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a7_0_seen
a7_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
a7_0_seen:
    SET mask=8 value=0 oe=0
    WAIT_PIN pin=2 level=1 timeout=DEADLINE on_timeout=timeout
    SET mask=0x30 value=0x10 oe=0x30
    HALT

reply_b:
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
    SET mask=8 value=8 oe=8
    LOOP count=37 end=b0_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b0_1_seen
b0_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b0_1_seen:
    LOOP count=37 end=b0_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b0_0_seen
b0_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b0_0_seen:
    SET mask=8 value=0 oe=8
    LOOP count=37 end=b1_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b1_1_seen
b1_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b1_1_seen:
    LOOP count=37 end=b1_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b1_0_seen
b1_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b1_0_seen:
    SET mask=8 value=8 oe=8
    LOOP count=37 end=b2_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b2_1_seen
b2_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b2_1_seen:
    LOOP count=37 end=b2_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b2_0_seen
b2_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b2_0_seen:
    SET mask=8 value=0 oe=8
    LOOP count=37 end=b3_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b3_1_seen
b3_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b3_1_seen:
    LOOP count=37 end=b3_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b3_0_seen
b3_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b3_0_seen:
    LOOP count=37 end=b4_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b4_1_seen
b4_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b4_1_seen:
    LOOP count=37 end=b4_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b4_0_seen
b4_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b4_0_seen:
    SET mask=8 value=8 oe=8
    LOOP count=37 end=b5_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b5_1_seen
b5_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b5_1_seen:
    LOOP count=37 end=b5_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b5_0_seen
b5_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b5_0_seen:
    LOOP count=37 end=b6_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b6_1_seen
b6_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b6_1_seen:
    LOOP count=37 end=b6_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b6_0_seen
b6_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b6_0_seen:
    LOOP count=37 end=b7_1_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b7_1_seen
b7_1_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b7_1_seen:
    LOOP count=37 end=b7_0_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b7_0_seen
b7_0_expired:
    SET mask=0x38 value=0x30 oe=0x30
    HALT
b7_0_seen:
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
