# The sensor must see the next falling edge

The ideal-wire ASIC and PIO tests agreed about when to drive and release the bus. This follow-up ran the same ASIC RTL with a target that starts its presence timer and counts slots at its own modeled threshold. Every image occupied 85 words and used 712 public programming steps. There were 32 in-envelope cases per image and two further stress cases per image. [Original contract](../rise-time-contract.md) · [Remote edge definition](../sensed-edge-note.md) · [Prospective wider-slot contract](../recovery-contract.md)

| Firmware | Accepted at 100 pF | Accepted at 1 nF | Measured outcome |
| --- | ---: | ---: | --- |
| Original, 70 µs slots | 16/16 | 8/16 | All eight local-power cases passed at 1 nF. Four modeled parasite-power cases missed presence. The other four recognized nine slot starts and sent the controller down the apparent local-power path. |
| Later presence, shorter one, same slot | 16/16 | 8/16 | Presence was recovered, but the sensor still recognized only nine of seventeen starts in all eight 1 nF parasite cases. |
| Same changes, 76 µs slots | 16/16 | 16/16 | Both actual command bytes decoded, the peer returned the correct power bit and the shortest sensed high interval between slots was 136 clocks, or 2.72 µs. All successful HALTs occurred at 114,303 clocks. |

After a 62 µs zero, the original slot allows only 8 µs before the next falling command. At the declared 3.3 V, 4.7 kΩ, 1 nF and 3.0 V threshold, the exponential crosses in 11.27 µs, rounded up to 11.28 µs on the model grid. Changing only short pulses and the presence sample leaves this longer recovery unresolved. Six extra microseconds per word-bit slot add 4,800 execution clocks or 96 µs for sixteen writes. At 2.2 nF, the wider candidate still missed presence in one case. In another it reported the expected parasite marker while the peer saw only nine slots. The protocol check rejected both. [First two profiles and all observations](original-results.json.gz) · [Wider-slot observations](recovery-results.json.gz)

Three assumptions materially affect the result. Low transitions are immediate, high transitions follow a lumped RC, and these model receivers switch at named thresholds. The DS18B20 input-high specification guarantees logic high by a voltage; it does not give the switching threshold of an individual sample. The controller's 2.31 V threshold is illustrative. This experiment demonstrates why a remote-node measurement can change which firmware is acceptable. It does not characterize a board, sensor population or foundry pad. The initial series ran from 15:29:42 to 15:30:55 UTC and the wider run finished at 15:33:37 UTC. [Manufacturer's DC/AC and slot specifications](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf) · [Digital receiver fixture](rise_peer.sv)

From the repository root in the pinned Linux workbench, use two fresh H:-backed output directories. The first script records the two rejected candidates and checks the favorable controls. The second succeeds only when its prespecified in-envelope and stress criteria hold.

```sh
python3 -B evidence/E0049-review-council/onewire/rise/rise_screen.py build/council-rise-replay
python3 -B evidence/E0049-review-council/onewire/rise/recovery_screen.py build/council-wider-replay
```
