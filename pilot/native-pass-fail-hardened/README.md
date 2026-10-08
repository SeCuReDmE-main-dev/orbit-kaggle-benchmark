# Hardened native pilot: prepared, not executed on Kaggle

This is a separately identified successor to the [historical Boolean pilot](../native-pass-fail/README.md). It has no hosted model results and is not a published Kaggle task. Its local unit tests are software checks using doubles, not benchmark observations. The historical source, notebook and receipts retain their original bytes and interpretations.

The new identity is `orbit-native-pass-fail-hardening-20261008-v1`; the prospective task function is `orbit_native_pass_fail_hardened`, display name `Orbit hardened native pass/fail`, decorator version 1. This version does not refer to publication version 2 of the existing Kaggle task. The exact historical prompt, twelve synthetic documents, six questions, reference answers and compiled engine are extracted by AST without importing or executing the historical task.

## Authored and generated files

- [contract.py](contract.py) is the sole authored pure validation implementation.
- [task-template.py.in](task-template.py.in) contains the five runtime cells and explicit injection markers.
- [task.py](task.py), [notebook](orbit-native-pass-fail-hardened.ipynb) and [manifest.json](manifest.json) are generated deterministically by [the builder](../../tools/build_native_pilot_hardened.py). Do not edit their embedded copies manually.
- [Local validation receipt](local-validation.json) identifies the actual pure tests, source hashes and execution times. No provider, SDK or real engine is invoked by those tests.

From the repository root:

```bash
python -B tools/build_native_pilot_hardened.py
python -B tools/build_native_pilot_hardened.py --check
python -B -m unittest discover -s tests -p test_native_pilot_hardened.py
```

The first command writes only the three generated successor artifacts. `--check` regenerates expected bytes in memory and compares them without changing files. Generation refuses a changed historical parent and verifies embedded-contract parity, frozen input hashes, five-cell layout, explicit Boolean result and `RUN_MODELS = False`. Unit tests additionally check the full frozen historical inventory.

## Corrected boundaries

Responses are bounded by actual UTF-8 bytes. Duplicate keys, non-finite numbers, malformed JSON and integers beyond a stable 4,300-digit bound are invalid model outputs. Decoder `ValueError` exceptions are normalized without becoming provider incidents. The UTF-16 string bounds used by the TypeScript schema are also enforced in Python: subject/property 300, value 1,000, optional scope fields 500 and quotations 2,000.

Malformed types and shapes return `False` with outcome `invalid-model-output`. Textual references to missing sources, quotations absent from the source, wrong authored-reference decisions and valid engine decisions that disagree with the reference return `False` as `contract-fail`. Provider, process and engine-protocol problems remain exceptions, not failed semantic answers. The frozen engine adapter combines schema and internal errors in `ok: false`; any such rejection after pure input validation is therefore a technical engine error requiring inspection, never a model score. There are no automatic retries; an invalid or false observation is final.

Per-model diagnostics and the aggregate receipt share ASCII JSON escaping and an atomic temporary-file replacement. If storage alone fails after a result was computed, `DiagnosticPersistenceError` retains `computedResult`, `computedOutcome`, phase `diagnostics` and `retryEligible: false`. An aggregate storage failure retains all computed observations in `AggregateDiagnosticPersistenceError.computedObservations` with the same no-retry status. The evidence is incomplete; fixing storage does not justify regenerating an answer. If provider or process failure is already in progress, a secondary diagnostic failure never replaces that original exception. Best-effort categorical events contain no model answer or source content.

Literal quotation occurrence, model-asserted relations and structured scope checks still do not verify semantic entailment or exhaustiveness. This hardening adds no semantic judge and proves no improvement in model accuracy. Local assertions and fixtures must not be merged into historical benchmark denominators.

## Future execution is a separate decision

`RUN_MODELS = False` disables both model dispatch and the native archive/`%choose` cells. The remaining cells are intended only for a native Kaggle runtime: they inspect its SDK/catalog and may prepare the existing hash-checked Node runtime and embedded engine. Importing `task.py` locally is unsupported; the unit tests select definitions by AST and replace external dependencies.

A future authorized execution must check the free quota, SDK 0.6.1 and exact model IDs, then explicitly enable dispatch. It would use a new task and execution identity. It must not overwrite the current task, relabel the historical Flash/Pro observations, or claim that the old native display discrepancy has been resolved. Runtime diagnostics and native archives can contain model outputs and must remain private pending a separate export review.
