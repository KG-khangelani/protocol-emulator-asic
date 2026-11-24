# Evidence at council entry

At the review's starting revision, the production guard and all twenty physical input hashes matched both local stable tags. The [fresh check](observation.json) reopens both original G4 submission archives, compares their GDS records with the repository parser and reads their final physical metrics. Both LEFs give 1,724.160 by 710.640 µm. Standard cells and SRAM occupy 110,782.6 µm² of a 1,208,170 µm² core, about 9.17%. Filler area is a separate metric. Routing failures on earlier register-based designs make this percentage a poor predictor of the smallest routable tile arrangement.

Anonymous GETs compared the live tag objects, release titles, descriptions and all 35 and 22 asset name/size/digest triples. The chair's first comparison encountered a title/body mismatch on v0.1.0. It had used the pre-closure release response. The audited [completion notice](../../E0047-g4-submission-candidate/release-notice.json) records the subsequent edit, and the final title/body matched that record. The announcement's HTML also matched the earlier same-day check. These reads check current metadata. The historical publication audits cover actual downloads.

From the repository root with Python 3.11 or later, use a fresh filename under `build/`. Omitting `--live` runs the archive and local Git checks offline.

```powershell
python -B evidence/E0049-review-council/baseline/check.py --live --out build/council-baseline-replay.json
```
