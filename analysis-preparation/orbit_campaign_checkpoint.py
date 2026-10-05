"""Analysis-only identity helpers copied from Orbit's checkpoint module.

These two pure functions retain the original canonical digest and operational
field exclusions. No model, account, resume, generation or transport code exists
in this module. Source: tools/orbit_campaign_checkpoint.py at Orbit commit
13b315696bfaf72ac371e5b3498e2ab0d3a9a00e, lines19-30.
"""
import hashlib
import json


def digest(value):
    encoded = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def campaign_identity(config):
    operational={'resumeDatasetDir','resumeArchives','inputCorpusDir','inputReferenceDir',
                 'workerSecretName','quotaSnapshot','state','quotaChecked','modelsChecked',
                 'publicRelease','modelCallsExecuted','softwareTestsExecuted','pricingObservation'}
    return digest({key:value for key,value in config.items() if key not in operational})
