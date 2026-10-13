import json
import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from app.main import create_app
from app.config import Settings
from app.db import versions, users, items, sessions

@pytest.fixture
def app(tmp_path):
    application = create_app(Settings('sqlite:///' + str(tmp_path / 'test.db'), secrets.token_bytes(32)))
    yield application
    application.state.engine.dispose()

@pytest.fixture
def client(app):
    with TestClient(app) as browser:
        yield browser

def csrf(client):
    return {'X-CSRF-Token': client.get('/api/v1/auth/csrf').json()['token']}

def account(client, name='tester'):
    headers = csrf(client)
    payload = {'username': name, 'password': 'password123'}
    assert client.post('/api/v1/auth/register', json=payload, headers=headers).status_code == 201
    assert client.post('/api/v1/auth/login', json=payload, headers=headers).status_code == 200
    return headers

def upload(client, headers):
    response = client.post('/api/v1/vault/files', files={'file': ('rahasia.pdf', b'%PDF-1.4\nSECRET-DUMMY-PAYLOAD', 'application/pdf')}, data={'category': 'document'}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()

def test_auth_csrf_validation_logout(client, app):
    assert client.get('/api/v1/auth/me').status_code == 401
    payload = {'username': 'tester', 'password': 'password123'}
    assert client.post('/api/v1/auth/register', json=payload).status_code == 403
    headers = account(client)
    assert client.get('/api/v1/auth/me').json()['username'] == 'tester'
    assert client.post('/api/v1/auth/register', json=payload, headers=headers).status_code == 409
    assert client.post('/api/v1/auth/login', json={**payload, 'password': 'wrong'}, headers=headers).status_code == 401
    assert client.post('/api/v1/auth/register', json={'username': 'x', 'password': 'a'}, headers=headers).status_code == 422
    assert client.post('/api/v1/auth/logout', headers={**headers, 'Origin': 'https://evil.example'}).status_code == 403
    with app.state.engine.connect() as connection:
        stored_hash = connection.execute(select(users.c.password_hash)).scalar_one()
        assert stored_hash.startswith('$argon2id$') and stored_hash != payload['password']
    assert 'HttpOnly' in client.post('/api/v1/auth/login', json=payload, headers=headers).headers['set-cookie']
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.get('/api/v1/auth/me').status_code == 401

@pytest.mark.parametrize('algorithm', ['AES', 'RC4', 'DES'])
def test_file_roundtrip_and_encrypted_storage(client, app, algorithm):
    headers = account(client)
    result = upload(client, headers)
    assert [v['algorithm'] for v in result['versions']] == ['AES', 'RC4', 'DES']
    response = client.get(f"/api/v1/vault/files/{result['id']}/download?algorithm={algorithm}")
    assert response.content == b'%PDF-1.4\nSECRET-DUMMY-PAYLOAD'
    assert response.headers['cache-control'] == 'no-store'
    with app.state.engine.connect() as connection:
        for envelope in connection.execute(select(versions.c.envelope)).scalars():
            assert b'SECRET-DUMMY-PAYLOAD' not in envelope
        meta = connection.execute(select(items.c.metadata_cipher)).scalar_one()
        assert b'rahasia.pdf' not in meta
    listed = client.get('/api/v1/vault/files?search=rahasia&page=1&page_size=1').json()
    assert listed['total'] == 1 and len(listed['items']) == 1
    assert client.get('/api/v1/vault/files?category=video').json()['total'] == 0
    assert client.get('/api/v1/vault/summary').json()['file_count'] == 1
    assert client.delete('/api/v1/vault/files/' + result['id'], headers=headers).status_code == 204
    with app.state.engine.connect() as connection:
        assert connection.execute(select(versions)).first() is None

@pytest.mark.parametrize('algorithm', ['AES', 'RC4', 'DES'])
def test_profile_create_update_reveal_delete(client, app, algorithm):
    headers = account(client)
    fields = {'full_name': 'Nama Rahasia Dummy', 'email': 'dummy@example.com', 'phone': '0800', 'address': 'Alamat Dummy', 'date_of_birth': '2000-01-01', 'identity_number': 'DUMMY-001'}
    assert client.get('/api/v1/vault/personal-data').json() is None
    response = client.post('/api/v1/vault/personal-data', json=fields, headers=headers)
    assert response.status_code == 201
    result = response.json()
    path = '/api/v1/vault/personal-data/' + result['id']
    assert client.post(path + '/decrypt', json={'algorithm': algorithm}, headers=headers).json() == fields
    assert client.post('/api/v1/vault/personal-data', json=fields, headers=headers).status_code == 409
    with app.state.engine.connect() as connection:
        before = connection.execute(select(versions.c.envelope).where(versions.c.algorithm == 'AES')).scalar_one()
        assert b'Nama Rahasia Dummy' not in before
    fields['full_name'] = 'Nama Baru'
    assert client.put(path, json=fields, headers=headers).status_code == 200
    assert client.post(path + '/decrypt', json={'algorithm': algorithm}, headers=headers).json() == fields
    with app.state.engine.connect() as connection:
        after = connection.execute(select(versions.c.envelope).where(versions.c.algorithm == 'AES')).scalar_one()
        assert before != after
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get('/api/v1/vault/personal-data').json() is None

def test_ownership_every_resource(client, app):
    headers = account(client)
    file = upload(client, headers)
    profile = client.post('/api/v1/vault/personal-data', json={'full_name': 'Dummy'}, headers=headers).json()
    benchmark = client.post('/api/v1/benchmarks', json={'source': {'type': 'file', 'id': file['id']}, 'repetitions': 10, 'warmups': 2}, headers=headers).json()
    download = client.post('/api/v1/download-tests', json={'file_id': file['id'], 'repetitions': 10}, headers=headers).json()
    with TestClient(app) as other:
        other_headers = account(other, 'other_user')
        paths = [f"/vault/files/{file['id']}", f"/vault/files/{file['id']}/download?algorithm=AES", f"/benchmarks/{benchmark['id']}", f"/benchmarks/{benchmark['id']}/export", f"/download-tests/{download['id']}/export"]
        for path in paths:
            assert other.get('/api/v1' + path).status_code == 404
        assert other.delete('/api/v1/vault/files/' + file['id'], headers=other_headers).status_code == 404
        assert other.post('/api/v1/vault/personal-data/' + profile['id'] + '/decrypt', json={'algorithm': 'AES'}, headers=other_headers).status_code == 404
        assert other.get('/api/v1/vault/files').json()['total'] == 0
        assert other.get('/api/v1/benchmarks').json() == []
        assert other.post('/api/v1/benchmarks', json={'source': {'type': 'file', 'id': file['id']}, 'repetitions': 10}, headers=other_headers).status_code == 404
        assert other.post('/api/v1/download-tests/' + download['id'] + '/results', json={'attempts': []}, headers=other_headers).status_code == 404

def test_benchmark_and_download_csv(client):
    headers = account(client)
    file = upload(client, headers)
    response = client.post('/api/v1/benchmarks', json={'source': {'type': 'file', 'id': file['id']}, 'repetitions': 10, 'warmups': 2}, headers=headers)
    assert response.status_code == 201, response.text
    result = response.json()
    assert len(result['samples']) == 30
    assert all(s['round_trip_ok'] and s['encrypt_ns'] > 0 and s['decrypt_ns'] > 0 for s in result['samples'])
    assert all(s['measured_runs'] == 10 for s in result['summary'])
    assert len(json.loads(result['environment']['execution_order'])) == 10
    assert client.get('/api/v1/benchmarks/' + result['id']).json() == result
    assert len(client.get('/api/v1/benchmarks/' + result['id'] + '/export').text.splitlines()) == 31
    assert len(client.get('/api/v1/benchmarks').json()) == 1
    bad = client.post('/api/v1/benchmarks', json={'source': result['source'], 'repetitions': 31}, headers=headers)
    assert bad.status_code == 422 and bad.json()['error']['code'] == 'VALIDATION_ERROR'
    run = client.post('/api/v1/download-tests', json={'file_id': file['id'], 'repetitions': 10}, headers=headers).json()
    attempt = {'algorithm': 'AES', 'repetition': 1, 'elapsed_ms': 1.5, 'received_bytes': file['original_bytes'], 'success': True}
    path = '/api/v1/download-tests/' + run['id']
    assert client.post(path + '/results', json={'attempts': [attempt], 'browser': 'Test'}, headers=headers).status_code == 200
    assert 'CLIENT-MEASURED-LIVE' in client.get(path + '/export').text
    assert client.post(path + '/results', json={'attempts': [attempt, attempt]}, headers=headers).status_code == 422
    assert client.post(path + '/results', json={'attempts': [{**attempt, 'elapsed_ms': -1}]}, headers=headers).status_code == 422

@pytest.mark.parametrize('algorithm', ['AES', 'RC4', 'DES'])
def test_tampering_rejected_before_decryption(client, app, algorithm):
    headers = account(client)
    file = upload(client, headers)
    with app.state.engine.begin() as connection:
        envelope = connection.execute(select(versions.c.envelope).where(versions.c.item_id == file['id'], versions.c.algorithm == algorithm)).scalar_one()
        tampered = envelope[:-1] + bytes([envelope[-1] ^ 1])
        connection.execute(update(versions).where(versions.c.item_id == file['id'], versions.c.algorithm == algorithm).values(envelope=tampered))
    response = client.get('/api/v1/vault/files/' + file['id'] + '/download?algorithm=' + algorithm)
    assert response.status_code == 409 and response.json()['error']['code'] == 'INTEGRITY_FAILED'

def test_upload_validation_and_limits(client, app):
    headers = account(client)
    assert client.post('/api/v1/vault/files', files={'file': ('script.exe', b'abc')}, data={'category': 'document'}, headers=headers).status_code == 415
    assert client.post('/api/v1/vault/files', files={'file': ('blank.pdf', b'')}, data={'category': 'document'}, headers=headers).status_code == 422
    assert client.post('/api/v1/vault/files', files={'file': ('video.mp4', b'abc')}, data={'category': 'identity'}, headers=headers).status_code == 415
    assert client.post('/api/v1/vault/files', files={'file': ('big.pdf', b'x' * 25_000_001)}, data={'category': 'document'}, headers=headers).status_code == 413
    assert client.post('/api/v1/vault/files', content=b'x' * 25_070_000, headers=headers).status_code == 413
    assert client.get('/api/v1/vault/files?page_size=101').status_code == 422
    with app.state.engine.connect() as connection:
        assert connection.execute(select(items)).first() is None

def test_persistence_after_restart(tmp_path):
    settings = Settings('sqlite:///' + str(tmp_path / 'persist.db'), secrets.token_bytes(32))
    first = create_app(settings)
    with TestClient(first) as browser:
        headers = account(browser)
        result = upload(browser, headers)
        cookies = dict(browser.cookies)
    second = create_app(settings)
    with TestClient(second) as browser:
        browser.cookies.update(cookies)
        assert browser.get('/api/v1/auth/me').status_code == 200
        assert browser.get('/api/v1/vault/files/' + result['id'] + '/download?algorithm=AES').content == b'%PDF-1.4\nSECRET-DUMMY-PAYLOAD'

def test_expired_session(client, app):
    account(client)
    with app.state.engine.begin() as connection:
        connection.execute(update(sessions).values(expires=0))
    assert client.get('/api/v1/auth/me').status_code == 401

def test_rate_limit(client):
    headers = account(client)
    for _ in range(9):
        assert client.post('/api/v1/auth/login', json={'username': 'tester', 'password': 'bad'}, headers=headers).status_code == 401
    assert client.post('/api/v1/auth/login', json={'username': 'tester', 'password': 'bad'}, headers=headers).status_code == 429
