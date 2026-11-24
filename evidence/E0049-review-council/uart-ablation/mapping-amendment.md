# Use the installed mapper's default Liberty recipe

At 15:53:01 UTC the first reference preparation stopped on an unknown `-fast` option in the physical container's Yosys 0.69 `abc` command. It reached generic synthesis and DFF mapping but never ran a technology-mapping ABC recipe or emitted area statistics. The [original result](mapping-first-attempt.json) and [log](mapping-first-attempt.log.gz) preserve that failure.

Before obtaining any reference or candidate mapped areas, select the documented default `abc -liberty` recipe for **both** copies, with the same 180-second limit, library pair, lack of physical constraints and verification conditions. This changes the mapping command consistently. The failed command is excluded from numerical comparisons.
