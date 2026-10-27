"""Real database/API tests; MySQL URL must point to an explicitly disposable DB."""
import base64
import hashlib
import json
import os
import secrets
import struct
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update, func, event
from kyc.config import Settings
from kyc.crypto import Envelope, IntegrityFailure, canonical
from kyc.db import database, metadata, users, sessions, applications, evidence, objects, profiles, events
from kyc.main import create_app
from kyc.migrate import migrate
from kyc.provision import create_user, check_keys
from kyc.lab import FIXTURE_PROFILE, fixture_bytes

P = '/api/v1'
PASSWORD = 'Test-only-password-123'

@pytest.fixture
def system(tmp_path):
    url = os.getenv('KYC_TEST_DATABASE_URL', 'sqlite:///' + str(tmp_path / 'bankkyc.db'))
    settings = Settings(url, secrets.token_bytes(32), secrets.token_bytes(32))
    engine = database(url)
    if os.getenv('KYC_TEST_DATABASE_URL'):
        assert os.getenv('KYC_TEST_ALLOW_RESET') == 'yes', 'Use an isolated, disposable test database only'
        metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql('DROP TABLE IF EXISTS alembic_version')
    migrate(engine, settings)
    accounts = {name: create_user(engine,name,PASSWORD,role) for name,role in
                [('owner','applicant'),('other','applicant'),('reviewer','reviewer'),('reviewer2','reviewer'),('admin','admin'),('evaluator','evaluator')]}
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield settings, app, client, accounts
    engine.dispose()

def csrf(client):
    return {'X-CSRF-Token':client.get(P+'/auth/csrf').json()['token'],'Origin':'http://127.0.0.1:3000'}
def mutate(client, method, path, **kwargs):
    return client.request(method,P+path,headers=csrf(client),**kwargs)
