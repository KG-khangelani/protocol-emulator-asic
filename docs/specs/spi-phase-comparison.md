# Isolated SPI phase/capacity comparison

Status: proposed experiment, 2026-11-03. Production `src/`, the official pins,
config and visualizer are immutable inputs. E0020's failed response-envelope
case remains a failure of the old schedule. This comparison does not qualify
four-mode SPI, physical timing or fabricated silicon.

## Three alternatives and a common ruler

1. Existing eight-word schedule: no RTL change, conditional digital success
   only when target response d<=88 quarter-clocks at H=25. d=89 remains FAIL.
2. Compact phase encoding: keep eight words and the original loader; combine
   DRIVE with a masked auxiliary GPIO update, and put a delay in SAMPLE.
3. Plain phase encoding plus a ten-word store: retain explicit SET/WAIT around
   DRIVE/SAMPLE; add an actual banked loader, not just 64 unaddressable bits.

All use E0020's same external 1 MHz-target SCK/CS and input-response oracle,
both byte orders and a complete byte alphabet. Compare exact word capacity,
public loading/readback, legacy behavior and generic whole-chip Yosys counts
with identical synthesis commands. Include top, loader, store, data registers,
synchronizer and executor. Generic cell/state counts are not CMOS5L area or
timing. No production promotion follows automatically from a lower count.

## Experimental encoding

Existing SET/WAIT/LOOP/WAIT_PIN/HALT, manual SHIFT_STEP and timed SHIFT_BURST
encodings retain their legal-program behavior. Only previously invalid manual
SHIFT reserved space is allocated. New words use opcode `[31:30]=10`, bit29=1,
bit28=order, TX `[27:25]`, RX `[24:22]`, and bit21=0.

| `[20:19]` | Meaning | Compact fields | Plain ten-word fields |
|---|---|---|---|
| 00 | legacy manual SHIFT_STEP | original `[20:0]=0` rule | same |
| 01 | DRIVE | aux mask `[18:11]`, aux value `[10:3]`, `[2:0]=0` | all `[18:0]=0` |
| 10 | SAMPLE | unsigned delay `[18:3]`, `[2:0]=0` | all `[18:0]=0` |
| 11 | invalid | FAULT | FAULT |

TX/RX differ. DRIVE's aux mask cannot include TX/RX. It atomically updates the
masked GPIO values/enables, drives the next TX bit and releases RX, without
sampling RX or advancing the completed-sample count. First DRIVE latches
payload/order/pins and initializes receive state; later DRIVE requires a
completed prior SAMPLE and identical configuration. Values outside aux mask
are ignored. SAMPLE requires a prepared phase byte and identical configuration;
it samples RX without changing any GPIO. After sample eight it commits RX on
that same edge and clears the phase byte. New phase and legacy shift operations
cannot interleave inside an incomplete byte; attempts fault without RX commit.
Sequential complete legacy/phase bytes are allowed and UART's slot flag persists.

Delay zero captures on the SAMPLE execution edge. Delay N>0 latches a pending
sample and captures on the Nth subsequent accepted edge; GPIO/PC hold meanwhile.
Operands are not re-fetched while pending. Disabled edges consume no delay;
reset wins, releases GPIO and aborts all phase flags. Partial HALT faults.
Ordinary SET/WAIT/WAIT_PIN may separate DRIVE/SAMPLE without changing phase
state. Pending phase sampling reuses the previously unreachable shift-period
value one; legal timed bursts still have period>=2. Two explicit phase flags
make this first implementation simple; neither their count nor encoding is a
minimum-state claim. Invalid words, duplicate DRIVE, SAMPLE before DRIVE,
configuration/mode changes and partial HALT must retain GPIO/result and FAULT.

## Exact images at H=25

Compact: LOOP(length=5,count=8), DRIVE(aux mask=0x0c,value=0), WAIT(H-2),
SET SCK high, SAMPLE(delay=1), WAIT(H-4), SET SCK low/CS high, HALT.
DRIVE is at L_j=2+2Hj; SCK rises at R_j=L_j+H; SAMPLE executes R_j+1 and
captures on R_j+2, consuming raw R_j after the synchronizer. Final CS release
is 2+16H=402; HALT PC7 on 403. MOSI changes with each low boundary, including
CS assertion. No nested loop or autonomous protocol clock is introduced.

Plain ten-word image remains E0020's LOOP(length=7,count=8), SET low, DRIVE,
WAIT(H-3), SET high, WAIT(0), SAMPLE(delay=0), WAIT(H-4), SET release, HALT.
It has the same SCK/CS/capture/terminal schedule, HALT PC9, but TX starts one
edge after each low boundary. Each instruction is an actual encoded 32-bit word.

## Ten-word loader and compatibility cost

The experimental banked store contains word0..word9. Data/control register 5
selects a one-bit program-byte bank: bank0 addresses bytes0..31; bank1 addresses
32..63. Only 32..39 are implemented; other reads return zero and writes cannot
alias a word. Only bank values 0/1 are accepted; other values clear ready/length
and restore bank0. A bank write clears ready/length; valid length commit 1..10
restores bank0. Reset clears all ten words and the bank. Register5 readback is
the bank, including the dedicated runtime read selector. GPIO ownership and
all original public ports are unchanged. Readback banking is followed by an
explicit length recommit before execution. Disabled bank writes have no effect.

This intentionally changes original reserved-register5 and invalid-length9/10
behavior. Record those differences; do not call it a drop-in loader. Run the
original legacy suite unmodified. A known failure in
`invalid_length_never_releases_engine` is expected only for this banked variant,
because length9 is now valid. Other unexpected failures block the comparison.
The compact variant must pass the entire original legacy suite. Previously
invalid new phase encodings becoming valid is separately declared above.

## Isolation and falsification

The source builder checks the five production hashes against E0020 before
creating versioned copies under ignored build/. It emits source hashes and
unified diffs. It must never write production files. Preserve failed attempts.
Check new public-pin phase programs on Icarus and Verilator, plus legacy
compatibility, invalid/mixed modes, reset/enable freeze and the bank bounds.
Report status and provenance separately: rejected hypotheses are FAIL/MEASURED,
successful scoped runs PASS/MEASURED, static capacity costs DERIVED, physical
and four-mode outcomes NOT_EVALUATED. Production changes require a subsequent
decision with measured whole-chip costs, compatibility evidence and remaining
formal/physical limitations explicit.
