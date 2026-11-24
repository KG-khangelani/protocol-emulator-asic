# Digital 1-Wire power-query screen

Frozen before assembly or simulation. The chair chose this job after inspecting the ISA. The repository's mandatory examples omit it. Selection after seeing the machine limits any inference about generality.

**Question.** Can one public-pin-loaded firmware image on the qualified `0x22` core ask a single modeled DS18B20 whether it uses external or parasite power? This transaction combines open-drain output, two wire-coded command bytes, a timed target response and two observable result paths. The result could distinguish a useful programming improvement from a need for new RTL.

**Independent reference.** Use the device manufacturer's *Powering the DS18B20*, *Initialization*, *Write Time Slots* and *Read Time Slots* sections. Issue Skip ROM (`CC` hex), then Read Power Supply (`B4` hex), least-significant bit first, then one read slot. The target pulls low for parasite power. The generic 1-Wire application note provides a second timing cross-check. [DS18B20 data sheet, Rev 6](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf) · [Analog Devices application note 126, Tables 1–2](https://www.analog.com/en/resources/technical-articles/2022/07/16/06/39/1wire-communication-through-software.html)

**Frozen digital fixture.** One ideal wired-AND DQ on bit 0 with a pull-up, at a continuous 50 MHz after loading. External circuitry releases the shared pins during loader readback. Run the published macro-pin loading sequence, including synchronizer initialization. Reset DQ low for 500 µs, then allow 500 µs from release to first write. Sample presence at about 70 µs after release and require the line back high before the first write. For each of 16 write slots use 70 µs spacing, 6 µs low for one and 62 µs low for zero. For the final read slot release after 6 µs and classify the synchronized input near 14 µs from its falling edge. The low-response fixture pulls DQ low by 10 µs and releases at 45 µs. These are declared digital operating points, including an ideal threshold crossing.

| Test | Independent public observation |
| --- | --- |
| Eight positive cases | Cross presence start at 15 or 60 µs after release, width 60 or 240 µs, and each power response. Observe reset, all 16 write pulses, command order, one read slot and the correct terminal result. |
| Absent target | Idle pull-up throughout presence window. Halt with error before sending commands. |
| Stuck low after reset release | Low through recovery. Halt with error before sending commands. |
| Command mutation | Flip the first transmitted command bit while preserving slot duration. The independent wire checker must detect the incorrect command. |
| Timing mutation | Cut the reset pulse to 400 µs. The independent wire checker must detect the shortened reset. |

Check DQ never actively drives high. Measure elapsed cycles, image words/bytes, decoded command bytes and pulse widths. Count from observed DQ transitions. For positives require the three predeclared drive widths and 70 µs slot spacing exact to one 20 ns edge, at least 60 µs until read-slot completion, clean release, and HALT within 125,000 accepted edges. Public result on bits 2:1 is 1 for external supply, 2 for parasite and 3 for error. Require all byte readbacks, 128 words or fewer, and all controls to discriminate. Any mismatch must remain visible with the original condition and diagnosis. End by **15:40 UTC** with the achieved level even if incomplete. Budget at most 8 MiB of scratch and one Icarus run series in the existing Docker workbench. Keep bulk outputs in the H: scratch folder.

The oracle may read the wire, direction and public result. It must derive expected bytes and times from the contract independently of the encoder, listing and DUT PC. Count simulator runs as digital experiments. Wider target timing, multidrop ROM search, thermometry, physical powering, analog edges, fabricated devices and a host adapter each require different evidence.