def login(client, name='owner'):
    r = mutate(client,'POST','/auth/login',json={'username':name,'password':PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()
def create(client):
    r = mutate(client,'POST','/applications',json={})
    assert r.status_code == 201, r.text
    return r.json()
def profile(client, row, value=None):
    return mutate(client,'PUT',f"/applications/{row['id']}/personal-data",json={'version':row['version'],'profile':value or FIXTURE_PROFILE})
def upload(client, row, category, data=None, name=None):
    fixture, filename = {'identity':('identity-png','DUMMY-private.png'),'document':('document-pdf','DUMMY-private.pdf'),'video':('video-mp4','DUMMY-private.mp4')}[category]
    return mutate(client,'POST',f"/applications/{row['id']}/evidence",data={'category':category,'version':str(row['version'])},
                  files={'file':(name or filename,fixture_bytes(fixture) if data is None else data,'application/octet-stream')})
def act(client, row, action, **extra):
    return mutate(client,'POST',f"/applications/{row['id']}/actions",json={'version':row['version'],'action':action,**extra})
def complete(client):
    row = create(client)
    r = profile(client,row)
    assert r.status_code == 200, r.text
    row = r.json()
    for category in ('identity','document','video'):
        r = upload(client,row,category)
        assert r.status_code == 201, r.text
        row = r.json()
    return row

def test_auth_csrf_and_no_role_escalation(system):
    settings, app, client, accounts = system
    assert client.get(P+'/health').status_code == 200
    assert client.get(P+'/applications').status_code == 401
    assert client.post(P+'/auth/register',json={'username':'new_user','password':PASSWORD}).status_code == 403
    pre = csrf(client)
    assert client.post(P+'/auth/register',headers={**pre,'Origin':'https://untrusted.invalid'},json={'username':'new_user','password':PASSWORD}).status_code == 403
    assert mutate(client,'POST','/auth/register',json={'username':'new_user','password':PASSWORD,'role':'admin'}).status_code == 422
    registered = mutate(client,'POST','/auth/register',json={'username':'new_user','password':PASSWORD})
    assert registered.status_code == 201 and registered.json()['role'] == 'applicant'
    assert mutate(client,'POST','/auth/register',json={'username':'new_user','password':PASSWORD}).status_code == 409
    login(client,'new_user')
    assert client.post(P+'/applications',headers=pre,json={}).status_code == 403
    assert create(client)['version'] == 1
    assert mutate(client,'POST','/applications',json={'owner_id':accounts['other']['id']}).status_code == 422
    with app.state.engine.connect() as connection:
        stored = connection.execute(select(users).where(users.c.username=='new_user')).mappings().one()
        assert stored['password_hash'].startswith('$argon2id$') and PASSWORD not in stored['password_hash']
        token = client.cookies.get('veltrix_session')
        assert connection.execute(select(sessions.c.token_hash).where(sessions.c.user_id==stored['id'])).scalar_one() == hashlib.sha256(token.encode()).hexdigest()
    assert mutate(client,'POST','/auth/logout').status_code == 204
    assert client.get(P+'/auth/me').status_code == 401

def test_all_payload_roundtrips_old_versions_and_restart(system):
    settings, app, client, accounts = system
    login(client)
    row = complete(client)
    assert row['personal_data_complete'] and len(row['evidence']) == 3
    assert client.get(P+f"/applications/{row['id']}/personal-data").json()['profile'] == FIXTURE_PROFILE
    r = client.get(P+f"/applications/{row['id']}/personal-data/download")
    assert r.content == canonical(FIXTURE_PROFILE) and r.headers['content-type'] == 'application/octet-stream'
    fixture_map = {'identity':'identity-png','document':'document-pdf','video':'video-mp4'}
    for entry in row['evidence']:
        r = client.get(P+f"/applications/{row['id']}/evidence/{entry['id']}/download")
        assert r.status_code == 200 and r.content == fixture_bytes(fixture_map[entry['category']])
        assert r.headers['cache-control'] == 'no-store' and r.headers['x-content-type-options'] == 'nosniff'
    first = next(e for e in row['evidence'] if e['category']=='identity')
    updated = upload(client,row,'identity').json()
    assert [e['version'] for e in updated['evidence'] if e['category']=='identity'] == [1,2]
    assert client.get(P+f"/applications/{row['id']}/evidence/{first['id']}/download").content == fixture_bytes('identity-png')
    changed = {**FIXTURE_PROFILE,'occupation':'Profesi revisi fiktif'}
    updated = profile(client,updated,changed).json()
    with app.state.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(profiles)).scalar_one() == 2
        encrypted = connection.execute(select(objects).where(objects.c.kind=='evidence',objects.c.category=='identity')).mappings().all()
        assert encrypted[0]['ciphertext'] != encrypted[1]['ciphertext']
        dump = b''.join(bytes(r['ciphertext'])+r['header'].encode()+bytes(r['wrapped_keys']) for r in connection.execute(select(objects)).mappings())
        assert all(marker not in dump for marker in (b'Nara Contoh',b'nara@example.com',b'DUMMY-private',b'Profesi revisi'))
    with TestClient(create_app(settings),raise_server_exceptions=False) as restarted:
        restarted.cookies.update(client.cookies)
        assert restarted.get(P+'/auth/me').json()['id'] == accounts['owner']['id']
        saved = restarted.get(P+f"/applications/{row['id']}").json()
        assert saved['version'] == updated['version'] and len(saved['evidence']) == 4
        assert restarted.get(P+f"/applications/{row['id']}/personal-data").json()['profile'] == changed

def test_owner_scope_and_parent_ids(system):
    _, _, client, _ = system
    login(client)
    row = complete(client)
    another = create(client)
    item = row['evidence'][0]['id']
    assert client.get(P+f"/applications/{another['id']}/evidence/{item}/download").status_code == 404
    login(client,'other')
    assert client.get(P+'/applications').json() == {'items':[],'total':0}
    for path in (f"/applications/{row['id']}",f"/applications/{row['id']}/personal-data",f"/applications/{row['id']}/personal-data/download",f"/applications/{row['id']}/evidence/{item}/download"):
        assert client.get(P+path).status_code == 404
    assert profile(client,row).status_code == 404
    assert upload(client,row,'identity').status_code == 404
    assert act(client,row,'withdraw').status_code == 404

def test_workflow_assignment_revision_and_private_projection(system):
    _, app, client, accounts = system
    login(client)
    row = complete(client)
    assert act(client,row,'submit',synthetic_acknowledged=False).status_code == 422
    row = act(client,row,'submit',synthetic_acknowledged=True).json()
    assert row['status']=='SUBMITTED' and profile(client,row).status_code==409
    login(client,'reviewer')
    assert client.get(P+'/applications').json()['total'] == 0
    login(client,'admin')
    def assign(row,name):
        return mutate(client,'PUT',f"/admin/assignments/{row['id']}",json={'version':row['version'],'reviewer_id':accounts[name]['id']})
    assert assign(row,'owner').status_code==422
    row = assign(row,'reviewer').json()
    login(client,'reviewer')
    assert client.get(P+'/applications').json()['total']==1
    assert client.get(P+f"/applications/{row['id']}/personal-data").status_code==404
    assert all('display_name' not in e for e in row['evidence'])
    login(client,'admin')
    row = assign(row,'reviewer2').json()
    login(client,'reviewer')
    assert act(client,row,'start-review').status_code==404
    login(client,'reviewer2')
    row = act(client,row,'start-review').json()
    assert row['status']=='UNDER_REVIEW'
    assert act(client,row,'request-revision',note='short').status_code==422
    row = act(client,row,'request-revision',note='Lengkapi dokumen simulasi versi baru.').json()
    assert row['status']=='NEEDS_REVISION' and row['revision_note']=='Lengkapi dokumen simulasi versi baru.'
    login(client,'admin')
    meta = client.get(P+'/admin/assignments').json()['items'][0]
    assert 'revision_note' not in meta and all('note' not in e for e in meta['events'])
    assert act(client,row,'accept').status_code==404
    login(client)
    row = upload(client,row,'document').json()
    row = act(client,row,'resubmit',synthetic_acknowledged=True).json()
    assert row['status']=='RESUBMITTED'
    login(client,'reviewer2')
    row = act(client,row,'start-review').json()
    row = act(client,row,'accept').json()
    assert row['status']=='ACCEPTED_DEMO'
    assert act(client,row,'reject',note='Dokumen tidak memenuhi ketentuan.').status_code==409
    login(client)
    assert act(client,row,'withdraw').status_code==409 and profile(client,row).status_code==409
    with app.state.engine.connect() as connection:
        assert b'Lengkapi dokumen' not in b''.join(bytes(v) for v in connection.execute(select(objects.c.ciphertext)).scalars())

def test_invalid_transitions_leave_no_partial_events(system):
    _, _, client, _ = system
    login(client)
    row = create(client)
    for action in ('accept','reject','resubmit','start-review','request-revision'):
        assert act(client,row,action,note='Catatan cukup panjang.').status_code==409
    assert act(client,row,'submit',synthetic_acknowledged=True).status_code==422
    current = client.get(P+f"/applications/{row['id']}").json()
    assert current['version']==1 and len(current['events'])==1
    assert act(client,row,'withdraw').json()['status']=='WITHDRAWN'

@pytest.mark.parametrize('field,value',[('identity_number','123456'),('email','a@gmail.com'),('phone','08123456789'),('date_of_birth','2020-02-31'),('date_of_birth','2999-01-01'),('occupation','   '),('full_name','x'*501)])
def test_profile_validation(system,field,value):
    _, _, client, _ = system
    login(client)
    row = create(client)
    assert profile(client,row,{**FIXTURE_PROFILE,field:value}).status_code==422
    assert client.get(P+f"/applications/{row['id']}").json()['version']==1

def test_file_validation_caps_and_no_disk_spooling(system,monkeypatch):
    _, _, client, _ = system
    login(client)
    row = create(client)
    def forbidden(*args,**kwargs):
        raise AssertionError('Plaintext upload rolled to disk')
    monkeypatch.setattr(tempfile.SpooledTemporaryFile,'rollover',forbidden)
    for category,data,name in [('identity',b'%PDF-fake','fake.pdf'),('identity',b'','empty.png'),('document',b'PK not DOCX','bad.docx'),('video',b'0000ftyp','bad.mp4')]:
        assert upload(client,row,category,data,name).status_code==422
    png=fixture_bytes('identity-png')
    png += b'\0'*(5*1024**2-len(png))
    response=upload(client,row,'identity',png,'DUMMY-boundary.png')
    assert response.status_code==201,response.text
    row=response.json()
    assert upload(client,row,'identity',png+b'\0','over.png').status_code==413
    video=fixture_bytes('video-mp4')
    remaining=30*1024**2-len(video)
    video+=struct.pack('>I4s',remaining,b'free')+b'\0'*(remaining-8)
    response=upload(client,row,'video',video,'DUMMY-boundary.mp4')
    assert response.status_code==201,response.text
    assert upload(client,response.json(),'video',video+b'0','over.mp4').status_code==413

def test_concurrent_same_version_only_one_commit(system):
    _, app, client, _=system
    login(client)
    row=create(client)
    contenders=[TestClient(app,raise_server_exceptions=False) for _ in range(2)]
    for contender in contenders:
        contender.cookies.update(client.cookies)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda c:profile(c,row),contenders))
    assert sorted(r.status_code for r in responses)==[200,409],[r.text for r in responses]
    with app.state.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(profiles)).scalar_one()==1
        assert connection.execute(select(func.count()).select_from(objects)).scalar_one()==1
    for contender in contenders:
        contender.close()

