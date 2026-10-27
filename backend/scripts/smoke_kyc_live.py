"""Live HTTP smoke through Next.js. Retains one synthetic account and case."""
import argparse
import hashlib
import secrets
import sys
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kyc.lab import FIXTURE_PROFILE, fixture_bytes
from kyc.crypto import canonical
parser=argparse.ArgumentParser()
parser.add_argument('--origin',default='http://127.0.0.1:3000')
args=parser.parse_args()
origin=args.origin.rstrip('/')
username,password='smoke_'+secrets.token_hex(5),secrets.token_urlsafe(20)
checks=[]
with httpx.Client(base_url=origin,timeout=90,trust_env=False) as client:
    def mutation(method,path,**kwargs):
        token=client.get('/api/v1/auth/csrf')
        token.raise_for_status()
        response=client.request(method,'/api/v1'+path,headers={'X-CSRF-Token':token.json()['token'],'Origin':origin},**kwargs)
        response.raise_for_status()
        return response
    health=client.get('/api/v1/health')
    health.raise_for_status()
    assert health.json()['api']=='bankkyc'
    checks.append('Next.js proxy -> BankKYC health')
    mutation('POST','/auth/register',json={'username':username,'password':password})
    account=mutation('POST','/auth/login',json={'username':username,'password':password}).json()
    assert account['role']=='applicant'
    checks.append('register/login + cookie + rotated CSRF')
    case=mutation('POST','/applications',json={}).json()
    case=mutation('PUT',f"/applications/{case['id']}/personal-data",json={'profile':FIXTURE_PROFILE,'version':case['version']}).json()
    for category,fixture,name in [('identity','identity-png','DUMMY.png'),('document','document-pdf','DUMMY.pdf'),('video','video-mp4','DUMMY.mp4')]:
        source=fixture_bytes(fixture)
        case=mutation('POST',f"/applications/{case['id']}/evidence",data={'category':category,'version':str(case['version'])},files={'file':(name,source,'application/octet-stream')}).json()
        item=next(e for e in case['evidence'] if e['category']==category)
        response=client.get(f"/api/v1/applications/{case['id']}/evidence/{item['id']}/download")
        response.raise_for_status()
        assert response.content==source
        checks.append(category+' byte match SHA256='+hashlib.sha256(source).hexdigest())
    response=client.get(f"/api/v1/applications/{case['id']}/personal-data/download")
    response.raise_for_status()
    assert response.content==canonical(FIXTURE_PROFILE)
    assert response.headers['content-type']=='application/octet-stream'
    checks.append('canonical profile attachment')
    case=mutation('POST',f"/applications/{case['id']}/actions",json={'action':'submit','version':case['version'],'synthetic_acknowledged':True}).json()
    assert case['status']=='SUBMITTED'
    assert len(client.get('/api/v1/applications').json()['items'])==1
    checks.append('submission and persisted reload')
    mutation('POST','/auth/logout')
    assert client.get('/api/v1/auth/me').status_code==401
    checks.append('logout revokes session')
print('LIVE HTTP checks: PASS')
for check in checks:
    print('PASS',check)
print('Synthetic case retained:',case['id'])
print('Optional cleanup: python manage.py cleanup-case '+case['id']+' --apply')
