# Handoff Maleka Ghaniya — VELTRIX BankKYC
## Bagian C: Cryptography & Backend Security Lead

> **Penulis:** Maleka Ghaniya (Cryptography & Backend Security Lead)  
> **Penerima:** Caca / Jahhaza (Backend Lead), Angela (Frontend Lead), Jorell (OCR & QA Lead), Dosen & Asisten Pengajar  
> **Tanggal Selesai:** 16 November 2026 (Assignment 1) · Diperbarui 22 November 2026 (Assignment 2)  
> **Status:** **100% Selesai & Terverifikasi (Assignment 1 + Assignment 2 Passed)**  
> **Prinsip Kepatuhan:** *Confidentiality & Integrity at Rest & Out-of-Band Key Distribution* (Pasal 35 UU No. 27/2022 UU PDP).

---

## 1. Ringkasan Eksekutif Pekerjaan Maleka

Sesuai dokumen pembagian tugas tim ([`VELTRIX_Assignment1_Revision_Task_Distribution.md`](docs/guides/VELTRIX_Assignment1_Revision_Task_Distribution.md)), Maleka Ghaniya bertanggung jawab penuh atas **keamanan kriptografi inti, proteksi data saat istirahat (*data at rest*), autentikasi akses pratinjau dokumen, dan pengujian ketahanan serangan (*anti-tampering & boundary testing*)**.

Seluruh pekerjaan `M-SEC-01` hingga `M-SEC-04` telah selesai diimplementasikan, diuji, dan diintegrasikan dengan modul backend (Caca/Jahhaza) dan mesin analisis dokumen (Jorell):

| ID Tugas | Komponen | Status | Hasil Verifikasi |
|---|---|---|---|
| **M-SEC-01** | Authorized Decrypt-for-Preview Service | **Selesai (P0)** | Dekripsi in-memory (RAM), reviewer terotorisasi, streaming privat, tanpa file plaintext sementara. |
| **M-SEC-02** | Enkripsi Data Hasil OCR & Catatan Reviewer | **Selesai (P0/P1)** | Hasil ekstraksi teks & catatan keputusan dienkripsi menggunakan `Envelope` Veltrix + ikatan AAD. |
| **M-SEC-03** | Justifikasi Ilmiah AES-GCM & AAD untuk BankKYC | **Selesai (P1)** | Dokumen justifikasi formal threat model: anti-tampering dan mitigasi *cross-application substitution*. |
| **M-SEC-04** | Security Regression, Tamper Proof & Recovery | **Selesai (P0/P1)** | Uji modifikasi 1-bit ciphertext ditolak (`IntegrityFailure`), AAD mismatch ditolak, SHA-256 cocok 100%. |
| **M-SEC-05** | Visualisasi Lab Benchmark & Karakteristik Ciphertext (Slide 2) | **Selesai (P1)** | Tab Bar Chart interaktif, uji Avalanche Effect (~50.2%), Entropi Shannon (~7.999), Chi-Square Uniformity. |
| **M-SEC-06** | In-Memory Document Preview & Profil Inspeksi Reviewer | **Selesai (P0)** | Pratinjau visual KTP/PDF & profil pemohon via memory blob URL tanpa pernah tersimpan ke disk. |
| **M-SEC-07** | Pipeline Analisis Dokumen & Verifikasi Otomatis Berlapis | **Selesai (P0/P1)** | Validasi magic bytes, deteksi keyword resmi KTP (PaddleOCR), komparasi NIK/Nama dengan form pendaftaran. |
| **M-SEC-08** | Panduan Foto KTP Presisi (*KTP Cropper Modal*) | **Selesai (P1)** | Bingkai panduan standar ID-1, penanganan auto-fit foto kamera resolusi tinggi, drag/zoom/rotate interaktif. |
| **M-A2-01** | Assignment 2: Client-Side RSA-OAEP-256 Web Crypto | **Selesai (P0)** | Pembangkitan RSA-2048 lokal di browser, ekspor SPKI/PKCS#8 PEM, dekripsi paket `VELTRIX-SHARE-1.` tanpa mengirim Private Key ke server. |
| **M-A2-02** | Assignment 2: Frontend Data Sharing UI & In-Memory Preview | **Selesai (P0)** | Menu `03 Berbagi data` (`/applicant/sharing`): Request, Approve + Modal WA/Email, Unlock paket & pratinjau in-memory. |
| **M-A2-03** | Assignment 2: Security Regression & Out-of-Band Demo | **Selesai (P0)** | 9/9 pytest lulus (Eve eavesdrop, bit-flip tampering, at-rest KEK audit, AAD substitution, key rotation) + CLI simulator 6 tahap. |
| **M-A2-04** | Assignment 2: Laporan Keamanan & Threat Model | **Selesai (P1)** | Dokumen `docs/verification/ASSIGNMENT_2_SECURITY_REPORT.md` mencakup arsitektur hibrida dan bukti uji aktual. |

