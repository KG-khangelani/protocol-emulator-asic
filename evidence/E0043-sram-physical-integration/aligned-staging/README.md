# Portable contact-rule alignment rehearsal

The explicit `prepare --guarded --align-magic` option stages D46's tested
Magic setup while retaining all 84 flow stages. Its native 300-second pilot
finishes in **78.771 seconds**, reproduces trial 05's exact fixed-pin database,
and passes both supply checks and all 43 public pin checks. Only the intended
Magic startup and design-directory paths differ in the normalized configuration.
The official workflow has not yet enabled this option.

Twelve actual bad configurations are rejected, including missing SRAM,
wrong timing library, waived DRC, extra source, removed pin guard, relaxed
clock, missing/broadened import patterns, abstract macro DRC, wrong startup,
wrong technology and a changed rule contract. Three additional checks reject
unguarded staging, an altered complete DRC script, and a changed technology
file outside the original two-file patch. Rejected staging creates no output.

The startup now validates the original 35-file Magic tree and the exact
original complete DRC script before checking. It records the actual executed
helper/startup hashes, copied script and two changed technology files.
The official-result auditor checks those actual receipts and file identities.
Native startup rehearsal repeats all 48 contact cases, reproduces all original
findings when used for another Magic stage, and changes only the declared DRC
invocation. Every original flow class and full-check script remains intact.

The **396-file archive**, 5,333,502 bytes, retains source inputs, databases,
native logs, resolved configuration, startup observations and rejection checks.
Windows archive audit and native Linux replay pass. The native replay uses
frozen audit functions, repeats all twelve configuration controls, checks the
actual retained database, reruns both startup scopes and rejects the three
changed inputs. Doctor and all 116 repository checks also pass.

```console
python evidence/E0043-sram-physical-integration/aligned-staging/verify.py --output build/sram-aligned-replay
# In the pinned physical image with the pinned PDK mounted read-only:
python evidence/E0043-sram-physical-integration/aligned-staging/replay_native.py --directory build/sram-aligned-replay
```

This rehearsal does not complete manufacturing qualification. The two initial
whole-chip diagnostics reached their 1,200-second bounds without a completed
DRC report. Their report writer then failed on the empty report; the original
receipts remain untouched, with separate incomplete-result reviews. Corrected
reporting now records execution before parsing, and separately declared
3,600-second diagnostics are running on the same unchanged GDS. The official
180/45/180-minute limits are unchanged. G2 remains active and production is
unchanged.
