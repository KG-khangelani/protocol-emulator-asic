# Passing manufacturing build, rejected supply-port precheck

Official run [43337581691](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43337581691)
builds exact source `232ee20e1eb35726f785225ecfc1a2641e10af33`.
The complete GDS job passes: zero original full Magic DRC findings, zero LVS,
power, routing and antenna errors, all required electrical limits, and positive
setup/hold margins at all three declared model sets. The original full DRC
takes 30:49.940. Worst setup/hold margins are +5.595886/+0.120791 ns at the
unchanged 20 ns target. The mixed fast-temperature model boundary remains.

The independent official precheck passes nine checks, including its complete
KLayout manufacturing deck, but rejects the power ports with **148 LEF errors**.
Internal fragmented supply stripes are exposed as external ports that do not
span within 10 micrometres of both vertical die edges. This is a genuine
submission-interface failure; the candidate is not qualified or promoted.
The netlist test is still running at this retained API snapshot.

Four unchanged original ZIPs retain 1,216 files. Their API digest/size/source
identities, the producing runtime, actual copied Magic rules and original full
DRC script, exact submitted GDS/netlist and 52 frozen producing inputs pass
audit. The precheck log binds the exact consumed submission. The final netlist
is `2a0304aebbb2c9a287cc16ac0e61221116c4f2001420baa7df9c0ab1f035cd2e`,
identical to corrected native trial 05; ongoing simulation remains functional
zero-delay evidence, separate from this rejected interface.

`verify.py --output build/<new-directory>` replays the complete GDS audit using
frozen definitions, verifies all original ZIP members and the pin rejection,
and proves that the aggregate qualification auditor refuses this run.
The standalone audit has an explicit GDS-only mode; that result never claims
passing precheck, netlist qualification or production adoption.
