"""Assignment 2 API integration with synthetic encrypted profile data."""
import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from sqlalchemy import select, update

from test_bankkyc import P, create, login, mutate, profile, system, upload
from kyc.db import applications, database, share_items, share_requests, user_public_keys, users
from kyc.lab import FIXTURE_PROFILE, fixture_bytes


def keypair(client):
    private = RSA.generate(2048)
    public = private.publickey().export_key(format='PEM', pkcs=8).decode()
    response = mutate(client, 'PUT', '/keys/me', json={'public_key_pem': public})
    assert response.status_code == 200, response.text
    return private


def share_key(package, private):
    encoded = package.removeprefix('VELTRIX-SHARE-1.')
    body = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
    return PKCS1_OAEP.new(private, hashAlgo=SHA256).decrypt(base64.b64decode(body['ek']))


def test_profile_share_open_rotate_revoke_and_scope(system):
    settings, app, client, accounts = system
    login(client, 'owner')
    row = create(client)
    saved = profile(client, row)
    assert saved.status_code == 200
    uploaded = upload(client, saved.json(), 'identity')
    assert uploaded.status_code == 201
    # A submitted case is required; this test seeds the state because MP4 validation
    # depends on an external ffprobe executable, unrelated to sharing behavior.
    engine = database(settings.database_url)
    with engine.begin() as connection:
        connection.execute(update(applications).where(applications.c.id == row['id']).values(status='SUBMITTED'))
    engine.dispose()

    login(client, 'other')
    private = keypair(client)
    created = mutate(client, 'POST', '/share-requests', json={
        'owner_username': 'owner', 'purpose': 'Pengajuan rekening HIMA Informatika', 'items': ['profile', 'identity']})
    assert created.status_code == 201, created.text
    request_id = created.json()['id']
    assert created.json()['status'] == 'PENDING'
    assert mutate(client, 'POST', f'/share-requests/{request_id}/approve',
                  json={'application_id': row['id'], 'items': ['profile', 'identity']}).status_code == 404

    login(client, 'owner')
    incoming = client.get(P + '/share-requests?box=incoming')
    assert incoming.status_code == 200 and incoming.json()['items'][0]['requester_key_fingerprint']
    approved = mutate(client, 'POST', f'/share-requests/{request_id}/approve',
                      json={'application_id': row['id'], 'items': ['profile', 'identity']})
    assert approved.status_code == 200, approved.text
    package = approved.json()['package']
    assert 'DUMMY-' not in package
    engine = database(settings.database_url)
    with engine.connect() as connection:
        stored = connection.execute(select(share_requests).where(share_requests.c.id == request_id)).mappings().one()
        for item in connection.execute(select(share_items).where(share_items.c.request_id == request_id)).mappings():
            assert FIXTURE_PROFILE['identity_number'].encode() not in item['ciphertext']
            assert item['ciphertext'] != fixture_bytes('identity-png')
        assert stored['wrapped_share_key'] != share_key(package, private)
    engine.dispose()

    login(client, 'other')
    items = client.get(P + f'/share-requests/{request_id}/items')
    assert items.status_code == 200 and len(items.json()['items']) == 2
    item_id = next(item['id'] for item in items.json()['items'] if item['kind'] == 'profile')
    identity_id = next(item['id'] for item in items.json()['items'] if item['kind'] == 'identity')
    key = share_key(package, private)
    opened = mutate(client, 'POST', f'/share-requests/{request_id}/items/{item_id}/open',
                    json={'share_key': base64.b64encode(key).decode()})
    assert opened.status_code == 200, opened.text
    assert json.loads(opened.content) == FIXTURE_PROFILE
    assert opened.headers['cache-control'] == 'no-store'
    identity = mutate(client, 'POST', f'/share-requests/{request_id}/items/{identity_id}/open',
                      json={'share_key': base64.b64encode(key).decode()})
    assert identity.status_code == 200 and identity.content == fixture_bytes('identity-png')
    engine = database(settings.database_url)
    with engine.begin() as connection:
        ciphertext = connection.execute(select(share_items.c.ciphertext).where(share_items.c.id == identity_id)).scalar_one()
        connection.execute(update(share_items).where(share_items.c.id == identity_id).values(
            ciphertext=bytes([ciphertext[0] ^ 1]) + ciphertext[1:]))
    engine.dispose()
    tampered = mutate(client, 'POST', f'/share-requests/{request_id}/items/{identity_id}/open',
                      json={'share_key': base64.b64encode(key).decode()})
    assert tampered.status_code == 403 and tampered.json()['error']['code'] == 'SHARE_OPEN_DENIED'
    wrong = mutate(client, 'POST', f'/share-requests/{request_id}/items/{item_id}/open',
                   json={'share_key': base64.b64encode(b'X' * 32).decode()})
    assert wrong.status_code == 403 and wrong.json()['error']['code'] == 'SHARE_OPEN_DENIED'
    malformed = mutate(client, 'POST', f'/share-requests/{request_id}/items/{item_id}/open', json={})
    assert malformed.status_code == wrong.status_code
    assert malformed.json()['error']['code'] == wrong.json()['error']['code']
    login(client, 'admin')
    assert mutate(client, 'POST', f'/share-requests/{request_id}/items/{item_id}/open',
                  json={'share_key': base64.b64encode(key).decode()}).status_code == 403
    login(client, 'other')
    new_private = keypair(client)

    login(client, 'owner')
    renewed = client.get(P + f'/share-requests/{request_id}/package')
    assert renewed.status_code == 200
    assert share_key(renewed.json()['package'], new_private) == key
    revoked = mutate(client, 'POST', f'/share-requests/{request_id}/revoke')
    assert revoked.status_code == 200
    engine = database(settings.database_url)
    with engine.connect() as connection:
        record = connection.execute(select(share_requests).where(share_requests.c.id == request_id)).mappings().one()
        assert record['wrapped_share_key'] is None
        assert connection.execute(select(share_items).where(share_items.c.request_id == request_id)).first() is None
    engine.dispose()
    login(client, 'other')
    denied = mutate(client, 'POST', f'/share-requests/{request_id}/items/{item_id}/open',
                    json={'share_key': base64.b64encode(key).decode()})
    assert denied.status_code == 403 and denied.json()['error']['code'] == 'SHARE_OPEN_DENIED'


