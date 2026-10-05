*This is a submission for the [Kaggle Benchmarking Challenge](https://dev.to/challenges/kaggle-2026-09-23)*

I started this benchmark with a familiar ambition: build three engines, compare them, and keep the best one.

Then I spent time with what each engine actually showed me. My goal changed. I wanted users to understand their strengths and choose the view that helped them work with the evidence.

That decision became the most useful result of this project. The measurements also gave me something harder to earn: a clearer sense of what I could claim, what I still needed to investigate, and where a successful-looking AI workflow could quietly fall short.

> I used Codex to its fullest potential as a research partner—for code mapping, source comparison, evidence organization, consistency checks, editorial control, and deliverable preparation. I formulated the intent, defined the scope, interpreted the results, arbitrated the conclusions, and preserved every public decision. This collaboration expands my investigative capacity; judgment, responsibility, authorship, and final signature remain under my authority.

## What I Benchmarked

I built **Orbit**, a research companion that connects questions, sources, passages, claims and human review. For this challenge, I focused on one behavior: **can an AI workflow preserve the exact scope of a claim and recognize when the available evidence justifies a conclusion—or a pause?**

Consider two documents about a feature. One says it is supported locally in version 1. Another says it is unavailable in a hosted configuration in version 2. A useful assistant must retain those conditions. Otherwise, it can manufacture a contradiction by comparing statements about different situations.

I examined three evidence engines:

| Engine | What it makes visible | When I would choose it |
|---|---|---|
| **Baseline** | Compact evidence items marked supporting, opposing or insufficient | A quick, readable review of the evidence |
| **N** | Independent sets of supporting evidence (T), indeterminacy (I) and refuting evidence (F) | Examining support and opposition together while keeping unresolved issues visible |
| **P** | Those evidence checks with declared, versioned scope and attribute-relation rules | Investigating how conditions and explicit relations affect the comparison |

The operational recommendations are **ADMIT, REJECT and HOLD**. HOLD records what is missing and what would allow the question to be revisited. These are evidence-handling decisions, not calibrated probabilities of truth.

Baseline and N share the same eligibility checks and equivalent decision logic in this implementation. P uses discrete rules inspired by plithogenic relations; it does not implement the whole mathematical theory. Those details matter when interpreting a tie.

I separated deterministic engine behavior from model behavior. The larger campaign used ten packets of twelve documents and six questions each: **36 authored synthetic reference questions** and **24 real-source questions awaiting human arbitration**. A model extracted evidence once, then received that same extraction under baseline, N, P and a **no-report control (`none`)**. The control is an experimental condition, not a fourth Orbit engine.

The public Kaggle task is a smaller, inspectable development pilot: twelve synthetic documents and six questions. It checks scoped decisions, verbatim quotations and evaluation by the shared TypeScript engine. The public repository also includes 36 synthetic development cases for deterministic replay. These are different artifacts with different denominators.

## Models Tested

I ran **`google/gemini-3.8-flash`** and **`google/gemini-3.1-pro-preview`** through Kaggle Benchmarks SDK **0.6.1**. I chose two distinct Gemini offerings to examine whether the same evidence reports elicited similar behavior across models.

The historical comparative campaign used medium reasoning, a 4,096-token output limit and three repetitions. Each model handled the four conditions with a common extraction, in the retained order baseline, N, P, then none. Keeping the order fixed limits what I can infer about order effects.

I also examined whether agents actually consumed an assigned Context resource. A separate native-browser experiment had a qualification gate before model dispatch. These measure different parts of an AI workflow, so I preserved their results separately.

## Findings

### A tie helped me make a better product decision

The deterministic check returned **108 correct decisions out of 108 scored synthetic evaluations** across the three engines. The broader check recorded **540 passing invariants out of 540**, including changes to ordering, duplicate origins and unrelated sources. Its 72 real-source decision evaluations remained unscored.

Equal recommendations were useful information. They showed that the controlled examples did not establish a winning engine. They also left room for a question I care about as a builder: **which representation helps a person understand the evidence?**

I decided to keep all three engines and let users choose. Baseline gives me a compact review; N helps me inspect coexisting evidence sets; P lets me examine declared relations and conditions. I see complementary value in those views through my product work. Measuring whether they improve user comprehension will require a separate study.

### Giving a model an evidence report can change its behavior

The earlier exploratory aggregate produced a striking pattern:

| Condition | Flash: correct synthetic decisions | Pro: correct synthetic decisions |
|---|---:|---:|
| No report | 90/102 | 108/108 |
| Baseline | 96/102 | 95/108 |
| N | 96/102 | 98/108 |
| P | 96/102 | 89/108 |

**This table belongs to the historical 221-production checkpoint**, not the later recovered campaign coverage. The repository retains its aggregate and identity. There are only six synthetic packet clusters, and repeated answers do not create independent new problems.

Flash returned more correct decisions with each assisted condition at that checkpoint. Pro introduced 13 excessive HOLD decisions with baseline, 10 with N and 19 with P; its no-report condition had none. That observation sharpened my next question: **how should a report communicate uncertainty so that a model preserves necessary caution without deferring a supported conclusion?**

It also reminded me to evaluate the model-report interaction. The same representation can be useful to a human and produce a different pattern in a model's answer.

### Completion and compliance need separate measurements

The latest historical C archive contains **60 extractions and 236 of 240 planned answer productions**, with 59 complete packet comparisons. A heavy-load HTTP 429 interrupted one packet; three following conditions were never dispatched. A separate four-production complement reused that packet's exact extraction and completed the remaining coverage.

I report **236 + 4 productions across two execution identities**. Final accuracy from those recovered archives still requires a new aggregate. The earlier score table stays explicitly historical.

The Context experiment delivered all twelve planned Provider outputs in that lot, but only **nine of twelve met the reading criterion**. All three Pro trajectories assigned Context read originals without consuming Context. A completed output was therefore insufficient evidence of protocol compliance. Semantic quality still awaits human review, and the second twelve-output lot remains open.

The latest native-browser experiment qualified seven of eight workers. One failed the release fingerprint check, so **zero of its 144 planned model trajectories were dispatched**. That is an environment qualification outcome; it contributes no model performance score.

These distinctions changed how I inspect agent systems. I now ask whether the evidence was eligible, the assigned resource was read, the run completed, and the answer was justified—each as its own question.

### What I would measure next

I would complete human arbitration of the 24 real-source questions, aggregate the recovered C and complement ledgers separately, and test new held-out packets with balanced condition order. I would also measure whether people can explain and resolve a scoped conflict more accurately using baseline, N or P.

That last experiment would directly examine the value behind my decision to retain user choice. The current results support a careful next step, with the strengths of each view explained clearly.

## My Benchmark

**[Orbit: scoped evidence and user choice — Kaggle Benchmark](https://www.kaggle.com/benchmarks/celebrum/orbit-scoped-evidence-and-user-choice)**

The collection contains the synthetic development pilot. Its native model results and task code belong to that pilot; the larger historical campaign is documented through separate receipts and aggregates.

**[Public GitHub repository: code, methodology, evidence and job trace](https://github.com/SeCuReDmE-main-dev/orbit-kaggle-benchmark)**

The README explains the experimental units, exact model IDs, source fingerprints, reproduction steps and remaining limitations. The package contains frozen engine source, authored synthetic cases, sanitized execution receipts and an analysis-only preparation notebook. Real-source snapshots, private model outputs and credentials are excluded from the public export.

The original Orbit application and its closed Sanity submission remain unchanged. This benchmark has its own repository and publication record.

I began by trying to choose an engine. I came away wanting to give users an informed choice—and a record they could inspect for themselves.