---

## 2. Rincian Teknis Implementasi (M-SEC-01 s.d. M-SEC-04)

### A. M-SEC-01: Authorized Decrypt-for-Preview Service (P0)

* **Tantangan Awal:** Sebelumnya, dokumen terenkripsi hanya dapat diunduh oleh pemilik akun (*Applicant*). Reviewer hanya melihat metadata, tidak dapat memeriksa substansi berkas KTP atau formulir.
* **Solusi Keamanan yang Dibangun:**
  1. **Strict Authorization Pipeline:**
     ```
     Request Pratinjau 
       → Otentikasi Sesi & Rotasi CSRF 
       → Verifikasi Peran Reviewer Aktif & Terdaftar pada Kasus (Assigned Reviewer)
       → Validasi Status Pengajuan (SUBMITTED, RESUBMITTED, UNDER_REVIEW)
       → Pengambilan Ciphertext BLOB & Header AAD dari Database
       → Pembukaan Kunci (Unwrap Keys dengan KEK Server)
       → Verifikasi Integritas Tag AES-256-GCM (16-byte MAC)
       → Dekripsi Pipeline Berlapis (AES-GCM → DES-CBC → ARC4-Drop3072)
       → Streaming ke Browser sebagai Inline Response Langsung dari RAM
     ```
  2. **Zero Plaintext on Disk:** Hasil dekripsi tidak pernah disimpan ke direktori temporer (`temp/`, `tmp/`, atau `public/`). Seluruh payload dikelola dalam objek `io.BytesIO` di memori dan langsung dialirkan ke klien.
  3. **Header Proteksi:** Setiap respons pratinjau disertai header `Cache-Control: no-store` dan `X-Content-Type-Options: nosniff` untuk mencegah penyimpanan cache di proxy atau disk browser.

---

### B. M-SEC-02: Enkripsi Data Hasil OCR & Catatan Reviewer (P0/P1)

* **Prinsip Utama:** Ekstraksi teks dari KTP (NIK, Nama, Tanggal Lahir, Alamat) dan formulir rekening mengandung **Data Pribadi Spesifik/Sensitif** sesuai UU PDP. Data ini **dilarang disimpan sebagai plaintext JSON** di SQLite.
* **Implementasi Enkripsi:**
  - Seluruh payload terstruktur hasil ekstraksi disimpan sebagai `ciphertext` terenkripsi menggunakan skema `Envelope` Veltrix yang sama dengan berkas bukti fisik.
  - **Pengikatan AAD (*Additional Authenticated Data*):** Konteks kepemilikan mengikat `application_id`, `evidence_id`, `version`, dan `kind` secara matematis ke tag autentikasi AES-GCM.
  - Hanya metadata non-PII (`analysis_status`, `model_version`, `processed_at`) yang tersimpan dalam format terindeks di database.
  - Catatan keputusan reviewer (`review_notes`) disimpan terenkripsi secara independen di tabel `objects` dengan `kind='review_note'`.

---

### C. M-SEC-03: Justifikasi Ilmiah Pemilihan AES-256-GCM & AAD

Dokumen teknis justifikasi kriptografi untuk arsitektur sistem VELTRIX BankKYC:

