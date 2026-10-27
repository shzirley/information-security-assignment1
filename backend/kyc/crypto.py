"""Versioned authenticated envelope. RC4/DES layers are academic only."""
import base64
import hashlib
import hmac
import json
import secrets
import struct
from Crypto.Cipher import AES, DES, ARC4
from Crypto.Util.Padding import pad, unpad

SUITE = 'vtx-kyc-layered-v1'
DROP = 3072

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')

def b64(value):
    return base64.b64encode(value).decode('ascii')

def unb64(value):
    return base64.b64decode(value, validate=True)

class IntegrityFailure(Exception):
    pass

class Envelope:
    def __init__(self, kek):
        self.kek = kek

    @staticmethod
    def context(row):
        return {key: row[key] for key in ('id', 'application_id', 'owner_id', 'kind', 'category', 'payload_version', 'key_version')}

    def encrypt(self, context, payload, private):
        metadata = canonical({**private, 'length': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
        if len(metadata) > 16384:
            raise ValueError('Private metadata exceeds limit')
        packed = struct.pack('>I', len(metadata)) + metadata + payload
        rc4_key, des_key, aes_key = secrets.token_bytes(32), secrets.token_bytes(8), secrets.token_bytes(32)
        des_iv, nonce = secrets.token_bytes(8), secrets.token_bytes(12)
        aad = {**context, 'envelope_version': 1, 'suite_id': SUITE, 'rc4_drop': DROP, 'des_iv': b64(des_iv)}
        rc4 = ARC4.new(rc4_key, drop=DROP).encrypt(packed)
        des = DES.new(des_key, DES.MODE_CBC, iv=des_iv).encrypt(pad(rc4, 8))
        aes = AES.new(aes_key, AES.MODE_GCM, nonce=nonce, mac_len=16)
        aes.update(canonical(aad))
        ciphertext, tag = aes.encrypt_and_digest(des)
        wrap_nonce = secrets.token_bytes(12)
        wrapper = AES.new(self.kek, AES.MODE_GCM, nonce=wrap_nonce, mac_len=16)
        wrapper.update(canonical({'purpose': 'key-wrap', **aad}))
        wrapped, wrap_tag = wrapper.encrypt_and_digest(rc4_key + des_key + aes_key)
        return dict(ciphertext=ciphertext, header=canonical({**aad, 'nonce': b64(nonce), 'tag': b64(tag)}).decode(),
                    wrapped_keys=wrapped, wrap_nonce=wrap_nonce, wrap_tag=wrap_tag)

    def decrypt(self, row):
        try:
            if len(row['header']) > 4096 or row['key_version'] != 1:
                raise ValueError()
            header = json.loads(row['header'])
            aad = {**self.context(row), 'envelope_version': 1, 'suite_id': SUITE, 'rc4_drop': DROP, 'des_iv': header['des_iv']}
            if set(header) != set(aad) | {'nonce', 'tag'} or any(header[k] != v for k, v in aad.items()):
                raise ValueError()
            iv, nonce, tag = unb64(header['des_iv']), unb64(header['nonce']), unb64(header['tag'])
            if (len(iv), len(nonce), len(tag), len(row['wrap_nonce']), len(row['wrap_tag']), len(row['wrapped_keys'])) != (8, 12, 16, 12, 16, 72):
                raise ValueError()
            wrapper = AES.new(self.kek, AES.MODE_GCM, nonce=row['wrap_nonce'], mac_len=16)
            wrapper.update(canonical({'purpose': 'key-wrap', **aad}))
            bundle = wrapper.decrypt_and_verify(row['wrapped_keys'], row['wrap_tag'])
            aes = AES.new(bundle[40:], AES.MODE_GCM, nonce=nonce, mac_len=16)
            aes.update(canonical(aad))
            des = aes.decrypt_and_verify(row['ciphertext'], tag)
            rc4 = unpad(DES.new(bundle[32:40], DES.MODE_CBC, iv=iv).decrypt(des), 8)
            packed = ARC4.new(bundle[:32], drop=DROP).decrypt(rc4)
            if len(packed) < 4:
                raise ValueError()
            length = struct.unpack('>I', packed[:4])[0]
            if length > 16384 or length > len(packed) - 4:
                raise ValueError()
            meta = json.loads(packed[4:4+length])
            payload = packed[4+length:]
            if meta['length'] != len(payload) or not hmac.compare_digest(meta['sha256'], hashlib.sha256(payload).hexdigest()):
                raise ValueError()
            return meta, payload
        except (ValueError, KeyError, TypeError, UnicodeError, struct.error) as exc:
            raise IntegrityFailure('Encrypted object cannot be recovered') from exc
