# Frozen physical comparison input

`d34-config.json` is the exact `src/config.json` from G1's qualified compact10
source `29f4b73ae66d2b955f512b5be250f6ed0afcdab8`. Its SHA256 is
`4a3d1133333451c48f550c9ff4a4cdd6255c56f4b43f7d0884b9275824ee790d`,
the unchanged value in `official_cmos5l_8x4.config_sha256_lf`.

Historical G1/G2 staging copies these bytes explicitly; SRAM staging derives
its existing additions from the same checked input. Later production changes
must not silently alter the earlier physical comparisons. Every staged
manifest identifies this source, and the original physical limits and
qualification records remain unchanged. This relocation adds no new physical
qualification and does not promote the experimental SRAM candidate.
