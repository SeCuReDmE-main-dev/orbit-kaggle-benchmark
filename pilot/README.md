# Native Kaggle six-question pilot

This folder contains the exact author-prepared source for `orbit_pilot`: twelve authored synthetic documents and six scoped-evidence questions. It is distinct from the later sixty-question C campaign and its C4 complement.

- `orbit-kaggle-pilot.ipynb`: exact notebook, four cells, three code cells, no stored outputs.
- `task.py`: exact equivalent prepared Python task source.
- `manifest.json`: original preparation manifest, deliberately retaining its historical `prepared-not-run` status. Later execution is recorded separately.
- `historical-run-metadata.json`: sanitized public metadata for the two observed September 30 Kaggle model runs, not current collection results.
- `provenance.json`: exact exported fingerprints, embedded engine/prompt identities and inspection scope.

The notebook embeds the original bundled TypeScript engine and synthetic scoring references. References are kept outside `PROMPT`; publishing them here improves inspection but makes this a transparent development benchmark, not a hidden held-out evaluation. Public synthetic data is authored Test Lab material, with no real-source snapshots or learner data. Raw model answers and hidden reasoning are excluded.

Known native task: https://www.kaggle.com/benchmarks/tasks/celebrum/orbit-scoped-evidence-pilot-v2/1 . The author made this task public and selected Apache 2.0 in Kaggle on October 5; that platform action does not relabel the formerly private parent notebook or the historical preparation files. Current live Code-tab parity should be checked against the `orbit_pilot` function, prompt and embedded-engine fingerprints before calling these bytes the current hosted task binary. The local source and archived run metadata match the same prompt/engine identities.

The first code cell imports Kaggle Benchmarks and inspects its runtime catalog. The second verifies or installs official Node 22.20.0 when Node is absent, refuses Node below 20, defines the task and installs the hash-checked embedded engine. The final cell dispatches both pinned Gemini models; execute it only inside a native Kaggle Benchmark Task after a fresh quota/catalog check. This export makes no model call and does not create a new run. The historical source does not enforce the later campaign's quota policy.

Old markdown says "Private preparation" because these exact bytes predate the task's public action. It describes the preparation's historical state, not the author's current public task visibility. For subsequent runs, pin and record the actual runtime SDK and host settings; avoid claiming that an unpinned import re-creates the exact historical environment.

The public archive shows one development repetition per model, each with six correct decisions, eight literal quotations and 53 passing assertions. Those assertions are correlated checks over six questions. Exact quotations do not establish semantic entailment, and these observations do not establish a universal winning model or engine.
