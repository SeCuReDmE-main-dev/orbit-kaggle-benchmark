"""Export of the two exact identity helpers used by the analyzer; no model calls."""
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


