; SPDX-License-Identifier: Apache-2.0
; One target, ideal open-drain DQ on GPIO 0. Result appears on GPIO 2:1.
; The 20 ns time base makes 50 edges per microsecond.
.target od128-sram-v1
.idle 1
.const SHORT 298
.const SHORT_RECOVERY 3198
.const LONG 3098
.const LONG_RECOVERY 398

    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=error
    SET mask=1 value=0 oe=1
    WAIT cycles=24998
    SET mask=1 value=0 oe=0
    WAIT cycles=3498
    WAIT_PIN pin=0 level=0 timeout=0 on_timeout=error
    WAIT cycles=21497
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
    WAIT cycles=398
    WAIT_PIN pin=0 level=1 timeout=0 on_timeout=parasite
    WAIT cycles=2798
    SET mask=7 value=2 oe=6
    HALT
parasite:
    WAIT cycles=2798
    SET mask=7 value=4 oe=6
    HALT
error:
    SET mask=7 value=6 oe=6
    HALT
