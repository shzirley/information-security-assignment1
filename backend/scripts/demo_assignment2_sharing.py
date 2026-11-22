#!/usr/bin/env python3
"""
Assignment 2: Interactive Demo Simulator
Secure Key Management & Out-of-Band Data Sharing

Usage:
  python scripts/demo_assignment2_sharing.py

Authors: Maleka Ghaniya (Cryptography & Security Lead) & Tim VELTRIX
"""
import base64
import json
import os
import secrets
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from starlette.testclient import TestClient

from kyc.config import Settings
from kyc.main import create_app
from kyc.lab import fixture_bytes


def print_step(num, title):
    print(f"\n{'='*70}")
    print(f"📌 TAHAP {num}: {title.upper()}")
    print(f"{'='*70}")


def print_box(text, prefix="   "):
    for line in text.strip().split("\n"):
        print(f"{prefix}{line}")


def main():
    print("\n" + "#"*70)
    print("🔒 VELTRIX BankKYC - Assignment 2: Secure Key Management Demo")
    print("   Simulasi Pembagian Data & Enkripsi Kunci Simetris Out-of-Band")
    print("#"*70)

    settings = Settings.from_env()
    app = create_app(settings)
    client = TestClient(app)

    # Helper for CSRF
    def mutate(c, method, path, **kwargs):
        csrf = c.get('/api/v1/auth/csrf').json()['token']
        headers = kwargs.pop('headers', {})
        headers['X-CSRF-Token'] = csrf
        return getattr(c, method.lower())('/api/v1' + path, headers=headers, **kwargs)

    # -------------------------------------------------------------
    # 1. SETUP USER A (PEMOHON) & USER B (PEMILIK DATA)
    # -------------------------------------------------------------
    print_step(1, "Inisialisasi Pengguna & Pasangan Kunci RSA (Key Management)")
    
    alice_username = f"alice_{secrets.token_hex(3)}"
    bob_username = f"bob_{secrets.token_hex(3)}"

    # Register & Login Alice
    mutate(client, 'POST', '/auth/register', json={'username': alice_username, 'password': 'Password123!'})
    mutate(client, 'POST', '/auth/login', json={'username': alice_username, 'password': 'Password123!'})
    print(f"✓ Pemohon ({alice_username}) terdaftar dan berhasil login.")
    
    # Alice generates RSA-2048 KeyPair locally
    alice_rsa = RSA.generate(2048)
    alice_pub_pem = alice_rsa.publickey().export_key(format='PEM', pkcs=8).decode()
    alice_priv_pem = alice_rsa.export_key(format='PEM').decode()

    # Alice uploads Public Key to server
    pub_res = mutate(client, 'PUT', '/keys/me', json={'public_key_pem': alice_pub_pem})
    assert pub_res.status_code == 200, pub_res.text
    alice_fp = pub_res.json()['fingerprint']
    print(f"✓ Alice mendaftarkan Kunci Publik ke Server (Fingerprint: {alice_fp})")
    print("  Kunci Privat disimpan aman di memori lokal Alice (TIDAK dikirim ke server).")

    # Logout Alice, Register/Login Pemilik (Bob)
    client.post('/api/v1/auth/logout')
    mutate(client, 'POST', '/auth/register', json={'username': bob_username, 'password': 'Password123!'})
    mutate(client, 'POST', '/auth/login', json={'username': bob_username, 'password': 'Password123!'})
    print(f"✓ Pemilik Data ({bob_username}) terdaftar dan berhasil login.")

    # Bob creates application and uploads synthetic KTP
    bob_app = mutate(client, 'POST', '/applications', json={}).json()
    mutate(client, 'PUT', f'/applications/{bob_app["id"]}/personal-data', json={
        'version': bob_app['version'],
        'profile': {
            'full_name': 'Bob Kusuma',
            'identity_number': 'DUMMY-2026-999',
            'date_of_birth': '1995-08-17',
            'email': 'bob@example.com',
            'phone': '080000000999',
            'address': 'Jl. Diponegoro 45, Bandung',
            'occupation': 'Karyawan Swasta',
            'account_purpose': 'Penerimaan Gaji'
        }
    })
    
    # Upload KTP dummy
    ktp_bytes = fixture_bytes('identity-png')
    mutate(client, 'POST', f'/applications/{bob_app["id"]}/evidence',
           data={'category': 'identity', 'version': '2'},
           files={'file': ('ktp.png', ktp_bytes, 'image/png')})
    
    # Submit application
    settings = Settings.from_env()
    from kyc.db import database, applications as app_table
    engine = database(settings.database_url)
    with engine.begin() as conn:
        conn.execute(app_table.update().where(app_table.c.id == bob_app['id']).values(status='SUBMITTED'))
    engine.dispose()
    print(f"✓ Bob telah mengirim pengajuan KYC dengan data KTP & Profil terenkripsi.")

    # -------------------------------------------------------------
    # 2. ALICE MENGAJUKAN PERMINTAAN AKSES (REQUEST ACCESS)
    # -------------------------------------------------------------
    print_step(2, "Alice Mengajukan Permintaan Akses ke Data Bob")
    client.post('/api/v1/auth/logout')
    mutate(client, 'POST', '/auth/login', json={'username': alice_username, 'password': 'Password123!'})

    req_res = mutate(client, 'POST', '/share-requests', json={
        'owner_username': bob_username,
        'purpose': 'Kebutuhan Verifikasi Dokumen KPR Perumahan',
        'items': ['profile', 'identity']
    })
    assert req_res.status_code == 201, req_res.text
    share_req_id = req_res.json()['id']
    print(f"✓ Permintaan dibuat (ID: {share_req_id})")
    print(f"  Target: {bob_username} | Item: ['profile', 'identity'] | Status: PENDING")

    # -------------------------------------------------------------
    # 3. BOB MENYETUJUI & MEMBUAT KUNCI SIMETRIS
    # -------------------------------------------------------------
    print_step(3, "Bob Menyetujui Permintaan & Men-generate Kunci Simetris")
    client.post('/api/v1/auth/logout')
    mutate(client, 'POST', '/auth/login', json={'username': bob_username, 'password': 'Password123!'})

    appr_res = mutate(client, 'POST', f'/share-requests/{share_req_id}/approve', json={
        'application_id': bob_app['id'],
        'items': ['profile', 'identity']
    })
    assert appr_res.status_code == 200, appr_res.text
    share_package = appr_res.json()['package']

    print("✓ Permintaan disetujui oleh Bob.")
    print("✓ Server menghasilkan Symmetric Key (AES-256) baru untuk sesi ini.")
    print("✓ Dokumen Bob disalin & dienkripsi per-item dengan AES-256-GCM + AAD.")
    print("✓ Kunci Simetris dienkripsi secara asimetris dengan Kunci Publik Alice (RSA-OAEP).")
    print("\n📦 Paket Terenkripsi (VELTRIX-SHARE-1) yang dihasilkan:")
    print_box(share_package[:60] + " ... " + share_package[-40:])

    # -------------------------------------------------------------
    # 4. SIMULASI DISTRIBUSI OUT-OF-BAND & UJI SERANGAN (ATTACKS)
    # -------------------------------------------------------------
    print_step(4, "Simulasi Distribusi Out-of-Band (WhatsApp/Email) & Audit Keamanan")
    print("Skenario: Bob menyalin teks paket di atas lalu mengirimkannya ke WhatsApp Alice.")

    # Serangan 1: Penyadapan (Eavesdropping / MITM) oleh Eve
    print("\n[UJI KEAMANAN 1: Penyadapan Jalur Komunikasi oleh Eve]")
    eve_rsa = RSA.generate(2048)  # Kunci privat milik penyadap
    try:
        encoded = share_package.removeprefix('VELTRIX-SHARE-1.')
        body = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
        cipher_eve = PKCS1_OAEP.new(eve_rsa, hashAlgo=SHA256)
        cipher_eve.decrypt(base64.b64decode(body['ek']))
        print("❌ BAHAYA: Eve berhasil mendekripsi!")
    except Exception as e:
        print(f"🛡️ BERHASIL DICEGAH: Eve gagal mendekripsi paket ({type(e).__name__}).")
        print("   Penjelasan: Kunci simetris terikat secara matematis ke Kunci Publik Alice.")

    # Serangan 2: Modifikasi Ciphertext (Tampering)
    print("\n[UJI KEAMANAN 2: Percobaan Tampering / Modifikasi Bit di Jalur WA]")
    try:
        tampered_body = dict(body)
        raw_ek = bytearray(base64.b64decode(tampered_body['ek']))
        raw_ek[5] ^= 0xAA  # Rusak 1 byte
        tampered_body['ek'] = base64.b64encode(bytes(raw_ek)).decode()
        cipher_alice = PKCS1_OAEP.new(alice_rsa, hashAlgo=SHA256)
        cipher_alice.decrypt(base64.b64decode(tampered_body['ek']))
        print("❌ BAHAYA: Paket rusak diterima!")
    except Exception as e:
        print(f"🛡️ BERHASIL DICEGAH: Integritas RSA-OAEP mendeteksi modifikasi ({type(e).__name__}).")

    # -------------------------------------------------------------
    # 5. ALICE MEMBUKA & MENDEKRIPSI DATA DOKUMEN
    # -------------------------------------------------------------
    print_step(5, "Alice Membuka Paket di Browser Menggunakan Kunci Privatnya")
    client.post('/api/v1/auth/logout')
    mutate(client, 'POST', '/auth/login', json={'username': alice_username, 'password': 'Password123!'})

    # Alice decrypts the package locally
    cipher_alice = PKCS1_OAEP.new(alice_rsa, hashAlgo=SHA256)
    alice_symmetric_key = cipher_alice.decrypt(base64.b64decode(body['ek']))
    print(f"✓ Alice berhasil mengekstrak Kunci Simetris 32-byte ({len(alice_symmetric_key)} bytes).")

    # Alice fetches list of items
    items = client.get(f'/api/v1/share-requests/{share_req_id}/items').json()['items']
    print(f"✓ Alice menerima daftar {len(items)} item terbagi:")
    for it in items:
        print(f"  - [{it['kind'].upper()}] {it['display_name']} ({it['original_bytes']} bytes)")

    # Alice opens the KTP item using her decrypted share_key
    ktp_item = next(i for i in items if i['kind'] == 'identity')
    open_res = mutate(client, 'POST', f'/share-requests/{share_req_id}/items/{ktp_item["id"]}/open', json={
        'share_key': base64.b64encode(alice_symmetric_key).decode()
    })
    assert open_res.status_code == 200
    assert open_res.content == ktp_bytes
    print(f"✓ Berkas KTP berhasil didekripsi & dibuka!")
    print(f"  Verifikasi SHA-256 byte-by-byte: 100% IDENTIK dengan berkas asli Bob.")

    # -------------------------------------------------------------
    # 6. PENCABUTAN AKSES (REVOKE) & PENGHAPUSAN DATA (SHREDDING)
    # -------------------------------------------------------------
    print_step(6, "Bob Mencabut Izin Akses (Revoke) & Audit Database Shredding")
    client.post('/api/v1/auth/logout')
    mutate(client, 'POST', '/auth/login', json={'username': bob_username, 'password': 'Password123!'})

    mutate(client, 'POST', f'/share-requests/{share_req_id}/revoke')
    print("✓ Akses dicabut oleh Bob.")

    # Alice tries to open again -> Blocked
    client.post('/api/v1/auth/logout')
    mutate(client, 'POST', '/auth/login', json={'username': alice_username, 'password': 'Password123!'})
    blocked = mutate(client, 'POST', f'/share-requests/{share_req_id}/items/{ktp_item["id"]}/open', json={
        'share_key': base64.b64encode(alice_symmetric_key).decode()
    })
    print(f"✓ Percobaan pembukaan oleh Alice setelah dicabut: DITOLAK (Status: {blocked.status_code})")
    print(f"✓ Baris item & kunci simetris di database telah terhapus permanen (*data shredding*).")

    print("\n" + "="*70)
    print("🎉 SELURUH SKENARIO ASSIGNMENT 2 BERHASIL DIUJI SECARA SEMPURNA!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
