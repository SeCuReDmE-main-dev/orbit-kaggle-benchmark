# Orbit: scoped evidence, uncertainty and real agent behavior

A public evidence and reproducibility package for the Kaggle Benchmarking Challenge. It asks a concrete question: **can an AI workflow preserve the scope of a claim, its exact supporting sources, and the difference between a justified conclusion and a necessary pause?**

Orbit is a source-grounded research workflow. This package separates deterministic engine checks, hosted model answers, Context consumption, and native-browser qualification. It is a measurement dossier, not a calibrated truth detector or a model leaderboard.

## From choosing a winner to giving the user a choice

The benchmark began with Jean-Sebastien's goal of finding the best engine for Orbit. During development, he chose to **keep all three and let the user select the representation that helps them examine the evidence**. He found their different qualities complementary in his product work. That is the author's design judgment, not a measured proof that the engines are complementary or that one is superior.

The baseline exposes a compact three-state representation of supporting, opposing and insufficient evidence. N makes the supporting, indeterminate and refuting sets explicit as T/I/F. P adds versioned scope and attribute-relation rules. The frozen code implements these representations in `harness/source/packages/evidence-review/src/classification.ts`, with relation rules in `relations.ts`. Baseline and N share the core eligibility and equivalent decision logic on the measured cases; the comparison must preserve that fact. Users retain the decision about which representation to use, and human review retains authority over conclusions.

The `none` condition is an experimental control with no engine report. **It is not a fourth selectable Orbit engine.** The benchmark can still expose costs, failure modes and useful distinctions even though the product decision is to preserve user choice.

- **Baseline:** choose a compact review of evidence items.
- **N:** inspect support, indeterminacy and refutation together as independent sets.
- **P:** examine declared scope and attribute relations with versioned rules.

