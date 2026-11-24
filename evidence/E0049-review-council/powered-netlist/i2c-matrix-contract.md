# Deep I²C check of the powered launch

The G3 comparison has passed all 55 records. The committee's strongest unresolved electrical challenge involves the I²C handoff and line thresholds. Before interpreting a firmware guard, test the existing powered launch across the entire **original digital** I²C matrix, including late/permanently held clocks and intentionally bad programs.

Use the same submitted G4 netlist, Icarus, pinned functional cell and SRAM models, and permanently high project enable as the [first netlist screen](contract.md). Keep the original `test_i2c_general_public.py` cases, words, target, oracle and trace collection. Change the two warm-up selectors in an isolated fixture to the powered `E7` write. Park at `67` then `00` before the first ordinary execution edge. Request high enable on the sampled reset and all warm-up edges. Reads use the existing clocked SRAM read helper. The project enable stays physically tied high in the testbench.

**Pass condition.** Compare all 1,160 distinct case records by name with the original G4 gate-test ZIP, including the acceptance decisions, error classifications and normalized wire trace hashes. Require every scheduled input class and the original wrong-program controls. A partial run or a changed case remains a reported result. Neither agreeing digital traces nor a larger case count measures pull-ups, threshold crossing, target isolation or PCB behavior.

Budget one Icarus job with a **90-minute** cap, at most **32 MiB** additional H: scratch and a cutoff of **16:46 UTC**. Stream archive members. Reuse the earlier verified netlist and models. Keep the original G4 archive and the prior screen's observations intact.
