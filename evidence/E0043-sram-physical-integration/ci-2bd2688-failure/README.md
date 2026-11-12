# E0043 - Rejected official SRAM physical run

[Run43303867849](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43303867849)
at `2bd2688ee0128e2d1a8d47f187ee7420cbd4d41d` fails. Precheck and the official
public netlist tests are skipped; no submission archive is produced.

Both original ZIPs are retained byte for byte, with API size/digest/source
identity, CRCs and all 961 file hashes verified. Forty exact producing-source
inputs are retained for replay. The original logs bind the actual outer
action, support checkout, immutable physical image and physical Yosys version.
The resolved configuration confirms the pinned 8x4, 50 MHz and electrical
conditions. The same five E0042 RTL files, vendor models, declared macro
views, 144 power-edge connections and nine input buffers are identified.

Magic reports 58,327 errors: 26,095 layer overlaps, 30,720 Metal2 area reports,
688 subcell-abutment reports, 650 latchup-extension reports, 116 SRAM well
spacing reports, 36 diffusion/contact reports and 22 Metal4 spacing reports.
These are preserved as failures; no category is waived.

LVS finds 4,700 layout nets versus 4,717 reference nets and fails top-level
pin matching. Its raw report then triggers a separate invalid JSON escape
error. The raw text and JSON remain in the original archive. Both native
power-continuity checks had passed; that does not establish the absence of
signal/power shorts. The later actual-database diagnosis identifies 17
public-pin/power overlaps. A corrected geometry must pass fresh physical
checks before adoption.

The upload also omitted `.github/workflows/gds-sram.yaml` from its captured
inputs because hidden-file upload was disabled. Its recorded hash matches the
exact producing Git commit, which is separately retained; the missing ZIP
member is recorded explicitly. The next qualification must fix this packaging
gap. Two initial audit assumptions are retained: the workflow file is absent,
and a failed flow has no successful-submission `pdk.json`. The completed audit
uses the actual resolved PDK configuration and reports the missing member.

```text
python evidence/E0043-sram-physical-integration/ci-2bd2688-failure/verify.py --output build/sram-physical-failure-replay
```

A passing replay verifies this rejection and its evidence. It does not qualify
the layout, complete G2 or supersede G1's qualified compact10 pilot.
