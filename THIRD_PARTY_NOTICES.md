# Third-party tools and sources

The project source is licensed under Apache-2.0. The development and physical
flows use independent open-source tools under their own licenses. They are not
relicensed by this repository.

| Project | Use | Upstream license reference |
|---|---|---|
| Tiny Tapeout templates/actions | Project interface and physical workflow | [Apache-2.0](https://github.com/TinyTapeout/tt-gds-action/blob/main/LICENSE) |
| IHP Open PDK | CMOS5L process and library data | [Apache-2.0](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/main/LICENSE) |
| LibreLane | Physical-flow orchestration | [Apache-2.0](https://github.com/librelane/librelane/blob/main/LICENSE) |
| OpenROAD | Physical implementation engine | [BSD-3-Clause](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/LICENSE) |
| Yosys and SBY | Synthesis and formal orchestration | [Yosys ISC](https://github.com/YosysHQ/yosys/blob/main/COPYING), [SBY ISC](https://github.com/YosysHQ/sby/blob/main/COPYING) |
| Icarus Verilog | RTL and gate-level simulation | [GPL-2.0-or-later](https://github.com/steveicarus/iverilog/blob/master/COPYING) |
| Verilator | Lint and secondary simulation | [Artistic-2.0 or LGPL-3.0](https://github.com/verilator/verilator/blob/master/LICENSE) |
| Verible | Verilog parsing and style checks | [Apache-2.0](https://github.com/chipsalliance/verible/blob/master/LICENSE) |
| cocotb | Python-driven verification | [BSD-3-Clause](https://github.com/cocotb/cocotb/blob/master/LICENSE) |

Before publishing a development container, generate an SBOM and retain the
exact notices/source references required by the versions actually distributed.
This table is a human-readable guide, not a substitute for that release audit.
