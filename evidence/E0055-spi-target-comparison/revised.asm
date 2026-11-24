; SPDX-License-Identifier: Apache-2.0
; Mode-0 emulator test device. SPI requester drives clock 0, MOSI 1, CS_n 2.
; MISO 3 is released throughout the opcode. Pins 5:4 carry terminal markers.
.target od128-sram-v1
.idle 0x04
.data TX0 0x3c
.data TX1 0xa7
.const DEADLINE 80

rearm:
    SET mask=8 value=0 oe=0
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
a0_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a0_await_1
a0_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a0_await_0
a1_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a1_await_1
a1_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a1_await_0
    SET mask=8 value=8 oe=8
a2_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a2_await_1
a2_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a2_await_0
a3_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a3_await_1
a3_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a3_await_0
a4_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a4_await_1
a4_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a4_await_0
a5_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a5_await_1
a5_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a5_await_0
    SET mask=8 value=0 oe=8
a6_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a6_await_1
a6_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a6_await_0
a7_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a7_await_1
a7_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a7_await_0
    SET mask=8 value=0 oe=0
    WAIT_PIN pin=2 level=1 timeout=DEADLINE on_timeout=timeout
    SET mask=0x30 value=0x10 oe=0x30
    HALT
reply_b:
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout
    SET mask=8 value=8 oe=8
b0_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b0_await_1
b0_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b0_await_0
    SET mask=8 value=0 oe=8
b1_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b1_await_1
b1_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b1_await_0
    SET mask=8 value=8 oe=8
b2_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b2_await_1
b2_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b2_await_0
    SET mask=8 value=0 oe=8
b3_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b3_await_1
b3_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b3_await_0
b4_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b4_await_1
b4_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b4_await_0
    SET mask=8 value=8 oe=8
b5_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b5_await_1
b5_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b5_await_0
b6_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b6_await_1
b6_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b6_await_0
b7_await_1:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=b7_await_1
b7_await_0:
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b7_await_0
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
