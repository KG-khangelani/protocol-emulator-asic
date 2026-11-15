; SPDX-License-Identifier: Apache-2.0
; G5 frozen control. Relative SET edges: 0,3,8,13,20,29,37,46,52.
.target od128-sram-v1
.idle 0
SET mask=255 value=0 oe=7
WAIT_PIN pin=7 level=1 timeout=32 on_timeout=cleanup
SET mask=7 value=1 oe=7
WAIT cycles=1
SET mask=7 value=3 oe=7
WAIT cycles=3
SET mask=7 value=2 oe=7
WAIT cycles=3
SET mask=7 value=6 oe=7
WAIT cycles=5
SET mask=7 value=7 oe=7
WAIT cycles=7
SET mask=7 value=3 oe=7
WAIT cycles=6
SET mask=7 value=1 oe=7
WAIT cycles=7
SET mask=7 value=0 oe=7
WAIT cycles=4
cleanup:
SET mask=255 value=0 oe=0
HALT
