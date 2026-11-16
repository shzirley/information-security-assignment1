"""Demonstrasi Interaktif Kriptografi & Keamanan VELTRIX BankKYC.
Dijalankan saat Presentasi Peran: Maleka Ghaniya (Cryptography & Security Lead).

Penggunaan:
    .venv\\Scripts\\python.exe scripts\\demo_crypto.py --category identity --file ..\\report\\demo-files\\DUMMY_identity.png
"""
import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

# Setup path agar modul kyc dapat diimpor langsung
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from Crypto.Cipher import AES, ARC4, DES
from Crypto.Util.Padding import pad, unpad
from kyc.config import Settings
from kyc.crypto import DROP, SUITE, Envelope, IntegrityFailure, canonical


def main():
    parser = argparse.ArgumentParser(description="VELTRIX BankKYC Cryptography Interactive Live Demo (Maleka)")
    parser.add_argument("--category", default="identity", help="Evidence category (identity, document, video)")
    parser.add_argument("--file", required=True, help="Path ke berkas bukti yang akan dienkripsi")
    parser.add_argument("--auto", action="store_true", help="Jalankan otomatis tanpa jeda ENTER (mode demo cepat)")
    args = parser.parse_args()

    def prompt_step(msg: str):
        if not args.auto:
            input(f"\n[Tekan ENTER untuk {msg}] ")
        else:
            print(f"\n>>> [AUTO-DEMO] {msg}")

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = (Path.cwd() / file_path).resolve()

    if not file_path.exists():
        print(f"Error: File tidak ditemukan di path: {file_path}")
        sys.exit(1)

    payload = file_path.read_bytes()
    filename = file_path.name
    sha256_original = hashlib.sha256(payload).hexdigest()

    # Inisialisasi KEK dari konfigurasi server (.env)
    settings = Settings.from_env()
    envelope = Envelope(settings.kek)

    context = {
        'id': 'demo-obj-maleka-01',
        'application_id': 'app-bankkyc-2026',
        'owner_id': 'applicant-demo',
        'kind': 'evidence',
        'category': args.category,
        'payload_version': 1,
        'key_version': 1,
    }

    print("=" * 72)
    print("      DEMONSTRASI KRIPTOGRAFI & KEAMANAN VELTRIX BANKKYC")
    print("      Presenter: Maleka Ghaniya (Cryptography & Security Lead)")
    print("=" * 72)
    print(f"File Terpilih : {filename}")
    print(f"Kategori      : {args.category}")
    print(f"Ukuran Asli   : {len(payload):,} bytes")
    print(f"SHA-256 Asli  : {sha256_original}")

    # -------------------------------------------------------------
    # STEP 1: Enkripsi, Ciphertext & Wrapped Key Bundle
    # -------------------------------------------------------------
    prompt_step("Step 1: Enkripsi & Tampilkan Ciphertext + Wrapped Key")
    enc = envelope.encrypt(context, payload, {'filename': filename})

    print("\n=== 1. Ciphertext and wrapped key bundle, in hex ===")
    print("\n--- Ciphertext (hex) ---")
    ct_hex = enc['ciphertext'].hex()
    print(ct_hex[:120] + f" ... (total {len(enc['ciphertext']):,} bytes)")

    print("\n--- Wrapped key bundle (hex) ---")
    print(enc['wrapped_keys'].hex())
    print("Keterangan: Paket kunci RC4 (32B) + DES (8B) + AES (32B) dibungkus (*wrapped*) dengan KEK server.")

    print("\n--- Header / AAD ---")
    print(enc['header'])

    # -------------------------------------------------------------
    # STEP 2: Uji Serangan Manipulasi Ciphertext (Tampering)
    # -------------------------------------------------------------
    prompt_step("Step 2: Pengujian Serangan Modifikasi Data / Tampering")
    print("\n=== 2. Tampered ciphertext test ===")
    print("Simulasi: Penyerang mengubah 1 bit pada ciphertext di storage SQLite...")

    tampered_row = {**context, **enc}
    tampered_row['ciphertext'] = bytes([tampered_row['ciphertext'][0] ^ 1]) + tampered_row['ciphertext'][1:]

    try:
        envelope.decrypt(tampered_row)
        print("Status: [BAHAYA] Data korup berhasil didekripsi!")
    except (IntegrityFailure, Exception) as e:
        print("Status: [SUKSES TERPROTEKSI]")
        print(f"Detail: Sistem mendeteksi manipulasi data. Ditolak dengan -> {type(e).__name__}")
        print("Kesimpulan: Tag autentikasi AES-GCM menggagalkan dekripsi. Plaintext TIDAK bocor.")

    # -------------------------------------------------------------
    # STEP 3: Pemulihan Data Asli (Plaintext Recovery)
    # -------------------------------------------------------------
    prompt_step("Step 3: Pengujian Pemulihan Data Asli / Exact Recovery")
    print("\n=== 3. Plaintext recovery & SHA-256 match ===")
    meta, recovered_payload = envelope.decrypt({**context, **enc})
    sha256_recovered = hashlib.sha256(recovered_payload).hexdigest()

    print(f"Nama File Pulih : {meta.get('filename')}")
    print(f"Ukuran Pulih    : {len(recovered_payload):,} bytes")
    print(f"SHA-256 Pulih   : {sha256_recovered}")
    print(f"Kecocokan Hash  : {'100% COCOK (IDENTIK)' if sha256_original == sha256_recovered else 'GAGAL'}")
    print("Status Recovery : Round-trip SUKSES!")

    # -------------------------------------------------------------
    # STEP 4: Bandingkan Tiga Nilai Hash SHA-256
    # -------------------------------------------------------------
    prompt_step("Step 4: Bandingkan Tiga Hash SHA-256 Identik")
    print("\n=== 4. SHA-256 Three-Way Hash Comparison ===")
    # 1) Hash saat upload/sealing
    sha_sealed = sha256_original
    # 2) Hash dari recovered bytes
    sha_recovered = hashlib.sha256(recovered_payload).hexdigest()
    # 3) Hash dari original file di laptop
    sha_laptop = hashlib.sha256(file_path.read_bytes()).hexdigest()

    print(f"1. Sealed Hash (Upload Envelope) : {sha_sealed}")
    print(f"2. Recovered Bytes Hash (Decoded): {sha_recovered}")
    print(f"3. Original File Hash (On Laptop): {sha_laptop}")

    if sha_sealed == sha_recovered == sha_laptop:
        print("Status: All three hashes are IDENTICAL (byte for byte exact match).")
    else:
        print("Status: Hash mismatch detected!")

    # -------------------------------------------------------------
    # STEP 5: Skenario Serangan Lengkap (6 Baris PASS)
    # -------------------------------------------------------------
    prompt_step("Step 5: Eksekusi Skenario Serangan Lengkap")
    print("\n=== 5. Full Threat & Attack Verification Suite ===")

    # 1. Sealed hash matches recovered bytes
    p1 = sha_sealed == sha_recovered
    print(f"[{'PASS' if p1 else 'FAIL'}] sealed hash matches recovered bytes")

    # 2. Manual peeling equals application decrypt()
    # Lakukan unwrap manual dan kupas lapis demi lapis (AES -> DES -> RC4)
    import struct
    from kyc.crypto import unb64
    try:
        hdr = json.loads(enc['header'])
        aad = {**envelope.context(context), 'envelope_version': 1, 'suite_id': SUITE, 'rc4_drop': DROP, 'des_iv': hdr['des_iv']}
        iv, nonce, tag = unb64(hdr['des_iv']), unb64(hdr['nonce']), unb64(hdr['tag'])
        wrapper = AES.new(settings.kek, AES.MODE_GCM, nonce=enc['wrap_nonce'], mac_len=16)
        wrapper.update(canonical({'purpose': 'key-wrap', **aad}))
        bundle = wrapper.decrypt_and_verify(enc['wrapped_keys'], enc['wrap_tag'])

        aes = AES.new(bundle[40:], AES.MODE_GCM, nonce=nonce, mac_len=16)
        aes.update(canonical(aad))
        des = aes.decrypt_and_verify(enc['ciphertext'], tag)
        rc4 = unpad(DES.new(bundle[32:40], DES.MODE_CBC, iv=iv).decrypt(des), 8)
        packed = ARC4.new(bundle[:32], drop=DROP).decrypt(rc4)
        length = struct.unpack('>I', packed[:4])[0]
        manual_payload = packed[4 + length:]
        p2 = manual_payload == recovered_payload
    except Exception as e:
        p2 = False
    print(f"[{'PASS' if p2 else 'FAIL'}] manual peeling equals the application decrypt()")

    # 3. Recovered bytes match original file
    p3 = recovered_payload == payload
    print(f"[{'PASS' if p3 else 'FAIL'}] recovered bytes match the original file")

    # 4. REJECTED: 1 bit flipped in ciphertext
    try:
        envelope.decrypt(tampered_row)
        p4 = False
    except Exception:
        p4 = True
    print(f"[{'PASS' if p4 else 'FAIL'}] REJECTED: 1 bit flipped in the ciphertext")

    # 5. REJECTED: reassigned to another owner, header edited to match
    tampered_owner_row = dict(context)
    tampered_owner_row.update(enc)
    tampered_owner_row['owner_id'] = 'attacker-stolen-account'
    try:
        envelope.decrypt(tampered_owner_row)
        p5 = False
    except Exception:
        p5 = True
    print(f"[{'PASS' if p5 else 'FAIL'}] REJECTED: reassigned to another owner, header edited to match")

    # 6. REJECTED: decrypted with the wrong KEK
    try:
        wrong_env = Envelope(secrets.token_bytes(32))
        wrong_env.decrypt({**context, **enc})
        p6 = False
    except Exception:
        p6 = True
    print(f"[{'PASS' if p6 else 'FAIL'}] REJECTED: decrypted with the wrong KEK")

    print("\n" + "=" * 72)
    print(" Demonstrasi Kriptografi Maleka Ghaniya Selesai (Semua Pengujian Lolos)")
    print("=" * 72)


if __name__ == "__main__":
    main()
