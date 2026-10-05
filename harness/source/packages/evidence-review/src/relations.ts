import {
  canonicalSourceUrl,
  type Claim,
  type ClaimEvidence,
  type ClaimScope,
  type Dossier,
  type Evidence,
} from "./index.js";

export type TifIndeterminacyCode =
  | "missing-source"
  | "source-not-read"
  | "source-excluded"
  | "quote-unverified"
  | "claim-scope-missing"
  | "evidence-scope-missing"
  | "scope-mismatch"
  | "context-changed"
  | "no-classifiable-evidence";

export type TifEvidence = {
  sourceId: string;
  title: string;
  url: string;
  quote: string;
  passages?: string[];
  independentSource: string;
};

export type TifIndeterminacy = {
  code: TifIndeterminacyCode;
  message: string;
  sourceId?: string;
};

export type TifAssessment = {
  claimId: string;
  truth: TifEvidence[];
  indeterminacy: TifIndeterminacy[];
  falsity: TifEvidence[];
  priority:
    | "same-scope-conflict"
    | "refutation"
    | "indeterminate"
    | "supported"
    | "unassessed";
};

export type RuleRelation = "identical" | "incompatible" | "unknown";
export type ContradictionRule = {
  id: string;
  attribute: string;
  left: string;
  right: string;
  relation: RuleRelation;
  justification: string;
  version: string;
};

export type AttributeComparison = {
  attribute: string;
  left?: string;
  right?: string;
  relation: RuleRelation;
  ruleId?: string;
  justification: string;
};

export type ClaimRelationKind =
  | "same-scope-contradiction"
  | "different-scope"
  | "version-succession"
  | "version-difference"
  | "contextual"
  | "indeterminate"
  | "unrelated";

export type ClaimRelationAssessment = {
  leftClaimId: string;
  rightClaimId: string;
  kind: ClaimRelationKind;
  comparisons: AttributeComparison[];
  explanation: string;
  /** Additional relations may coexist; kind remains the legacy primary label. */
  kinds?: ClaimRelationKind[];
};

const baseScopeKeys = [
  "provider",
  "product",
  "mode",
  "condition",
  "jurisdiction",
  "audience",
] as const;

function clean(value: string | undefined): string | undefined {
  const normalized = value?.trim().toLocaleLowerCase("en-US");
  return normalized || undefined;
}

function sourceIdentity(source: Evidence, quote: string): string {
  return JSON.stringify([
    canonicalSourceUrl(source.originUrl ?? source.url),
    source.knowledgePath ?? "",
    source.contentHash ?? "",
    source.version ?? "",
  ]);
}

function sameEvidenceScope(claim: ClaimScope, evidence: ClaimScope, rules: ContradictionRule[]): boolean {
  if (
    clean(claim.subject) !== clean(evidence.subject) ||
    clean(claim.property) !== clean(evidence.property)
  ) return false;
  if (!baseScopeKeys.some((key) => clean(claim[key]) || clean(evidence[key])) && !Object.keys(claim.attributes ?? {}).length) return false;
  for (const key of [...baseScopeKeys, "version", "effectiveFrom", "effectiveTo"] as const) {
    if (!clean(claim[key]) && !clean(evidence[key])) continue;
    if (lookupRule(`scope:${key}`, claim[key], evidence[key], rules).relation !== 'identical') return false;
  }
  const keys = new Set([
    ...Object.keys(claim.attributes ?? {}),
    ...Object.keys(evidence.attributes ?? {}),
  ]);
  for (const key of keys) {
    if (lookupRule(`scope:${key}`, claim.attributes?.[key], evidence.attributes?.[key], rules).relation !== 'identical')
      return false;
  }
  return true;
}

function reason(
  code: TifIndeterminacyCode,
  message: string,
  sourceId?: string,
): TifIndeterminacy {
  return { code, message, ...(sourceId ? { sourceId } : {}) };
}

function verifiableSource(
  dossier: Dossier,
  link: ClaimEvidence,
): { source?: Evidence; problem?: TifIndeterminacy } {
  const source = dossier.sources.find((item) => item.id === link.sourceId);
  if (!source)
    return { problem: reason("missing-source", `Source absente : ${link.sourceId}.`, link.sourceId) };
  if (source.status === "discovered")
    return { source, problem: reason("source-not-read", `${source.title} n’est pas déclarée lue.`, source.id) };
  const admission = dossier.sourceDecisions.find((item) => item.sourceId === source.id);
  if (admission?.decision === "excluded")
    return { source, problem: reason("source-excluded", `${source.title} a été exclue du dossier.`, source.id) };
  if (!link.quote || !source.text?.includes(link.quote))
    return { source, problem: reason("quote-unverified", `Le passage de ${source.title} n’est pas vérifiable dans le texte conservé.`, source.id) };
  return { source };
}

