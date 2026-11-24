# Evidence at council entry

At the review's starting revision, the production guard and all twenty physical input hashes matched both local stable tags. The [fresh check](observation.json) reopens both original G4 submission archives, compares their GDS records with the repository parser and reads their final physical metrics. Both LEFs give 1,724.160 by 710.640 µm. Standard cells and SRAM occupy 110,782.6 µm² of a 1,208,170 µm² core, about 9.17%. Filler area is a separate metric. Routing failures on earlier register-based designs make this percentage a poor predictor of the smallest routable tile arrangement.

Anonymous GETs compared the live tag objects, release titles, descriptions and all 35 and 22 asset name/size/digest triples. The chair's first comparison encountered a title/body mismatch on v0.1.0. It had used the pre-closure release response. The audited [completion notice](../../E0047-g4-submission-candidate/release-notice.json) records the subsequent edit, and the final title/body matched that record. The announcement's HTML also matched the earlier same-day check. These reads check current metadata. The historical publication audits cover actual downloads.

From the repository root with Python 3.11 or later, use a fresh filename under `build/`. Omitting `--live` runs the archive and local Git checks offline.

```powershell
python -B evidence/E0049-review-council/baseline/check.py --live --out build/council-baseline-replay.json
```

The chair also streamed each member of the two G4 run archive sets and the original G5 program CI artifact against the retained SHA-256 indexes. All thirteen ZIP identities and 3,768 member instances matched. The decompressed input total was 1,588,332,728 bytes. Instances include files present in both builds. The original G5 verifier independently re-evaluated the CI evidence and the archived native Windows assembly. Its receipt equals the original CI verification object in every common field and adds the eight-file Windows comparison. Source and asset integrity, digital semantics and human reproducibility answer different questions. [Streamed results](streamed-archives.json) · [Fresh G5 verifier output](g5-original-audit.json) · [Original G5 CI](../../E0048-waveform-replay/ci-66743b6/verification.json)

```powershell
python -B evidence/E0049-review-council/baseline/check_archives.py build/council-original-archives.json
python -B evidence/E0048-waveform-replay/verify.py --directory evidence/E0048-waveform-replay/ci-66743b6 --windows-build evidence/E0048-waveform-replay/windows-build-66743b6 --output build/council-original-g5.json
```
