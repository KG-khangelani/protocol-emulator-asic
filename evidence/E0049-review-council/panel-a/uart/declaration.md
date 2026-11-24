# UART frame timing and the external service deadline

Declared before execution on 2026-11-24 during the independent review. The council began at 14:31:37 UTC. The source under review is `e90cca228490423a7fe7c4ae40f7e669200b4d0e`.

## Question and hypothesis

For a continuously enabled 0x22 receiver executing the catalog's eight-word UART RX image, can two back-to-back frames be correctly sampled at a modest transmitter rate error while the exact-rate host deadline admits a wrong byte? The prediction is yes when the transmitter is faster. The time between raw result overwrites depends on the actual transmitter rate when the program detects each start separately.

Fix receiver period P=434 clocks, transmitter rate offsets of -2%, -1%, 0%, +1%, +2% relative to its nominal reciprocal period and constant ideal bit period throughout both frames. Let s be the start time in receiver-clock units. Transitions coincident with a sampling edge reach the input before its sample in the discrete model. The line is high through initialization. First start occurs at 4 plus a fraction of one clock. There is no jitter, pad uncertainty, reset, loader entry or enable interruption during reception.

## Independent checks and exclusions

1. Derive which raw sampling times must lie in each transmitter bit cell, including the first stop followed immediately by the next start. Check all ten bit cells, early and late phase limits, and that the next start detector is armed in time. Use rational arithmetic. Evaluate the minimum capture interval over all start phases. The proposed uniform host bound is `H+L <= floor(10*T)` in clocks, where T is the actual transmitter period in receiver-clock units and the start detector re-arms in time.
2. Cross-check with the exact-rate published timing table and one deliberately weakened service bound. Find the poll residue that makes a late copy observe the second byte, with dissimilar payloads. Fail the hypothesis if every old-bound first copy is safe for these rates.
3. If the available local Icarus image can run without a pull, exercise the production top, vendor simulation models verified against the profile hashes, and catalog program bytes loaded and read back on the public pins. Use byte pair 55/aa (hex), raw starts at 4, 4.25, 4.5, and 4.75 clocks. Check both raw capture edges, both recovered byte values, terminal state, safe and unsafe first-copy observations. Match a nominal-rate control. A short public-clock-grid stimulus represents constant-period ideal transitions before the first sampling edge at or after each rational boundary. It supplies no analog phase or glitch coverage. Count a tool failure explicitly. Any unanticipated discrepancies stay in the review.
4. Use at most 25 minutes for this independent experiment and at most 8 MiB of H: scratch. A single simulator can corroborate only these cases. The assigned scope includes no requalification or new support claim. A second simulator, new conditions, changed evidence or comparisons with physical host behavior need separate reporting.