/**
 * Classifies review evidence into independent T/I/F collections. These are
 * evidence states, not probabilities and not a truth score.
 */
export function assessTif(dossier: Dossier, claim: Claim, rules: ContradictionRule[] = []): TifAssessment {
  const truth = new Map<string, TifEvidence>();
  const falsity = new Map<string, TifEvidence>();
  const indeterminacy = new Map<string, TifIndeterminacy>();
  if (!claim.scopeAttributes) {
    const item = reason("claim-scope-missing", "La portée structurée de l’affirmation est absente.");
    indeterminacy.set(item.code, item);
  }
  for (const read of claim.contextReads ?? []) {
    const current = dossier.knowledgeReads.find((row) => row.path === read.path);
    if (!current || current.digest !== read.digest) {
      const item = reason('context-changed', `L’entrée ${read.path} a changé ou n’est plus disponible; réexaminez la conclusion.`);
      indeterminacy.set(`${item.code}:${read.path}`, item);
    }
  }
  for (const link of [...claim.evidence].sort((a, b) => a.sourceId.localeCompare(b.sourceId) || a.quote.localeCompare(b.quote))) {
    const { source, problem } = verifiableSource(dossier, link);
    if (problem) {
      indeterminacy.set(`${problem.code}:${source ? sourceIdentity(source, '') : problem.sourceId ?? "claim"}`, problem);
      continue;
    }
    if (!source) continue;
    if (!link.scope) {
      const item = reason("evidence-scope-missing", `La portée du passage de ${source.title} est absente.`, source.id);
      indeterminacy.set(`${item.code}:${sourceIdentity(source, '')}`, item);
      continue;
    }
    if (!claim.scopeAttributes || !sameEvidenceScope(claim.scopeAttributes, link.scope, rules)) {
      const item = reason("scope-mismatch", `${source.title} ne porte pas sur le même périmètre structuré.`, source.id);
      indeterminacy.set(`${item.code}:${sourceIdentity(source, '')}`, item);
      continue;
    }
    const row: TifEvidence = { sourceId: source.id, title: source.title, url: source.url, quote: link.quote,
      independentSource: canonicalSourceUrl(source.originUrl ?? source.url), passages: [link.quote] };
    const key = sourceIdentity(source, link.quote);
    const add = (target: Map<string, TifEvidence>) => {
      const previous = target.get(key);
      if (previous) previous.passages = [...new Set([...(previous.passages ?? [previous.quote]), link.quote])].sort();
      else target.set(key, row);
    };
    if (link.relation === "supports") add(truth);
    else if (link.relation === "contradicts") add(falsity);
    else {
      const item = reason("no-classifiable-evidence", `${source.title} contextualise l’affirmation sans la soutenir ni la réfuter.`, source.id);
      indeterminacy.set(`${item.code}:${sourceIdentity(source, '')}`, item);
    }
  }
  if (!truth.size && !falsity.size && !indeterminacy.size) {
    const item = reason("no-classifiable-evidence", "Aucun passage classable n’est lié à cette affirmation.");
    indeterminacy.set(item.code, item);
  }
  const priority = truth.size && falsity.size
    ? "same-scope-conflict"
    : falsity.size
      ? "refutation"
      : indeterminacy.size
        ? "indeterminate"
        : truth.size
          ? "supported"
          : "unassessed";
  return {
    claimId: claim.id,
    truth: [...truth.values()],
    indeterminacy: [...indeterminacy.values()],
    falsity: [...falsity.values()],
    priority,
  };
}

export function rankTif(dossier: Dossier): TifAssessment[] {
  const priority = new Map<TifAssessment["priority"], number>([
    ["same-scope-conflict", 0],
    ["refutation", 1],
    ["indeterminate", 2],
    ["supported", 3],
    ["unassessed", 4],
  ]);
  return dossier.claims.map((claim) => assessTif(dossier, claim)).sort((a, b) =>
    (priority.get(a.priority) ?? 99) - (priority.get(b.priority) ?? 99) ||
    a.claimId.localeCompare(b.claimId));
}

function lookupRule(
  attribute: string,
  left: string | undefined,
  right: string | undefined,
  rules: ContradictionRule[],
): AttributeComparison {
  if (!clean(left) || !clean(right))
    return { attribute, left, right, relation: "unknown", justification: "Un attribut manque dans une des affirmations." };
  if (clean(left) === clean(right))
    return { attribute, left, right, relation: "identical", justification: "Les valeurs déclarées sont identiques." };
  const match = rules.find((rule) =>
    clean(rule.attribute) === clean(attribute) &&
    ((clean(rule.left) === clean(left) && clean(rule.right) === clean(right)) ||
      (clean(rule.left) === clean(right) && clean(rule.right) === clean(left))));
  if (!match)
    return { attribute, left, right, relation: "unknown", justification: "Aucune règle de domaine versionnée ne couvre cette paire." };
  return {
    attribute,
    left,
    right,
    relation: match.relation,
    ruleId: match.id,
    justification: `${match.justification} (règle ${match.version})`,
  };
}