1. **Mengapa AES-256-GCM (Galois/Counter Mode)?**
   * **Kerahasiaan + Integritas Sekaligus (AEAD):** Algoritma stream cipher tradisional (RC4) atau mode block cipher standar (CBC tanpa HMAC) rentan terhadap serangan manipulasi bit (*bit-flipping attack*). AES-GCM menyediakan *Authenticated Encryption* yang memvalidasi tag autentikasi 128-bit sebelum data dirilis.
   * **Fail-Closed Guarantee:** Jika penyerang memanipulasi bit sekecil apa pun pada ciphertext di database, proses dekripsi langsung gagal (*fail-closed*), menjamin tidak ada plaintext yang bocor sebagian (*no partial plaintext leakage*).
2. **Peran Kritis AAD (Additional Authenticated Data):**
   * **Ancaman Cross-Application Document Substitution:** Penyerang dengan akses tulis database dapat mencoba memindahkan ciphertext KTP nasabah A ke berkas nasabah B.
   * **Mitigasi:** AAD memasukkan `owner_id`, `application_id`, `kind`, dan `category` ke dalam komputasi GMAC. Jika penyerang memindahkan baris ciphertext ke aplikasi lain tanpa mengetahui KEK server, tag autentikasi menjadi tidak valid dan sistem menolak mendekripsi.
3. **Justifikasi Keberadaan RC4 dan DES-CBC:**
   * Dipertahankan semata-mata untuk **keperluan pemenuhan akademik, demonstrasi laboratorium perbandingan algoritma, dan benchmark latensi/overhead**.
   * Tim secara tegas menyatakan dalam dokumentasi bahwa dalam arsitektur perbankan komersial riil modern, RC4 dan DES-CBC wajib ditinggalkan demi AES-256-GCM atau ChaCha20-Poly1305.

---

### D. M-SEC-04: Pengujian Keamanan, Ketahanan Serangan & Recovery (P0/P1)

Pengujian keamanan regresi telah dijalankan dengan hasil sebagai berikut:

```text
========================================================================================
                          SECURITY TEST MATRIX — MALEKA GHANIYA
========================================================================================
No. | Skenario Pengujian                    | Target Uji            | Hasil  | Status
----+---------------------------------------+-----------------------+--------+----------
 1. | 1-Bit Flipped Ciphertext              | kyc.crypto.Envelope   | REJECT | [PASS]
 2. | AAD Swapping (Wrong Application ID)   | kyc.crypto.Envelope   | REJECT | [PASS]
 3. | Context Swapping (Wrong Owner ID)     | kyc.crypto.Envelope   | REJECT | [PASS]
 4. | Wrong Server KEK                      | kyc.crypto.Envelope   | REJECT | [PASS]
 5. | Unassigned Reviewer Access            | /review-preview       | HTTP404| [PASS]
 6. | Unauthenticated Preview Access        | /review-preview       | HTTP401| [PASS]
 7. | Non-Reviewer Role Preview Access      | /review-preview       | HTTP403| [PASS]
 8. | Round-trip Exact Byte Recovery        | SHA-256 Comparison   | 100%   | [PASS]
 9. | Zero-Plaintext at Rest in SQLite      | Raw DB Inspection     | CLEAN  | [PASS]
10. | No Plaintext PII / Key in Server Log  | Stdout / Stderr Audit | CLEAN  | [PASS]
========================================================================================
```

---

### E. M-SEC-05: Lab Benchmark & Karakteristik Ciphertext (Slide 2 Perkuliahan) (P1)

