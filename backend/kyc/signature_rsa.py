"""Assignment 3 (M3-SEC-01): the team's own RSASSA-PKCS1-v1_5 with SHA-256 (RFC 8017 §8.2).

Libraries only parse keys and hash. Encoding, RSASP1 and verification are written here.
Verification is encode-then-compare: the expected block is rebuilt from the hash and compared in
full, so a loose padding parser (Bleichenbacher 2006, e = 3) cannot be fooled.
"""
import hmac
import secrets

from Crypto.PublicKey import RSA

# DER prefix of DigestInfo for SHA-256 (RFC 8017 §9.2, note 1).
DIGEST_INFO_SHA256 = bytes.fromhex('3031300d060960864801650304020105000420')
E = 65537


def i2osp(value, length):
    return value.to_bytes(length, 'big')


def os2ip(data):
    return int.from_bytes(data, 'big')


def emsa_pkcs1_v15_encode(message_hash, k):
    """EM = 0x00 || 0x01 || PS (0xFF...) || 0x00 || DigestInfo || H."""
    if len(message_hash) != 32:
        raise ValueError('SHA-256 hash must be 32 bytes')
    t = DIGEST_INFO_SHA256 + message_hash
    if k < len(t) + 11:
        raise ValueError('Modulus too short')
    return b'\x00\x01' + b'\xff' * (k - len(t) - 3) + b'\x00' + t


def private_params(key):
    """CRT parameters (n, e, d, p, q, dp, dq, qinv) from a parsed private key."""
    n, e, d, p, q = key.n, key.e, key.d, key.p, key.q
    return {'n': n, 'e': e, 'd': d, 'p': p, 'q': q,
            'dp': d % (p - 1), 'dq': d % (q - 1), 'qinv': pow(q, -1, p)}


def rsasp1(m, key):
    """s = m^d mod n with CRT, blinded by a random r so timing does not depend on m."""
    n, e = key['n'], key['e']
    if not 0 <= m < n:
        raise ValueError('Message representative out of range')
    r = 0
    while r < 2:
        r = secrets.randbelow(n)
    blinded = (m * pow(r, e, n)) % n
    s1 = pow(blinded, key['dp'], key['p'])
    s2 = pow(blinded, key['dq'], key['q'])
    h = (key['qinv'] * (s1 - s2)) % key['p']
    return ((s2 + h * key['q']) * pow(r, -1, n)) % n


def rsavp1(s, n, e):
    """m = s^e mod n."""
    if not 0 <= s < n:
        raise ValueError('Signature representative out of range')
    return pow(s, e, n)


def sign_pkcs1_v15(key, message_hash):
    """Signs a SHA-256 hash; the result is verified before it is returned (CRT fault protection)."""
    k = (key['n'].bit_length() + 7) // 8
    em = emsa_pkcs1_v15_encode(message_hash, k)
    m = os2ip(em)
    s = rsasp1(m, key)
    if rsavp1(s, key['n'], key['e']) != m:
        raise ValueError('Signature self-check failed')
    return i2osp(s, k)


def validate_public_key(public_key_pem, min_bits=2048):
    """Returns (n, e) or raises: RSA public key, e = 65537, at least `min_bits`."""
    key = RSA.import_key(public_key_pem)
    if key.has_private() or key.e != E or key.size_in_bits() < min_bits:
        raise ValueError('Unsupported RSA public key')
    return key.n, key.e


def verify_with(n, e, message_hash, signature):
    k = (n.bit_length() + 7) // 8
    if e != E or len(signature) != k:
        return False
    s = os2ip(signature)
    if s >= n:
        return False
    expected = emsa_pkcs1_v15_encode(message_hash, k)
    return hmac.compare_digest(i2osp(rsavp1(s, n, e), k), expected)


def verify_pkcs1_v15(public_key_pem, message_hash, signature):
    """Backend contract: verify RSASSA-PKCS1-v1_5/SHA-256 over an already computed hash."""
    try:
        n, e = validate_public_key(public_key_pem)
        return verify_with(n, e, message_hash, signature)
    except (ValueError, TypeError, IndexError):
        return False
