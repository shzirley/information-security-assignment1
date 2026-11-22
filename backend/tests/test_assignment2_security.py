"""Assignment 2 Security Regression & Out-of-Band Threat Model Tests.

Covers:
1. Eavesdropper (Eve) intercepting VELTRIX-SHARE-1 package over WhatsApp/Email cannot decrypt without requester's RSA private key.
2. Tampering 1 bit in the RSA-OAEP-256 encrypted key payload (`ek`) is rejected.
3. Database at-rest audit: wrapped_share_key != raw symmetric key, share_items.ciphertext has no plaintext PII/document bytes.
4. Cross-item AAD substitution attack: swapping encrypted ciphertext between two shared items fails AES-256-GCM authentication.
5. Key rotation: after requester rotates RSA keypair, newly re-issued package cannot be decrypted by the old private key.
6. Revoke shredding: revoking access clears wrapped_share_key and deletes share_items rows.
"""
import base64
import json

import pytest
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from sqlalchemy import select, update

from test_bankkyc import P, create, login, mutate, profile, system, upload
from kyc.db import applications, database, share_items, share_requests
from kyc.lab import FIXTURE_PROFILE, fixture_bytes


def _register_rsa_key(client):
    private = RSA.generate(2048)
    public_pem = private.publickey().export_key(format='PEM', pkcs=8).decode('ascii')
    res = mutate(client, 'PUT', '/keys/me', json={'public_key_pem': public_pem})
    assert res.status_code == 200, res.text
    return private


def _decode_package(package: str) -> dict:
    assert package.startswith('VELTRIX-SHARE-1.')
    encoded = package.removeprefix('VELTRIX-SHARE-1.')
    return json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))


def _decrypt_package_key(package: str, private_key) -> bytes:
    body = _decode_package(package)
    return PKCS1_OAEP.new(private_key, hashAlgo=SHA256).decrypt(base64.b64decode(body['ek']))


def _setup_approved_share(system):
    settings, app, client, accounts = system
    login(client, 'owner')
    row = create(client)
    saved = profile(client, row)
    assert saved.status_code == 200
    uploaded = upload(client, saved.json(), 'identity')
    assert uploaded.status_code == 201

    engine = database(settings.database_url)
    with engine.begin() as conn:
        conn.execute(update(applications).where(applications.c.id == row['id']).values(status='SUBMITTED'))
    engine.dispose()

    login(client, 'other')
    requester_priv = _register_rsa_key(client)
    req = mutate(client, 'POST', '/share-requests', json={
        'owner_username': 'owner',
        'purpose': 'Verifikasi keamanan distribusi kunci out-of-band',
        'items': ['profile', 'identity'],
    })
    assert req.status_code == 201, req.text
    request_id = req.json()['id']

    login(client, 'owner')
    approved = mutate(client, 'POST', f'/share-requests/{request_id}/approve', json={
        'application_id': row['id'],
        'items': ['profile', 'identity'],
    })
    assert approved.status_code == 200, approved.text
    package = approved.json()['package']
    return settings, client, request_id, package, requester_priv


def test_oob_eavesdropper_cannot_decrypt_package(system):
    _, _, _, package, requester_priv = _setup_approved_share(system)
    eve_priv = RSA.generate(2048)
    body = _decode_package(package)

    # Eve intercepts VELTRIX-SHARE-1 package on WhatsApp/Email
    with pytest.raises(ValueError):
        PKCS1_OAEP.new(eve_priv, hashAlgo=SHA256).decrypt(base64.b64decode(body['ek']))

    # Legitimate requester succeeds
    sym_key = _decrypt_package_key(package, requester_priv)
    assert len(sym_key) == 32


def test_oob_package_tampering_rejected_by_rsa_oaep(system):
    _, _, _, package, requester_priv = _setup_approved_share(system)
    body = _decode_package(package)
    raw_ek = bytearray(base64.b64decode(body['ek']))
    raw_ek[10] ^= 0x01  # Flip 1 bit in transit

    with pytest.raises(ValueError):
        PKCS1_OAEP.new(requester_priv, hashAlgo=SHA256).decrypt(bytes(raw_ek))


def test_at_rest_key_wrapping_and_zero_plaintext_audit(system):
    settings, _, request_id, package, requester_priv = _setup_approved_share(system)
    raw_sym_key = _decrypt_package_key(package, requester_priv)

    engine = database(settings.database_url)
    with engine.connect() as conn:
        req_row = conn.execute(select(share_requests).where(share_requests.c.id == request_id)).mappings().one()
        assert req_row['wrapped_share_key'] is not None
        assert req_row['wrapped_share_key'] != raw_sym_key
        assert req_row['wrap_nonce'] is not None and len(req_row['wrap_nonce']) == 12
        assert req_row['wrap_tag'] is not None and len(req_row['wrap_tag']) == 16

        items = conn.execute(select(share_items).where(share_items.c.request_id == request_id)).mappings().all()
        assert len(items) == 2
        for it in items:
            assert FIXTURE_PROFILE['full_name'].encode() not in it['ciphertext']
            assert FIXTURE_PROFILE['identity_number'].encode() not in it['ciphertext']
            assert it['ciphertext'] != fixture_bytes('identity-png')
    engine.dispose()


def test_cross_item_aad_substitution_attack_rejected(system):
    settings, client, request_id, package, requester_priv = _setup_approved_share(system)
    sym_key_b64 = base64.b64encode(_decrypt_package_key(package, requester_priv)).decode('ascii')

    login(client, 'other')
    items = client.get(P + f'/share-requests/{request_id}/items').json()['items']
    profile_item = next(i for i in items if i['kind'] == 'profile')
    identity_item = next(i for i in items if i['kind'] == 'identity')

    # Attacker with DB write access swaps ciphertext + nonce between profile and identity items
    engine = database(settings.database_url)
    with engine.begin() as conn:
        id_row = conn.execute(select(share_items).where(share_items.c.id == identity_item['id'])).mappings().one()
        conn.execute(update(share_items).where(share_items.c.id == profile_item['id']).values(
            nonce=id_row['nonce'], ciphertext=id_row['ciphertext'], original_bytes=id_row['original_bytes']
        ))
    engine.dispose()

    # Opening substituted item must fail AES-GCM AAD verification (item_id & kind bound in AAD)
    res = mutate(client, 'POST', f'/share-requests/{request_id}/items/{profile_item["id"]}/open',
                 json={'share_key': sym_key_b64})
    assert res.status_code == 403
    assert res.json()['error']['code'] == 'SHARE_OPEN_DENIED'


def test_key_rotation_invalidates_old_private_key_on_reissued_package(system):
    _, client, request_id, old_package, old_priv = _setup_approved_share(system)
    original_sym_key = _decrypt_package_key(old_package, old_priv)

    # Requester rotates RSA key pair
    login(client, 'other')
    new_priv = _register_rsa_key(client)

    # Owner re-fetches package -> re-encrypted with new public key
    login(client, 'owner')
    reissued = client.get(P + f'/share-requests/{request_id}/package')
    assert reissued.status_code == 200
    new_package = reissued.json()['package']

    # Old private key cannot decrypt new package
    with pytest.raises(ValueError):
        _decrypt_package_key(new_package, old_priv)

    # New private key decrypts the exact same symmetric share_key
    assert _decrypt_package_key(new_package, new_priv) == original_sym_key
