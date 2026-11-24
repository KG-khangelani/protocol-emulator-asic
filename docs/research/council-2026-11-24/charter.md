# Technical review council, 24 November 2026

The council opened at **14:31:37 UTC / 16:31:37 SAST**. The three-hour review window ends at **17:31:37 UTC / 19:31:37 SAST**. These are the observed start and the planned close. The closing record will give the actual end.

The starting checkout was `e90cca228490423a7fe7c4ae40f7e669200b4d0e` on `main`. Review source, measurements and published material as of this date. The decision concerns where to spend the next engineering day and the remaining time before submission. Adoption of a different chip, a submission, and an owner's demonstration of fluency require separate evidence or action.

## People represented and procedure

One AI chair and three AI reviewers occupy the four available agent slots. Each reviewer prepares one independent brief with three disciplinary perspectives. These are nine assignments across three reviewers. They share a model environment, project history and sources.

| Reviewer | Seats and independent question |
| --- | --- |
| A | Research, computer architecture and mathematics. What would disconfirm generality, compactness or the timing argument? |
| B | Hardware, electrical engineering and embedded systems. Where can behavior at a project pin diverge from that of a powered board and target? |
| C | Software, design and industrial engineering. Can someone program, operate and reproduce this chip, and which changes are affordable before the deadline? |
| Chair | Check claims against primary artifacts, run a separate workload, route adversarial questions, record disagreements and complete the report. |

| Planned UTC interval | Work |
| --- | --- |
| 14:31:37–15:13 | Independent briefs, current rule check, baseline inventory, preregistration and small experiments |
| 15:13–15:48 | Exchange briefs. Each panel challenges another panel's most consequential assumption or recommendation. |
| 15:48–16:32 | Rebuttals, boundary cases and attempts to reproduce or falsify disputed results |
| 16:32–17:01 | Adjudicate evidence, record remaining dissent and agree on what observation would change the ranking |
| 17:01–17:31:37 | Synthesize, check citations, validate the final tree and close the record |

Earlier handoffs may advance individual questions. The time log will record what actually happened. Initial briefs are deposited independently under each panel's own H: scratch directory. Each panel must also name a way its preferred proposal could lose.

## Evidence and decision rules

1. Trace a material claim to a specification, implementation, raw result, independently calculated consequence or original external publication. Distinguish fresh execution, retained execution, derivation, external precedent and untested proposal.
2. Preserve failures, assumptions, timing origins, units and resource denominators. Keep independent expected observations separate from implementation details. Agreement by agents or simulators cannot establish that a common assumption is correct.
3. Compare full-chip alternatives under the existing [evaluation contract](../evaluation-contract.md). Retain the project's mandatory public workloads, actual storage, process, clock constraint, physical gates and evidence level for any claim of architectural superiority.
4. Rank next actions on expected benefit, evidence strength, feasibility, downside and estimated effort. Give priority to a concrete impediment to a required outcome, followed by low-cost tests that could change a consequential decision. Estimates are planning judgments. No synthetic weighted score selects an architecture.
5. Keep scratch in `build/council-2026-11-24/` on H:. Use existing tools and stream large artifacts. Retain small reproducible witnesses under `evidence/E0049-review-council/`. Review commits contain documentation and research records. Keep the twenty D48 inputs, release tags, historical evidence and unrelated working files intact.