def test_atomic_database_failure_rollback(system):
    _, app, client, _=system
    login(client)
    row=create(client)
    def fail_event(connection,cursor,statement,parameters,context,executemany):
        if statement.startswith('INSERT INTO case_events'):
            raise RuntimeError('Injected event write failure')
    event.listen(app.state.engine,'before_cursor_execute',fail_event)
    try:
        assert profile(client,row).status_code==500
    finally:
        event.remove(app.state.engine,'before_cursor_execute',fail_event)
    with app.state.engine.connect() as connection:
        assert connection.execute(select(applications.c.version)).scalar_one()==1
        assert connection.execute(select(func.count()).select_from(profiles)).scalar_one()==0
        assert connection.execute(select(func.count()).select_from(objects)).scalar_one()==0
        assert connection.execute(select(func.count()).select_from(events)).scalar_one()==1

def test_corrupted_download_fails_without_plaintext(system):
    _, app, client, _=system
    login(client)
    row=complete(client)
    entry=row['evidence'][0]
    with app.state.engine.begin() as connection:
        object_id=connection.execute(select(evidence.c.object_id).where(evidence.c.id==entry['id'])).scalar_one()
        data=connection.execute(select(objects.c.ciphertext).where(objects.c.id==object_id)).scalar_one()
        connection.execute(update(objects).where(objects.c.id==object_id).values(ciphertext=bytes([data[0]^1])+data[1:]))
    response=client.get(P+f"/applications/{row['id']}/evidence/{entry['id']}/download")
    assert response.status_code==500 and response.json()['error']['code']=='INTEGRITY_CHECK_FAILED'
    assert 'DUMMY-private' not in response.text

