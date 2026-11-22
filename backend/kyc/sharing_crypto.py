"""Small cryptographic interface consumed by the Assignment 2 API."""
import base64
import hashlib
import secrets

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

from .crypto import canonical


def public_key_details(pem):
    if not pem.startswith('-----BEGIN PUBLIC KEY-----\n') or not pem.rstrip().endswith('-----END PUBLIC KEY-----'):
        raise ValueError('SPKI public key required')
    key = RSA.import_key(pem)
    if key.has_private() or key.size_in_bits() < 2048 or key.e != 65537:
        raise ValueError('Invalid public key')
    spki = key.export_key(format='DER')
    return key.export_key(format='PEM').decode('ascii'), hashlib.sha256(spki).hexdigest()


def package_key(request_id, key, pem, fingerprint):
    public = RSA.import_key(pem)
    encrypted = PKCS1_OAEP.new(public, hashAlgo=SHA256).encrypt(key)
    body = {'v': 1, 'request_id': request_id, 'alg': 'RSA-OAEP-256',
            'key_fp': fingerprint[:16], 'ek': base64.b64encode(encrypted).decode('ascii')}
    return 'VELTRIX-SHARE-1.' + base64.urlsafe_b64encode(canonical(body)).rstrip(b'=').decode('ascii')


def wrap_key(kek, request_id, owner_id, requester_id, key):
    nonce = secrets.token_bytes(12)
    cipher = AES.new(kek, AES.MODE_GCM, nonce=nonce)
    cipher.update(canonical({'purpose': 'share-key', 'request_id': request_id,
                             'owner_id': owner_id, 'requester_id': requester_id}))
    wrapped, tag = cipher.encrypt_and_digest(key)
    return wrapped, nonce, tag


def unwrap_key(kek, request):
    cipher = AES.new(kek, AES.MODE_GCM, nonce=request['wrap_nonce'])
    cipher.update(canonical({'purpose': 'share-key', 'request_id': request['id'],
                             'owner_id': request['owner_id'], 'requester_id': request['requester_id']}))
    return cipher.decrypt_and_verify(request['wrapped_share_key'], request['wrap_tag'])


def item_aad(request, item_id, kind):
    return canonical({'request_id': request['id'], 'item_id': item_id,
                      'owner_id': request['owner_id'], 'requester_id': request['requester_id'], 'kind': kind})


def encrypt_item(request, item_id, kind, key, plaintext):
    nonce = secrets.token_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(item_aad(request, item_id, kind))
    encrypted, tag = cipher.encrypt_and_digest(plaintext)
    return nonce, encrypted + tag


def decrypt_item(request, item, key):
    if len(key) != 32 or len(item['nonce']) != 12 or len(item['ciphertext']) < 16:
        raise ValueError('Invalid encrypted item')
    cipher = AES.new(key, AES.MODE_GCM, nonce=item['nonce'])
    cipher.update(item_aad(request, item['id'], item['kind']))
    return cipher.decrypt_and_verify(item['ciphertext'][:-16], item['ciphertext'][-16:])
