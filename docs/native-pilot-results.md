# Native Boolean pilot: observed results and display limitation

On 5 October 2026, the new `orbit_native_pass_fail` task was executed once against each of two models in Kaggle. This is a separate Boolean-result experiment; historical pilot and campaign results are not pooled with it. The notebook source remains unchanged at the hashes recorded in the [safe receipt](../evidence/native-20261005/receipt.json).

The runtime reported SDK 0.6.1, `shimMode: true`, and `kaggle_benchmarks.results.Boolean`. Each task attempt asks one model to answer six questions using twelve synthetic documents. A `True` result requires the complete output contract, source quotations, authored reference decisions and all three engine checks to pass. Recorded assertion counts are interdependent checks, not independent accuracy samples.

| Model | Provider attempts | Notebook Boolean | Recorded checks | Failed checks | Recorded outcome |
| --- | ---: | --- | ---: | ---: | --- |
| `google/gemini-3.8-flash` | 1 | `True` | 99 | 0 | Pass |
| `google/gemini-3.1-pro-preview` | 1 | `False` | 3 | 1 | Invalid model output: missing `uncertainties` (`row fields 0`) |

Flash ran from `2026-10-05T05:35:18.666501Z` to `2026-10-05T05:35:27.877957Z`. Pro ran from `2026-10-05T05:35:27.897793Z` to `2026-10-05T05:36:12.339163Z`. Two provider attempts were observed in total. No automatic retry or manual corrective technical retry was used. Invalid or `False` output is not eligible for that technical retry.

Pro passed the outer-object and six-row-count checks, then failed the first row's field/object check. The required row keys are `questionId`, `decision`, `evidence`, `excluded`, `uncertainties` and `justification`, matching the schema shown in the prompt. The observed Pro first-row keys were `decision`, `evidence`, `excluded`, `justification` and `questionId`: the required `uncertainties` field was missing, with no extra keys. An empty `uncertainties: []` would satisfy that field-presence requirement. Flash's first row contained all six required keys. The failure establishes an output-contract problem; downstream semantic and engine checks were not reached. It is not a measured semantic accuracy of zero, a transport failure or evidence of general model inferiority.

The safe native JSON projection records an `AGGREGATED` result with `booleanResult: true` for Flash and `booleanResult: false` for Pro. Both runs have state `COMPLETED`, which describes completed execution. The [official SDK documentation](https://github.com/Kaggle/kaggle-benchmarks/blob/ci/user_guide.md) defines Boolean `False` as a failed task result.

The [native task page](https://www.kaggle.com/benchmarks/tasks/celebrum/orbit-native-pass-fail) did not present these two observations together. Publication version 1 displayed only Pro and labelled it PASS, contradicting its serialized `false`. After the archived Flash run JSON was restored to the working output and Update Task was requested, publication version 2 displayed only Flash as PASS. That update added no model execution. The notebook's source decorator remains `version=1`; native publication versions are a separate identity.

The Pro display discrepancy remains unresolved. The unchanged notebook Boolean and native JSON projection are preserved; no receipt was altered to match the page. No backend cause or newer model run is asserted. BuildTaskSnapshot API counts remain pending separate verification. The current page should not be presented as a verified two-model leaderboard.

This is a transparent development pilot with one attempt per model and public synthetic references. It supports the specific pass/contract-failure observations above, not a statistical ranking or proof that one of Orbit's engines is superior. The safe receipt contains selected metadata only, with no original native run hashes, raw chats, source document text, model answers or provider reasoning.

## Guest observation on October 8

A browser without an owner session rendered the public collection and native task version 2, with Sign In/Register controls visible. The collection showed two tasks and two models. The native results table showed Flash as Pass and a Pro row whose output link was labelled `undefined`. Pro did not have a usable displayed score. This is a newer interface observation, separate from the October 5 publication sequence above; it neither changes the archived Boolean nor establishes a backend cause.

## Prepared hardening successor

The [separate hardened pilot](../pilot/native-pass-fail-hardened/README.md) addresses three implementation boundaries found during review: decoder rejection of oversized integers, UTF-8 byte limits and Unicode-safe diagnostic persistence. Schema bounds follow the frozen engine contract. Diagnostic storage failure remains distinct from an invalid model output or failed contract, and must never trigger a new model attempt.

The successor is prepared for inspection and local regression testing. It has not been executed or published on Kaggle. No evidence establishes that these newly covered edge cases caused either historical model observation. The original pilot, engine and receipts remain byte-identical under the [frozen-history inventory](../metadata/frozen-history.json).