@pytest.mark.parametrize('length',[0,1,7,8,9,15,16,17,257,4096])
def test_crypto_boundaries_tamper_and_wrong_owner(length):
    envelope=Envelope(secrets.token_bytes(32))
    context=dict(id='o',application_id='a',owner_id='u',kind='evidence',category='identity',payload_version=1,key_version=1)
    payload=secrets.token_bytes(length)
    row={**context,**envelope.encrypt(context,payload,{'filename':'fiktif-测试.png'})}
    assert envelope.decrypt(row)[1]==payload
    assert envelope.decrypt(row)[0]['filename']=='fiktif-测试.png'
    with pytest.raises(IntegrityFailure):
        Envelope(secrets.token_bytes(32)).decrypt(row)
    with pytest.raises(IntegrityFailure):
        envelope.decrypt({**row,'owner_id':'other'})
    for field in ('ciphertext','wrap_tag','wrap_nonce','wrapped_keys'):
        data=row[field]
        with pytest.raises(IntegrityFailure):
            envelope.decrypt({**row,field:bytes([data[0]^1])+data[1:]})
    header=json.loads(row['header'])
    for field in ('tag','nonce','des_iv'):
        damaged={**header,field:base64.b64encode(b'0'*len(base64.b64decode(header[field]))).decode()}
        with pytest.raises(IntegrityFailure):
            envelope.decrypt({**row,'header':json.dumps(damaged)})

