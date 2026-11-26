# VELTRIX BankKYC — Assignment 2 E2E Verification & Storage Audit Report (J-QA-02 & J-QA-03)

**Tanggal Pengujian:** 24 November 2026  
**Pelaksana Pengujian:** Jorell (QA, Demo Fixtures & Forensic Audit Lead)  
**Lingkungan Uji:** Local Test & Automated Runner (`backend/scripts/verify_e2e_scenarios.py`)  
**Basis Data:** SQLite (`backend/data/bankkyc.db`) – Skema Head `0003_data_sharing`  
**Status Keseluruhan:** **10/10 SCENARIOS PASSED (100% SUCCESS)**

---

## 1. Ringkasan Eksekutif Hasil Uji Skenario E01–E10

Pengujian dilakukan untuk membuktikan integritas, kerahasiaan, otorisasi, dan mekanisme *crypto-shredding* dalam fitur **Key Management & Document Sharing** pada VELTRIX BankKYC. Skenario bisnis mengacu pada pembukaan rekening organisasi mahasiswa (**HIMA Informatika**), di mana **Andi** (Ketua HIMA) membutuhkan dokumen KYC milik **Budi** (Bendahara HIMA) sebagai co-signer, dan **Citra** bertindak sebagai pihak ketiga tanpa otorisasi.

| Skenario | Deskripsi Uji | Target Aktor | Hasil Pengamatan | Status |
|:---|:---|:---|:---|:---:|
| **E01** | Pembuatan pasangan kunci RSA-OAEP 2048-bit & registrasi public key | Andi & Budi | Fingerprint terhitung konsisten, private key tidak pernah menyentuh server | **PASSED** |
| **E02** | Verifikasi pengajuan dokumen pemilik data | Budi | Profil, KTP, dan Formulir Rekening tersimpan terenkripsi dengan status `SUBMITTED` | **PASSED** |
| **E03** | Pengajuan permintaan akses dokumen oleh peminta | Andi | Request ID diterbitkan, status awal `PENDING` dengan alasan jelas | **PASSED** |
| **E04** | Verifikasi sidik jari kunci peminta oleh pemilik data | Budi & Andi | Sidik jari Andi dicocokkan (8e070b7c956aeafe), status berubah menjadi `APPROVED` | **PASSED** |
| **E05** | Pembuatan dan pengiriman paket out-of-band (email) | Budi | Paket terenkripsi RSA-OAEP diterbitkan dengan prefix `VELTRIX-SHARE-1.` | **PASSED** |
| **E06** | Dekripsi paket lokal & pembukaan dokumen terenkripsi | Andi | Kunci simetris terdekripsi di sisi klien, dokumen identik byte-demi-byte (SHA-256 cocok) | **PASSED** |
| **E07** | Percobaan pembukaan dokumen oleh pihak ketiga yang tidak berhak | Citra | Dekripsi lokal gagal secara matematis; API menolak dengan `403 SHARE_OPEN_DENIED` | **PASSED** |
| **E08** | Pencabutan hak akses (*Revocation*) oleh pemilik data | Budi & Andi | Status berubah menjadi `REVOKED`; pembukaan ulang oleh Andi ditolak `403` | **PASSED** |
| **E09** | Audit forensik penyimpanan SQLite & *Crypto-Shredding* | Sistem DB | Sebelum revoke: KEK-wrapped key & 0 plaintext PII. Pasca revoke: `wrapped_share_key` menjadi `NULL`, `share_items` dihapus tuntas (0 baris) | **PASSED** |
| **E10** | Persistensi status pasca-restart aplikasi | Sistem DB | Status `REVOKED` dan audit trail tetap persisten di database SQLite | **PASSED** |

---

## 2. Bukti & Detail Pengujian Per Skenario

### E01 — Pembuatan Kunci & Registrasi Public Key (Andi & Budi)
- **Tujuan:** Memastikan kunci RSA-2048 dibuat di sisi klien, private key disimpan lokal di file `.pem`, dan hanya SPKI public key yang didaftarkan ke backend (`PUT /api/v1/keys/me`).
- **Hasil Pengamatan:**
  - **Andi (Peminta):**
    - Private Key Path: `backend/fixtures/demo_keys/andi_private_key.pem`
    - SHA-256 Public Key Fingerprint: `8e070b7c956aeafe1e47ec2a6bb211d70133744201fad3184bea844524f28efa`
    - Display Prefix (16 hex): `8e070b7c956aeafe`
  - **Budi (Pemilik):**
    - Private Key Path: `backend/fixtures/demo_keys/budi_private_key.pem`
    - SHA-256 Public Key Fingerprint: `9fbf4a0ffa96d2c4d43667511e02fede26bf46e4056cb13be50250ef3078ba46`
    - Display Prefix (16 hex): `9fbf4a0ffa96d2c4`
  - **Citra (Pihak Ketiga):**
    - Private Key Path: `backend/fixtures/demo_keys/citra_private_key.pem`
    - SHA-256 Public Key Fingerprint: `1ea1b43091737b5877faa3245f95688c836c3e53e7d7941e30e074008a4dbbf3`
    - Display Prefix (16 hex): `1ea1b43091737b58`

