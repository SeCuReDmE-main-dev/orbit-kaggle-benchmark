/** The Python/Kaggle harness invokes this implementation, never a Python port. */
import { createInterface } from 'node:readline'
import { parseDossier } from '../packages/evidence-review/src/index.js'
import { classifyDossier, findRelations, resolveHold, traceImpact } from '../packages/evidence-review/src/classification.js'
const input = createInterface({ input: process.stdin });
for await (const line of input) {
  if (!line.trim()) continue;
  try {
    const request = JSON.parse(line), d = parseDossier(request.dossier);
    const engine = request.engine ?? 'n'; if (!['baseline', 'n', 'p'].includes(engine)) throw Error('Unknown engine.');
    const started = performance.now();
    const result = request.operation === 'relations' ? findRelations(d, request.claimIds, engine, request.rules)
      : request.operation === 'impact' ? traceImpact(d, request.changes)
      : request.operation === 'resolve' ? resolveHold(d, d.claims.find(c => c.id === request.claimId)!, request.additionalEvidence, request.attempt, engine, request.rules, request.candidateScope)
      : classifyDossier(d, engine, request.rules);
    process.stdout.write(JSON.stringify({ ok: true, result, durationMs: performance.now() - started }) + '\n');
  } catch (error) { process.stdout.write(JSON.stringify({ ok: false, error: (error as Error).message }) + '\n'); }
}
