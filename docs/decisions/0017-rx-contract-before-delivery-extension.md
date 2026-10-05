# D17 - Test UART-RX scheduling before extending result delivery

Date: 2026-10-05. Status: reference experiment; no RTL decision yet.

The existing instructions admit an eight-word receive schedule with bounded
start detection, start-center verification, eight center samples and a stop
check, all without a UART-specific RTL path. Freeze and falsify that schedule
before adding storage or control state. See `specs/p-uart-rx-8n1.md` and E0017.

Do not call raw capture a validated frame. The eighth-bit generic write occurs
before the stop check, and a bad stop can leave raw-valid asserted. Nor does a
single overwritten register deliver two retained bytes after HALT. These are
explicit acceptance/delivery questions for the next public-pin RTL experiment,
not reasons to silently add UART-specific error flags or a speculative FIFO.

Verification is risk-based: exhaustive bytes once at the mandatory point,
retained phase corners, timeout, high-at-start-center, bad stops and operand
overflow. Iterate with that focused reference check; run required aggregate
CI at a coherent review milestone. Existing timing/fail-closed/formal and
evidence-integrity gates remain intact. Model success is not RTL or hardware
success, and engineering progress does not promote human fluency.
