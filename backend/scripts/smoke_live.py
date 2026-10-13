"""Exercise real Next.js proxy + FastAPI. Both servers must already be running."""
import argparse
import hashlib
import secrets
import httpx

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:3000')
parser.add_argument('--large-upload', action='store_true', help='Also verify the full 25 MB upload limit')
args = parser.parse_args()
with httpx.Client(base_url=args.base_url + '/api/v1', timeout=180, trust_env=False) as client:
    token = client.get('/auth/csrf').json()['token']
    client.headers.update({'X-CSRF-Token': token, 'Origin': args.base_url})
    creds = {'username': 'test_' + secrets.token_hex(6), 'password': secrets.token_urlsafe(20)}
    assert client.post('/auth/register', json=creds).status_code == 201
    assert client.post('/auth/login', json=creds).status_code == 200
    assert client.get('/auth/me').json()['username'] == creds['username']
    for length in ([1000, 25_000_000] if args.large_upload else [1000]):
        original = b'%PDF-1.4\n' + b'DUMMY' * ((length - 9) // 5) + b'x' * ((length - 9) % 5)
        response = client.post('/vault/files', files={'file': ('proxy-test.pdf', original, 'application/pdf')}, data={'category': 'document'})
        assert response.status_code == 201, response.text
        file = response.json()
        assert file['original_bytes'] == length
        for algorithm in ('AES', 'RC4', 'DES'):
            result = client.get('/vault/files/' + file['id'] + '/download', params={'algorithm': algorithm})
            assert result.status_code == 200, result.text[:100]
            assert hashlib.sha256(result.content).digest() == hashlib.sha256(original).digest()
        assert client.get('/vault/files', params={'search': 'proxy-test'}).json()['total'] == 1
        if length == 1000:
            response = client.post('/benchmarks', json={'source': {'type': 'file', 'id': file['id']}, 'repetitions': 10, 'warmups': 2})
            assert response.status_code == 201, response.text
            run = response.json()
            assert len(run['samples']) == 30 and all(s['round_trip_ok'] for s in run['samples'])
            assert client.get('/benchmarks/' + run['id'] + '/export').status_code == 200
            download = client.post('/download-tests', json={'file_id': file['id'], 'repetitions': 10}).json()
            assert client.post('/download-tests/' + download['id'] + '/results', json={'attempts': [
                {'algorithm': 'AES', 'repetition': 1, 'elapsed_ms': 0, 'received_bytes': length, 'success': True}], 'browser': 'httpx integration smoke'}).status_code == 200
            assert 'CLIENT-MEASURED-LIVE' in client.get('/download-tests/' + download['id'] + '/export').text
        assert client.delete('/vault/files/' + file['id']).status_code == 204
        print(f'PASS: {length:,} byte upload + AES/RC4/DES downloads via Next.js proxy')
    fields = {'full_name': 'Dummy Integration', 'email': 'dummy@example.com'}
    response = client.post('/vault/personal-data', json=fields)
    assert response.status_code == 201, response.text
    profile = response.json()
    for algorithm in ('AES', 'RC4', 'DES'):
        assert client.post('/vault/personal-data/' + profile['id'] + '/decrypt', json={'algorithm': algorithm}).json()['full_name'] == fields['full_name']
    assert client.delete('/vault/personal-data/' + profile['id']).status_code == 204
    assert client.post('/auth/logout').status_code == 204
    assert client.get('/auth/me').status_code == 401
    print('PASS: auth, profile, real benchmark, CSV, deletion, logout')