**Review the article:** [English submission draft](docs/article.en.md).  
**Original implementation:** [SeCuReDmE-main-dev/Orbit](https://github.com/SeCuReDmE-main-dev/Orbit).  
**Public application:** [orbit.securedme.ca](https://orbit.securedme.ca/).

## Models and experimental conditions

The observed Kaggle catalog models were `google/gemini-3.8-flash` and `google/gemini-3.1-pro-preview`. Their exact provider IDs are retained instead of silently substituting newer versions. Kaggle Benchmarks SDK **0.6.1** hosted model runs; the later bootstrap pinned protobuf **5.29.6**. Historical C used reasoning `medium`, a 4,096-token output limit and three repetitions.

Each common extraction was examined under four answer conditions: no engine report (`none`), classic three-way baseline, N (independent supporting/refuting evidence sets and uncertainty), and P (those checks with discrete versioned attribute rules). Baseline and N share decision logic in the measured implementation; different output representations do not establish algorithmic advantage. P is inspired by plithogenic relations and is not a complete implementation of that mathematical theory.

## What actually ran

| Component | Latest archive-backed observation | Interpretation |
|---|---|---|
| B: deterministic engines | 60 questions, 180 evaluations; 108/108 scored synthetic decisions; 540/540 invariants | 72 real-source decisions unscored; controlled inputs show equality |
| Historical C | 60 extractions, 236 productions, 59 completed packet comparisons | Original frozen identity remains 236/240 |
| C4 complement | Four productions, one packet, zero new extractions | Reuses the exact prior extraction under a separate configuration |
| C coverage | 236 historical + four complementary = 240 productions | Two execution identities; not relabeled as one uninterrupted execution |
| D Provider | 12 outputs of 12 planned in this lot; full D target 24 | Nine met the reading criterion; three Pro Context runs did not read Context |
| E native agents | Seven of eight workers passed qualification; zero of 144 planned model trajectories | Fingerprint gate failed before model dispatch |

The reference corpus comprises ten packets of twelve documents and six questions each: **36 authored synthetic reference questions and 24 real questions awaiting human arbitration**. Completion, protocol adherence, literal provenance and semantic accuracy are reported separately.

The historical [221-production aggregate](evidence/c-analysis-historical-221-productions.json) is preserved unchanged. On October 5, the recovered archives were reanalyzed **inside Kaggle, with zero model calls**. The new [C aggregate](evidence/analysis-20261005/c-resumption-analysis.json) verifies 60 extractions, 236 productions and 59 complete comparisons; the [C4 aggregate](evidence/analysis-20261005/c4-complement-analysis.json) verifies a separate four-production, one-packet complement. [The summary](evidence/analysis-20261005/analysis-summary.json) keeps both identities separate. The synthetic C numerators below are unchanged from the earlier checkpoint; additional real-source coverage remains unscored. C4 records 6/6 synthetic decisions per condition on its single reused-extraction packet and is not pooled into C accuracy.

## Native six-question contract result

The new [Boolean task](https://www.kaggle.com/benchmarks/tasks/celebrum/orbit-native-pass-fail) preserves the historical pilot's prompt and bundled engine, while making strict output validity and all checks part of an explicit `bool`. One draft observation per model returned **Flash: True (99 checks, zero failures); Pro: False (invalid output, three checks, one failure)**. A contract failure is retained as an observation; it is not retried or interpreted as semantic accuracy.

Kaggle's version 1 task page displayed PASS for Pro despite its unchanged native JSON containing `booleanResult: false`. Version 2 imported the Flash observation only. This platform display discrepancy is documented in [the native result note](docs/native-pilot-results.md); use the recorded Boolean and checks, not an execution-completed badge. The separate native pilot, 36-case replay and historical campaign have different denominators. See [native source and contract](pilot/native-pass-fail/README.md).

## Findings worth examining

The controlled deterministic engines tied. In the earlier C aggregate, Flash returned 90/102 correct synthetic decisions without an engine report and 96/102 under each assisted condition. Pro returned 108/108 without a report, versus 95/108 baseline, 98/108 N and 89/108 P. Its assisted conditions accumulated 13, 10 and 19 excessive HOLD decisions respectively. These are bounded, historical observations on six synthetic packet clusters, not evidence that an engine or model wins in general.

D demonstrates why a completed checkpoint is an insufficient success criterion: all twelve Provider outputs existed, yet all three Pro runs assigned Context used originals without consuming Context. Nine trajectories met the prescribed read criterion; human semantic review remains pending. E demonstrates a separate boundary: qualification stopped before any model call when one worker failed the release fingerprint.

## Reproduce the public synthetic check in Kaggle

The export contains **only the 36 synthetic development cases**, their authored references and exact frozen C TypeScript engine source. It does not contain private real-source snapshots, real answer keys, provider credentials or raw model answers. This replay is development QA, not a re-creation of the whole hosted C/D/E campaign.

Upload/clone this package into a Kaggle notebook, enable the ordinary dependency download required by npm, and run the following from the repository root in that notebook. Python 3 and **Node.js 20+ with npm** are required (the frozen source uses global Web Crypto). No provider or Kaggle model API key is needed.

```bash
npm install --prefix harness/source --ignore-scripts --no-audit --no-fund
harness/source/node_modules/.bin/esbuild harness/source/tools/engine-jsonl.ts --bundle --platform=node --format=esm --outfile=harness/source/engine-jsonl.mjs
python harness/replay_synthetic.py --corpus harness/synthetic --output outputs/synthetic-replay.json
```

The adapter changes only filesystem locations and invokes the esbuild bundle. Its scoring logic comes from the original Suite A script; every export transformation and both byte hashes are in [the manifest](evidence/export-manifest.json). The self-contained [Kaggle replay notebook](harness/kaggle-replay/README.md) was executed on October 5. It checks every embedded source hash, pins esbuild 0.25.12 and records the runtime and compiled-engine fingerprint. No local benchmark execution is implied.

The public replay schedules **108 decision evaluations, 324 metamorphic checks and 54 relation checks** from its 36 synthetic cases. It does not reproduce the broader B receipt's 540 invariants, which include the unpublished real packets. A zero process exit is insufficient: require `correct == questions`, `invariantsPassed == invariantsTotal`, `relationPassed == relationTotal` for every engine, and an empty printed `failures` list. Inspect failed rows rather than treating execution as a passing score.

The October 5 execution passed all **486 detailed checks**, with zero failures and zero model calls. Inspect the [execution receipt](evidence/replay-20261005/execution-receipt.json) and [complete synthetic rows](evidence/replay-20261005/synthetic-replay.json). The receipt's result SHA-256 matches the downloaded bytes. Runtime: Node 20.19.0 and esbuild 0.25.12.

For authorized owners of the private campaign inputs, `harness/scoring/analyze_kaggle_campaign_results.py` retains the actual aggregate analyzer and its two identity helpers. `write_c_analysis()` requires `/kaggle/working`. It accepts a frozen configuration, the public question metadata, independently supplied references and that configuration's checkpoint directory. Private inputs are not distributed here, and C4 must retain its distinct identity; do not merge ledgers simply to produce a completed-looking score.

[Analysis-only notebook source](analysis-preparation/README.md) supplies the exact public code used for the October 5 Kaggle reanalysis. The executed private runtime added only hash-checked mounted inputs; input paths and real-source content are excluded from this repository. The public source notebooks are intentionally stored without execution outputs; the resulting aggregates are separate evidence files.

## Evidence and job trace

- [Methodology and validity boundaries](docs/methodology.md)
- [Evidence index and chronological job trace](docs/evidence-index.md)
- [Hash and export transformation manifest](evidence/export-manifest.json)
- [Searchable artifact catalog](metadata/artifacts.json)
- [Challenge requirements checklist](docs/judge-checklist.md)
- [Technical delivery and remaining limitations](docs/delivery-20261005.md)

Run the static package validation from this repository root with `python tools/verify_package.py`. After an intentional public edit, regenerate its catalog with `python tools/verify_package.py --refresh-catalog`. Search by a tag with `python tools/verify_package.py --search evidence-provenance`. These checks parse JSON/Python/notebooks, verify empty stored outputs, byte hashes, relative links and Git exclusions. They do not run the benchmark or call models.

Source project at export: branch `master`, HEAD `13b315696bfaf72ac371e5b3498e2ab0d3a9a00e`. The source working tree contained unrelated uncommitted changes. The exported engine is taken from the immutable historical C snapshot, not from those edits. No original Orbit files or deployed application were changed for this package.

## Kaggle links and publication state

The [historical task](https://www.kaggle.com/benchmarks/tasks/celebrum/orbit-scoped-evidence-pilot-v2/1), new Boolean task v2 and [Benchmark collection](https://www.kaggle.com/benchmarks/celebrum/orbit-scoped-evidence-and-user-choice) are public, verified by saved visibility and readback in Kaggle on October 5. The collection includes both task versions. The author explicitly approved Apache 2.0 publication of the new task and collection; this does not assign a blanket license to every historical source export. Parent notebooks and input datasets remain private. Kaggle tags are Evaluation, Factuality, Question Answering, Reasoning and Synthetic.

The [GitHub repository](https://github.com/SeCuReDmE-main-dev/orbit-kaggle-benchmark) was verified without an owner session. Independent Kaggle access remains unverified: the web reader could not open either page, and a cookie-free HTTP request returned 404 for the collection and a generic 200 application shell for the task. This is not evidence that a guest can inspect the rendered collection. See the [publication receipt](evidence/publication-20261005.json); a non-owner browser check remains necessary before submission.

The [English article](docs/article.en.md) remains the earlier working draft delivered for graphics and podcast preparation. Final editorial writing and DEV publication are outside this technical delivery. Update its execution-status sentences from these receipts before submitting; the draft alone is not a final experimental report.

## Limitations and next measurements

Real-source semantic arbitration, independent held-out cases, the second D lot and E model trajectories remain separate open work. Literal quotation checks do not establish relevance or entailment. The synthetic packets are authored reference cases; repetitions of their six packet clusters do not create 108 independent problems. Failed transport, invalid model output, unused tools, policy stops and never-run conditions retain different meanings.

Historical C's HTTP 429 explicitly reported heavy load. The old classifier recorded it as terminal; three later conditions in that packet were never dispatched. The complementary four outputs retain a new identity rather than rewriting that event. The earlier 85% quota stop was local policy, not an observed provider quota-exhaustion refusal. Missing cost values remain unknown, never zero.

Authorship: Jean-Sebastien Beaulieu / SecuredMe. Prepared with Codex as a research and editorial partner, with public decisions, responsibility and final approval retained by the author. No license has been invented for this export; licensing remains the author's decision.
