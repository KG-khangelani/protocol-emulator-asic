# Isolated Linux replay proof

[Run 43554467650](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43554467650)
at isolated source `7b73d99fbf300c1041aa930409ea63fc031d20f4` passes both frozen physical replays. Each verifies
1,729 original members and 84 producing inputs; the reproduction run also
rejects all nine corruptions. Both full results exactly match their retained
records and Windows reports, apart from the declared controls flag.

The original 14098180180.zip retains 33 indexed proof members,
including actual commands, raw compressed logs, results and runtime identities.
API size/digest, completed upload log, workflow source and all job steps agree.
The CI runner pulled the exact verified public alpha.7 image and inspected its
configuration before and after execution. Image manifest and configuration
digests have distinct roles and are retained in verification.json.

Source scripts and metadata are frozen here. The per-run directories retain
their extracted Linux reports/logs. The original archive preserves every member
without a second copy of the large physical archives. This is separate from
the failed local startup attempts and makes no claim of local Docker recovery.