def test_wrong_startup_key_fails_closed(system):
    settings,app,_,_=system
    with pytest.raises(RuntimeError):
        check_keys(app.state.engine,replace(settings,kek=secrets.token_bytes(32)))

@pytest.mark.parametrize('fixture',['personal-json','identity-png','document-pdf','video-mp4'])
def test_lab_real_samples_export_and_restart(system,fixture):
    settings,app,client,_=system
    login(client,'evaluator')
    response=mutate(client,'POST','/lab/runs',json={'kind':'verification','fixture':fixture,'repetitions':100,'warmups':2})
    assert response.status_code==201,response.text
    run=response.json()
    assert run['simulated'] is False and len(run['samples'])==400
    assert {s['trial'] for s in run['samples']}==set(range(1,101))
    assert all(r['round_trip_ok'] for r in run['rows'])
    assert all(s['encrypt_ns']>0 and s['decrypt_ns']>0 for s in run['samples'])
    assert run['fixture_sha256']==hashlib.sha256(fixture_bytes(fixture)).hexdigest()
    assert client.get(P+'/lab/runs').json()[0]['id']==run['id']
    response=client.get(P+f"/lab/runs/{run['id']}/export")
    assert response.status_code==200 and len(response.text.splitlines())==401
    login(client)
    assert client.get(P+'/lab/runs').status_code==403
    assert client.get(P+f"/lab/runs/{run['id']}/export").status_code==403
    with TestClient(create_app(settings)) as restarted:
        login(restarted,'evaluator')
        assert restarted.get(P+'/lab/runs').json()[0]['id']==run['id']

def test_expired_session_and_username_case_sensitivity(system):
    _, app, client, accounts = system
    login(client)
    wrong_case = mutate(client,'POST','/auth/login',json={'username':'OWNER','password':PASSWORD})
    assert wrong_case.status_code == 401
    with app.state.engine.begin() as connection:
        connection.execute(update(sessions).where(sessions.c.user_id==accounts['owner']['id']).values(expires_at=0))
    assert client.get(P+'/auth/me').status_code == 401

def test_lab_lock_and_input_allowlist(system):
    _, app, client, _ = system
    from kyc.db import lab_lock
    login(client,'evaluator')
    bad=mutate(client,'POST','/lab/runs',json={'kind':'benchmark','fixture':'../../database','repetitions':30,'warmups':2})
    assert bad.status_code==422
    import time
    with app.state.engine.begin() as connection:
        connection.execute(update(lab_lock).values(expires_at=time.time()+30,owner='other-worker'))
    busy=mutate(client,'POST','/lab/runs',json={'kind':'benchmark','fixture':'personal-json','repetitions':30,'warmups':2})
    assert busy.status_code==429 and busy.json()['error']['code']=='LAB_BUSY'