---

### E02 — Verifikasi Pengajuan Dokumen Budi
- **Tujuan:** Memverifikasi pengajuan KYC milik Budi Pratama telah lengkap dan siap dibagikan.
- **Hasil Pengamatan:**
  - **Application ID:** `1e72ced6-842f-4313-918e-71637d0917b9`
  - **Status:** `SUBMITTED`
  - **Item Terlampir:**
    1. Data Profil / Personal Data (`DUMMY-3273-011508-0001`, Mahasiswa / Bendahara HIMA)
    2. Identitas: `ktp_budi_pratama.png` (KTP Sintetis Bandung)
    3. Dokumen Pendukung: `bank_account_form_budi.pdf` (Formulir Pembukaan Rekening HIMA)

---

### E03 — Andi Mengajukan Permintaan Akses Dokumen
- **Tujuan:** Andi mengajukan permintaan akses ke Budi melalui `POST /api/v1/share-requests`.
- **Hasil Pengamatan:**
  - **Request ID:** `5b47f550-bb62-4580-929c-8b446ebd989c`
  - **Target Owner:** `budi`
  - **Purpose:** `"Pengajuan rekening HIMA Informatika"`
  - **Requested Kinds:** `['profile', 'identity', 'document']`
  - **Status Awal:** `PENDING`
  - **HTTP Response:** `201 Created`

---

### E04 — Budi Memvalidasi Sidik Jari Kunci & Menyetujui Permintaan
- **Tujuan:** Budi memeriksa fingerprint peminta dan melakukan approve melalui `POST /api/v1/share-requests/{id}/approve`.
- **Hasil Pengamatan:**
  - **Verified Requester Fingerprint:** `8e070b7c956aeafe` (Cocok 100% dengan public key Andi)
  - **Decision:** `APPROVED`
  - **HTTP Response:** `200 OK`
  - **Tindakan Sistem:**
    - Membuat kunci simetris acak 256-bit (`share_key`).
    - Mengenkripsi ulang salinan profil, KTP, dan formulir dengan AES-256-GCM + AAD terikat pada ID permintaan dan item.
    - Membungkus `share_key` dengan server KEK untuk disimpan di `share_requests.wrapped_share_key`.

---

### E05 — Penerbitan Paket Out-of-Band (Paket Email)
- **Tujuan:** Menguji pembuatan paket terenkripsi asimetris untuk kanal komunikasi eksternal.
- **Hasil Pengamatan:**
  - **Format Paket:** `VELTRIX-SHARE-1.<base64url_json_payload>`
  - **Panjang Karakter:** 630 karakter
  - **Header Kriptografi:** `{"alg": "RSA-OAEP-256", "typ": "VELTRIX-SHARE-PACKAGE"}`
  - **Target Fingerprint Prefix:** `8e070b7c956aeafe`
  - **Payload Snippet:**
    ```text
    VELTRIX-SHARE-1.eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJ0eXAiOiJWRUxUUklYLVNIQVJFLVBBQ0tBR0UifQ.e3JlcXVlc3RfaWQiOiAiNWI0N2Y1NTAtYmI2Mi00NW...
    ```

---

### E06 — Andi Mendekripsi Paket & Membuka Dokumen
- **Tujuan:** Andi mengimpor private key miliknya, mendekripsi paket secara lokal via Web Crypto / RSA-OAEP, lalu mengambil dokumen via API `POST /api/v1/share-requests/{id}/items/{item_id}/open`.
- **Hasil Pengamatan:**
  - Kunci berbagi simetris 256-bit berhasil di-unwrap secara lokal.
  - Server mengembalikan konten dengan header `Cache-Control: no-store` (mencegah disk caching).
  - **Integritas Dokumen (Byte-Identical Verification):**
    | Dokumen | MIME Type | Ukuran (Bytes) | SHA-256 Hash |
    |---|---|---|---|
    | **profile** | `application/json` | 305 | `fd37d7bd28ecd5dea040fe0b9ed148f3bd40fada16f9ea87d3c70fe9e0f92e7f` |
    | **identity** | `image/png` | 60,617 | `92f7b399fe90efc2a4d905b4e64ee815946f0cc6e4d0ce8fd6225221c1f02db3` |
    | **document** | `application/pdf` | 3,294 | `e3220409a8f9b18704ec3bd59c465d74482ac791931c9d53d55696d63a5da4f9` |
  - *Catatan:* Hash SHA-256 dokumen yang dibuka identik 100% dengan file asli di disk sebelum dibagikan.

---

