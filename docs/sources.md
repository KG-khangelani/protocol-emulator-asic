# Sources and provenance

Checked: 2026-09-25. Recheck changeable rules before a release/submission.

| ID | Source | Use |
|---|---|---|
| S1 | https://blog.janestreet.com/protocol-emulator-asic-competition/ | Official scope, deadline, allocation and process |
| S2 | https://www.tinytapeout.com/ | Project documentation |
| S3 | https://github.com/TinyTapeout/ttihp-verilog-template/tree/cmos5l | Required starting template |
| S4 | https://github.com/TinyTapeout/ttihp-verilog-template/commit/b86a2a781484bcab7ba522dc5de540086695a430 | Imported immutable revision |
| S5 | https://www.tinytapeout.com/guides/local-hardening/ | General hardening guide; does not itself lock CMOS5L inputs |
| S6 | https://developers.openai.com/codex/guides/agents-md | Repository instructions for Codex |
| S7 | https://github.com/YosysHQ/oss-cad-suite-build/releases/tag/2026-07-29 | Pinned open EDA developer bundle |
| S8 | https://github.com/chipsalliance/verible/releases/tag/v0.0-4296-g0f262651 | Pinned Verible lint binary |
| S9 | https://github.com/raspberrypi/pico-sdk/tree/079c6f39023649b154152db30f1d781e884879bc | Immutable Raspberry Pi PIO SDK source studied as an I/O-engine precedent |
| S10 | https://github.com/olofk/serv/tree/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8 | Immutable SERV bit-serial CPU reference |
| S11 | https://github.com/YosysHQ/picorv32/tree/ef203c2b0a3fb793280f5114941416c425c5b461 | Immutable PicoRV32 configurable CPU reference; archived at observation |
| S12 | https://github.com/lowRISC/opentitan/tree/0863fb90a54fb6bf53dd26f379337e2f1e7d5916/hw/ip | Immutable OpenTitan protocol-IP documentation reference |
| C1 | https://github.com/Abagel-coder/protocol-emulator/tree/3546bcf6836ecc5256602812337cb92b11f0723f | Contemporary competition architecture self-report; not independently reproduced |
| C2 | https://github.com/satyaammu93/jane-street-asic-2026/tree/65e0a742c1f91ac730c137afea5e154287267d67/protocol_emulator | Contemporary competition architecture self-report; not independently reproduced |
| C3 | https://github.com/sjrai007/gp_pae/tree/621f4326131681d3d76320b83e9d14375961ce3a | Contemporary competition architecture self-report; not independently reproduced |
| U1 | `source-pack.md` | User-provided project direction and historical OpenKnowledge references |

Rule snapshot: open-source and programmable after fabrication; begin with UART,
SPI and I2C. Use IHP CMOS5L and a 6x4 tile allocation. The brief mentions 8x4 as
a potential expansion, not an available budget. Deadline is 18 January 2027.
Stretch protocols do not take priority over the core verification gates.

The template's old inline tile-size comment is not used as a physical-area
measurement. Physical reports will be the authority for usable area and fit.

Research metadata, licenses, Git blob identities and the observation timestamp
for S9-S12 and C1-C3 are locked in `research/source-lock.json`. Upstream claims
remain upstream claims until reproduced in this repository's controlled flow.