def test_stream_request_limits_without_content_length(system):
    _, _, client, _=system
    login(client)
    row=create(client)
    # A generator is transfer-encoded, so the stream limit must work without Content-Length.
    response=client.post(P+f"/applications/{row['id']}/personal-data",headers={**csrf(client),'Content-Type':'application/json'},content=iter([b'x'*70000,b'x'*70000]))
    assert response.status_code==413
    response=client.post(P+f"/applications/{row['id']}/evidence",headers={**csrf(client),'Content-Type':'application/octet-stream'},content=iter([b'x'*(1024**2)]*35))
    assert response.status_code==413
    assert client.get(P+f"/applications/{row['id']}").json()['version']==1

def test_docx_roundtrip_and_zip_traversal_rejection(system):
    import io
    import zipfile
    _, _, client, _=system
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
    login(client)
    row=create(client)
    data=output.getvalue()
    response=upload(client,row,'document',data,'DUMMY-form.docx')
    assert response.status_code==201,response.text
    row=response.json()
    item=row['evidence'][0]
    assert client.get(P+f"/applications/{row['id']}/evidence/{item['id']}/download").content==data
    with zipfile.ZipFile(output,'a') as archive:
        archive.writestr('../unsafe.xml','<x/>')
    assert upload(client,row,'document',output.getvalue(),'unsafe.docx').status_code==422

def test_sqlite_backup_and_restore_with_original_keys(system,tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    settings, app, client, _=system
    if app.state.engine.dialect.name!='sqlite':
        pytest.skip('SQLite backup command is specific to SQLite')
    login(client)
    row=complete(client)
    output=tmp_path/'backup.db'
    environment={**os.environ,'KYC_DATABASE_URL':settings.database_url,
        'VELTRIX_KEK_V1_BASE64':base64.b64encode(settings.kek).decode(),
        'VELTRIX_AUTH_SECRET_BASE64':base64.b64encode(settings.auth_secret).decode()}
    response=subprocess.run([sys.executable,'manage.py','backup',str(output)],cwd=Path(__file__).resolve().parents[1],env=environment,capture_output=True,text=True)
    assert response.returncode==0,response.stderr
    restored_settings=replace(settings,database_url='sqlite:///'+str(output))
    with TestClient(create_app(restored_settings)) as restored:
        login(restored)
        assert restored.get(P+f"/applications/{row['id']}/personal-data").json()['profile']==FIXTURE_PROFILE

def test_cleanup_dry_run_and_foreign_key_cascade(system):
    import subprocess
    import sys
    from pathlib import Path
    settings,app,client,_=system
    login(client)
    row=complete(client)
    other=create(client)
    environment={**os.environ,'APP_ENV':'demo','KYC_DATABASE_URL':settings.database_url,
        'VELTRIX_KEK_V1_BASE64':base64.b64encode(settings.kek).decode(),
        'VELTRIX_AUTH_SECRET_BASE64':base64.b64encode(settings.auth_secret).decode()}
    command=[sys.executable,'manage.py','cleanup-case',row['id']]
    location=Path(__file__).resolve().parents[1]
    dry=subprocess.run(command,cwd=location,env=environment,capture_output=True,text=True)
    assert dry.returncode==0,dry.stderr
    assert client.get(P+f"/applications/{row['id']}").status_code==200
    applied=subprocess.run(command+['--apply'],cwd=location,env=environment,capture_output=True,text=True)
    assert applied.returncode==0,applied.stderr
    assert client.get(P+f"/applications/{row['id']}").status_code==404
    assert client.get(P+f"/applications/{other['id']}").status_code==200
    with app.state.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(objects)).scalar_one()==0
        assert connection.execute(select(func.count()).select_from(users)).scalar_one()==6