* **Tujuan:** Memenuhi secara tuntas materi evaluasi Slide 2 Dosen mengenai komparasi algoritma kriptografi dan pembuktian empiris karakteristik ciphertext.
* **Fitur yang Diimplementasikan:**
  1. **Visualisasi Bar Chart Interaktif:** Grafik dual-metrik komparasi Throughput (MB/s) dan Latensi ($\mu$s) untuk ChaCha20-Poly1305 vs AES-256-GCM.
  2. **Analisis Statistik Ciphertext:**
     * **Avalanche Effect (~50.2%):** Pembuktian bahwa pengubahan 1 bit pada plaintext menghasilkan perubahan >50% bit ciphertext secara deterministik acak.
     * **Entropi Shannon (~7.999 bit/byte):** Mengukur tingkat keacakan mendekati batas teoritis ideal 8.000 bit/byte.
     * **Uji Keseragaman Chi-Square:** Memvalidasi distribusi nilai byte 0-255 yang seragam, membuktikan ciphertext tidak membocorkan struktur frekuensi plaintext.
  3. **Tabel Metrik Lengkap:** Pengujian payload dari ukuran 1 KB hingga 10 MB dengan ekspor CSV.

---

### F. M-SEC-06: In-Memory Document Preview & Profil Inspeksi Reviewer (P0)

* **Tujuan:** Memungkinkan petugas Reviewer memeriksa berkas visual (KTP & PDF Formulir) serta data diri pemohon secara substantif tanpa melanggar kebijakan *zero-disk-leak*.
* **Fitur yang Diimplementasikan:**
  1. **Substantive In-Memory Decryption:** Dokumen didekripsi hanya di RAM server dan dialirkan sebagai *streaming response*, kemudian dirender di browser menggunakan *temporary Object URL* (Blob).
  2. **Applicant Profile Reveal:** Reviewer dapat membuka dan membandingkan profil pendaftaran nasabah (Nama, NIK, Tempat/Tgl Lahir, Alamat) langsung di samping dokumen fisik.
  3. **Keamanan Klien:** Blob URL segera direvoke saat dialog ditutup untuk mencegah kebocoran memori pada browser.

---

### G. M-SEC-07: Verifikasi Keabsahan Dokumen Berlapis (Multi-tier Verification) (P0/P1)

* **Tujuan:** Memastikan sistem dapat mengenali secara otomatis apakah berkas yang diunggah benar-benar dokumen yang diminta (KTP asli vs gambar acak/salah).
* **Arsitektur 4 Lapis Verifikasi:**
  1. **Level 1 (Format & Magic Bytes):** Memeriksa header biner file mentah (`validation.py`) untuk menolak file rusak, script berbahaya, atau ekstensi palsu sebelum enkripsi.
  2. **Level 2 (Klasifikasi Dokumen via AI OCR & Parser):**
     * Foto KTP dipindai untuk mendeteksi kata kunci resmi identitas Indonesia (`PROVINSI`, `KOTA`, `KABUPATEN`, `NIK`, `REPUBLIK`, `KARTU TANDA PENDUDUK`).
     * Jika diunggah foto non-KTP (pemandangan, struk, hewan), sistem menandai `document_type: "unknown"` dan `is_ktp: false`.
  3. **Level 3 (Pencocokan Konsistensi Data Otomatis):** Mencocokkan 16-digit NIK dan Nama hasil OCR dengan input form nasabah (`MATCH` vs `MISMATCH`).
  4. **Level 4 (Checklist & Rekomendasi Reviewer):** Dashboard reviewer menampilkan checklist otomatis dan menyarankan aksi `REJECT_OR_REVISE` dengan alasan `WRONG_DOCUMENT_TYPE` atau `MISMATCH`.

---

### H. M-SEC-08: Panduan Foto KTP Presisi (*KTP Cropper Modal*) (P1)

* **Tujuan:** Membantu nasabah mengambil dan memposisikan foto KTP agar pas dengan bingkai kartu sebelum dikirim ke sistem.
* **Fitur yang Diimplementasikan:**
  1. **Bingkai Panduan ID-1:** Rasio standar kartu identitas/ATM dengan panduan visual kotak NIK dan pasfoto.
  2. **Auto-Fit Skala Foto Resolusi Tinggi:** Menangani foto kamera ponsel resolusi tinggi (3000px) menggunakan kalkulasi `baseScale` otomatis sehingga foto langsung pas di dalam bingkai tanpa *overflow*.
  3. **Kontrol Interaktif Lengkap:** Drag posisi foto, slider zoom + tombol `[-]`/`[+]`, tombol `Pas Bingkai`, dan rotasi 90 derajat.
  4. **Penyelarasan Tema:** Tampilan modal dan tombol diselaraskan dengan palet warna resmi Veltrix (`var(--primary)`, `var(--surface)`).

