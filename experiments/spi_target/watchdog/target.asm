; SPDX-License-Identifier: Apache-2.0
; Mode-0 SPI research target on the unmodified 0x22 VM, MSB first.
; Pins 0/1/2 are SCK/MOSI/CS. Pin 3 is MISO. Pins 5:4 report terminal results.
; A4 returns 00111100. A5 returns 10100111. Bit positions below count from the MSB.
.target od128-sram-v1
.idle 0x04
.data TX0 0x3c
.data TX1 0xa7
.const DEADLINE 80
.const POLLS 32

rearm:
    SET mask=8 value=0 oe=0
    WAIT_PIN pin=2 level=0 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=bad
; The first four bits are 1010. Repeat the same two-bit test twice.
    LOOP count=2 end=command_tail
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=1 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout_head
command_tail:
; The remaining common bits are 010.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=1 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout_head
; The final MOSI bit selects the reply on its rising edge.
    WAIT_PIN pin=0 level=1 timeout=DEADLINE on_timeout=timeout_head
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad
    WAIT_PIN pin=1 level=0 timeout=0 on_timeout=reply_b

; Each half-clock wait has a hardware iteration limit. CS high returns to
; rearm. The opposite SCK level keeps polling; the desired level branches
; out of the loop. Exhaustion jumps forward to a nearby timeout handler.
reply_a:
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout_head
    SET mask=8 value=0 oe=8
    LOOP count=0 end=a_first
after_a_next:
; A1 holds zero and now sets A2 high. A3 holds one and continues at A4.
    WAIT_PIN pin=3 level=0 timeout=0 on_timeout=middle_first
    SET mask=8 value=8 oe=8

; A0 (low) or A2 (high). Hold the same level into the next bit.
a_first:
    LOOP count=POLLS end=a_first_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a_first_fall
a_first_rise_expired:
    LOOP count=0 end=timeout_head
a_first_fall:
    LOOP count=POLLS end=a_first_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=a_next
a_first_fall_expired:
    LOOP count=0 end=timeout_head

; A1 (low) or A3 (high). The held data chooses the next position.
a_next:
    LOOP count=POLLS end=a_next_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=a_next_fall
a_next_rise_expired:
    LOOP count=0 end=timeout_head
a_next_fall:
    LOOP count=POLLS end=a_next_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=after_a_next
a_next_fall_expired:
    LOOP count=0 end=timeout_head

reply_b:
    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout_head
    SET mask=8 value=8 oe=8
    LOOP count=0 end=b_first
after_b_first:
; B0 holds one and now sets B1 low. B1 holds zero and sets B2 high.
    WAIT_PIN pin=3 level=1 timeout=0 on_timeout=b_third_high
    SET mask=8 value=0 oe=8

; B0 (high) or B1 (low).
b_first:
    LOOP count=POLLS end=b_first_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b_first_fall
b_first_rise_expired:
    LOOP count=0 end=timeout_head
b_first_fall:
    LOOP count=POLLS end=b_first_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=after_b_first
b_first_fall_expired:
timeout_head:
    SET mask=0x38 value=0x30 oe=0x30
    HALT

b_third_high:
    SET mask=8 value=8 oe=8

; B2 (high).
b_third:
    LOOP count=POLLS end=b_third_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b_third_fall
b_third_rise_expired:
    LOOP count=0 end=timeout_middle
b_third_fall:
    LOOP count=POLLS end=b_third_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=middle_low
b_third_fall_expired:
    LOOP count=0 end=timeout_middle

middle_low:
    SET mask=8 value=0 oe=8

; A4 (high) or B3 (low). Both keep their level for one more bit.
middle_first:
    LOOP count=POLLS end=middle_first_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=middle_first_fall
middle_first_rise_expired:
    LOOP count=0 end=timeout_middle
middle_first_fall:
    LOOP count=POLLS end=middle_first_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=middle_second
middle_first_fall_expired:
    LOOP count=0 end=timeout_middle

; A5 (high) or B4 (low).
middle_second:
    LOOP count=POLLS end=middle_second_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=middle_second_fall
middle_second_rise_expired:
    LOOP count=0 end=timeout_middle
middle_second_fall:
    LOOP count=POLLS end=middle_second_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=after_middle
middle_second_fall_expired:
timeout_middle:
    SET mask=0x38 value=0x30 oe=0x30
    HALT

after_middle:
; A5 holds one and sets A6 low. B4 holds zero and sets B5 high.
    WAIT_PIN pin=3 level=0 timeout=0 on_timeout=tail_low
    SET mask=8 value=8 oe=8

; B5 (high). Continue directly into B6 without another drive.
b_sixth:
    LOOP count=POLLS end=b_sixth_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=b_sixth_fall
b_sixth_rise_expired:
    LOOP count=0 end=timeout_tail
b_sixth_fall:
    LOOP count=POLLS end=b_sixth_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=tail_first
b_sixth_fall_expired:
    LOOP count=0 end=timeout_tail

tail_low:
    SET mask=8 value=0 oe=8

; A6 (low) or B6 (high). Both keep their level through the last bit.
tail_first:
    LOOP count=POLLS end=tail_first_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=tail_first_fall
tail_first_rise_expired:
    LOOP count=0 end=timeout_tail
tail_first_fall:
    LOOP count=POLLS end=tail_first_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=tail_last
tail_first_fall_expired:
    LOOP count=0 end=timeout_tail

; A7 (low) or B7 (high). Release after the final falling edge.
tail_last:
    LOOP count=POLLS end=tail_last_rise_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=tail_last_fall
tail_last_rise_expired:
    LOOP count=0 end=timeout_tail
tail_last_fall:
    LOOP count=POLLS end=tail_last_fall_expired
    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=rearm
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=finish
tail_last_fall_expired:
timeout_tail:
    SET mask=0x38 value=0x30 oe=0x30
    HALT

finish:
    SET mask=8 value=0 oe=0
    WAIT_PIN pin=2 level=1 timeout=DEADLINE on_timeout=timeout_tail
    SET mask=0x30 value=0x10 oe=0x30
    HALT
bad:
    SET mask=0x38 value=0x20 oe=0x30
    HALT
