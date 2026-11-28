"""Assignment 3 cryptography tests (Maleka, M3-SEC-04): own RSASSA, PKI, CMS, and key registration.

Plan §3.1 ids are noted per test. PDF-level cases (T01, T04-T08, T13, T14, T16, T18) need
kyc.pdf_signing / kyc.pdf_verify (Jorell) and are not covered here.
"""
import base64
import hashlib
import json
import secrets
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
from asn1crypto import cms as asn1_cms
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from test_bankkyc import P, login, mutate, system  # noqa: F401  (pytest fixture)
from kyc import cms, pki
from kyc.db import pki_authority, user_signing_keys
from kyc.signature_rsa import (emsa_pkcs1_v15_encode, i2osp, os2ip, private_params, rsasp1,
                               sign_pkcs1_v15, verify_pkcs1_v15, verify_with)

KEK = secrets.token_bytes(32)


def new_key(bits=3072):
    """Fast OpenSSL key generation; returns (pycryptodome key, canonical SPKI PEM, CRT params)."""
    der = rsa.generate_private_key(65537, bits).private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    key = RSA.import_key(der)
    return key, key.publickey().export_key(format='PEM').decode(), private_params(key)


@pytest.fixture(scope='module')
def signer():
    return new_key()


@pytest.fixture(scope='module')
def authority():
    return pki.create_authority(KEK)


@pytest.fixture(scope='module')
def signed(signer, authority):
    """A detached CMS over synthetic content, signed with the user's key and certificate."""
    key, pem, params = signer
    cert, _, _ = pki.issue_certificate(pem, {'username': 'budi', 'display_name': 'Budi Pratama'}, authority, KEK)
    content = b'%PDF-1.7 synthetic byte range'
    attrs = cms.build_signed_attrs(hashlib.sha256(content).digest(), cert, datetime.now(timezone.utc))
    signature = sign_pkcs1_v15(params, hashlib.sha256(attrs).digest())
    return {'cert': cert, 'content': content, 'cms': cms.build_signed_data(attrs, signature, [cert, authority['certificate_der']])}


def test_t02_own_rsassa_matches_pycryptodome(signer):
    key, pem, params = signer
    for i in range(50):
        message = secrets.token_bytes(1 + i * 7)
        ours = sign_pkcs1_v15(params, hashlib.sha256(message).digest())
        assert ours == pkcs1_15.new(key).sign(SHA256.new(message))
        assert verify_pkcs1_v15(pem, hashlib.sha256(message).digest(), ours)


def test_t03_verify_rejects_wrong_key_tamper_and_bad_length(signer):
    _, pem, params = signer
    _, other_pem, _ = new_key()
    digest = hashlib.sha256(b'form').digest()
    signature = sign_pkcs1_v15(params, digest)
    assert not verify_pkcs1_v15(other_pem, digest, signature)
    flipped = bytearray(signature); flipped[-1] ^= 1
    assert not verify_pkcs1_v15(pem, digest, bytes(flipped))
    assert not verify_pkcs1_v15(pem, digest, signature[1:])
    assert not verify_pkcs1_v15(pem, hashlib.sha256(b'other').digest(), signature)
    assert not verify_with(params['n'], params['e'], digest, i2osp(params['n'], len(signature)))


