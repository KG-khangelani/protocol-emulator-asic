# Corrected routed netlist in both simulators

Icarus and Verilator each pass all eighteen public UART/SPI/I2C groups on the
same corrected routed netlist. The 1,052 SPI records, 1,160 I2C records, four
boundary records and 36 abort records exactly match the frozen RTL references.
Icarus completes in 3,682.630 seconds; Verilator in 5,393.933 seconds, including
compilation. Both stay inside the predeclared 10,800-second test bound.

The actual netlist SHA256 is
`2a0304aebbb2c9a287cc16ac0e61221116c4f2001420baa7df9c0ab1f035cd2e`.
It contains one real SRAM instance and 353 standard-cell flip-flops and is
byte-identical to the submitted netlist of official run43337581691 at 232ee20.
The 194 test/reference files are frozen from ec5df14. Vendor models and the
netlist are unmodified; the actual pinned workbench container exits zero in
both cases and mounts the original PDK read-only.

Verilator uses the previously qualified zero-delay reset alias with only the
two recorded warning flags. The retained four-way cell probe rechecks 1,025
samples: original Icarus and corrected Verilator agree exactly; original
Verilator and the deliberately stuck reset each disagree on 249 samples.
The earlier CRLF preparation rejection is retained separately.

The 1,246-file archive retains full test logs, results, records, exact inputs,
source/model identities, declarations, container completions and cell probes.
Windows and native Linux evidence replay pass:

```console
python evidence/E0043-sram-physical-integration/guarded-netlist/verify.py --output build/sram-corrected-netlist-replay
```

These are **zero-delay functional** tests. Native trial 05's original-rule
36-contact rejection and the later official power-port precheck rejection
remain failures. D47's fresh complete physical qualification, production
adoption and publication remain separate gates.