### E07 — Uji Keamanan Pihak Ketiga (Citra Mencoba Membuka Dokumen)
- **Tujuan:** Citra menyadap paket out-of-band dan mencoba membukanya dengan private key miliknya atau memanggil API.
- **Hasil Pengamatan:**
  - **Tahap 1 (Dekripsi RSA Lokal):** Citra mencoba `unwrapShareKey` menggunakan private key miliknya (`citra_private_key.pem`).
    - *Hasil:* **GAGAL (Mathematical Rejection).** RSA-OAEP menolak dekripsi karena ciphertext dienkripsi dengan public key Andi.
  - **Tahap 2 (Panggilan API Langsung):** Citra mencoba memanggil `POST /api/v1/share-requests/{id}/items/{first_item_id}/open`.
    - *Hasil:* **DITOLAK.** HTTP Status `403 Forbidden`, Error Code `SHARE_OPEN_DENIED`. Citra bukan peminta sah dari request tersebut.

---

### E08 — Budi Mencabut Akses & Andi Mencoba Membuka Ulang
- **Tujuan:** Budi memanggil `POST /api/v1/share-requests/{id}/revoke`. Andi mencoba memanggil API open kembali.
- **Hasil Pengamatan:**
  - Status pencabutan akses: HTTP `200 OK`.
  - Percobaan buka ulang oleh Andi: HTTP `403 Forbidden`, Error Code `SHARE_OPEN_DENIED`.
  - Akses langsung terputus seketika.

---

### E09 — Audit Forensik Database SQLite & Crypto-Shredding (J-QA-03)
- **Tujuan:** Memeriksa langsung tabel `bankkyc.db` saat status `APPROVED` dan setelah `REVOKED`.

#### A. Sebelum Revoke (Status: `APPROVED`)
```sql
SELECT id, status, LENGTH(wrapped_share_key) FROM share_requests WHERE id = '5b47f550-bb62-4580-929c-8b446ebd989c';
-- Output:
-- id: 5b47f550-bb62-4580-929c-8b446ebd989c | status: APPROVED | LENGTH(wrapped_share_key): 32 bytes

SELECT id, request_id, kind, LENGTH(encrypted_blob) FROM share_items WHERE request_id = '5b47f550-bb62-4580-929c-8b446ebd989c';
-- Output:
-- item 1: profile  | LENGTH: 333 bytes (Ciphertext)
-- item 2: identity | LENGTH: 60645 bytes (Ciphertext)
-- item 3: document | LENGTH: 3322 bytes (Ciphertext)
```
- **Temuan Forensik Nol Plaintext:**
  Pencarian string biner terhadap `"Budi Pratama"`, `"3273011508950001"`, dan `"DUMMY-3273"` pada kolom `encrypted_blob` menghasilkan **0 temuan** (`Found 0 occurrences`). Data tersimpan murni sebagai ciphertext AES-GCM acak.

#### B. Setelah Revoke (Status: `REVOKED` - Crypto-Shredding)
```sql
SELECT id, status, wrapped_share_key FROM share_requests WHERE id = '5b47f550-bb62-4580-929c-8b446ebd989c';
-- Output:
-- id: 5b47f550-bb62-4580-929c-8b446ebd989c | status: REVOKED | wrapped_share_key: NULL

SELECT COUNT(*) FROM share_items WHERE request_id = '5b47f550-bb62-4580-929c-8b446ebd989c';
-- Output:
-- COUNT(*): 0
```
- **Kesimpulan Crypto-Shredding:**
  1. Kunci terbungkus `wrapped_share_key` di-overwrite menjadi `NULL`.
  2. Seluruh baris dokumen salinan pada `share_items` dihapus secara permanen (`DELETE`).
  3. Dokumen tidak dapat didekripsi kembali oleh siapa pun, bahkan jika penyerang memiliki salinan dump database dan paket email lama.

---

### E10 — Persistensi Pasca-Restart Server
- **Tujuan:** Menghentikan koneksi database SQLite (`engine.dispose()`), menginisialisasi engine baru, dan memverifikasi persistensi catatan riwayat.
- **Hasil Pengamatan:**
  - Record permintaan tetap ada dengan status `REVOKED`.
  - Audit trail dan status penolakan tetap utuh dan konsisten.

---

## 3. Kesimpulan Verifikasi

Rangkaian skenario **E01 hingga E10** telah terverifikasi secara tuntas dan terdokumentasi dengan bukti forensik digital. Mekanisme pembagian dokumen membuktikan kepatuhan penuh terhadap prinsip:
1. **Zero-Knowledge Key Delivery:** Server tidak pernah menerima atau menyimpan private key pengguna.
2. **Authenticated Encryption with Associated Data (AEAD):** Mencegah serangan substitusi item antar pengajuan.
3. **Strict Crypto-Shredding:** Pemusnahan kunci dan ciphertext saat masa berlaku berakhir atau dicabut oleh pemilik.