def test_t09_lenient_padding_and_small_exponent_are_rejected(signer):
    _, pem, params = signer
    k = len(i2osp(params['n'], (params['n'].bit_length() + 7) // 8))
    digest = hashlib.sha256(b'form').digest()
    good = emsa_pkcs1_v15_encode(digest, k)
    # Bleichenbacher-style block: correct prefix and hash, garbage after it instead of FF padding.
    forged = b'\x00\x01\xff\x00' + good[-51:] + secrets.token_bytes(k - 55)
    signature = i2osp(rsasp1(os2ip(forged), params), k)
    assert not verify_pkcs1_v15(pem, digest, signature)
    assert not verify_with(params['n'], 3, digest, sign_pkcs1_v15(params, digest))


def test_t15_proof_of_possession(signer):
    _, pem, params = signer
    challenge = secrets.token_bytes(32)
    spki = pki._spki_from_pem(pem)
    message = json.dumps({'challenge': base64.b64encode(challenge).decode(),
                          'spki_sha256': hashlib.sha256(spki).hexdigest(), 'user_id': 'user-1'},
                         separators=(',', ':'), sort_keys=True).encode()
    pop = sign_pkcs1_v15(params, hashlib.sha256(message).digest())
    assert pki.verify_pop(pem, 'user-1', challenge, pop)
    assert not pki.verify_pop(pem, 'user-2', challenge, pop)
    assert not pki.verify_pop(pem, 'user-1', secrets.token_bytes(32), pop)
    _, small_pem, small_params = new_key(2048)
    small_pop = sign_pkcs1_v15(small_params, hashlib.sha256(pki.pop_message('user-1', pki._spki_from_pem(small_pem), challenge)).digest())
    assert not pki.verify_pop(small_pem, 'user-1', challenge, small_pop)


def test_ca_key_is_wrapped_and_certificates_chain(authority, signed):
    assert b'PRIVATE' not in authority['wrapped_private_key']
    assert pki._authority_params(authority, KEK)['n'] > 0
    with pytest.raises(ValueError):
        pki._authority_params(authority, secrets.token_bytes(32))
    assert pki.verify_chain(signed['cert'], authority['certificate_der'])
    assert pki.verify_chain(authority['certificate_der'], authority['certificate_der'])
    assert not pki.verify_chain(signed['cert'], authority['certificate_der'], at=datetime.now(timezone.utc) + timedelta(days=3 * 365))
    broken = bytearray(signed['cert']); broken[-1] ^= 1
    assert not pki.verify_chain(bytes(broken), authority['certificate_der'])


def test_cms_statuses(signer, authority, signed):
    digest = hashlib.sha256(signed['content']).digest()
    ca = authority['certificate_der']
    result = cms.parse_and_verify(signed['cms'], digest, ca)
    assert result['status'] == 'VALID' and result['signer'] == 'Budi Pratama'
    # Same fingerprint as the backend stores for the registered key.
    assert result['fingerprint'] == hashlib.sha256(RSA.import_key(signer[1]).export_key(format='DER')).hexdigest()
    assert cms.parse_and_verify(signed['cms'], hashlib.sha256(b'changed').digest(), ca)['status'] == 'INVALID'  # T04/T08
    assert cms.parse_and_verify(signed['cms'], digest, pki.create_authority(KEK)['certificate_der'])['status'] == 'VALID_UNTRUSTED'  # T11
    assert cms.parse_and_verify(b'\x30\x03\x02\x01\x00', digest, ca)['status'] == 'MALFORMED'


def test_t05_t10_tampered_signature_and_weak_digest_algorithm(authority, signed):
    digest = hashlib.sha256(signed['content']).digest()
    ca = authority['certificate_der']
    info = asn1_cms.ContentInfo.load(signed['cms'])
    signer_info = info['content']['signer_infos'][0]
    original = signer_info['signature'].native
    signer_info['signature'] = original[:-1] + bytes([original[-1] ^ 1])
    assert cms.parse_and_verify(info.dump(force=True), digest, ca)['status'] == 'INVALID'
    info = asn1_cms.ContentInfo.load(signed['cms'])
    info['content']['signer_infos'][0]['digest_algorithm'] = {'algorithm': 'sha1'}
    assert cms.parse_and_verify(info.dump(force=True), digest, ca)['status'] == 'INVALID'


@pytest.mark.skipif(shutil.which('openssl') is None, reason='openssl CLI not installed')
def test_openssl_accepts_our_certificate_and_cms(tmp_path, authority, signed):
    (tmp_path / 'ca.der').write_bytes(authority['certificate_der'])
    (tmp_path / 'sig.der').write_bytes(signed['cms'])
    (tmp_path / 'content.bin').write_bytes(signed['content'])
    run = lambda *args: subprocess.run(['openssl', *args], cwd=tmp_path, capture_output=True, text=True)
    assert run('x509', '-inform', 'DER', '-in', 'ca.der', '-out', 'ca.pem').returncode == 0
    verified = run('cms', '-verify', '-inform', 'DER', '-in', 'sig.der', '-binary', '-content', 'content.bin',
                   '-CAfile', 'ca.pem', '-purpose', 'any', '-out', 'out.bin')
    assert verified.returncode == 0, verified.stderr


def register(client, pem, params, *, user_id=None, tamper=False):
    challenge = mutate(client, 'POST', '/signing-keys/challenge').json()
    message = pki.pop_message(user_id or challenge['user_id'], pki._spki_from_pem(pem), base64.b64decode(challenge['challenge']))
    pop = sign_pkcs1_v15(params, hashlib.sha256(message + (b'x' if tamper else b'')).digest())
    body = {'public_key_pem': pem, 'challenge_id': challenge['challenge_id'], 'pop_signature': base64.b64encode(pop).decode()}
    return mutate(client, 'PUT', '/signing-keys/me', json=body), body


def test_t12_t15_key_registration_api(system):  # noqa: F811
    _, app, client, _ = system
    login(client, 'owner')
    _, pem, params = new_key()
    created, body = register(client, pem, params)
    assert created.status_code == 200, created.text
    with app.state.engine.connect() as connection:
        ca_der = connection.execute(select(pki_authority.c.certificate_der)).scalar_one()
    assert pki.verify_chain(base64.b64decode(''.join(created.json()['certificate_pem'].splitlines()[1:-1])), ca_der)
    assert mutate(client, 'PUT', '/signing-keys/me', json=body).status_code == 422  # challenge reused
    assert register(client, pem, params, tamper=True)[0].status_code == 422      # wrong proof
    assert register(client, pem, params, user_id='someone-else')[0].status_code == 422
    _, small_pem, small_params = new_key(2048)
    assert register(client, small_pem, small_params)[0].status_code == 422
    _, pem2, params2 = new_key()
    assert register(client, pem2, params2)[0].status_code == 200                 # rotation
    state = client.get(P + '/signing-keys/me').json()
    assert state['active']['fingerprint'] != created.json()['fingerprint']
    assert [old['revoke_reason'] for old in state['history']] == ['replaced']
    with app.state.engine.connect() as connection:
        stored = connection.execute(select(user_signing_keys.c.public_key_pem)).scalars().all()
    assert all('PRIVATE' not in value for value in stored)
    ca = client.get(P + '/pki/ca.pem')
    assert ca.status_code == 200 and ca.text.startswith('-----BEGIN CERTIFICATE-----')