def test_request_validation_and_expiry_shreds_copy(system):
    settings, app, client, accounts = system
    login(client, 'other')
    payload = {'owner_username': 'owner', 'purpose': 'Pengajuan rekening HIMA Informatika', 'items': ['profile']}
    assert mutate(client, 'POST', '/share-requests', json=payload).status_code == 422
    keypair(client)
    assert mutate(client, 'POST', '/share-requests', json={**payload, 'owner_username': 'other'}).status_code == 422
    assert mutate(client, 'POST', '/share-requests', json={**payload, 'owner_username': 'reviewer'}).status_code == 422
    created = mutate(client, 'POST', '/share-requests', json=payload)
    assert created.status_code == 201
    request_id = created.json()['id']
    assert mutate(client, 'POST', f'/share-requests/{request_id}/cancel').status_code == 200
    assert mutate(client, 'POST', f'/share-requests/{request_id}/cancel').status_code == 409


def test_expiry_persists_and_removes_wrapped_key(system):
    settings, app, client, accounts = system
    login(client, 'owner')
    row = create(client)
    assert profile(client, row).status_code == 200
    engine = database(settings.database_url)
    with engine.begin() as connection:
        connection.execute(update(applications).where(applications.c.id == row['id']).values(status='SUBMITTED'))
    engine.dispose()


    login(client, 'other')
    private = keypair(client)
    created = mutate(client, 'POST', '/share-requests', json={
        'owner_username': 'owner', 'purpose': 'Pengajuan rekening HIMA Informatika', 'items': ['profile']})
    request_id = created.json()['id']
    login(client, 'owner')
    approved = mutate(client, 'POST', f'/share-requests/{request_id}/approve',
                      json={'application_id': row['id'], 'items': ['profile']})
    assert approved.status_code == 200
    engine = database(settings.database_url)
    with engine.begin() as connection:
        connection.execute(update(share_requests).where(share_requests.c.id == request_id).values(
            expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()))
    engine.dispose()
    login(client, 'other')
    result = client.get(P + f'/share-requests/{request_id}/items')
    assert result.status_code == 409
    engine = database(settings.database_url)
    with engine.connect() as connection:
        stored = connection.execute(select(share_requests).where(share_requests.c.id == request_id)).mappings().one()
        assert stored['status'] == 'EXPIRED' and stored['wrapped_share_key'] is None
        assert connection.execute(select(share_items).where(share_items.c.request_id == request_id)).first() is None
    engine.dispose()


def test_upgrade_from_existing_0002_keeps_user(tmp_path):
    engine = database('sqlite:///' + str(tmp_path / 'upgrade.db'))
    config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, '0002_document_review')
    # The legacy 0001 migration uses current metadata. Remove newly declared
    # tables to model an actual database created before Assignment 2.
    with engine.begin() as connection:
        for table in (share_items, share_requests, user_public_keys):
            table.drop(connection, checkfirst=True)
        connection.execute(users.insert().values(id='old-applicant', username='old_applicant',
            display_name='old_applicant', password_hash='synthetic', role='applicant',
            is_active=True, created_at='2026-01-01T00:00:00+00:00'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
        assert connection.execute(select(users.c.username).where(users.c.id == 'old-applicant')).scalar_one() == 'old_applicant'
        assert user_public_keys.name in connection.dialect.get_table_names(connection)
        assert share_requests.name in connection.dialect.get_table_names(connection)
    engine.dispose()
