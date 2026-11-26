"""Presentation demo: peel the latest stored evidence object layer by layer.

Read-only: nothing is written to the database and all tampering happens on in-memory copies.
Run from backend/: .venv\\Scripts\\python.exe scripts\\demo_crypto.py --category identity --file PATH
"""
import argparse
import hashlib
import json
import secrets
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Crypto.Cipher import AES, ARC4, DES
from Crypto.Util.Padding import unpad
from sqlalchemy import select
from kyc.config import Settings
from kyc.crypto import DROP, Envelope, IntegrityFailure, canonical, unb64
from kyc.db import database, evidence, objects

sys.stdout.reconfigure(errors='replace')


def show(label, data, count=24):
    print(f'  {label:<33} {data[:count].hex(" ")} ...  ({len(data):,} bytes)')


def step(title):
    try:
        input('\n[Enter] ')
    except EOFError:  # non-interactive run: no pause, and Windows NUL reports isatty() as true
        pass
    print(f'\n=== {title}')


def rejected(envelope, row):
    try:
        envelope.decrypt(row)
    except IntegrityFailure:
        return True
    return False


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--category', choices=['identity', 'document', 'video'], help='default: newest upload of any category')
parser.add_argument('--file', type=Path, help='original file, to compare its SHA-256 with the recovered bytes')
args = parser.parse_args()

settings = Settings.from_env()
envelope = Envelope(settings.kek)
query = select(objects).join(evidence, evidence.c.object_id == objects.c.id).order_by(evidence.c.created_at.desc())
if args.category:
    query = query.where(evidence.c.category == args.category)
with database(settings.database_url).connect() as connection:
    found = connection.execute(query).mappings().first()
if found is None:
    sys.exit('No evidence stored yet. Upload a file through the web application first.')
row = dict(found)
row['ciphertext'], row['wrapped_keys'] = bytes(row['ciphertext']), bytes(row['wrapped_keys'])
header = json.loads(row['header'])

step('1. WHAT THE DATABASE ACTUALLY STORES (table encrypted_objects)')
print(f'  object={row["id"]}\n  category={row["category"]}  version={row["payload_version"]}  suite={header["suite_id"]}')
show('ciphertext', row['ciphertext'])
show('wrapped key bundle', row['wrapped_keys'])
print('  Plaintext columns: IDs, category, DES IV, GCM nonce and tag. Filename and content are not among them.')

step('2. UNWRAP THE PER-OBJECT KEYS WITH THE KEK (kept in server env, not in the database)')
aad = {**Envelope.context(row), 'envelope_version': 1, 'suite_id': header['suite_id'], 'rc4_drop': DROP, 'des_iv': header['des_iv']}
wrapper = AES.new(settings.kek, AES.MODE_GCM, nonce=row['wrap_nonce'], mac_len=16)
wrapper.update(canonical({'purpose': 'key-wrap', **aad}))
bundle = wrapper.decrypt_and_verify(row['wrapped_keys'], row['wrap_tag'])
print(f'  Bundle of {len(bundle)} bytes = RC4 key 32 + DES key 8 + AES key 32 (values deliberately not printed)')

step('3. PEEL THE LAYERS IN REVERSE ORDER: AES-GCM -> DES-CBC -> RC4')
aes = AES.new(bundle[40:], AES.MODE_GCM, nonce=unb64(header['nonce']), mac_len=16)
aes.update(canonical(aad))
after_aes = aes.decrypt_and_verify(row['ciphertext'], unb64(header['tag']))
show('after AES-GCM (tag verified)', after_aes)
after_des = unpad(DES.new(bundle[32:40], DES.MODE_CBC, iv=unb64(header['des_iv'])).decrypt(after_aes), 8)
show('after DES-CBC (still unreadable)', after_des)
packed = ARC4.new(bundle[:32], drop=DROP).decrypt(after_des)
length = struct.unpack('>I', packed[:4])[0]
meta, payload = json.loads(packed[4:4 + length]), packed[4 + length:]
show('after RC4 = ORIGINAL FILE', payload)
print(f'  decrypted private metadata:    filename={meta["filename"]!r}  mime={meta["mime_type"]}')

step('4. IS IT THE EXACT SAME FILE?')
recovered = hashlib.sha256(payload).hexdigest()
print(f'  SHA-256 sealed at upload       {meta["sha256"]}\n  SHA-256 of recovered bytes     {recovered}')
checks = [('sealed hash matches recovered bytes', meta['sha256'] == recovered),
          ('manual peeling equals the application decrypt()', envelope.decrypt(row)[1] == payload)]
if args.file:
    original = hashlib.sha256(args.file.read_bytes()).hexdigest()
    print(f'  SHA-256 of original on disk    {original}')
    checks.append(('recovered bytes match the original file', original == recovered))

step('5. ATTACKS ON IN-MEMORY COPIES: EVERY ONE MUST BE REJECTED')
flipped = bytearray(row['ciphertext'])
flipped[len(flipped) // 2] ^= 1
moved = {**header, 'owner_id': 'attacker-account'}
checks += [('REJECTED: 1 bit flipped in the ciphertext', rejected(envelope, {**row, 'ciphertext': bytes(flipped)})),
           ('REJECTED: reassigned to another owner, header edited to match',
            rejected(envelope, {**row, 'owner_id': 'attacker-account', 'header': canonical(moved).decode()})),
           ('REJECTED: decrypted with the wrong KEK', rejected(Envelope(secrets.token_bytes(32)), row))]

print()
for label, passed in checks:
    print(f'  [{"PASS" if passed else "FAIL"}] {label}')
sys.exit(0 if all(passed for _, passed in checks) else 1)
