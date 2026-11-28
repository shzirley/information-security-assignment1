"""Assignment 3 (M3-SEC-03): VELTRIX Demo CA, proof of possession, and X.509 v3 certificates.

`cryptography` only generates the CA key pair (OpenSSL is ~80x faster than pure Python for RSA-3072)
and `asn1crypto` only encodes DER. Every certificate signature is made with kyc.signature_rsa.
The CA private key is stored wrapped with the existing KEK (AES-256-GCM, AAD purpose='ca-key').
"""
import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from asn1crypto import keys, x509
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .crypto import canonical
from .signature_rsa import private_params, sign_pkcs1_v15, validate_public_key, verify_with

CA_NAME = {'common_name': 'VELTRIX Demo CA', 'organization_name': 'VELTRIX BankKYC (academic demo)'}
CA_YEARS, USER_YEARS = 10, 2
SIGNATURE_ALGORITHM = {'algorithm': 'sha256_rsa'}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _wrap_aad(authority_id):
    return canonical({'purpose': 'ca-key', 'id': authority_id})


def _spki_from_pem(public_key_pem):
    body = ''.join(line for line in public_key_pem.strip().splitlines() if not line.startswith('-----'))
    return base64.b64decode(body, validate=True)


def _key_identifier(public_key_info):
    # RFC 5280 §4.2.1.2 method 1; SHA-1 here only names the key, it is not a security check.
    return hashlib.sha1(public_key_info['public_key'].contents[1:]).digest()


def _sign_tbs(tbs, ca_params):
    signature = sign_pkcs1_v15(ca_params, hashlib.sha256(tbs.dump()).digest())
    return x509.Certificate({'tbs_certificate': tbs, 'signature_algorithm': SIGNATURE_ALGORITHM,
                             'signature_value': signature})


def _tbs(serial, issuer, subject, spki, days, extensions):
    start = _now()
    return x509.TbsCertificate({
        'version': 'v3', 'serial_number': serial, 'signature': SIGNATURE_ALGORITHM,
        'issuer': issuer, 'subject': subject, 'subject_public_key_info': spki,
        'validity': {'not_before': x509.Time({'utc_time': start}),
                     'not_after': x509.Time({'utc_time': start + timedelta(days=days)})},
        'extensions': extensions,
    })


def _serial():
    return secrets.randbits(127) | (1 << 126)  # positive, fixed length, unpredictable


def create_authority(kek):
    """Self-signed root, private key wrapped with the KEK. Returns a pki_authority row."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    pkcs8 = private.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption())
    params = private_params(RSA.import_key(pkcs8))
    spki = keys.PublicKeyInfo.load(private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo))
    name = x509.Name.build(CA_NAME)
    tbs = _tbs(_serial(), name, name, spki, CA_YEARS * 365, [
        {'extn_id': 'basic_constraints', 'critical': True, 'extn_value': {'ca': True}},
        {'extn_id': 'key_usage', 'critical': True, 'extn_value': {'key_cert_sign', 'crl_sign'}},
        {'extn_id': 'key_identifier', 'critical': False, 'extn_value': _key_identifier(spki)},
    ])
    certificate = _sign_tbs(tbs, params).dump()
    authority_id = str(uuid.uuid4())
    nonce = secrets.token_bytes(12)
    cipher = AES.new(kek, AES.MODE_GCM, nonce=nonce)
    cipher.update(_wrap_aad(authority_id))
    wrapped, tag = cipher.encrypt_and_digest(pkcs8)
    return {'id': authority_id, 'certificate_der': certificate, 'wrapped_private_key': wrapped,
            'wrap_nonce': nonce, 'wrap_tag': tag, 'created_at': _now().isoformat()}


def _authority_params(authority_row, kek):
    cipher = AES.new(kek, AES.MODE_GCM, nonce=authority_row['wrap_nonce'])
    cipher.update(_wrap_aad(authority_row['id']))
    pkcs8 = cipher.decrypt_and_verify(authority_row['wrapped_private_key'], authority_row['wrap_tag'])
    return private_params(RSA.import_key(pkcs8))


def pop_message(user_id, spki_der, challenge):
    """Bytes the browser signs: canonical JSON of the base64 challenge, SPKI hash, and user id."""
    return canonical({'challenge': base64.b64encode(challenge).decode('ascii'),
                      'spki_sha256': hashlib.sha256(spki_der).hexdigest(), 'user_id': user_id})


def verify_pop(public_key_pem, user_id, challenge, signature):
    """Proof of possession: the registering browser signed this user's fresh challenge with the key."""
    try:
        n, e = validate_public_key(public_key_pem, min_bits=3072)
        message = pop_message(user_id, _spki_from_pem(public_key_pem), challenge)
        return verify_with(n, e, hashlib.sha256(message).digest(), signature)
    except (ValueError, TypeError):
        return False


def issue_certificate(public_key_pem, account, authority_row, kek):
    """X.509 v3 end-entity certificate for a signing key. Returns (DER, serial hex, expires_at)."""
    ca = x509.Certificate.load(authority_row['certificate_der'])
    spki = keys.PublicKeyInfo.load(_spki_from_pem(public_key_pem))
    subject = x509.Name.build({'common_name': account.get('display_name') or account['username'],
                               'user_id': account['username'], 'organization_name': CA_NAME['organization_name']})
    serial = _serial()
    tbs = _tbs(serial, ca.subject, subject, spki, USER_YEARS * 365, [
        {'extn_id': 'basic_constraints', 'critical': True, 'extn_value': {'ca': False}},
        {'extn_id': 'key_usage', 'critical': True, 'extn_value': {'digital_signature', 'non_repudiation'}},
        {'extn_id': 'key_identifier', 'critical': False, 'extn_value': _key_identifier(spki)},
        {'extn_id': 'authority_key_identifier', 'critical': False,
         'extn_value': {'key_identifier': _key_identifier(ca.public_key)}},
    ])
    certificate = _sign_tbs(tbs, _authority_params(authority_row, kek))
    return certificate.dump(), format(serial, 'x'), tbs['validity']['not_after'].native.isoformat()


def rsa_numbers(public_key_info):
    parsed = public_key_info['public_key'].parsed
    return parsed['modulus'].native, parsed['public_exponent'].native


def verify_chain(cert_der, ca_der, at=None):
    """True if `cert_der` was signed by the VELTRIX CA with our verifier and is valid at `at`."""
    try:
        cert, ca = x509.Certificate.load(cert_der), x509.Certificate.load(ca_der)
        if cert.issuer != ca.subject or cert['signature_algorithm']['algorithm'].native != 'sha256_rsa':
            return False
        n, e = rsa_numbers(ca.public_key)
        if not verify_with(n, e, hashlib.sha256(cert['tbs_certificate'].dump()).digest(), cert['signature_value'].native):
            return False
        moment = at or _now()
        validity = cert['tbs_certificate']['validity']
        return validity['not_before'].native <= moment <= validity['not_after'].native
    except (ValueError, TypeError, KeyError):
        return False
