# D49 - Freeze the qualified SRAM design for G4

Date: 2026-11-14. Status: accepted for execution; final qualification pending.

G1 resolved P versus compact10. G2 qualified and adopted SRAM after the
register-store candidates failed placement or routing. G3 supplied a
byte-compatible assembler and independently checked programs. There is no
measured reason to change the core before submission.

Freeze D48's twenty physical inputs and the settled G3 program contract.
Use two independent clean checkouts of one committed candidate for the
official production flow, retaining both original results. Require every
physical, precheck and public-netlist gate, then compare actual geometry,
metrics and observations. The [G4 contract](../specs/g4-submission-candidate.md)
states acceptance and falsification criteria before either run starts.

Close the delivery gaps: current architecture/ISA and Tiny Tapeout documents,
verification and AI-use accounts, external requirements, fresh reproduction
evidence and a verified stable release/submission packet. Correct the obsolete
eight-word/no-SPI/no-I2C datasheet without changing the circuit.

E0047 records execution. Failed gates remain failed; changing a limit or
silently replacing evidence is not completion. Actual submission and owner
fluency remain separate.
