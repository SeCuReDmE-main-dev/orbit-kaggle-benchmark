"""Aggregate actual Orbit checkpoints inside Kaggle; no model calls.

Public aggregates contain neither original source text nor reference answers.
Only synthetic specification references are scored. Real semantic review stays
pending, and partial conditions are not promoted to complete comparisons.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import itertools
import json
import math
from pathlib import Path
import random
import statistics


def _cluster_interval(differences, seed=20261001, repetitions=2000):
    """Paired descriptive interval, resampling whole packets, not questions."""
    if len(differences)<2:
        return {'clusters':len(differences),'interval':None,'reason':'fewer-than-two-packet-clusters'}
    rng=random.Random(seed)
    values=list(differences.values())
    samples=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(repetitions))
    return {'clusters':len(values),'meanDifference':statistics.mean(values),
            'interval':[samples[int(.025*(repetitions-1))],samples[int(.975*(repetitions-1))]],
            'method':'paired-packet-cluster-bootstrap-descriptive','resamples':repetitions,'seed':seed,
            'limitations':['Only six synthetic packets carry reference labels.',
                           'No causal or population-wide superiority is certified.']}


def _attempt_costs(all_rows, identity):
    """Include observed failed/retried generations, without charging a replay twice."""
    from orbit_campaign_checkpoint import digest
    latest={}
    for row in all_rows:
        if row.get('configurationSha256')!=identity or row.get('suite')!='C':
            continue
        if row.get('parameters',{}).get('phase') not in ('extraction','production'):
            continue
        key=row.get('key'); attempt=row.get('attempt')
        if not isinstance(key,str) or not isinstance(attempt,int) or isinstance(attempt,bool) or attempt<0:
            raise RuntimeError('ANALYSIS_ATTEMPT_IDENTITY_REQUIRED')
        identifier=(identity,key,attempt)
        if row.get('observedAtUnix',0)>=latest.get(identifier,{}).get('observedAtUnix',0):
            latest[identifier]=row
    usages={}; attempts_without_usage=0
    for row in latest.values():
        usage=(row.get('result') or {}).get('usage')
        if not isinstance(usage,dict) or not usage:
            attempts_without_usage+=1
            continue
        # A restored observation retains its timestamp/content. Distinct
        # attempts with genuinely new usage remain separately chargeable.
        observed_at=usage.get('observedAtUnix')
        replay_identity=(observed_at if isinstance(observed_at,(int,float)) and not isinstance(observed_at,bool)
                         and math.isfinite(observed_at) else ('attempt',row['attempt']))
        identifier=(identity,row['key'],replay_identity,digest(usage))
        usages[identifier]=usage
    known_components=[]; complete_costs=0; missing_units=2*attempts_without_usage
    for usage in usages.values():
        components=[usage.get(name) for name in
                    ('input_tokens_cost_nanodollars','output_tokens_cost_nanodollars')]
        valid=[isinstance(value,(int,float)) and not isinstance(value,bool)
               and math.isfinite(value) and value>=0 for value in components]
        known_components.extend(value for value,ok in zip(components,valid) if ok)
        complete_costs+=int(all(valid)); missing_units+=sum(not ok for ok in valid)
    subtotal=sum(known_components) if known_components else None
    total=subtotal if usages and missing_units==0 else None
    return {'generationAttemptRecords':len(latest),'generations':len(usages),
            'generationsWithCost':complete_costs,'generationsWithMissingCost':len(usages)-complete_costs,
            'attemptsWithoutUsage':attempts_without_usage,'missingCostUnits':missing_units,
            'knownSubtotalNanodollars':subtotal,'totalNanodollars':total,
            'knownNanodollars':subtotal,'missingCostIsNotZero':True,
            'costScope':'observed attempts of the selected C identity; not a projection of unrun tasks',
            'attemptStates':dict(Counter(row.get('state','unspecified') for row in latest.values())),
            'deduplication':'latest identity/key/attempt, then identical usage identity/key/timestamp/content'}


def analyze_c(config, public, gold, ledger_directory):
    from orbit_campaign_checkpoint import campaign_identity
    identity=campaign_identity(config)
    all_rows=[json.loads(p.read_text()) for p in Path(ledger_directory).glob('*.json')]
    rows=[r for r in all_rows if r.get('configurationSha256')==identity and r.get('suite')=='C']
    attempt_rows=[json.loads(p.read_text()) for p in Path(ledger_directory).rglob('*.json')]
    current=[r for r in rows if r.get('state')=='completed']
    historical=Counter(r.get('state','unspecified') for r in all_rows if r.get('configurationSha256')!=identity)
    phases=Counter(r.get('parameters',{}).get('phase') for r in current)
    questions=defaultdict(list)
    for q in public['questions']:questions[q['packet']].append(q['id'])
    targets={identifier:value.get('modelDecision',value['decision']) for identifier,value in gold.items()}
    interpreted={tuple(r['parameters'][k] for k in ('model','packet','repetition','condition')):r['result']
                 for r in current if r.get('parameters',{}).get('phase')=='production-interpretation'}
    productions={tuple(r['parameters'][k] for k in ('model','packet','repetition','condition')):r
                 for r in rows if r.get('parameters',{}).get('phase')=='production'}
    metrics=[]; paired=defaultdict(dict)
    for model in config['models']:
        for condition in ('none','baseline','n','p'):
            counts=Counter();confusion=Counter();packet_counts=defaultdict(Counter);missing_states=Counter()
            for packet in range(1,11):
                for repetition in range(3):
                    output=interpreted.get((model,packet,repetition,condition))
                    if output is None:
                        counts['missingProductions']+=1
                        production=productions.get((model,packet,repetition,condition))
                        state=production.get('state','unspecified') if production else 'never-run'
                        missing_states[state]+=1
                        category=('neverRunProductions' if production is None else
                                  'inProgressProductions' if state in ('running','observing') else
                                  'uninterpretedProductions' if state=='completed' else 'failedProductions')
                        counts[category]+=1
                        continue
                    counts['observedProductions']+=1
                    answers=output.get('answer',{}).get('results',[]) if output.get('status')=='completed' else []
                    lookup={a.get('questionId'):a for a in answers if isinstance(a,dict)}
                    if output.get('status')!='completed':counts['invalidProductions']+=1
                    for identifier in questions[packet]:
                        if identifier not in targets:
                            counts['realDecisionsUnscored']+=1
                            continue
                        reference=targets[identifier]
                        decision=lookup.get(identifier,{}).get('decision','INVALID')
                        if decision not in ('ADMIT','REJECT','HOLD'):decision='INVALID'
                        counts['syntheticDecisionsObserved']+=1
                        correct=decision==reference
                        counts['syntheticCorrect']+=int(correct)
                        counts['invalidSyntheticDecisions']+=int(decision=='INVALID')
                        counts['necessaryHold']+=int(reference=='HOLD')
                        counts['necessaryHoldUsed']+=int(reference=='HOLD' and decision=='HOLD')
                        counts['excessiveHold']+=int(reference!='HOLD' and decision=='HOLD')
                        counts['unjustifiedConclusion']+=int(reference=='HOLD' and decision in ('ADMIT','REJECT'))
                        confusion[(reference,decision)]+=1
                        packet_counts[packet]['correct']+=int(correct)
                        packet_counts[packet]['total']+=1
                        paired[(model,packet,repetition,identifier)][condition]=int(correct)
            observed=counts['syntheticDecisionsObserved']
            metrics.append({'model':model,'condition':condition,'counts':dict(counts),
                'missingProductionStates':dict(missing_states),
                'syntheticAccuracyObserved':counts['syntheticCorrect']/observed if observed else None,
                'plannedProductions':30,'plannedSyntheticDecisions':108,'plannedRealDecisionsUnscored':72,
                'complete':counts['observedProductions']==30,
                'confusion':[{'referenceCategory':a,'predictedCategory':b,'count':n} for (a,b),n in sorted(confusion.items())],
                'packets':[{'packet':p,**dict(v)} for p,v in sorted(packet_counts.items())]})
    comparisons=[]
    for model in config['models']:
        for a,b in itertools.combinations(('none','baseline','n','p'),2):
            differences=defaultdict(list)
            for (observed_model,packet,repetition,question),values in paired.items():
                if observed_model==model and a in values and b in values:
                    differences[packet].append(values[b]-values[a])
            means={packet:statistics.mean(values) for packet,values in differences.items()}
            comparisons.append({'model':model,'from':a,'to':b,
                'matchedSyntheticDecisions':sum(map(len,differences.values())),
                'plannedMatchedSyntheticDecisions':108,'complete':sum(map(len,differences.values()))==108,
                **_cluster_interval(means)})
    return {'format':'orbit-c-actual-checkpoint-analysis-v1','host':'Kaggle','modelCallsDuringAnalysis':0,
        'campaignId':config['campaignId'],'configurationSha256':identity,
        'execution':{'plannedExtractions':60,'observedExtractions':phases['extraction'],
                     'plannedProductions':240,'observedProductions':phases['production'],
                     'completedPackets':phases['packet'],
                     'currentStates':dict(Counter(r.get('state','unspecified') for r in rows)),
                     'complete':phases['extraction']==60 and phases['production']==240 and phases['packet']==60},
        'historicalStatesNotPooled':dict(historical),'metrics':metrics,'pairedComparisons':comparisons,
        'observedCosts':_attempt_costs(attempt_rows,identity),
        'referenceStatus':{'syntheticQuestions':36,'realQuestionsPendingHuman':24},
        'limitations':['Synthetic specification accuracy does not establish real-source semantic truth.',
                      'Exact quotes and citations require a separate relevance audit.',
                      'Partial runs remain partial; completed-condition selection is not a final ranking.',
                      'No engine is selected or activated automatically.']}


def write_c_analysis(config,public,gold,ledger_directory,output):
    if not Path('/kaggle/working').is_dir():raise RuntimeError('KAGGLE_ANALYSIS_REQUIRED')
    result=analyze_c(config,public,gold,ledger_directory)
    Path(output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'execution':result['execution'],'referenceStatus':result['referenceStatus'],
                      'observedCosts':result['observedCosts'],'modelCallsDuringAnalysis':0}))
    return result