---

## 3. Cara Menjalankan Verifikasi Keamanan di Windows

Jalankan perintah berikut dari folder `backend` dengan virtual environment aktif:

### 1. Menjalankan Seluruh Security Unit Tests:
```powershell
cd praktikum_1\backend
.\.venv\Scripts\python.exe -m pytest -q --basetemp=temp_pytest tests\test_security.py tests\test_crypto.py tests\test_bankkyc.py
```
*Hasil yang diharapkan: Seluruh pengujian keamanan, kriptografi, dan kontrol akses role lolos (`passed`).*

### 2. Menjalankan Verifikasi Integrasi HTTP Live (Smoke Test):
```powershell
.\.venv\Scripts\python.exe scripts\smoke_kyc_live.py
```
*Hasil yang diharapkan: Seluruh 8 tahapan live HTTP lolos (`PASS`), termasuk pembuktian kecocokan SHA-256 byte-by-byte.*

### 3. Memeriksa Bukti Zero-Plaintext at Rest di Database:
```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; con=sqlite3.connect('data/bankkyc.db'); cur=con.cursor(); cur.execute('SELECT id, kind, category, substr(ciphertext, 1, 16) FROM objects LIMIT 5'); print(cur.fetchall())"
```
*Hasil yang diharapkan: Seluruh isi dokumen dan data pribadi tersimpan dalam format biner acak (BLOB).*

---

## 4. Panduan untuk Tim

* **Untuk Angela (Frontend):** Pratinjau gambar, PDF, dan video dapat diakses melalui endpoint `GET /api/v1/applications/{id}/evidence/{eid}/review-preview` menggunakan kredensial reviewer yang ditugaskan.
* **Untuk Caca / Jahhaza (Backend):** Layanan dekripsi aman terintegrasi penuh dalam rute review dan worker analisis dokumen tanpa perlu membuka kunci master KEK ke komponen publik.
* **Untuk Jorell (QA & Dokumen):** Seluruh angka pengujian keamanan, skenario penolakan tampering, dan pembuktian matematis siap dirujuk ke dalam laporan akhir revisi tugas.

---

## 5. Assignment 2: Key Management & Out-of-Band Data Sharing

Melanjutkan Backend API Assignment 2 yang telah dibangun oleh Jahhaza (`backend/kyc/sharing_crypto.py`, `backend/kyc/main.py`, migrasi `0003_data_sharing`), Maleka menyelesaikan implementasi **kriptografi sisi klien, antarmuka pengguna (UI), pengujian regresi keamanan *out-of-band*, simulator demo CLI, dan dokumentasi laporan keamanan**.

### A. M-A2-01: Client-Side Web Crypto Engine (`frontend/src/lib/sharing-crypto.ts`)

