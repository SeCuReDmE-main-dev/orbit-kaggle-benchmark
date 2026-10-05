/** Deterministic, network-free engine API shared by the Web, Studio and harness. */
import { canonicalSourceUrl, sourceKey, type Claim, type ClaimEvidence, type ClaimScope, type Dossier } from './index.js'
import { assessTif, buildRelationGraph, compareClaims, type ContradictionRule, type TifAssessment } from './relations.js'

export type EngineId = 'baseline' | 'n' | 'p'
export type Decision = 'ADMIT' | 'REJECT' | 'HOLD'
export const ENGINE_VERSION = 'orbit-classification-1.1.0'
export type EngineRepresentation =
  | { kind: 'three-state'; items: Array<{ sourceId: string; state: 'support' | 'opposition' | 'insufficient'; reasons: string[] }> }
  | { kind: 'independent-sets'; T: string[]; I: string[]; F: string[] }
  | { kind: 'attribute-relations'; T: string[]; I: string[]; F: string[]; ruleVersions: string[]; relations: ReturnType<typeof compareClaims>[] };

/** Classical decision table. Evidence eligibility is identical across engines. */
export function standardDecision(states: Array<'support' | 'opposition' | 'insufficient'>): Decision {
  const present = new Set(states);
  if (!states.length || present.has('insufficient') || present.has('support') && present.has('opposition')) return 'HOLD';
  return present.has('opposition') ? 'REJECT' : 'ADMIT';
}
/** Independent evidence sets may coexist; these are not normalized scores. */
export function independentDecision(result: TifAssessment): Decision {
  if (result.indeterminacy.length || result.truth.length && result.falsity.length) return 'HOLD';
  return result.falsity.length ? 'REJECT' : result.truth.length ? 'ADMIT' : 'HOLD';
}
export const LOGICAL_RULES: ContradictionRule[] = [
  ['allowed', 'prohibited'], ['yes', 'no'], ['true', 'false'],
].flatMap(([left, right]) => ['availability', 'retention', 'supported', 'permitted'].map((property) => ({
  id: `logical:${property}:${left}:${right}`, attribute: `value:${property}`, left, right,
  relation: 'incompatible' as const, version: '1.0.0',
  justification: 'Mutually exclusive declared values of one atomic property under identical explicit conditions. Not a judgment about source truth.',
})))
export type Classification = TifAssessment & {
  engine: EngineId; engineVersion: string; revision: number; decision: Decision;
  independentSources: number; reasons: string[];
  hold?: { missing: string[]; resumeWhen: string; maxAdditionalRequests: 2 };
  semanticVerification: 'agent-asserted-relation';
  representation: EngineRepresentation;
}
export function classifyEvidence(dossier: Dossier, claim: Claim, engine: EngineId = dossier.classificationEngine ?? 'n', rules: ContradictionRule[] = LOGICAL_RULES): Classification {
  const result = assessTif(dossier, claim, engine === 'p' ? rules : []);
  const conflict = Boolean(result.truth.length && result.falsity.length);
  const items: Extract<EngineRepresentation, {kind: 'three-state'}>['items'] = [
    ...result.truth.map(row => ({sourceId: row.sourceId, state: 'support' as const, reasons: []})),
    ...result.falsity.map(row => ({sourceId: row.sourceId, state: 'opposition' as const, reasons: []})),
    ...result.indeterminacy.map(row => ({sourceId: row.sourceId ?? '', state: 'insufficient' as const, reasons: [row.code]})),
  ];
  const sets = {T: result.truth.map(row => row.sourceId), I: result.indeterminacy.map(row => row.code), F: result.falsity.map(row => row.sourceId)};
  const representation: EngineRepresentation = engine === 'baseline' ? {kind: 'three-state', items}
    : engine === 'n' ? {kind: 'independent-sets', ...sets}
    : {kind: 'attribute-relations', ...sets, ruleVersions: [...new Set(rules.map(row => `${row.id}@${row.version}`))].sort(),
        relations: dossier.claims.filter(other => other.id !== claim.id).map(other => compareClaims(claim, other, rules)).filter(row => row.kind !== 'unrelated')};
  // Equal recommendations are valid results: representation and rule application
  // differ, while the shared integrity gate must never be weakened for a comparator.
  const decision = engine === 'baseline' ? standardDecision(items.map(row => row.state)) : independentDecision(result);
  const reasons = [...(conflict ? ['Supporting and refuting passages coexist under the recorded scope.'] : []),
    ...result.indeterminacy.map((row) => `${row.code}: ${row.message}`)];
  const missing = [...new Set([...(conflict ? ['Explain or adjudicate the opposing same-scope passages.'] : []),
    ...result.indeterminacy.map((row) => row.message)])];
  return { ...result, engine, engineVersion: ENGINE_VERSION, revision: dossier.revision, decision,
    independentSources: new Set([...result.truth, ...result.falsity].map((row) => row.independentSource)).size,
    reasons: reasons.length ? reasons : [decision === 'ADMIT' ? 'Only eligible supporting passages remain.' : 'Only eligible refuting passages remain.'],
    ...(decision === 'HOLD' ? { hold: { missing, resumeWhen: 'Supply the missing passage, scope or reviewed distinction, then rerun against the new revision.', maxAdditionalRequests: 2 as const } } : {}),
    semanticVerification: 'agent-asserted-relation', representation,
  };
}
export function classifyDossier(dossier: Dossier, engine: EngineId = dossier.classificationEngine ?? 'n', rules: ContradictionRule[] = LOGICAL_RULES): Classification[] {
  return [...dossier.claims].sort((a, b) => a.id.localeCompare(b.id)).map((claim) => classifyEvidence(dossier, claim, engine, rules));
}
export function compareEvidenceClaims(dossier: Dossier, left: Claim, right: Claim, engine: EngineId = dossier.classificationEngine ?? 'n', rules: ContradictionRule[] = LOGICAL_RULES) {
  const relation = compareClaims(left, right, engine === 'p' ? rules : LOGICAL_RULES);
  const assessments = [classifyEvidence(dossier, left, engine, rules), classifyEvidence(dossier, right, engine, rules)];
  return { ...relation, engine, engineVersion: ENGINE_VERSION,
    basis: assessments.every((a) => a.truth.length || a.falsity.length) ? 'PASSAGE_CHECKED_DECLARED_RELATIONS' : 'DECLARED_ATTRIBUTES_ONLY',
    assessments, humanDecision: null };
}
export function findRelations(dossier: Dossier, ids: string[], engine: EngineId = dossier.classificationEngine ?? 'n', rules: ContradictionRule[] = LOGICAL_RULES) {
  if (ids.length > 25 || new Set(ids).size !== ids.length || ids.some((id) => !dossier.claims.some((c) => c.id === id)))
    throw Error('Select at most 25 unique claim IDs from this dossier.');
  const selected = { ...dossier, claims: dossier.claims.filter((c) => ids.includes(c.id)) };
  return buildRelationGraph(selected, engine === 'p' ? rules : LOGICAL_RULES)
    .map((row) => ({ ...row, engine, engineVersion: ENGINE_VERSION, basis: 'DECLARED_ATTRIBUTES_ONLY' }));
}
export function resolveHold(dossier: Dossier, claim: Claim, additions: ClaimEvidence[], attempt: number, engine: EngineId = dossier.classificationEngine ?? 'n', rules: ContradictionRule[] = LOGICAL_RULES, candidateScope?: ClaimScope) {
  if (!Number.isInteger(attempt) || attempt < 1 || attempt > 2) throw Error('HOLD_REQUEST_LIMIT: at most two additional requests.');
  if (additions.length > 30 || additions.some((e) => !dossier.sources.some((s) => s.id === e.sourceId))) throw Error('Additional evidence must reference this dossier.');
  const before = classifyEvidence(dossier, claim, engine, rules);
  const evidence = [...claim.evidence];
  for (const item of additions) if (!evidence.some((old) => JSON.stringify(old) === JSON.stringify(item))) evidence.push(item);
  if (candidateScope && claim.scopeAttributes && (candidateScope.subject !== claim.scopeAttributes.subject || candidateScope.property !== claim.scopeAttributes.property || candidateScope.value !== claim.scopeAttributes.value))
    throw Error('A scope clarification cannot replace the subject, property or value of the claim.');
  const after = classifyEvidence(dossier, { ...claim, evidence, ...(candidateScope ? { scopeAttributes: candidateScope } : {}) }, engine, rules);
  return { before, after, changed: before.decision !== after.decision,
    attempt, remainingRequests: 2 - attempt, persisted: false,
    nextAction: after.decision === 'HOLD' && attempt === 2 ? 'Keep the conclusion indeterminate.' : 'Propose the revised evidence for human review.' };
}
export type DependencyChange = { kind: 'context' | 'source'; id: string; currentDigest?: string; removed?: boolean };
export function traceImpact(dossier: Dossier, changes: DependencyChange[] = []) {
  if (changes.length > 30) throw Error('At most 30 dependency changes per call.');
  if (changes.some((c) => c.kind === 'source' ? !dossier.sources.some((s) => s.id === c.id)
    : !dossier.knowledgeReads.some((r) => r.path === c.id) && !dossier.claims.some((claim) => claim.contextReads?.some((r) => r.path === c.id))))
    throw Error('Dependency reference is outside this dossier.');
  const links: Array<{ dependency: string; claimId: string; reason: string; responseRevision: number }> = [];
  const evaluate = (claims: Claim[], revision: number, sources: Dossier['sources'], reads: Dossier['knowledgeReads']) => {
    for (const claim of claims) {
      for (const read of claim.contextReads ?? reads) {
        const change = changes.find((c) => c.kind === 'context' && c.id === read.path);
        const current = dossier.knowledgeReads.find((r) => r.path === read.path);
        const digest = change?.removed ? undefined : change?.currentDigest ?? current?.digest;
        if (digest !== read.digest) links.push({ dependency: `context:${read.path}`, claimId: claim.id, reason: 'Context content changed or is missing.', responseRevision: revision });
      }
      for (const evidence of claim.evidence) {
        const change = changes.find((c) => c.kind === 'source' && c.id === evidence.sourceId);
        const original = sources.find((s) => s.id === evidence.sourceId);
        const current = dossier.sources.find((s) => s.id === evidence.sourceId);
        if (change?.removed || !current || change?.currentDigest && change.currentDigest !== original?.contentHash || original && current && sourceKey(original) !== sourceKey(current))
          links.push({ dependency: `source:${evidence.sourceId}`, claimId: claim.id, reason: 'Source content changed or is missing.', responseRevision: revision });
      }
    }
  };
  evaluate(dossier.claims, dossier.revision, dossier.sources, dossier.knowledgeReads);
  for (const snapshot of dossier.history) if (snapshot.answer || snapshot.report) evaluate(snapshot.claims, snapshot.revision, snapshot.sources, snapshot.knowledgeReads);
  return { links, affectedClaimIds: [...new Set(links.map((row) => row.claimId))].sort(),
    affectedResponseRevisions: [...new Set(links.map((row) => row.responseRevision))].sort((a, b) => a - b),
    comparisonInput: changes.length ? 'agent-supplied-changes' : 'recorded-dossier-revisions', persisted: false };
}
export function handoffFindings(dossier: Dossier) {
  const findings: Array<{ handoffId: string; code: string; claimId?: string }> = [];
  for (const handoff of dossier.handoffs ?? []) {
    if (handoff.revision !== dossier.revision) findings.push({ handoffId: handoff.id, code: 'handoff-revision-differs' });
    for (const id of handoff.claimIds) {
      const claim = dossier.claims.find((c) => c.id === id);
      if (!claim) { findings.push({ handoffId: handoff.id, code: 'claim-missing', claimId: id }); continue; }
      if (claim.evidence.some((e) => !handoff.sourceIds.includes(e.sourceId))) findings.push({ handoffId: handoff.id, code: 'provenance-lost', claimId: id });
      if (classifyEvidence(dossier, claim).decision === 'HOLD' && !handoff.openQuestions.length) findings.push({ handoffId: handoff.id, code: 'uncertainty-omitted', claimId: id });
    }
  }
  return findings;
}
export function independentSourceGroups(dossier: Dossier) {
  const groups = new Map<string, string[]>();
  for (const source of dossier.sources) {
    const key = canonicalSourceUrl(source.originUrl ?? source.url);
    groups.set(key, [...(groups.get(key) ?? []), source.id]);
  }
  return [...groups].sort(([a], [b]) => a.localeCompare(b)).map(([origin, sourceIds]) => ({ origin, sourceIds: sourceIds.sort() }));
}
