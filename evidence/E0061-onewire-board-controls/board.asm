; SPDX-License-Identifier: Apache-2.0
; One target, ideal open-drain DQ on GPIO 0. Result appears on GPIO 3:2.
; The 80 ns FPGA clock gives 12.5 edges per microsecond.
.target od128-sram-v1
.idle 1
.const SHORT 23
.const SHORT_RECOVERY 923
.const LONG 773
.const LONG_RECOVERY 173

    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=error
    SET mask=1 value=0 oe=1
    WAIT cycles=6248
    SET mask=1 value=0 oe=0
    WAIT cycles=910
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=error
    WAIT cycles=5335
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=error

; Skip ROM, least-significant bit first.
; bit 0 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 1 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 2 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY
; bit 3 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY
; bit 4 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 5 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 6 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY
; bit 7 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY

; Read Power Supply, least-significant bit first.
; bit 0 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 1 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 2 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY
; bit 3 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 4 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY
; bit 5 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY
; bit 6 = 0
    SET mask=1 value=0 oe=1
    WAIT cycles=LONG
    SET mask=1 value=0 oe=0
    WAIT cycles=LONG_RECOVERY
; bit 7 = 1
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=SHORT_RECOVERY

; Read one slot and preserve its minimum duration on either result path.
    SET mask=1 value=0 oe=1
    WAIT cycles=SHORT
    SET mask=1 value=0 oe=0
    WAIT cycles=148
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=parasite
    WAIT cycles=698
    SET mask=13 value=4 oe=12
    HALT
parasite:
    WAIT cycles=698
    SET mask=13 value=8 oe=12
    HALT
error:
    SET mask=13 value=12 oe=12
    HALT
