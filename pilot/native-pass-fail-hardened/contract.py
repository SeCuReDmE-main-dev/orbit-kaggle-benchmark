"""Pure strict pilot contract. No SDK, provider, engine or filesystem calls."""
import json
import math

MAX_RESPONSE_BYTES = 1_048_576
SCOPE_LIMITS = {"subject": 300, "property": 300, "value": 1000,
                "provider": 500, "product": 500, "mode": 500, "version": 500}
# ECMA-262 WhiteSpace + LineTerminator used by the frozen TypeScript str().
# Unlike Python's default strip(), this includes FEFF and excludes 0085/001C-001F.
JS_TRIM_CHARACTERS = ("\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680"
                      "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
                      "\u2028\u2029\u202f\u205f\u3000\ufeff")


class InvalidModelOutput(ValueError):
    """The provider returned text that cannot satisfy the output schema."""


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise InvalidModelOutput("Duplicate JSON object key")
        obj[key] = value
    return obj


def _reject_constant(value):
    raise InvalidModelOutput("Non-finite JSON value")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InvalidModelOutput("Non-finite JSON value")
    return result


def _bounded_integer(value):
    # A stable bound also applies on runtimes with the Python integer cap disabled.
    if len(value.lstrip("-")) > 4300:
        raise InvalidModelOutput("JSON integer exceeds 4300 digits")
    return int(value)


def parse_answer(raw):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_RESPONSE_BYTES:
        raise InvalidModelOutput("Response must be nonempty text within one MiB")
    try:
        if len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise InvalidModelOutput("Response exceeds one MiB of UTF-8")
    except UnicodeEncodeError as error:
        raise InvalidModelOutput("Response is not encodable as UTF-8") from error
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or lines[0] not in ("```", "```json") or lines[-1] != "```":
            raise InvalidModelOutput("Malformed JSON fence")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant, parse_float=_finite_float,
                          parse_int=_bounded_integer)
    except InvalidModelOutput:
        raise
    except (ValueError, RecursionError) as error:
        raise InvalidModelOutput(type(error).__name__) from error


def _text(value, maximum):
    # JavaScript String.length counts UTF-16 units, including surrogate pairs.
    return (isinstance(value, str) and bool(value.strip(JS_TRIM_CHARACTERS))
            and len(value.encode("utf-16-le", errors="surrogatepass")) // 2 <= maximum)


def validate_answer(answer, public, gold):
    """Shape failures are invalid output; false source/reference claims fail the contract."""
    checks = []

    def check(ok, name):
        checks.append({"name": name, "passed": bool(ok)})
        return bool(ok)

    def failure(outcome="invalid-model-output"):
        return {"valid": False, "outcome": outcome, "checks": checks}

    if not check(isinstance(answer, dict) and set(answer) == {"results"},
                 "one object with only results"):
        return failure()
    rows = answer["results"]
    if not check(isinstance(rows, list) and len(rows) == 6, "exactly six result rows"):
        return failure()
    fields = {"questionId", "decision", "evidence", "excluded", "uncertainties", "justification"}
    required_scope = {"subject", "property", "value"}
    docs = {d["id"]: d for d in public["documents"]}
    ids = []
    for position, row in enumerate(rows):
        if not check(isinstance(row, dict) and set(row) == fields, "row fields " + str(position)):
            return failure()
        qid = row["questionId"]
        if not check(isinstance(qid, str) and qid in gold, "known question " + str(position)):
            return failure()
        ids.append(qid)
        shape = (row["decision"] in ("ADMIT", "REJECT", "HOLD")
                 and isinstance(row["evidence"], list) and 1 <= len(row["evidence"]) <= 24
                 and isinstance(row["excluded"], list) and len(row["excluded"]) <= 12
                 and isinstance(row["uncertainties"], list) and len(row["uncertainties"]) <= 24
                 and all(_text(x, 3000) for x in row["uncertainties"])
                 and _text(row["justification"], 10000))
        if not check(shape, "required output types and bounded evidence " + qid):
            return failure()
        for ev in row["evidence"]:
            if not check(isinstance(ev, dict) and {"sourceId", "quote", "relation"} <= set(ev)
                         <= {"sourceId", "quote", "relation", "scope"}, "evidence fields " + qid):
                return failure()
            sid, quote, relation = ev["sourceId"], ev["quote"], ev["relation"]
            if not check(_text(sid, 160) and _text(quote, 2000)
                         and relation in ("supports", "contradicts", "contextualizes"),
                         "evidence types and bounds " + qid):
                return failure()
            if not check(sid in docs, "known source " + qid):
                return failure("contract-fail")
            if not check(quote in docs[sid]["text"], "verbatim passage in named source " + qid + "/" + sid):
                return failure("contract-fail")
            if "scope" in ev:
                scope = ev["scope"]
                if not check(isinstance(scope, dict) and required_scope <= set(scope) <= set(SCOPE_LIMITS)
                             and all(_text(value, SCOPE_LIMITS[key]) for key, value in scope.items()),
                             "complete bounded atomic scope or wholly absent scope " + qid):
                    return failure()
        for excluded in row["excluded"]:
            if not check(isinstance(excluded, dict) and set(excluded) == {"sourceId", "reason"}
                         and _text(excluded["sourceId"], 160) and _text(excluded["reason"], 3000),
                         "excluded source types " + qid):
                return failure()
            if not check(excluded["sourceId"] in docs, "known excluded source " + qid):
                return failure("contract-fail")
    if not check(len(set(ids)) == 6 and set(ids) == set(gold), "all six distinct questions exactly once"):
        return failure()
    correct = True
    for row in rows:
        correct = check(row["decision"] == gold[row["questionId"]],
                        "decision matches authored reference " + row["questionId"]) and correct
    return {"valid": True, "outcome": "pass" if correct else "contract-fail", "checks": checks}
