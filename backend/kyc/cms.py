"""Assignment 3 (M3-SEC-02): CMS SignedData for /adbe.pkcs7.detached (RFC 5652).

`asn1crypto` encodes and decodes DER only. Attribute ordering, the SET OF (0x31) form that is
signed, and every verification rule (implementation plan §1.7 steps 5-9) are written here.
"""
import hashlib
from datetime import datetime

from asn1crypto import cms, tsp, x509  # noqa: F401  tsp registers signing_certificate_v2

from .pki import rsa_numbers, verify_chain
from .signature_rsa import verify_with

DIGEST = {'algorithm': 'sha256'}
SIGNATURE_ALGORITHMS = {'rsassa_pkcs1v15', 'sha256_rsa'}
SET_TAG, IMPLICIT_0_TAG = 0x31, 0xA0


def build_signed_attrs(digest, cert_der, signing_time):
    """DER SET OF Attribute with tag 0x31: the exact bytes the signer hashes and signs."""
    attributes = [
        cms.CMSAttribute({'type': 'content_type', 'values': ['data']}),
        cms.CMSAttribute({'type': 'signing_time', 'values': [cms.Time({'utc_time': signing_time.replace(microsecond=0)})]}),
        cms.CMSAttribute({'type': 'message_digest', 'values': [digest]}),
        # ESSCertIDv2 (RFC 5035) binds the signature to one certificate; sha256 is the default hash.
        cms.CMSAttribute({'type': 'signing_certificate_v2', 'values': [{'certs': [{'cert_hash': hashlib.sha256(cert_der).digest()}]}]}),
    ]
    # DER sorts SET OF members by encoding; verifiers such as OpenSSL re-encode before hashing.
    encoded = sorted(attribute.dump() for attribute in attributes)
    return cms.CMSAttributes([cms.CMSAttribute.load(item) for item in encoded]).dump()


def build_signed_data(signed_attrs, signature, cert_chain):
    """ContentInfo(SignedData) with one SignerInfo and no encapsulated content (detached)."""
    signer = x509.Certificate.load(cert_chain[0])
    signer_info = cms.SignerInfo({
        'version': 'v1',
        'sid': cms.SignerIdentifier({'issuer_and_serial_number': {
            'issuer': signer.issuer, 'serial_number': signer.serial_number}}),
        'digest_algorithm': DIGEST,
        'signed_attrs': cms.CMSAttributes.load(signed_attrs),
        'signature_algorithm': {'algorithm': 'sha256_rsa'},
        'signature': signature,
    })
    der = cms.ContentInfo({'content_type': 'signed_data', 'content': {
        'version': 'v1', 'digest_algorithms': [DIGEST],
        'encap_content_info': {'content_type': 'data'},
        'certificates': [x509.Certificate.load(cert) for cert in cert_chain],
        'signer_infos': [signer_info],
    }}).dump()
    # The embedded [0] attributes must be the signed bytes with only the tag changed.
    if signed_attributes_der(cms.ContentInfo.load(der)['content']['signer_infos'][0]) != signed_attrs:
        raise ValueError('Signed attributes changed while embedding')
    return der


def signed_attributes_der(signer_info):
    raw = signer_info['signed_attrs'].dump()
    if raw[0] != IMPLICIT_0_TAG:
        raise ValueError('Signed attributes missing')
    return bytes([SET_TAG]) + raw[1:]


def _attributes(signer_info):
    values = {}
    for attribute in signer_info['signed_attrs']:
        name = attribute['type'].native
        if name in values or len(attribute['values']) != 1:
            raise ValueError(f'Attribute {name} must appear once with one value')
        values[name] = attribute['values'][0]
    return values


def _result(status, reason, signer=None, fingerprint=None, signed_at=None):
    return {'status': status, 'reasons': [reason] if reason else [], 'signer': signer,
            'fingerprint': fingerprint, 'signed_at': signed_at}


def parse_and_verify(cms_der, content_digest, ca_der):
    """Plan §1.7 steps 5-9 for a CMS blob taken from /Contents. Stops at the first failure.

    `content_digest` is SHA-256 over the PDF ByteRange. Returns status, reasons, signer (certificate
    CN), fingerprint (SHA-256 of the signer's SPKI, same as user_signing_keys.fingerprint), signed_at.
    """
    try:
        info = cms.ContentInfo.load(cms_der)
        if info['content_type'].native != 'signed_data':
            return _result('MALFORMED', 'Isi /Contents bukan CMS SignedData.')
        signed_data = info['content']
        if len(signed_data['signer_infos']) != 1:
            return _result('MALFORMED', 'CMS harus berisi tepat satu penandatangan.')
        if signed_data['encap_content_info']['content'].native is not None:
            return _result('MALFORMED', 'CMS untuk PDF harus detached (tanpa isi tertanam).')
        signer_info = signed_data['signer_infos'][0]
        if (signer_info['digest_algorithm']['algorithm'].native != 'sha256'
                or signer_info['signature_algorithm']['algorithm'].native not in SIGNATURE_ALGORITHMS):
            return _result('INVALID', 'Algoritma tidak diizinkan; hanya SHA-256 dengan RSA PKCS#1 v1.5.')
        attributes = _attributes(signer_info)
        if attributes.get('content_type') is None or attributes['content_type'].native != 'data' or 'message_digest' not in attributes:
            return _result('MALFORMED', 'Atribut content-type atau message-digest tidak ada.')

        sid = signer_info['sid'].chosen
        certificate = next((cert.chosen for cert in signed_data['certificates']
                            if cert.name == 'certificate' and cert.chosen.issuer == sid['issuer']
                            and cert.chosen.serial_number == sid['serial_number'].native), None)
        if certificate is None:
            return _result('MALFORMED', 'Sertifikat penandatangan tidak ada di CMS.')
        signer = certificate.subject.native.get('common_name')
        fingerprint = hashlib.sha256(certificate.public_key.dump()).hexdigest()
        signing_time = attributes.get('signing_time')
        signed_at = signing_time.native.isoformat() if signing_time is not None and isinstance(signing_time.native, datetime) else None
        details = {'signer': signer, 'fingerprint': fingerprint, 'signed_at': signed_at}

        if attributes['message_digest'].native != content_digest:
            return _result('INVALID', 'Isi dokumen berubah: hash tidak sama dengan messageDigest.', **details)
        certificate_ids = attributes.get('signing_certificate_v2')
        expected_hash = hashlib.sha256(certificate.dump()).digest()
        if certificate_ids is None or not any(entry['cert_hash'].native == expected_hash
                                              and entry['hash_algorithm']['algorithm'].native == 'sha256'
                                              for entry in certificate_ids['certs']):
            return _result('INVALID', 'signingCertificateV2 tidak cocok dengan sertifikat penandatangan.', **details)
        n, e = rsa_numbers(certificate.public_key)
        if n.bit_length() < 2048:
            return _result('INVALID', 'Kunci RSA penandatangan terlalu pendek.', **details)
        signed_hash = hashlib.sha256(signed_attributes_der(signer_info)).digest()
        if not verify_with(n, e, signed_hash, signer_info['signature'].native):
            return _result('INVALID', 'Tanda tangan tidak cocok dengan kunci publik sertifikat.', **details)
        if not verify_chain(certificate.dump(), ca_der):
            return _result('VALID_UNTRUSTED', 'Sertifikat tidak diterbitkan VELTRIX Demo CA atau sudah tidak berlaku.', **details)
        return _result('VALID', None, **details)
    except (ValueError, TypeError, KeyError, AttributeError, IndexError):
        return _result('MALFORMED', 'Struktur CMS tidak dapat dibaca dengan aman.')
