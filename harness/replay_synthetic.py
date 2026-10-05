"""Measure the shared TypeScript engines. Gold never enters the engine process."""
import argparse
import copy
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'source'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(corpus: Path, output: Path):
    manifest = json.loads((corpus / 'manifest.json').read_text(encoding='utf-8'))
    cases = json.loads((corpus / 'reference-cases.json').read_text(encoding='utf-8'))
    requests, metadata = [], []
    for case in cases:
        if case['annotationStatus'] not in ('specification', 'human-reviewed'):
            continue
        for engine in ('baseline', 'n', 'p'):
            request = {'dossier': case['dossier'], 'engine': engine}
            if case['rules']: request['rules'] = case['rules']
            requests.append(request); metadata.append((case,engine,'original'))
            shuffled = copy.deepcopy(request)
            shuffled['dossier']['sources'].reverse()
            shuffled['dossier']['claims'].reverse()
            for claim in shuffled['dossier']['claims']: claim['evidence'].reverse()
            requests.append(shuffled); metadata.append((case,engine,'order'))
            duplicate = copy.deepcopy(request)
            source = duplicate['dossier']['sources'][0]
            clone = {**source, 'id': source['id']+'-copy', 'originUrl': source.get('originUrl', source['url'])}
            duplicate['dossier']['sources'].append(clone)
            for claim in duplicate['dossier']['claims']:
                claim['evidence'] += [{**e,'sourceId':clone['id']} for e in list(claim['evidence']) if e['sourceId']==source['id']]
            requests.append(duplicate); metadata.append((case,engine,'duplicate'))
            unrelated = copy.deepcopy(request)
            unrelated['dossier']['sources'].append({'id':'unrelated','title':'Unrelated','url':'https://example.org/unrelated','status':'discovered'})
            requests.append(unrelated); metadata.append((case,engine,'unrelated'))
            if case['expected'].get('relation'):
                requests.append({**request,'operation':'relations','claimIds':[c['id'] for c in case['dossier']['claims']]}); metadata.append((case,engine,'relation'))
    payload = ''.join(json.dumps(r)+'\n' for r in requests)
    completed = subprocess.run(['node',str(ROOT/'engine-jsonl.mjs')], input=payload, text=True, capture_output=True, cwd=ROOT, timeout=90)
    if completed.returncode: raise RuntimeError('TypeScript harness failed: '+completed.stderr[:500])
    responses = [json.loads(row) for row in completed.stdout.splitlines() if row.strip()]
    if len(responses) != len(requests): raise RuntimeError('Incomplete engine response stream; do not score.')
    original, rows = {}, []
    for (case,engine,operation), response in zip(metadata,responses):
        row = {'caseId':case['id'],'packet':case['packet'],'engine':engine,'operation':operation,**response}
        if not response.get('ok'): row['pass']=False
        elif operation=='relation': row['pass']=any(r['kind']==case['expected']['relation'] or case['expected']['relation'] in r.get('kinds',[]) for r in response['result'])
        else:
            target = next(r for r in response['result'] if r['claimId']==case['dossier']['claims'][0]['id'])
            summary = {'decision':target['decision'],'T':len(target['truth']),'I':sorted(r['code'] for r in target['indeterminacy']),'F':len(target['falsity']),'origins':target['independentSources']}
            key = (case['id'],engine)
            if operation=='original':
                original[key]=summary
                row['pass'] = target['decision']==case['expected']['decision'] and target['independentSources']==case['expected'].get('independentSources',target['independentSources'])
            else: row['pass']=summary==original[key]
            row['summary']=summary
        rows.append(row)
    summary = {engine:{'questions':sum(r['engine']==engine and r['operation']=='original' for r in rows), 'correct':sum(r['engine']==engine and r['operation']=='original' and r['pass'] for r in rows),
        'invariantsPassed':sum(r['engine']==engine and r['operation'] in ('order','duplicate','unrelated') and r['pass'] for r in rows),
        'invariantsTotal':sum(r['engine']==engine and r['operation'] in ('order','duplicate','unrelated') for r in rows),
        'relationPassed':sum(r['engine']==engine and r['operation']=='relation' and r['pass'] for r in rows),
        'relationTotal':sum(r['engine']==engine and r['operation']=='relation' for r in rows)} for engine in ('baseline','n','p')}
    result = {'format':'orbit-benchmark-results-v1','suite':'A','executedAt':datetime.now(timezone.utc).isoformat(),'corpusStatus':manifest['status'],
        'engineSha256':sha(ROOT/'packages/evidence-review/src/classification.ts'),'relationEngineSha256':sha(ROOT/'packages/evidence-review/src/relations.ts'),
        'oracleSha256':sha(corpus/'reference-cases.json'),'summary':summary,'rows':rows,
        'limitations':['Development synthetic corpus; not the frozen final 60-question campaign.','Specification-derived annotations are authored, not an independent human accuracy study.','No semantic entailment model or live browser execution in suite A.','Ties between baseline and N are reported, not concealed.']}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(output),'summary':summary,'failures':[{'case':r['caseId'],'engine':r['engine'],'operation':r['operation']} for r in rows if not r['pass']]}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();run(args.corpus.resolve(),args.output.resolve())
