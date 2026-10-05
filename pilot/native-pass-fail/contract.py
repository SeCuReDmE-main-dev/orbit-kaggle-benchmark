"""Strict six-question contract, no SDK import, provider calls or filesystem I/O."""
import json

class InvalidModelOutput(ValueError):
    pass

def _unique_object(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:raise InvalidModelOutput('Duplicate JSON object key')
        obj[key]=value
    return obj

def _reject_constant(value):
    raise InvalidModelOutput('Non-finite JSON value')

def parse_answer(raw):
    if not isinstance(raw,str) or not raw.strip() or len(raw)>1048576:
        raise InvalidModelOutput('Response must be nonempty text within one MiB')
    text=raw.strip()
    if text.startswith('```'):
        lines=text.splitlines()
        if len(lines)<3 or lines[0] not in ('```','```json') or lines[-1]!='```':
            raise InvalidModelOutput('Malformed JSON fence')
        text='\n'.join(lines[1:-1])
    try:
        return json.loads(text,object_pairs_hook=_unique_object,parse_constant=_reject_constant)
    except (json.JSONDecodeError,RecursionError) as error:
        raise InvalidModelOutput(type(error).__name__) from error

def validate_answer(answer,public,gold):
    """Record structural and source checks. No empty collection is a successful pilot."""
    checks=[]
    def check(ok,name):
        checks.append({'name':name,'passed':bool(ok)})
        return bool(ok)
    if not check(isinstance(answer,dict) and set(answer)=={'results'},'one object with only results'):
        return {'valid':False,'outcome':'invalid-model-output','checks':checks}
    rows=answer['results']
    if not check(isinstance(rows,list) and len(rows)==6,'exactly six result rows'):
        return {'valid':False,'outcome':'invalid-model-output','checks':checks}
    fields={'questionId','decision','evidence','excluded','uncertainties','justification'}
    required_scope={'subject','property','value'}
    allowed_scope=required_scope|{'provider','product','mode','version'}
    docs={d['id']:d for d in public['documents']}
    ids=[]
    for position,row in enumerate(rows):
        if not check(isinstance(row,dict) and set(row)==fields,'row fields '+str(position)):
            return {'valid':False,'outcome':'invalid-model-output','checks':checks}
        qid=row['questionId']
        if not check(isinstance(qid,str) and qid in gold,'known question '+str(position)):
            return {'valid':False,'outcome':'invalid-model-output','checks':checks}
        ids.append(qid)
        shape=(row['decision'] in ('ADMIT','REJECT','HOLD') and
               isinstance(row['evidence'],list) and 1<=len(row['evidence'])<=24 and
               isinstance(row['excluded'],list) and len(row['excluded'])<=12 and
               isinstance(row['uncertainties'],list) and len(row['uncertainties'])<=24 and
               all(isinstance(x,str) and bool(x.strip()) and len(x)<=3000 for x in row['uncertainties']) and
               isinstance(row['justification'],str) and bool(row['justification'].strip()) and len(row['justification'])<=10000)
        if not check(shape,'required output types and bounded evidence '+qid):
            return {'valid':False,'outcome':'invalid-model-output','checks':checks}
        for ev in row['evidence']:
            if not check(isinstance(ev,dict) and {'sourceId','quote','relation'}<=set(ev)<= {'sourceId','quote','relation','scope'},'evidence fields '+qid):
                return {'valid':False,'outcome':'invalid-model-output','checks':checks}
            sid=ev['sourceId'];quote=ev['quote'];rel=ev['relation']
            if not check(isinstance(sid,str) and sid in docs and isinstance(quote,str) and bool(quote.strip()) and len(quote)<=12000 and rel in ('supports','contradicts','contextualizes'),'known source, nonempty quote and relation '+qid):
                return {'valid':False,'outcome':'contract-fail','checks':checks}
            if not check(quote in docs[sid]['text'],'verbatim passage in named source '+qid+'/'+sid):
                return {'valid':False,'outcome':'contract-fail','checks':checks}
            if 'scope' in ev:
                scope=ev['scope']
                if not check(isinstance(scope,dict) and required_scope<=set(scope)<=allowed_scope and all(isinstance(v,str) and bool(v.strip()) and len(v)<=500 for v in scope.values()),'complete atomic scope or wholly absent scope '+qid):
                    return {'valid':False,'outcome':'invalid-model-output','checks':checks}
        for excluded in row['excluded']:
            if not check(isinstance(excluded,dict) and set(excluded)=={'sourceId','reason'} and isinstance(excluded['sourceId'],str) and excluded['sourceId'] in docs and isinstance(excluded['reason'],str) and bool(excluded['reason'].strip()) and len(excluded['reason'])<=3000,'valid excluded source '+qid):
                return {'valid':False,'outcome':'invalid-model-output','checks':checks}
    if not check(len(set(ids))==6 and set(ids)==set(gold),'all six distinct questions exactly once'):
        return {'valid':False,'outcome':'invalid-model-output','checks':checks}
    correct=True
    for row in rows:correct=check(row['decision']==gold[row['questionId']],'decision matches authored reference '+row['questionId']) and correct
    return {'valid':True,'outcome':'pass' if correct else 'contract-fail','checks':checks}
