# Source-only Kaggle synthetic replay

Upload `orbit-synthetic-replay.ipynb` into a new Kaggle notebook, enable internet, and run once. This notebook makes **zero model calls** and requires no private dataset. It embeds exact bytes of the eight public source/input files listed in `provenance.json` and verifies each SHA-256 before compilation. `run_replay.py` is the readable entry point; the existing `harness/replay_synthetic.py` engine path and logic are preserved exactly.

The runtime requires Node 20 or later. If Node/npm are absent, it uses the official Node 22.20.0 Linux x64 archive after its pinned SHA-256 check, copies only regular Node/npm files, and ignores archive links. It installs pinned esbuild 0.25.12 with lifecycle scripts disabled, verifies the installed version, compiles the unchanged TypeScript implementation, and executes the unchanged replay script. Source files, generated engine, npm cache, and results remain under `/kaggle/working/orbit-synthetic-replay/`.

Download these safe synthetic outputs after execution:

- `results/synthetic-replay.json`: all 486 synthetic rows, per-engine summaries, input engine/oracle hashes, and limitations.
- `results/execution-receipt.json`: 108 decisions, 324 metamorphic checks, 54 relation checks, runtime versions, input/output hashes, and explicit failures.

The notebook fails if coverage differs from the expected counts or any decision, invariant, or relation check fails. The underlying script's exit code alone is insufficient. Preserve failed outputs as observations. A runtime/download/dependency error is a technical failure, not a failing engine score.

`provenance.json` describes this **prepared, unexecuted** source package. An actual receipt is required before reporting a measured result. The corpus contains 36 authored development cases with specification-derived gold; it is not the frozen final 60-question campaign, an independent human accuracy study, or semantic entailment validation.

Subsequent execution on October 5, 2026 passed all 486 checks in Kaggle with
zero model calls. The [downloaded receipt](../../evidence/replay-20261005/execution-receipt.json)
records runtime versions and the matching SHA-256 of the
[complete detailed result](../../evidence/replay-20261005/synthetic-replay.json).
The source preparation provenance above is preserved as historical metadata.

For source-only rebuilding, execute `python harness/kaggle-replay/build_notebook.py` from the repository root. This rebuilds the embedded package and provenance without executing the replay. Do not change the eight frozen inputs to repair a failed measurement.
