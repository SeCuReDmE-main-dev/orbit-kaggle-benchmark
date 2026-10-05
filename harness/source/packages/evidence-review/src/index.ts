/** Portable review format shared by Orbit and the Studio import tool. No network or storage. */
export type Stage = "question" | "plan" | "evidence" | "review" | "report";
export type Relation = "supports" | "contradicts" | "contextualizes";
/** A conclusion label, not a confidence score or a measurement of truth. */
export type ClaimDisposition = "supported" | "contested" | "indeterminate";
export type ResearchCorpusKey =
  | "clean-reference"
  | "direct-contradiction"
  | "scope-ambiguity"
  | "version-evolution";
export type ClaimScope = {
  subject: string;
  property: string;
  value: string;
  provider?: string;
  product?: string;
  mode?: string;
  condition?: string;
  version?: string;
  /** Explicit replacement assertion, never inferred from a version number. */
  supersedesVersion?: string;
  effectiveFrom?: string;
  effectiveTo?: string;
  jurisdiction?: string;
  audience?: string;
  attributes?: Record<string, string>;
};
export type ClaimEvidence = {
  sourceId: string;
  quote: string;
  relation: Relation;
  /** Scope asserted by this exact passage, separate from the claim scope. */
  scope?: ClaimScope;
};
export type ContextReference = { path: string; digest: string };
export type Evidence = {
  id: string;
  title: string;
  url: string;
  status: "discovered" | "excerpt-read" | "read";
  text?: string;
  publisher?: string;
  retrievedAt?: string;
  /** Optional path and digest of the Context entry actually inspected. */
  knowledgePath?: string;
  contentHash?: string;
  version?: string;
  /** Original source when this document repeats another publication. */
  originUrl?: string;
};
export type AgentHandoff = {
  id: string;
  fromAgent: string;
  toRole: string;
  revision: number;
  claimIds: string[];
  sourceIds: string[];
  openQuestions: string[];
  /** Identity is declared by the sender, not authenticated by this portable file. */
  attribution: 'agent-declared';
};
export type SourceDecision = {
  sourceId: string;
  decision: "included" | "excluded";
  reason: string;
  at: string;
  by: "human";
  contentKey: string;
};
export type Extraction = {
  id: string;
  sourceId: string;
  field: string;
  value: string;
  quote: string;
  axisId?: string;
};
export type KnowledgeRead = {
  path: string;
  digest: string;
  retrievedAt: string;
  verifiedAt?: string;
};
export type Claim = {
  id: string;
  statement: string;
  kind: "reported" | "inferred" | "hypothesis";
  /** What the recorded evidence currently permits Orbit to say. */
  disposition: ClaimDisposition;
  /** Product, provider, version, or other boundary that qualifies this claim. */
  scope?: string;
  /** Machine-comparable scope. It never replaces the human-readable scope. */
  scopeAttributes?: ClaimScope;
  conditions?: string[];
  effectiveAt?: string;
  /** Exact Knowledge Base entries that influenced this claim. */
  contextReads?: ContextReference[];
  axisIds?: string[];
  evidence: ClaimEvidence[];
  assessment?: string;
  correction?: string;
};
export type Review = {
  claimId: string;
  decision: "accepted" | "needs-work";
  note: string;
  at: string;
  by: "human";
  contentKey: string;
};
/** Derived observations; these never carry human approval. */
export type ClassificationRun = {
  claimId: string;
  inputRevision: number;
  contentKey: string;
  at: string;
  engine: 'baseline' | 'n' | 'p';
  engineVersion: string;
  decision: 'ADMIT' | 'REJECT' | 'HOLD';
  reasons: string[];
  by: 'calculation';
};
export type Proposal = {
  id: string;
  baseRevision: number;
  stage: Stage;
  answer: string;
  report: string;
  axes: string[];
  sources: Evidence[];
  claims: Claim[];
  screeningCriteria: string[];
  extractions: Extraction[];
  knowledgeReads: KnowledgeRead[];
  submissionId?: string;
  submissionKey?: string;
  handoffs?: AgentHandoff[];
  status: "pending" | "accepted" | "rejected";
  createdAt: string;
};
export type Snapshot = {
  revision: number;
  at: string;
  reason: string;
  corpusKey?: ResearchCorpusKey;
  question: string;
  context: string;
  objective: string;
  axes: string[];
  sources: Evidence[];
  claims: Claim[];
  screeningCriteria: string[];
  sourceDecisions: SourceDecision[];
  extractions: Extraction[];
  knowledgeReads: KnowledgeRead[];
  answer: string;
  report: string;
  approvedPlan?: number;
  reviews: Review[];
  classificationEngine?: 'baseline' | 'n' | 'p';
  handoffs?: AgentHandoff[];
};
export type Dossier = {
  format: "orbit-evidence-v1";
  id: string;
  title: string;
  corpusKey?: ResearchCorpusKey;
  question: string;
  objective: string;
  context: string;
  revision: number;
  createdAt: string;
  updatedAt: string;
  axes: string[];
  sources: Evidence[];
  claims: Claim[];
  screeningCriteria: string[];
  sourceDecisions: SourceDecision[];
  extractions: Extraction[];
  knowledgeReads: KnowledgeRead[];
  /** Short answer shown in the observatory before the full audit report. */
  answer: string;
  report: string;
  approvedPlan?: number;
  proposals: Proposal[];
  reviews: Review[];
  history: Snapshot[];
  example: boolean;
  classificationEngine?: 'baseline' | 'n' | 'p';
  handoffs?: AgentHandoff[];
  classificationHistory?: ClassificationRun[];
};
export type Finding = { claimId: string; code: string; message: string };
const stages: Stage[] = ["question", "plan", "evidence", "review", "report"];
const now = () => new Date().toISOString();
export const newId = () => crypto.randomUUID().replaceAll("-", "");
export function createDossier(): Dossier {
  return {
    format: "orbit-evidence-v1",
    id: newId(),
    title: "Nouvelle recherche",
    question: "",
    objective: "",
    context: "",
    revision: 0,
    createdAt: now(),
    updatedAt: now(),
    axes: [],
    sources: [],
    claims: [],
    screeningCriteria: [],
    sourceDecisions: [],
    extractions: [],
    knowledgeReads: [],
    answer: "",
    report: "",
    proposals: [],
    reviews: [],
    history: [],
    example: false,
  };
}