function customScope(scope: ClaimScope): Record<string, string | undefined> {
  return {
    provider: scope.provider,
    product: scope.product,
    mode: scope.mode,
    condition: scope.condition,
    jurisdiction: scope.jurisdiction,
    audience: scope.audience,
    ...(scope.attributes ?? {}),
  };
}

export function compareClaims(
  left: Claim,
  right: Claim,
  rules: ContradictionRule[],
): ClaimRelationAssessment {
  const a = left.scopeAttributes, b = right.scopeAttributes;
  if (!a || !b)
    return { leftClaimId: left.id, rightClaimId: right.id, kind: "indeterminate", comparisons: [],
      explanation: "Une portée structurée manque; Orbit ne peut pas comparer les deux affirmations." };
  if (clean(a.subject) !== clean(b.subject) || clean(a.property) !== clean(b.property))
    return { leftClaimId: left.id, rightClaimId: right.id, kind: "unrelated", comparisons: [],
      explanation: "Les affirmations ne portent pas sur le même sujet et la même propriété." };

  const scopeA = customScope(a), scopeB = customScope(b);
  const scopeKeys = [...new Set([...Object.keys(scopeA), ...Object.keys(scopeB)])].filter((key) => clean(scopeA[key]) || clean(scopeB[key])).sort();
  const scopeComparisons = scopeKeys.map((key) => lookupRule(`scope:${key}`, scopeA[key], scopeB[key], rules));
  const scopeMissing = !scopeKeys.length || scopeComparisons.some((row) => !clean(row.left) || !clean(row.right));
  const scopeDiffers = scopeComparisons.some((row) => row.relation !== 'identical' && clean(row.left) && clean(row.right));
  const temporalKeys = ['version', 'effectiveFrom', 'effectiveTo'] as const;
  const temporalMissing = temporalKeys.some((key) => Boolean(clean(a[key])) !== Boolean(clean(b[key])));
  const versionDiffers = temporalKeys.some((key) => clean(a[key]) !== clean(b[key]));
  const explicitReplacement = Boolean(a.version && b.version && (a.supersedesVersion === b.version || b.supersedesVersion === a.version));
  const valueComparison = lookupRule(`value:${a.property}`, a.value, b.value, rules);
  const comparisons = [...scopeComparisons, valueComparison];

  let kind: ClaimRelationKind;
  let explanation: string;
  if (scopeMissing || temporalMissing) {
    kind = 'indeterminate';
    explanation = 'Un attribut de portée ou de version manque; deux absences ne prouvent pas une identité.';
  } else if (scopeDiffers) {
    kind = "different-scope";
    explanation = "Les affirmations concernent des portées différentes; elles ne forment pas encore une contradiction directe.";
  } else if (versionDiffers) {
    kind = explicitReplacement ? 'version-succession' : 'version-difference';
    explanation = explicitReplacement
      ? 'Un remplacement de version est déclaré explicitement. Les passages et cette déclaration restent à vérifier.'
      : 'Les versions ou périodes diffèrent; cette différence ne prouve pas que l’une remplace l’autre.';
  } else if (valueComparison.relation === "incompatible") {
    kind = "same-scope-contradiction";
    explanation = "Une règle de domaine versionnée déclare les valeurs incompatibles dans la même portée.";
  } else if (valueComparison.relation === "identical") {
    kind = "contextual";
    explanation = "Les deux affirmations décrivent la même valeur dans la même portée.";
  } else {
    kind = "indeterminate";
    explanation = "Aucune règle de domaine ne permet encore de qualifier la relation entre les valeurs.";
  }
  const kinds: ClaimRelationKind[] = [kind];
  if (scopeDiffers && versionDiffers && !temporalMissing) kinds.push(explicitReplacement ? 'version-succession' : 'version-difference');
  return { leftClaimId: left.id, rightClaimId: right.id, kind, kinds, comparisons, explanation };
}

export function buildRelationGraph(
  dossier: Dossier,
  rules: ContradictionRule[],
): ClaimRelationAssessment[] {
  const rows: ClaimRelationAssessment[] = [];
  for (let left = 0; left < dossier.claims.length; left++)
    for (let right = left + 1; right < dossier.claims.length; right++) {
      const relation = compareClaims(dossier.claims[left], dossier.claims[right], rules);
      if (relation.kind !== "unrelated") rows.push(relation);
    }
  const order = new Map<ClaimRelationKind, number>([
    ["same-scope-contradiction", 0],
    ["version-succession", 1],
    ["version-difference", 1],
    ["different-scope", 2],
    ["indeterminate", 3],
    ["contextual", 4],
    ["unrelated", 5],
  ]);
  return rows.sort((a, b) => (order.get(a.kind) ?? 99) - (order.get(b.kind) ?? 99));
}
