# Evidence index and job trace

This is a curated chronology of observable jobs, not an entire private conversation export. JSON projections retain campaign/configuration fingerprints, counts and limitations. Full source receipt hashes and exported byte hashes appear in [export-manifest.json](../evidence/export-manifest.json).

| Stage | Observation | Evidence |
|---|---|---|
| Development | Six-question model contract pilot; 36-case synthetic engine development corpus | `harness/synthetic/`; exact source provenance in export manifest |
| October 1 C checkpoint | 57 extractions, 221 productions, 55 completed comparisons | [Historical analysis](../evidence/c-analysis-historical-221-productions.json) |
| October 1 incident | Heavy-load 429 terminates Flash packet 5/repetition 0; following three conditions never run | [Resumption receipt](../evidence/c-resumption-20261003.json), retained failure metadata |
| October 3 C resume | Same configuration; 60 extractions, 236 productions, 59 completed comparisons | [C resumption](../evidence/c-resumption-20261003.json) |
| October 3 C4 | Four separately identified outputs reuse exact retained extraction | [C4 complement](../evidence/c4-complement-20261003.json) |
| October 3 D Provider | 12 outputs, 9 satisfying read protocol, 3 Context-assigned Pro runs omit Context | [D Provider](../evidence/d-provider-20261003.json) |
| October 3 E qualification | Seven of eight native workers pass; dispatch withheld; zero model trajectories | [E qualification](../evidence/e-qualification-20261003.json) |
| October 5 package | Read-only export from original Orbit project into isolated public package | [Export manifest](../evidence/export-manifest.json) |
| October 5 native contract | One draft observation per model: Flash True, 99 checks; Pro False, invalid output, three checks | [Native receipt](../evidence/native-20261005/receipt.json), [display limitation](native-pilot-results.md) |
| October 5 synthetic replay | Executed in Kaggle: 108 decisions, 324 metamorphic checks, 54 relations; all 486 pass, zero model calls | [Execution receipt](../evidence/replay-20261005/execution-receipt.json), [detailed rows](../evidence/replay-20261005/synthetic-replay.json) |
| October 5 retained archive analysis | Executed in Kaggle: C 236 productions and C4 four, separate identities; zero new model calls | [Analysis summary](../evidence/analysis-20261005/analysis-summary.json) |

The original project is frozen for the Sanity judging period. This standalone package does not modify its source, working tree, deployments or historical checkpoint identities. Static package checks execute locally; benchmark and retained-archive analysis executions occur in Kaggle. The zero-call claim applies to replay and archive analysis, not to the native model pilot.

## Reviewable outcome boundaries

- The author chose to keep all three engines and preserve user choice. Their complementary value is his product interpretation, not a statistical finding. The no-report condition is a control.

- Deterministic B equality applies to authored synthetic references; 72 real evaluations are unscored.
- C's latest production coverage is 236 + four across two identities. The October 5 reanalysis retains the historical synthetic numerators; the 24 real questions remain unscored. C4's one-packet results are not pooled into C accuracy.
- D's twelve completed checkpoints are not twelve compliant Context-consumption tests or twelve semantically correct answers.
- E's failed qualification is not 144 model failures; those trajectories were never dispatched.
- Archive fingerprints establish the identity of recovered bytes, not semantic correctness or redistribution rights.

## Excluded materials

Private model answers, real-source snapshots, real reference answer keys, full chat logs, secrets, robot tokens, private dataset links and operational endpoint configuration are not released. Synthetic reference cases are authored test fixtures, distinctly labeled and never represented as real-source gold. The historical score summary contains only public aggregate counts and descriptive intervals.
