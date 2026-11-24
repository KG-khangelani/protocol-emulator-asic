# SPI sampling on the nominal wire edge

Frozen independently at approximately 14:45 UTC on 2026-11-24, before running this test. Production hardware at starting checkout `e90cca2` and the thirteen versioned examples are read-only inputs. H: is the only scratch volume. Stop this screen at 15:10 UTC or 8 MiB total panel scratch. A clean build from a different simulator and an actual peripheral belong to a later experiment.

## Question

Can the current 128-word machine use the prior E0027 9/11-word EXACT images to consume the MISO level sampled at the nominal SPI wire edge, preserving the published 8/10-word HELD images' output pin schedule? At the old eight-word limit the all-mode comparison used a larger reference store. The modern 0x22 interface has 128 words. An extra instruction buys sample placement if execution and input latency match the prior model.

## Conditions and independent predictions

At H=25, let S be the nominal sample edge of each of eight bits. Use the unchanged independent equations and adversarial input profiles in `tools/spi_four_mode_oracle.py`. Generate a separate in-memory assembly image from each published source by replacing the one SAMPLE delay of H-2 with delay 1 followed by WAIT H-4. The assembler must produce the archived E0027 EXACT words for that mode and bit order. Compare every emitted word and retain all eight program hashes. Published inputs must assemble to their catalog words.

Use four modes, both bit orders, MOSI0/MISO1/SCK2/CS3, TX=0x96, fixed digital board pulls and continuous execution. The two-flop synchronizer remains active. Drive the raw MISO input per judged core edge with the target released for loader reads. Use only the production chip's public pins, including 0x22 identity, all banks, byte writes/readbacks, committed length, payloads and two disabled flush edges. The simulator runs with hash-checked current RTL and vendor SRAM functional models.

For each mode/order combination run fourteen cases. The EXACT family must pass nine edge-only patterns (RX 0x69 and each of eight one-hot bytes) and two held profiles (RX 0x69, earliest and latest allowed responses). The published HELD image must pass the latest held profile and return the complemented RX byte under the adversarial edge-only target. A one-clock-early mutant with SAMPLE 0 followed by WAIT H-3 must keep the same wire schedule and fail the edge-only case with a wrong RX byte. Total expected results are 96 accepted cases and 16 deliberate rejections in one available simulator.

Check CS idle before assertion and setup/hold, both SCK phases, every resolved MOSI launch, MISO ownership, all output-enable bits, exact byte and valid timing, HALT edge and terminal PC. The expected first-valid edge is last S+2 for EXACT, last S+24 for HELD, last S+1 for the mutant. The oracle judges the mutant against its actual commit edge so a rejection must come from the received byte, not the monitor's choice of capture time. Compare the full driven output and output-enable sequence for the corresponding families. Report changes in public status/PC or raw-result availability separately. No analog aperture, skew, pad delay or attached peripheral behavior is inferred. Preserve any unexpected failure, including disagreement with the E0027 byte listing.
