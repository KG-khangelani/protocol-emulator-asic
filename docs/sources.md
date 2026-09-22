# Sources and provenance

Checked: 2026-09-22. Recheck changeable rules before a release/submission.

| ID | Source | Use |
|---|---|---|
| S1 | https://blog.janestreet.com/protocol-emulator-asic-competition/ | Official scope, deadline, allocation and process |
| S2 | https://www.tinytapeout.com/ | Project documentation |
| S3 | https://github.com/TinyTapeout/ttihp-verilog-template/tree/cmos5l | Required starting template |
| S4 | https://github.com/TinyTapeout/ttihp-verilog-template/commit/b86a2a781484bcab7ba522dc5de540086695a430 | Imported immutable revision |
| S5 | https://www.tinytapeout.com/guides/local-hardening/ | General hardening guide; does not itself lock CMOS5L inputs |
| S6 | https://developers.openai.com/codex/guides/agents-md | Repository instructions for Codex |
| U1 | `source-pack.md` | User-provided project direction and historical OpenKnowledge references |

Rule snapshot: open-source and programmable after fabrication; begin with UART,
SPI and I2C. Use IHP CMOS5L and a 6x4 tile allocation. The brief mentions 8x4 as
a potential expansion, not an available budget. Deadline is 18 January 2027.
Stretch protocols do not take priority over the core verification gates.

The template's old inline tile-size comment is not used as a physical-area
measurement. Physical reports will be the authority for usable area and fit.
