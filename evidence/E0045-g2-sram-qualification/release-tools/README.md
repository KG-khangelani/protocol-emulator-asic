# G2 publication tools

`package.py` refuses a dirty source tree or changed verification inputs. From
the clean milestone commit it packages all six original physical ZIPs, the
original default-command ZIP, and the complete committed E0032-E0045 research
trail, including failures and frozen replay inputs. Its own manifest/checksum
list is separate from the workbench publication's files.

The first preparation check compared Windows working-tree bytes with Linux CI
and rejected an untouched workflow's CRLF checkout. The corrected packager
compares every verification input directly with committed Git bytes, without
normalizing either side. The production guard separately requires the twenty
qualified physical files to match their original bytes in the working tree.

```sh
python3 evidence/E0045-g2-sram-qualification/release-tools/package.py --normal-ci evidence/E0045-g2-sram-qualification/ci-default-75c1e7d
```

`verify_publication.py --directory build/<new-audit>` requires the completed
publication run/job/artifact API records, completed job log, original artifact
ZIP, release metadata and resolved tag commit. Run it in the pinned Linux
workbench after uploading the prepared G2 assets. It verifies every original
publication member, all normal-command stage results and source bindings,
anonymous downloads, committed bundle members, historical SPI gates and exact
public image manifests/configuration/tags. Layer read permission and size are
checked by anonymous HEAD; layer bodies are not downloaded. A failed audit is
retained; use a fresh output location for a corrected attempt.

These tools do not weaken a qualification gate or run a new physical design.
The subsequent publication record retains the exact API/log/archive inputs and
observations from the actual release. It is deliberately outside the release
itself to avoid claiming a self-referential publication proof.
