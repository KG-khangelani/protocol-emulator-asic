# ETR board handoff and threshold check

**Concrete test fixture, proposed.** Use Tiny Tapeout's ETR Rev 3.3 demo-board
layout and its released RP2350 firmware v3.1.1. Connect a separately commanded
3.3 V push-pull UART pattern source through a removable signal link to BIDIR
Pmod J15 pin 2, common ground on pin 5 or 11. The released `uart_rx.asm`
receives on UIO1. In PCB Git blob `39427e1e68171522df00475d72d5b052b0d30687`,
J15.2, RP2350 U6.27/GPIO26 and breakout J5.L7 share the same `uio1` net.
J15.1 is UIO0, which this firmware may drive as a dummy TX. Leave it unloaded.
This is a source-based fixture design. The council had no board measurement.
[Board CAD and revision](https://github.com/TinyTapeout/tt-demo-pcb/blob/bbf3dd1f771d5aed249b07ddf130b3ddc8261d60/tinytapeout-demo.kicad_pcb)
[Board pin map](https://github.com/TinyTapeout/tt-demo-pcb/blob/bbf3dd1f771d5aed249b07ddf130b3ddc8261d60/README.md#L56-L85)
[Firmware release](https://github.com/TinyTapeout/tt-micropython-firmware/releases/tag/v3.1.1)

| Fixture operation | What enforces it |
|---|---|
| Select, reset, clock | Select the design once and hold its reset low through a rising edge. The SDK's mux `disable()` selects project zero and drops carrier enable. Disable PWM and manual-button clock monitoring, exclude external clocks, and establish actively driven clock-low before loading. `clock_project_once()` toggles twice. `clock_project_stop()` relinquishes RP2 clock drive, so a stop call in isolation provides no held-low guarantee. |
| Write and read turnaround | Keep the external TX link **open** during all loader operations, including reset and readback. At stopped clock, release the chip via loader-write selection before enabling any RP2 data drivers. For a read, first release all RP2 data drivers while the chip still releases, allow settling, then select the loader read, clock and sample. The SDK's `uio_oe_pico` controls the RP2. UIO0–6 and UIO7 span two SIO banks written separately. Check the settled mask before handing over. |
| Active external source | An idle UART TX is actively high. The second byte of the checked-in eight-word RX image reads `00` at selector `81`, with chip OE `FF`. That would drive UIO1 low against a directly attached idle-high transmitter. A released RP2 pin cannot isolate a second driver on the same copper net. The open link or a separately controlled tri-state buffer is required for this fixture. A host that only stops characters still leaves the active idle level. |
| Arm and run | With the core clock low, establish `E7` and zero RP2 data OE before closing the UART link onto stable idle-high. Give two selected clocks at `E7`. Then `E7 → 67` changes only UI7/GPIO24. The v3.1.1 input-byte writer XORs only changed GPIO17–24 bits in one SIO write. After settling, move `67 → 00` with UI7 still low. Start the continuous measured clock and command the peer's first start within the program's qualified arming window. GPIO writes, pad settling, line release and worst-case UART host-service latency still require fixture timing evidence. |

The peer must have an independently timed start source. A human or USB
command issued after observing PC1 supplies no bound within the two-bit
start timeout at full speed. Pre-arm the two-frame stimulus against a shared
hardware trigger or clock counter. Observe UI7, clock, the shared line and
the fixture's first start. Log the RP2 direction register and physical link or
buffer-enable state. The ASIC's separate internal OE signal is unavailable
on this board pin. A scope trace of a single voltage can miss simultaneous
drivers, especially when they agree on the level.
[Clock, reset and PWM implementation](https://github.com/TinyTapeout/tt-micropython-firmware/blob/d485c7a9986336024e35d790568fca33be1c5665/src/ttboard/demoboard.py#L267-L403)
[Clock pin direction](https://github.com/TinyTapeout/tt-micropython-firmware/blob/d485c7a9986336024e35d790568fca33be1c5665/src/ttboard/pins/pins.py#L279-L285)
[Manual clock monitor](https://github.com/TinyTapeout/tt-micropython-firmware/blob/d485c7a9986336024e35d790568fca33be1c5665/src/ttboard/pins/manual_clock.py#L52-L80)
[RP2350 byte and direction writes](https://github.com/TinyTapeout/tt-micropython-firmware/blob/d485c7a9986336024e35d790568fca33be1c5665/src/ttboard/util/platform/rp2350.py#L67-L119)
[Project selection](https://github.com/TinyTapeout/tt-micropython-firmware/blob/d485c7a9986336024e35d790568fca33be1c5665/src/ttboard/project_mux.py#L503-L578)

**I²C direction and thresholds.** NXP UM10204 Rev. 7.0, §6.1 Table 11,
`tHD;DAT` note 2, concerns the *falling* SCL edge. Its requirement orders
SCL below 0.3 VDD before SDA enters the 0.3–0.7 VDD indeterminate region.
For the selected retained transition SDA is **falling** from high, entering at
0.7 VDD. For a rising SDA the entry threshold would be 0.3 VDD. Figure 38
defines these levels and note 1 applies the data hold timing to data and ACK.
The positive 20 ns digital command gap and the −113.68 ns hypothesized
falling-edge margin refer to the first case. No threshold crossing was measured
on a real bus. [UM10204 Rev. 7.0, pp. 44–45](https://www.nxp.com/docs/en/user-guide/UM10204.pdf#page=44)
