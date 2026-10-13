"""Academic ciphers. RC4/DES are included for comparison, not production use."""
import hashlib
import hmac
import json
import secrets
import struct
from time import perf_counter_ns
from Crypto.Cipher import AES, DES, ARC4
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.Util.Padding import pad, unpad

ALGORITHMS = ('AES', 'RC4', 'DES')
ARC4_DROP = 3072

class IntegrityError(Exception):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

class Crypto:
    def __init__(self, master):
        self.master = master

    def prepare(self, algorithm, item_id):
        header = {'format': 'veltrix-v1', 'key_version': 1, 'algorithm': algorithm,
                  'item_id': item_id, 'salt': secrets.token_bytes(32).hex(),
                  'iv': secrets.token_bytes(16 if algorithm == 'AES' else 8).hex() if algorithm != 'RC4' else '',
                  'drop': ARC4_DROP if algorithm == 'RC4' else 0}
        return header, *self.keys(header)

    def keys(self, header):
        algorithm = header['algorithm']
        salt = bytes.fromhex(header['salt'])
        context = f"veltrix-v1:{header['item_id']}:{algorithm}:".encode()
        key = HKDF(self.master, 8 if algorithm == 'DES' else 32, salt, SHA256, context=context + b'encryption')
        mac_key = HKDF(self.master, 32, salt, SHA256, context=context + b'authentication')
        return key, mac_key

    @staticmethod
    def encrypt_core(data, header, key):
        algorithm = header['algorithm']
        if algorithm == 'RC4':
            return ARC4.new(key, drop=ARC4_DROP).encrypt(data)
        cipher = AES if algorithm == 'AES' else DES
        return cipher.new(key, cipher.MODE_CBC, bytes.fromhex(header['iv'])).encrypt(pad(data, cipher.block_size))

    @staticmethod
    def decrypt_core(data, header, key):
        algorithm = header['algorithm']
        if algorithm == 'RC4':
            return ARC4.new(key, drop=ARC4_DROP).decrypt(data)
        cipher = AES if algorithm == 'AES' else DES
        return unpad(cipher.new(key, cipher.MODE_CBC, bytes.fromhex(header['iv'])).decrypt(data), cipher.block_size)

    @staticmethod
    def seal(ciphertext, header, mac_key):
        encoded = canonical(header)
        body = struct.pack('>I', len(encoded)) + encoded + ciphertext
        return body + hmac.digest(mac_key, body, 'sha256')

    def inspect(self, envelope, expected_id, expected_algorithm):
        try:
            length = struct.unpack('>I', envelope[:4])[0]
            if not 1 <= length <= 4096 or len(envelope) < 4 + length + 32:
                raise ValueError()
            header = json.loads(envelope[4:4+length])
            if (header['item_id'] != expected_id or header['algorithm'] != expected_algorithm
                    or header['format'] != 'veltrix-v1' or header['key_version'] != 1
                    or header['drop'] != (ARC4_DROP if expected_algorithm == 'RC4' else 0)):
                raise ValueError()
            key, mac_key = self.keys(header)
            if not hmac.compare_digest(hmac.digest(mac_key, envelope[:-32], 'sha256'), envelope[-32:]):
                raise ValueError()
            return header, key, envelope[4+length:-32]
        except (ValueError, KeyError, TypeError, struct.error, UnicodeError) as exc:
            raise IntegrityError('Encrypted data failed integrity verification') from exc

    def encrypt(self, data, algorithm, item_id):
        header, key, mac_key = self.prepare(algorithm, item_id)
        return self.seal(self.encrypt_core(data, header, key), header, mac_key)

    def decrypt(self, envelope, algorithm, item_id):
        header, key, ciphertext = self.inspect(envelope, item_id, algorithm)
        try:
            return self.decrypt_core(ciphertext, header, key)
        except ValueError as exc:
            raise IntegrityError('Invalid encrypted payload') from exc

    @staticmethod
    def version(envelope, algorithm):
        length = struct.unpack('>I', envelope[:4])[0]
        ciphertext = envelope[4+length:-32]
        return {'algorithm': algorithm, 'mode': None if algorithm == 'RC4' else 'CBC',
                'ciphertext_bytes': len(ciphertext), 'stored_bytes': len(envelope),
                'ciphertext_sample_hex': ciphertext[:32].hex()}

    def sample(self, data, algorithm, item_id, repetition):
        header, key, mac_key = self.prepare(algorithm, item_id)
        start = perf_counter_ns()
        ciphertext = self.encrypt_core(data, header, key)
        encrypt_ns = perf_counter_ns() - start
        start = perf_counter_ns()
        envelope = self.seal(ciphertext, header, mac_key)
        checked_header, checked_key, checked_ciphertext = self.inspect(envelope, item_id, algorithm)
        integrity_ns = perf_counter_ns() - start
        start = perf_counter_ns()
        plaintext = self.decrypt_core(checked_ciphertext, checked_header, checked_key)
        decrypt_ns = perf_counter_ns() - start
        start = perf_counter_ns()
        correct = hmac.compare_digest(data, plaintext)
        correctness_ns = perf_counter_ns() - start
        return {'algorithm': algorithm, 'repetition': repetition, 'encrypt_ns': encrypt_ns,
                'decrypt_ns': decrypt_ns, 'integrity_ns': integrity_ns, 'correctness_ns': correctness_ns,
                'ciphertext_bytes': len(ciphertext), 'stored_bytes': len(envelope), 'round_trip_ok': correct}