const corpusKeys: ResearchCorpusKey[] = [
  "clean-reference",
  "direct-contradiction",
  "scope-ambiguity",
  "version-evolution",
];

function parseScope(value: unknown): ClaimScope {
  const v = object(value);
  const result: ClaimScope = {
    subject: str(v.subject, 300),
    property: str(v.property, 300),
    value: str(v.value, 1000),
  };
  for (const key of [
    "provider",
    "product",
    "mode",
    "condition",
    "version",
    "supersedesVersion",
    "effectiveFrom",
    "effectiveTo",
    "jurisdiction",
    "audience",
  ] as const) {
    if (v[key] !== undefined) result[key] = str(v[key], 500, true);
  }
  if (v.attributes !== undefined) {
    const attributes = object(v.attributes);
    const entries = Object.entries(attributes);
    if (entries.length > 20) throw Error("Trop d’attributs de portée.");
    result.attributes = Object.fromEntries(
      entries.map(([key, item]) => {
        if (!/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/.test(key))
          throw Error("Nom d’attribut de portée invalide.");
        return [key, str(item, 500, true)];
      }),
    );
  }
  return result;
}
function object(v: unknown): Record<string, any> {
  if (!v || typeof v !== "object" || Array.isArray(v))
    throw Error("Objet attendu.");
  return v as Record<string, any>;
}
function str(v: unknown, max: number, empty = false): string {
  if (typeof v !== "string" || v.length > max || (!empty && !v.trim()))
    throw Error("Texte absent ou trop long.");
  return v;
}
function list(v: unknown, max: number): any[] {
  if (!Array.isArray(v) || v.length > max)
    throw Error("Liste invalide ou trop longue.");
  return v;
}
function integer(v: unknown): number {
  if (!Number.isSafeInteger(v) || Number(v) < 0)
    throw Error("Révision invalide.");
  return Number(v);
}
function unique<T extends { id: string }>(rows: T[]): T[] {
  if (new Set(rows.map((r) => r.id)).size !== rows.length)
    throw Error("Identifiants dupliqués.");
  return rows;
}
export function canonicalSourceUrl(url: string): string {
  const parsed = new URL(publicUrl(url));
  parsed.hash = "";
  return parsed.href;
}
function uniqueSources(rows: Evidence[]): Evidence[] {
  unique(rows);
  // Context entries are separate documents behind one Knowledge Base dashboard URL.
  const identities = rows.map((source) => `${canonicalSourceUrl(source.url)}${source.knowledgePath ? `#kb:${source.knowledgePath}` : ""}`);
  if (new Set(identities).size !== rows.length)
    throw Error("URL de source dupliquée : une URL ne compte qu’une fois, même si elle informe plusieurs axes.");
  return rows;
}
export function publicUrl(v: unknown): string {
  const value = str(v, 2000),
    url = new URL(value);
  if (
    !["https:", "http:"].includes(url.protocol) ||
    url.username ||
    url.password
  )
    throw Error("Une URL HTTP(S) sans identifiants est requise.");
  return value;
}
export function parseEvidence(value: unknown, fallbackId?: string): Evidence {
  const v = object(value);
  if (!["discovered", "excerpt-read", "read"].includes(v.status))
    throw Error("Statut de lecture invalide.");
  return {
    id: str(v.id ?? fallbackId, 160),
    title: str(v.title, 500),
    url: publicUrl(v.url),
    status: v.status,
    ...(v.text !== undefined ? { text: str(v.text, 12000, true) } : {}),
    ...(v.publisher !== undefined
      ? { publisher: str(v.publisher, 300, true) }
      : {}),
    ...(v.retrievedAt !== undefined
      ? { retrievedAt: str(v.retrievedAt, 80) }
      : {}),
    ...(v.knowledgePath !== undefined
      ? { knowledgePath: entryPath(v.knowledgePath) }
      : {}),
    ...(v.contentHash !== undefined
      ? { contentHash: digest(v.contentHash) }
      : {}),
    ...(v.version !== undefined ? { version: str(v.version, 500) } : {}),
    ...(v.originUrl !== undefined ? { originUrl: publicUrl(v.originUrl) } : {}),
  };
}
export function parseHandoffs(value: unknown, claims: Claim[], sources: Evidence[]): AgentHandoff[] {
  return unique(list(value, 60).map((row) => {
    const v = object(row);
    const claimIds = list(v.claimIds, 100).map((id) => str(id, 160));
    const sourceIds = list(v.sourceIds, 30).map((id) => str(id, 160));
    if (claimIds.some((id) => !claims.some((c) => c.id === id)) || sourceIds.some((id) => !sources.some((s) => s.id === id)))
      throw Error('Transmission hors dossier.');
    const referenced = claims.filter((c) => claimIds.includes(c.id));
    if (referenced.some((c) => c.evidence.some((e) => !sourceIds.includes(e.sourceId))))
      throw Error('Une transmission doit conserver les sources de chaque affirmation.');
    return { id: str(v.id, 160), fromAgent: str(v.fromAgent, 160), toRole: str(v.toRole, 160),
      revision: integer(v.revision), claimIds, sourceIds,
      openQuestions: list(v.openQuestions, 30).map((q) => str(q, 1000)), attribution: 'agent-declared' as const };
  }));
}
function entryPath(value: unknown): string {
  const path = str(value, 200);
  if (!/^[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_-]+)*$/.test(path))
    throw Error("Chemin Knowledge Base invalide.");
  return path;
}
function digest(value: unknown): string {
  const hash = str(value, 64);
  if (!/^[a-f0-9]{64}$/.test(hash)) throw Error("Empreinte invalide.");
  return hash;
}
function parseCriteria(value: unknown): string[] {
  return list(value, 12).map((item) => str(item, 300));
}
function parseDecisions(value: unknown, sources: Evidence[]): SourceDecision[] {
  const rows = list(value, 30).map((item) => {
    const v = object(item);
    const sourceId = str(v.sourceId, 160);
    if (!sources.some((s) => s.id === sourceId) ||
        !["included", "excluded"].includes(v.decision) || v.by !== "human")
      throw Error("Décision de source invalide.");
    return { sourceId, decision: v.decision as SourceDecision["decision"],
      reason: str(v.reason, 2000), at: str(v.at, 80), by: "human" as const,
      contentKey: str(v.contentKey, 20000) };
  });
  if (new Set(rows.map((r) => r.sourceId)).size !== rows.length)
    throw Error("Décisions de source dupliquées.");
  return rows;
}
function parseExtractions(value: unknown, sources: Evidence[], axes: string[]): Extraction[] {
  return unique(list(value, 120).map((item) => {
    const v = object(item), sourceId = str(v.sourceId, 160);
    if (!sources.some((s) => s.id === sourceId)) throw Error("Source d’extraction inconnue.");
    const axisId = v.axisId === undefined ? undefined : str(v.axisId, 16);
    if (axisId && (!/^axis_[0-8]$/.test(axisId) || !axes[Number(axisId.slice(5))]))
      throw Error("Axe d’extraction inconnu.");
    return { id: str(v.id, 160), sourceId, field: str(v.field, 300),
      value: str(v.value, 3000), quote: str(v.quote, 2000), ...(axisId ? { axisId } : {}) };
  }));
}
function parseKnowledgeReads(value: unknown): KnowledgeRead[] {
  const rows = list(value, 20).map((item) => {
    const v = object(item);
    return { path: entryPath(v.path), digest: digest(v.digest),
      retrievedAt: str(v.retrievedAt, 80),
      ...(v.verifiedAt === undefined ? {} : { verifiedAt: str(v.verifiedAt, 80) }) };
  });
  if (new Set(rows.map((r) => r.path)).size !== rows.length)
    throw Error("Entrées Knowledge Base dupliquées.");
  return rows;
}
function parseContextReferences(value: unknown): ContextReference[] {
  const rows = list(value, 20).map((item) => {
    const v = object(item);
    return { path: entryPath(v.path), digest: digest(v.digest) };
  });
  if (new Set(rows.map((row) => row.path)).size !== rows.length)
    throw Error("Dépendances Context dupliquées.");
  return rows;
}
function inferredDisposition(evidence: { relation: Relation }[]): ClaimDisposition {
  return evidence.some((item) => item.relation === "contradicts")
    ? "contested"
    : "indeterminate";
}
export function parseClaims(value: unknown): Claim[] {
  return unique(
    list(value, 100).map((row) => {
      const v = object(row);
      if (!["reported", "inferred", "hypothesis"].includes(v.kind))
        throw Error("Nature de l’affirmation invalide.");
      const evidence = list(v.evidence, 30).map((item) => {
        const e = object(item);
        if (!["supports", "contradicts", "contextualizes"].includes(e.relation))
          throw Error("Relation invalide.");
        return {
          sourceId: str(e.sourceId, 160),
          quote: str(e.quote, 2000, true),
          relation: e.relation as Relation,
          ...(e.scope !== undefined ? { scope: parseScope(e.scope) } : {}),
        };
      });
      if (v.disposition !== undefined && !["supported", "contested", "indeterminate"].includes(v.disposition))
        throw Error("État de conclusion invalide.");
      return {
        id: str(v.id, 160),
        statement: str(v.statement, 3000),
        kind: v.kind,
        disposition: (v.disposition ?? inferredDisposition(evidence)) as ClaimDisposition,
        evidence,
        ...(v.scope !== undefined ? { scope: str(v.scope, 1200, true) } : {}),
        ...(v.scopeAttributes !== undefined
          ? { scopeAttributes: parseScope(v.scopeAttributes) }
          : {}),
        ...(v.conditions !== undefined ? { conditions: list(v.conditions, 12).map((condition) => str(condition, 500)) } : {}),
        ...(v.effectiveAt !== undefined ? { effectiveAt: str(v.effectiveAt, 160, true) } : {}),
        ...(v.contextReads !== undefined ? { contextReads: parseContextReferences(v.contextReads) } : {}),
        ...(v.axisIds !== undefined
          ? { axisIds: list(v.axisIds, 9).map((id) => str(id, 16)) }
          : {}),
        ...(v.assessment !== undefined
          ? { assessment: str(v.assessment, 3000, true) }
          : {}),
        ...(v.correction !== undefined
          ? { correction: str(v.correction, 3000, true) }
          : {}),
      };
    }),
  );
}
export function parseProposal(value: unknown, d: Dossier): Proposal {
  const v = object(value),
    stage = v.stage ?? "report";
  if (!stages.includes(stage)) throw Error("Étape inconnue.");
  if (['approvedPlan', 'reviews', 'sourceDecisions', 'humanDecision', 'classificationEngine'].some((key) => key in v))
    throw Error('Une proposition ne peut attribuer ni décision humaine ni moteur.');
  const baseRevision =
    v.expectedRevision === undefined ? d.revision : integer(v.expectedRevision);
  if (baseRevision !== d.revision)
    throw Error("STALE_REVISION: relisez le dossier avant de proposer.");
  const axes = list(v.axes, 9).map((a) => str(a, 300));
  const sources = uniqueSources(
    list(v.sources, 30).map((s, i) => parseEvidence(s, `source_${d.id}_${i}`)),
  );
  const claims = parseClaims(v.claims ?? []);
  const screeningCriteria = parseCriteria(v.screeningCriteria ?? d.screeningCriteria);
  const extractions = parseExtractions(v.extractions ?? [], sources, axes);
  // A proposal cannot confer server verification upon its own Context receipts.
  const knowledgeReads = v.knowledgeReads === undefined
    ? parseKnowledgeReads(d.knowledgeReads)
    : parseKnowledgeReads(v.knowledgeReads).map(({ verifiedAt: _ignored, ...read }) => read);
  for (const c of claims)
    for (const id of c.axisIds ?? [])
      if (!/^axis_[0-8]$/.test(id) || !axes[Number(id.slice(5))])
        throw Error("Axe référencé inexistant.");
  for (const c of claims)
    for (const e of c.evidence)
      if (!sources.some((s) => s.id === e.sourceId))
        throw Error(`Source inconnue : ${e.sourceId}`);
  return {
    id: newId(),
    baseRevision,
    stage,
    answer: str(v.answer ?? "", 10000, true),
    report: str(v.report, 40000),
    axes,
    sources,
    claims,
    screeningCriteria,
    extractions,
    knowledgeReads,
    ...(v.submissionId === undefined ? {} : { submissionId: str(v.submissionId, 160) }),
    ...(v.submissionKey === undefined ? {} : { submissionKey: str(v.submissionKey, 700000) }),
    ...(v.handoffs === undefined ? {} : { handoffs: parseHandoffs(v.handoffs, claims, sources) }),
    status: "pending",
    createdAt: now(),
  };
}
function parseReviews(value: unknown): Review[] {
  return list(value, 200).map((r) => {
    object(r);
    if (!["accepted", "needs-work"].includes(r.decision) || r.by !== "human")
      throw Error("Revue invalide.");
    return {
      claimId: str(r.claimId, 160),
      decision: r.decision,
      note: str(r.note, 3000, true),
      at: str(r.at, 80),
      by: "human",
      contentKey: str(r.contentKey, 700000),
    };
  });
}
/** Imported JSON is never authority: unknown fields are discarded and size limits are reapplied. */
export function parseDossier(value: unknown): Dossier {
  const v = object(value);
  if (v.format !== "orbit-evidence-v1")
    throw Error("Format de dossier inconnu.");
  const d = createDossier();
  d.id = str(v.id, 128);
  if (!/^[a-zA-Z0-9_-]+$/.test(d.id))
    throw Error("Identifiant de dossier invalide.");
  d.title = str(v.title, 500);
  if (v.corpusKey !== undefined) {
    if (!corpusKeys.includes(v.corpusKey)) throw Error("Corpus de recherche inconnu.");
    d.corpusKey = v.corpusKey;
  }
  d.question = str(v.question, 2000, true);
  d.objective = str(v.objective, 3000, true);
  d.context = str(v.context, 12000, true);
  d.revision = integer(v.revision);
  d.createdAt = str(v.createdAt, 80);
  d.updatedAt = str(v.updatedAt, 80);
  d.example = v.example === true;
  if (v.classificationEngine !== undefined) {
    if (!['baseline', 'n', 'p'].includes(v.classificationEngine)) throw Error('Moteur inconnu.');
    d.classificationEngine = v.classificationEngine;
  }
  d.axes = list(v.axes, 9).map((a) => str(a, 300));
  d.sources = unique(list(v.sources, 30).map((s) => parseEvidence(s)));
  d.claims = parseClaims(v.claims);
  if (v.handoffs !== undefined) d.handoffs = parseHandoffs(v.handoffs, d.claims, d.sources);
  d.screeningCriteria = parseCriteria(v.screeningCriteria ?? []);
  d.sourceDecisions = parseDecisions(v.sourceDecisions ?? [], d.sources);
  d.extractions = parseExtractions(v.extractions ?? [], d.sources, d.axes);
  d.knowledgeReads = parseKnowledgeReads(v.knowledgeReads ?? []);
  d.answer = str(v.answer ?? "", 10000, true);
  d.report = str(v.report, 40000, true);
  d.approvedPlan =
    v.approvedPlan === undefined ? undefined : integer(v.approvedPlan);
  d.reviews = parseReviews(v.reviews ?? []);
  if (v.classificationHistory !== undefined) d.classificationHistory = list(v.classificationHistory, 240).map((entry) => {
    const item = object(entry);
    if (item.by !== 'calculation' || !['baseline','n','p'].includes(item.engine)
      || !['ADMIT','REJECT','HOLD'].includes(item.decision)) throw Error('Historique de calcul invalide.');
    return { claimId:str(item.claimId,128),inputRevision:integer(item.inputRevision),contentKey:str(item.contentKey,100000),
      at:str(item.at,80),engine:item.engine,engineVersion:str(item.engineVersion,120),decision:item.decision,
      reasons:list(item.reasons,100).map(reason=>str(reason,1000)),by:'calculation' as const };
  });
  d.proposals = list(v.proposals ?? [], 60).map((p) => {
    object(p);
    const parsed = parseProposal({ ...p, expectedRevision: d.revision }, d);
    if (!["pending", "accepted", "rejected"].includes(p.status))
      throw Error("Proposition invalide.");
    return {
      ...parsed,
      id: str(p.id, 128),
      baseRevision: integer(p.baseRevision),
      createdAt: str(p.createdAt, 80),
      status: p.status,
    };
  });
  d.history = list(v.history ?? [], 60).map((h) => {
    object(h);
    return {
      revision: integer(h.revision),
      at: str(h.at, 80),
      reason: str(h.reason, 500),
      ...(h.corpusKey === undefined
        ? {}
        : corpusKeys.includes(h.corpusKey)
          ? { corpusKey: h.corpusKey as ResearchCorpusKey }
          : (() => { throw Error("Corpus historique inconnu."); })()),
      question: str(h.question ?? "", 2000, true),
      objective: str(h.objective ?? "", 3000, true),
      context: str(h.context ?? "", 12000, true),
      axes: list(h.axes, 9).map((a) => str(a, 300)),
      sources: unique(list(h.sources, 30).map((s) => parseEvidence(s))),
      claims: parseClaims(h.claims),
      screeningCriteria: parseCriteria(h.screeningCriteria ?? []),
      sourceDecisions: parseDecisions(h.sourceDecisions ?? [], list(h.sources, 30).map((s) => parseEvidence(s))),
      extractions: parseExtractions(h.extractions ?? [], list(h.sources, 30).map((s) => parseEvidence(s)), list(h.axes, 9).map((a) => str(a, 300))),
      knowledgeReads: parseKnowledgeReads(h.knowledgeReads ?? []),
      answer: str(h.answer ?? "", 10000, true),
      report: str(h.report, 40000, true),
      approvedPlan:
        h.approvedPlan === undefined ? undefined : integer(h.approvedPlan),
      reviews: parseReviews(h.reviews ?? []),
      ...(h.classificationEngine === undefined ? {} : ['baseline', 'n', 'p'].includes(h.classificationEngine)
        ? { classificationEngine: h.classificationEngine as Dossier['classificationEngine'] }
        : (() => { throw Error('Moteur historique inconnu.'); })()),
      ...(h.handoffs === undefined ? {} : { handoffs: parseHandoffs(h.handoffs, parseClaims(h.claims), list(h.sources, 30).map((s) => parseEvidence(s))) }),
    };
  });
  return d;
}
/** Stable content binding invalidates a human review when its statement or evidence changes. */
export function claimKey(d: Dossier, c: Claim): string {
  const contextReads = c.contextReads ?? d.knowledgeReads.map(({ path, digest }) => ({ path, digest }));
  const currentByPath = new Map(d.knowledgeReads.map((row) => [row.path, row.digest]));
  return JSON.stringify([
    d.question,
    d.objective,
    d.context,
    c,
    c.evidence.map((e) => d.sources.find((s) => s.id === e.sourceId) ?? null),
    d.sourceDecisions.filter((item) => c.evidence.some((e) => e.sourceId === item.sourceId)),
    contextReads.map((read) => ({ ...read, currentDigest: currentByPath.get(read.path) ?? null })),
  ]);
}
/** Binding admission to source content makes a changed source require a new human decision. */
export function sourceKey(source: Evidence): string {
  return JSON.stringify([canonicalSourceUrl(source.url), source.title, source.text ?? "",
    source.knowledgePath ?? "", source.contentHash ?? "", source.version ?? "", source.originUrl ?? ""]);
}
export function changedKnowledgeReads(previous: KnowledgeRead[], current: KnowledgeRead[]): string[] {
  const observed = new Map(current.map((row) => [row.path, row.digest]));
  return previous.filter((row) => observed.has(row.path) && observed.get(row.path) !== row.digest)
    .map((row) => row.path);
}
export function checkpoint(d: Dossier, reason: string): Dossier {
  if (d.history.length >= 60)
    throw Error(
      "Historique plein : exportez puis ouvrez un nouveau dossier. Aucune version n’a été effacée.",
    );
  const next = structuredClone(d);
  next.history.push({
    revision: d.revision,
    at: now(),
    reason,
    corpusKey: d.corpusKey,
    question: d.question,
    objective: d.objective,
    context: d.context,
    axes: d.axes,
    sources: d.sources,
    claims: d.claims,
    screeningCriteria: d.screeningCriteria,
    sourceDecisions: d.sourceDecisions,
    extractions: d.extractions,
    knowledgeReads: d.knowledgeReads,
    answer: d.answer,
    report: d.report,
    approvedPlan: d.approvedPlan,
    reviews: d.reviews,
    classificationEngine: d.classificationEngine,
    handoffs: d.handoffs,
  });
  next.revision++;
  next.updatedAt = now();
  return next;
}
export function acceptProposal(d: Dossier, id: string): Dossier {
  const p = d.proposals.find((p) => p.id === id);
  if (!p || p.status !== "pending") throw Error("Proposition indisponible.");
  if (p.baseRevision !== d.revision)
    throw Error(
      "Proposition périmée : demandez une nouvelle version à l’agent.",
    );
  if (
    p.stage !== "question" &&
    p.stage !== "plan" &&
    d.approvedPlan === undefined
  )
    throw Error(
      "Approuvez un plan avant d’intégrer les preuves ou le rapport.",
    );
  const next = checkpoint(d, `Proposition acceptée : ${p.stage}`);
  if (p.stage === "plan") {
    next.axes = p.axes;
    next.screeningCriteria = p.screeningCriteria;
    next.knowledgeReads = p.knowledgeReads;
    next.approvedPlan = undefined;
  } else if (p.stage !== "question") {
    const axesChanged = JSON.stringify(next.axes) !== JSON.stringify(p.axes);
    next.axes = p.axes;
    next.sources = p.sources;
    next.claims = p.claims;
    next.handoffs = p.handoffs;
    next.extractions = p.extractions;
    next.knowledgeReads = p.knowledgeReads;
    next.screeningCriteria = p.screeningCriteria;
    next.sourceDecisions = next.sourceDecisions.filter((item) => next.sources.some((source) => source.id === item.sourceId));
    if (axesChanged) next.approvedPlan = undefined;
    if (p.stage === "report") {
      next.answer = p.answer;
      next.report = p.report;
    }
  }
  next.proposals.find((row) => row.id === id)!.status = "accepted";
  return next;
}
export function reviewFindings(d: Dossier): Finding[] {
  const findings: Finding[] = [];
  for (const source of d.sources) {
    const decision = d.sourceDecisions.find((item) => item.sourceId === source.id);
    if (!decision) findings.push({ claimId: source.id, code: "SOURCE_SCREENING_PENDING",
      message: `${source.title} : décision d’admission manquante.` });
    else if (decision.contentKey !== sourceKey(source)) findings.push({ claimId: source.id,
      code: "SOURCE_SCREENING_STALE", message: `${source.title} : la source a changé depuis son admission.` });
  }
  for (const c of d.claims) {
    const contextReads = c.contextReads ?? d.knowledgeReads.map(({ path, digest }) => ({ path, digest }));
    for (const read of contextReads) {
      const current = d.knowledgeReads.find((item) => item.path === read.path);
      if (!current || current.digest !== read.digest)
        findings.push({
          claimId: c.id,
          code: "CONTEXT_ENTRY_CHANGED",
          message: `Entrée Sanity Context modifiée ou non disponible : ${read.path}. Cette conclusion doit être revue.`,
        });
    }
    if (!c.evidence.length)
      findings.push({
        claimId: c.id,
        code: "NO_EVIDENCE",
        message: "Aucune preuve liée à cette affirmation.",
      });
    for (const e of c.evidence) {
      const s = d.sources.find((s) => s.id === e.sourceId);
      if (!s) {
        findings.push({
          claimId: c.id,
          code: "MISSING_SOURCE",
          message: `Source absente : ${e.sourceId}`,
        });
        continue;
      }
      if (s.status === "discovered")
        findings.push({
          claimId: c.id,
          code: "NOT_READ",
          message: `${s.title} : lecture non déclarée.`,
        });
      const decision = d.sourceDecisions.find((item) => item.sourceId === s.id);
      if (decision?.decision === "excluded") findings.push({ claimId: c.id,
        code: "EXCLUDED_SOURCE_CITED", message: `${s.title} : source exclue mais citée.` });
      if (!e.quote || !s.text || !s.text.includes(e.quote))
        findings.push({
          claimId: c.id,
          code: "QUOTE_UNVERIFIED",
          message: `${s.title} : passage exact non vérifiable dans l’extrait conservé.`,
        });
      if (e.relation === "contradicts")
        findings.push({
          claimId: c.id,
          code: "CONTRADICTION_REPORTED",
          message:
            "Contradiction signalée par l’agent : comparer les périmètres avant de conclure.",
        });
    }
    if (c.disposition === "supported" && c.evidence.some((e) => e.relation === "contradicts"))
      findings.push({
        claimId: c.id,
        code: "SUPPORTED_CLAIM_HAS_CONTRADICTION",
        message: "Conclusion déclarée soutenue malgré une preuve contradictoire : vérifier la portée ou choisir « contestée ».",
      });
    if (c.disposition === "contested" && !c.evidence.some((e) => e.relation === "contradicts"))
      findings.push({
        claimId: c.id,
        code: "CONTESTED_CLAIM_NEEDS_CONTRADICTION",
        message: "Conclusion déclarée contestée sans passage contradictoire enregistré.",
      });
    if (c.disposition === "supported" && !c.evidence.some((e) => e.relation === "supports"))
      findings.push({
        claimId: c.id,
        code: "SUPPORTED_CLAIM_NEEDS_SUPPORT",
        message: "Conclusion déclarée soutenue sans passage qui la soutient.",
      });
    const review = d.reviews.find((r) => r.claimId === c.id);
    if (!review || review.contentKey !== claimKey(d, c))
      findings.push({
        claimId: c.id,
        code: "HUMAN_REVIEW_PENDING",
        message: "Revue humaine absente ou devenue périmée.",
      });
    else if (review.decision === "needs-work")
      findings.push({
        claimId: c.id,
        code: "HUMAN_REVISION_REQUESTED",
        message: "Une correction a été demandée par la personne qui révise.",
      });
  }
  for (const extraction of d.extractions) {
    const source = d.sources.find((item) => item.id === extraction.sourceId);
    if (!source?.text?.includes(extraction.quote)) findings.push({ claimId: extraction.id,
      code: "EXTRACTION_QUOTE_UNVERIFIED",
      message: `${extraction.field} : passage d’extraction introuvable dans la source conservée.` });
  }
  if (d.report && !d.example) {
    if (/(?:filecite|oaicite|cite)\s*[]|\bturn\d+(?:search|view|file)\d+\b/.test(d.report))
      findings.push({
        claimId: "report",
        code: "REPORT_UNRESOLVED_PROVIDER_CITATION",
        message: "Référence interne d’un fournisseur non résolue : remplacer par une source vérifiable du dossier.",
      });
    const citations = [
      ...d.report.matchAll(/\[\[source:([A-Za-z0-9_-]+)\]\]/g),
    ];
    if (!citations.length)
      findings.push({
        claimId: "report",
        code: "REPORT_CITATIONS_MISSING",
        message: "Aucune citation structurée [[source:ID]] dans le rapport.",
      });
    for (const match of citations)
      if (!d.sources.some((s) => s.id === match[1]))
        findings.push({
          claimId: "report",
          code: "REPORT_SOURCE_MISSING",
          message: `Référence du rapport introuvable : ${match[1]}`,
        });
  }
  return findings;
}
export function exportMarkdown(d: Dossier): string {
  const report = d.report.replace(
    /\[\[source:([A-Za-z0-9_-]+)\]\]/g,
    (_, id) => {
      const index = d.sources.findIndex((s) => s.id === id);
      return index < 0 ? `[Référence introuvable : ${id}]` : `[${index + 1}]`;
    },
  );
  return [
    `# ${d.title}`,
    d.example ? "> EXEMPLE SYNTHÉTIQUE — aucune recherche réelle." : "",
    `Question : ${d.question}`,
    `Objectif : ${d.objective}`,
    d.corpusKey ? `Corpus : ${d.corpusKey}` : "Corpus : non attribué",
    `Révision : ${d.revision}`,
    "## Réponse courte et état des conclusions",
    d.answer || "_Réponse courte non rédigée._",
    ...(d.claims.length ? d.claims.map((claim) =>
      `- **${claim.disposition === "supported" ? "Soutenue" : claim.disposition === "contested" ? "Contestée" : "Indéterminée"}** — ${claim.statement}${claim.scope ? ` _(portée : ${claim.scope})_` : ""}${claim.effectiveAt ? ` _(date/version : ${claim.effectiveAt})_` : ""}`) : ["Aucune affirmation structurée."]),
    "## Méthode et sélection",
    d.screeningCriteria.length ? d.screeningCriteria.map((item) => `- ${item}`).join("\n") : "Critères de sélection non enregistrés.",
    ...d.sources.map((source) => {
      const decision = d.sourceDecisions.find((item) => item.sourceId === source.id);
      return `- ${source.title} : ${decision?.decision ?? "à examiner"}${decision ? ` — ${decision.reason}` : ""}`;
    }),
    report || "_Rapport non rédigé._",
    "## Extractions contrôlables",
    ...(d.extractions.length ? d.extractions.map((row) =>
      `- ${row.field} : ${row.value} — ${row.sourceId}, « ${row.quote} »`) : ["Aucune extraction conservée."]),
    "## Lectures Sanity Context",
    ...(d.knowledgeReads.length ? d.knowledgeReads.map((row) =>
      `- ${row.path} — SHA-256 ${row.digest} — ${row.retrievedAt} — ${row.verifiedAt ? `revérifié par Orbit le ${row.verifiedAt}` : "déclaré, non revérifié par Orbit"}`) : ["Aucune entrée Knowledge Base enregistrée dans ce dossier."]),
    "## Références",
    ...d.sources.map(
      (s, i) =>
        `${i + 1}. ${s.title} — ${s.url} (${s.status}, lecture déclarée)`,
    ),
    "## Dossier de preuves associé",
    "Les extraits, affirmations, décisions et historiques restent dans le fichier JSON associé. Les contrôles structurels ne prouvent pas la vérité des sources.",
    `${reviewFindings(d).length} point(s) restent à examiner dans Orbit avant diffusion.`,
  ]
    .filter(Boolean)
    .join("\n\n");
}
export function exampleDossier(): Dossier {
  const d = createDossier();
  d.example = true;
  d.title = "Comprendre une preuve";
  d.question =
    "Le délai de 30 jours concerne-t-il aussi les fichiers temporaires ?";
  d.objective = "Distinguer les périmètres avant de conclure.";
  d.axes = ["Conservation des journaux", "Durée des fichiers temporaires"];
  d.approvedPlan = 0;
  d.sources = [
    {
      id: "source_logs",
      title: "Politique fictive — journaux",
      url: "https://example.org/logs",
      status: "read",
      text: "Les journaux techniques sont conservés 30 jours.",
    },
    {
      id: "source_files",
      title: "Politique fictive — fichiers",
      url: "https://example.org/files",
      status: "read",
      text: "Les fichiers temporaires sont supprimés après 48 heures.",
    },
  ];
  d.claims = [
    {
      id: "claim_retention",
      statement: "Toutes les données sont conservées 30 jours.",
      kind: "reported",
      disposition: "contested",
      scope: "Les journaux techniques et les fichiers temporaires ne sont pas le même type de donnée.",
      conditions: ["Distinguer le type de donnée avant de généraliser une durée."],
      axisIds: ["axis_0", "axis_1"],
      evidence: [
        {
          sourceId: "source_logs",
          quote: d.sources[0].text!,
          relation: "supports",
        },
        {
          sourceId: "source_files",
          quote: d.sources[1].text!,
          relation: "contradicts",
        },
      ],
      assessment:
        "Exemple pédagogique : la phrase généralise une durée propre aux journaux.",
      correction:
        "Les journaux techniques sont conservés 30 jours ; les fichiers temporaires, 48 heures.",
    },
  ];
  d.report =
    "## Un même mot, deux périmètres\n\nDans cet exemple fictif, « données » regroupe des objets soumis à des durées différentes. La conclusion doit distinguer les journaux des fichiers temporaires.\n\nCe dossier sert uniquement à découvrir les commandes ; aucune source réelle n’a été consultée.";
  d.answer = "Indéterminé pour « toutes les données » : les deux sources fictives décrivent des périmètres différents.";
  return d;
}