* **Pembangkitan Kunci RSA-2048 di Browser:** Menggunakan Web Crypto API (`RSA-OAEP` + `SHA-256`) untuk membuat pasangan kunci asimetris secara lokal.
* **Isolasi Private Key:** Hanya *Public Key* (format SPKI PEM) yang dikirim ke server (`PUT /api/v1/keys/me`). *Private Key* (format PKCS#8 PEM) disimpan secara lokal di browser dan tersedia opsi unduh cadangan `.pem` (**tidak pernah dikirim ke server**).
* **Dekripsi Paket `VELTRIX-SHARE-1.`:** Membongkar paket teks yang diterima dari WhatsApp/Email dan mendekripsi `ek` menggunakan *Private Key* lokal untuk mengekstrak kunci simetris AES-256 (32 byte).

### B. M-A2-02: Frontend Data Sharing UI & Pratinjau In-Memory (`/applicant/sharing`)

* **File Terkait:**
  * `frontend/src/lib/kyc-api.ts` — integrasi seluruh endpoint Assignment 2 (`/keys/me`, `/share-requests`, `/approve`, `/reject`, `/cancel`, `/revoke`, `/package`, `/items`, `/open`).
  * `frontend/src/features/kyc/sharing-workspace.tsx` & `frontend/src/app/(workspace)/applicant/sharing/page.tsx` — ruang kerja lengkap berbagi data.
  * `frontend/src/components/app-shell.tsx` — navigasi sidebar **`03 Berbagi data`** untuk peran Pemohon (`applicant`).
* **Alur Fitur di Browser:**
  1. **Panel Manajemen Kunci RSA-2048:** Generate/rotasi kunci, status fingerprint server vs lokal, dan cadangan Private Key `.pem`.
  2. **Tab Ajukan Permintaan Akses:** Memilih username pemilik data, tujuan, dan item (`profile`, `identity`, `document`, `kk`, `video`).
  3. **Tab Permintaan Masuk (Pemilik Data):** Menyetujui permintaan (memilih pengajuan & subset item) → muncul pop-up **Paket Kunci Terenkripsi (`VELTRIX-SHARE-1...`)** dengan tombol salin ke clipboard serta pintasan **Kirim via WhatsApp** dan **Kirim via Email**, plus tombol **Cabut Akses (Revoke)**.
  4. **Tab Permintaan Keluar & Unlock (Pemohon):** Menempel paket dari WhatsApp/Email + Private Key → dekripsi lokal → pratinjau dokumen **in-memory** (Profil JSON, gambar KTP, PDF, video via temporary Blob URL yang langsung di-revoke saat dialog ditutup).

### C. M-A2-03: Security Regression Tests & Demo Simulator

* **Security Regression Suite (`backend/tests/test_assignment2_security.py`):**
  * `test_oob_eavesdropper_cannot_decrypt_package`: Penyadap (*Eve*) yang menyalin paket dari WA/Email gagal mendekripsi tanpa Private Key pemohon.
  * `test_oob_package_tampering_rejected_by_rsa_oaep`: Modifikasi 1 bit pada ciphertext kunci (`ek`) langsung ditolak RSA-OAEP-256.
  * `test_at_rest_key_wrapping_and_zero_plaintext_audit`: Audit database SQLite membuktikan `wrapped_share_key != raw_key` dan nol plaintext PII di `share_items`.
  * `test_cross_item_aad_substitution_attack_rejected`: Penukaran ciphertext antar-item ditolak AES-256-GCM AAD (`403 SHARE_OPEN_DENIED`).
  * `test_key_rotation_invalidates_old_private_key_on_reissued_package`: Setelah rotasi kunci RSA, Private Key lama tidak dapat membuka paket yang diterbitkan ulang.
* **CLI Demo Simulator (`backend/scripts/demo_assignment2_sharing.py`):** Simulasi interaktif 6 tahap (Registrasi & RSA Keypair → Request → Approve & Paket `VELTRIX-SHARE-1` → Uji Serangan Penyadapan & Tampering → Dekripsi & Verifikasi SHA-256 100% Identik → Revoke & Data Shredding).

### D. M-A2-04: Laporan Keamanan Assignment 2

* Dokumentasi arsitektur enkripsi hibrida, *threat model* distribusi kunci *out-of-band*, dan tabel hasil pengujian aktual tersedia di [`docs/verification/ASSIGNMENT_2_SECURITY_REPORT.md`](docs/verification/ASSIGNMENT_2_SECURITY_REPORT.md).

### E. Perintah Verifikasi Assignment 2 (Windows)

```powershell
# 1. Migrasi skema Assignment 2 (0003_data_sharing)
cd backend
.\.venv\Scripts\python.exe manage.py migrate

# 2. Jalankan seluruh tes API + regresi keamanan Assignment 2 (9 passed)
.\.venv\Scripts\python.exe -m pytest -v --basetemp=temp_pytest tests/test_sharing_api.py tests/test_assignment2_security.py

# 3. Jalankan simulator demo end-to-end 6 tahap
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe scripts/demo_assignment2_sharing.py

# 4. Verifikasi TypeScript frontend (0 errors)
cd ..\frontend
npm.cmd run typecheck
```
