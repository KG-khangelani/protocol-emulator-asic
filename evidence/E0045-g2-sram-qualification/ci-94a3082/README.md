# Complete official SRAM physical qualification

[Run 43348171110](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43348171110)
at `94a30825c633778b8fb1b8374b79d1a419d3fc96` passes GDS, every official
precheck and the complete eighteen-group public-program netlist selection.
`result.json` rechecks the original archives, exact producing inputs, immutable
runtime, actual submitted GDS/netlist and every required observation.

The six required original ZIPs are retained unchanged. `storage.json` describes
their storage, and `zip-files.json` identifies every original member. The API
snapshots and all three completed job logs bind those archives to their actual
producing and consuming jobs. `producer.tar.gz` freezes the audit's source
dependencies from the producing Git revision; replay does not fetch Git history.

All 85 stages retain the original 80 checks in order. The complete original
Magic rule check and LVS report zero violations, all required electrical/timing
conditions pass and all ten prechecks pass. D47's power-port receipt preserves
the original conductors, instances and all 43 public signal pins while exposing
54 existing full-height supply rectangles. The D46 import and exact two-file
contact-rule alignment remain explicit and hash-bound.

The eighteen netlist groups reproduce all 1,052 SPI observations, 1,160 I2C
observations, four boundary records and 36 abort records. The submitted netlist
is byte-identical to E0043's corrected Icarus/Verilator pair. Simulation is
functional zero-delay testing. Positive slack at the 20 ns target is not a
measured maximum frequency. The fast model set combines -40 C standard cells
and -55 C SRAM; it is not an isothermal characterization.

Replay into a fresh directory under `build/`:

```text
python evidence/E0045-g2-sram-qualification/ci-94a3082/verify.py --output build/sram-qualified-replay --controls
```

The controls attempt an unfinished workflow, wrong archive digest, rehashed
power-port count, rehashed skipped required test and rehashed submitted netlist.
Original archives and historical failed runs remain unchanged. Production
adoption, actual-default-command verification and publication are separate G2
completion requirements.
