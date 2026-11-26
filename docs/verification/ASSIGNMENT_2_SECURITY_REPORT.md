# Laporan Keamanan & Verifikasi — Assignment 2: Key Management

> **Proyek:** VELTRIX BankKYC  
> **Kontributor:** Maleka Ghaniya (Cryptography & Security Lead) — integrasi atas Backend API Jahhaza  
> **Tanggal Verifikasi:** 22 November 2026  
> **Lingkup:** Enkripsi Hibrida (RSA-OAEP-256 + AES-256-GCM), Distribusi Kunci *Out-of-Band* (email), Penyimpanan Kunci Aman (*Key Wrapping*), dan Pratinjau In-Memory di Sisi Klien.

---

## 1. Arsitektur Kriptografi Hibrida (Hybrid Encryption)

Assignment 2 menambahkan mekanisme **berbagi data privat antar-pengguna** tanpa mengorbankan kerahasiaan data maupun keamanan kanal distribusi kunci.

| Lapisan | Algoritma | Peran & Lokasi Eksekusi |
|---|---|---|
| **Identitas Kunci Klien** | **RSA-2048 (SPKI / PKCS#8)** | Pasangan kunci dibuat di browser pemohon via **Web Crypto API** (`frontend/src/lib/sharing-crypto.ts`). Hanya *Public Key* yang dikirim ke server (`PUT /api/v1/keys/me`); *Private Key* tetap berada di sisi klien. |
| **Enkripsi Data Terbagi** | **AES-256-GCM + AAD** | Saat pemilik menyetujui permintaan, server membuat kunci simetris acak 32 byte (`share_key`) lalu mengenkripsi setiap salinan item (profil, KTP, formulir, KK, video) dengan AAD yang mengikat `request_id`, `item_id`, `owner_id`, `requester_id`, dan `kind`. |
| **Distribusi Kunci (Out-of-Band)** | **RSA-OAEP-256 (SHA-256)** | Kunci simetris 32 byte dienkripsi menggunakan *Public Key* pemohon menjadi paket teks `VELTRIX-SHARE-1.<base64url>`. Paket ini disalin dan dikirim lewat email. |
| **Penyimpanan Kunci di Sistem** | **AES-256-GCM Key Wrapping (KEK)** | Di tabel `share_requests`, `share_key` tidak pernah disimpan sebagai *plaintext*, melainkan dibungkus dengan Master KEK server (`VELTRIX_KEK_V1_BASE64`) bersama nonce 12-byte, tag 16-byte, dan AAD. |
| **Dekripsi & Pratinjau Klien** | **Web Crypto RSA-OAEP-256 + Blob URL** | Pemohon menempelkan paket dari email di browser, mendekripsi `share_key` secara lokal memakai *Private Key*, lalu menampilkan gambar/PDF/video/profil secara *in-memory* (Blob URL langsung dicabut saat modal ditutup). |

---

## 2. Analisis Keamanan Distribusi Out-of-Band (Threat Model)

1. **Penyadapan Kanal Publik (Email Eavesdropping):**
   * Meskipun penyerang (*Eve*) berhasil menyalin paket `VELTRIX-SHARE-1...` dari email, *Eve* tidak memiliki *Private Key* RSA milik pemohon sehingga operasi dekripsi RSA-OAEP-256 gagal secara matematis (`ValueError` / `OperationError`).
2. **Modifikasi Paket di Jalur Transmisi (Tampering / Bit-Flip):**
   * Perubahan 1 bit saja pada payload `ek` (*encrypted key*) menyebabkan verifikasi padding OAEP-SHA256 gagal dan langsung ditolak sebelum kunci simetris terbentuk.
3. **Serangan Substitusi Lintas Item (Cross-Item Substitution di Database):**
   * Karena setiap baris `share_items` diikat dengan AAD (`request_id`, `item_id`, `owner_id`, `requester_id`, `kind`), menukar ciphertext KTP ke baris profil akan gagal diverifikasi oleh tag autentikasi AES-256-GCM (`403 SHARE_OPEN_DENIED`).
4. **Kebocoran Database (*Data at Rest*):**
   * Baik isi dokumen (`share_items.ciphertext`) maupun kunci simetris (`share_requests.wrapped_share_key`) tersimpan dalam bentuk terenkripsi. Tanpa KEK server yang berada di luar database, kunci simetris tidak dapat diekstrak dari file SQLite/MySQL.
5. **Pencabutan Akses & Kedaluwarsa (*Crypto-Shredding*):**
   * Saat pemilik menekan **Cabut Akses (Revoke)** atau masa berlaku 7 hari berakhir, server menghapus seluruh baris `share_items` dan mengosongkan `wrapped_share_key` (`NULL`), sehingga kunci lama tidak lagi dapat digunakan (`403 SHARE_OPEN_DENIED`).

---

## 3. Hasil Verifikasi & Pengujian Aktual

### A. Automated Security & Integration Suite (`pytest`)
Perintah:
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v --basetemp=temp_pytest tests/test_sharing_api.py tests/test_assignment2_security.py
```

| Test Case | Skenario Uji | Hasil |
|---|---|---|
| `test_profile_share_open_rotate_revoke_and_scope` | Siklus penuh request, approve, open, rotasi kunci, revoke, dan pembatasan peran | **PASSED** |
| `test_request_validation_and_expiry_shreds_copy` | Validasi input, penolakan self-share/non-applicant, pembatalan | **PASSED** |
| `test_expiry_persists_and_removes_wrapped_key` | Kedaluwarsa otomatis menghapus item dan `wrapped_share_key` | **PASSED** |
| `test_upgrade_from_existing_0002_keeps_user` | Migrasi Alembic `0002` → `0003` mempertahankan akun & data lama | **PASSED** |
| `test_oob_eavesdropper_cannot_decrypt_package` | Penyadap (*Eve*) dengan Private Key lain gagal mendekripsi paket kunci | **PASSED** |
| `test_oob_package_tampering_rejected_by_rsa_oaep` | Modifikasi 1 bit pada `ek` ditolak oleh RSA-OAEP-256 | **PASSED** |
| `test_at_rest_key_wrapping_and_zero_plaintext_audit` | Audit DB: `wrapped_share_key != raw_key` & nol plaintext PII di `share_items` | **PASSED** |
| `test_cross_item_aad_substitution_attack_rejected` | Penukaran ciphertext antar-item ditolak oleh AES-GCM AAD (`403`) | **PASSED** |
| `test_key_rotation_invalidates_old_private_key_on_reissued_package` | Rotasi kunci RSA membuat Private Key lama tidak bisa membuka paket baru | **PASSED** |
| `test_draft_case_can_be_shared` | Pengajuan yang masih draf bisa dibagikan (ketua dan bendahara saling cek sebelum mengirim) | **PASSED** |
| `test_active_key_index_is_sqlite_only` | Indeks "satu kunci aktif per user" hanya dibuat di SQLite, agar rotasi kunci tetap jalan di MySQL | **PASSED** |

**Ringkasan (26 November 2026):** **11 passed, 0 failed**. Seluruh tes backend (Assignment 1 + 2): **114 passed**.

### B. Simulasi End-to-End CLI (`scripts/demo_assignment2_sharing.py`)
Perintah:
```powershell
cd backend
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe scripts/demo_assignment2_sharing.py
```
Seluruh 6 tahap simulasi (Registrasi & Keypair RSA → Request Akses → Approve & Generate Paket `VELTRIX-SHARE-1` → Simulasi Serangan Penyadapan & Tampering di email → Dekripsi & Verifikasi SHA-256 100% Identik → Revoke & Data Shredding) **BERHASIL (Exit Code 0)**.

### C. Verifikasi Frontend Next.js
* `npm.cmd run typecheck` (`tsc --noEmit`): **PASSED (0 errors)**.
* Halaman baru: `/applicant/sharing` (`frontend/src/features/kyc/sharing-workspace.tsx`) + modul Web Crypto (`frontend/src/lib/sharing-crypto.ts`).
* Alur lengkap E01–E10 di browser sungguhan, beserta screenshot: [VERIFICATION.md](../assignment-2/VERIFICATION.md).
