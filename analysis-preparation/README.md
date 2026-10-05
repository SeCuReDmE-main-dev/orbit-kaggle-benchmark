# Prepared analysis only — not an executed result

The notebook and script re-score retained observations on Kaggle with zero
model calls. Historical C and the prospective C4 complement stay separate.
Only 36 synthetic questions have scoring references; 24 real questions remain
unscored pending human arbitration. No automatic engine winner is emitted.

## Inputs supplied privately at runtime

Set five environment variables in a PRIVATE Kaggle notebook cell, pointing to
attached files beneath `/kaggle/input`. Do not commit that cell or input paths.

- `ORBIT_C_ARCHIVE`: retained C ZIP, SHA256
  `55276f8c2d772d1c87caec867e0678a7d16d9eec2b97e09beea1ba471c0f3116`.
- `ORBIT_C4_ARCHIVE`: retained C4 ZIP, SHA256
  `3d5ae48fb3900fe04eab8b2a625fee49301adf4d787a9f3079c2ec485ee8326b`.
- `ORBIT_C_CONFIG`: exact historical C manifest. Its canonical campaign identity
  must equal `0d433497a1e6fa7810c68a51709e821d204f3241707e39850e45b2ce6283ad85`.
- `ORBIT_PUBLIC_INPUT`: frozen corpus JSON, file SHA256
  `c8d7f865ba2c9667f43759a053174e3250150704746141e52fc0dca236190f5a`.
- `ORBIT_PRIVATE_GOLD`: synthetic reference JSON, file SHA256
  `a0fffdf104aa36b3e994c57902ffc7a76f2d1a1fd143cc821ca60a4c88e93b23`.

C4's exact manifest is read from its archive. Its identity must equal
`feb51fee0843163946fa85f39e1d450db5960a0375c9c989f60a55c86e433177`.

The original analyser is copied unchanged. Its required SHA256 is
`1ae7a80aaf7fcfbec2e1121af6a73f30777b26976400308bedb7d5e30ecc21d3`.
The companion checkpoint module contains only the two pure identity helpers;
it has no model or transport code.

## Notebook attachment options

Use a private notebook and existing private attachments for the frozen corpus,
references and parent manifest. Attach the two recovered ZIPs through an
owner-authorized private dataset upload only if not already mounted. A `.zip.bin`
suffix preserves byte hashes if Kaggle otherwise expands ZIP attachments.
The source notebook itself contains no input dataset IDs or runtime paths.

Alternatively, attach the public source-only preparation directory as a source
dataset, add it to `sys.path`, set the five private input variables, then call
`run_analysis_only.run()` once on Kaggle. No SDK, secrets or accelerator required.

## Outputs and scope

Only three aggregate JSONs are written beneath
`/kaggle/working/orbit-analysis-public`: C resumption, C4 complement and their
separately identified summary. Temporary categorical ledger projections live
under `/kaggle/temp` and are removed after analysis. Raw archive contents are
never extracted into public notebook outputs. Raw answers, source text, private
input paths and reference labels are not printed or emitted.

C's expected coverage is 60 extractions, 236 productions, 59 complete packets.
C4's expected coverage is zero new extractions, four productions, one packet.
The complement supplies six synthetic decisions per condition in one packet;
its scope is not treated as a full campaign or a population-level comparison.
The combined 240-production coverage is not pooled into one execution identity.

Prepared on 2026-10-05. No local analysis, tests, model generation, account
actions or Kaggle execution have been performed by this preparation task.

## Subsequent execution

Later on October 5, this source was executed in a private Kaggle notebook with
five mounted, hash-verified private inputs. The source preparation state above
is historical. The [resulting public aggregates](../evidence/analysis-20261005/analysis-summary.json)
record Kaggle execution and zero model calls during analysis. Private input
paths, source text and raw answers remain excluded. C and C4 keep separate
identities, with 236 and four productions respectively.
