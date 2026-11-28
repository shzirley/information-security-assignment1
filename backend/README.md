# Backend BankKYC v2

## Assignment 3 — bagian Caca/Jahhaza

Revisi `0004_digital_signature` menambah metadata kunci tanda tangan, challenge PoP, CA, sesi, dan referensi PDF bertanda tangan. Jalankan `python manage.py migrate` pada database Assignment 2 yang telah dicadangkan. Migrasi `0001`–`0003` tidak diubah. SQLite memakai indeks parsial untuk satu kunci aktif per user; MySQL memakai lock baris `kyc_users` saat rotasi. Private key pemohon tidak diterima API; PDF prepared dan signed disimpan sebagai `encrypted_objects` dengan envelope yang sudah ada.

Kontrak endpoint terdapat di [openapi.json](openapi.json). Semua path memakai prefix `/api/v1`; rute mutasi membutuhkan login dan CSRF. `POST /signing-keys/challenge` mengembalikan `challenge_id`, challenge base64 32 byte, `user_id`, dan `expires_at` (5 menit). Browser menandatangani `canonical{user_id, spki_sha256, challenge}`. `PUT /signing-keys/me` menerima `public_key_pem`, `challenge_id`, `pop_signature` base64. `prepare` mengembalikan `session_id`, `signed_attrs_der` base64 (DER tag `0x31`), `digest` hex SHA-256, `byte_range` empat integer, `key_fingerprint`, dan `expires_at` (10 menit). `complete` menerima signature base64 dan mengembalikan `signature_id`, `status`. Verifikasi mengembalikan `status`, `reasons[]`, `signer`, `fingerprint`, `signed_at`; tidak mengembalikan byte dokumen.

Integrasi dengan modul Maleka/Jorell menggunakan fungsi berikut. Modul yang belum digabung menghasilkan respons `503 SIGNING_UNAVAILABLE`; sesi/kunci tidak dibuat diam-diam:

| Modul | Fungsi yang dipanggil backend |
| --- | --- |
| `kyc.pki` | `create_authority(kek) -> dict` berisi kolom `pki_authority`; `verify_pop(public_key_pem, user_id, challenge_bytes, signature_bytes) -> bool`; `issue_certificate(public_key_pem, account, authority_row, kek) -> (cert_der, serial, expires_at)` |
| `kyc.pdf_signing` | `normalize(pdf_bytes) -> bytes`; `assert_signable(pdf_bytes)`; `prepare_incremental_update(pdf_bytes, signer_name, reason) -> (prepared_bytes, byte_range)`; `digest_byte_range(prepared_bytes, byte_range) -> 32-byte digest`; `embed_cms(prepared_bytes, cms_der) -> signed_pdf_bytes` |
| `kyc.cms` | `build_signed_attrs(digest_bytes, cert_der, signing_time) -> DER bytes` (tag `0x31`); `build_signed_data(signed_attrs_der, signature_bytes, [cert_der, ca_der]) -> CMS DER` |
| `kyc.signature_rsa` | `verify_pkcs1_v15(public_key_pem, sha256_signed_attrs_bytes, signature_bytes) -> bool` |
| `kyc.pdf_verify` | `verify_pdf(pdf_bytes, ca_der) -> {status, reasons, signer, fingerprint, signed_at}`. Must enforce all checks in implementation plan §1.7, including exact ByteRange coverage and one signature. |

**Modul kriptografi (Maleka) sudah digabung:** `kyc.signature_rsa`, `kyc.cms`, dan `kyc.pki`. Untuk `kyc.pdf_verify.verify_pdf`, langkah 5–9 §1.7 sudah tersedia sebagai `kyc.cms.parse_and_verify(cms_der, sha256_byte_range_digest, ca_der) -> {status, reasons, signer, fingerprint, signed_at}`; `pdf_verify` cukup menjalankan langkah 1–4 (struktur PDF, satu `/Sig`, ByteRange menutup seluruh berkas) lalu memanggil fungsi ini. `kyc.pki.verify_chain(cert_der, ca_der)` memeriksa rantai sertifikat. Dependensi baru: `asn1crypto` (encode/decode DER) dan `cryptography` (hanya pembuatan kunci CA). Desain dan alasannya: [ADR tanda tangan digital](../docs/decisions/ADR_DIGITAL_SIGNATURE.md).

**Yang dikirim frontend** (`frontend/src/lib/signing-crypto.ts`, dites terhadap OpenSSL dengan `npm run test:signing`). Kedua tanda tangan memakai RSASSA-PKCS1-v1_5 dengan SHA-256 dan kunci RSA-3072 (e = 65537):

- `pop_signature` = tanda tangan atas `SHA-256(canonical({"challenge": <string base64 persis dari server>, "spki_sha256": <hex huruf kecil SHA-256 dari SPKI DER>, "user_id": <user_id dari challenge>}))`, dengan `canonical` = `kyc.crypto.canonical` (kunci terurut, tanpa spasi).
- `signature` pada `complete` = tanda tangan atas `SHA-256(signed_attrs_der)`, yaitu byte bertag `0x31` dari `prepare`, sesuai pemanggilan `verify_pkcs1_v15` di atas.
- Sebelum menandatangani, browser menghitung ulang SHA-256 `byte_range` dari `preview` dan menolak bila tidak sama dengan `digest` maupun atribut `messageDigest` di `signed_attrs_der`.

Pembuatan CA hanya saat `manage.py migrate`, bukan saat request/startup. Bila modul PKI digabung setelah migrasi sudah dijalankan, jalankan `manage.py migrate` sekali lagi untuk membuat CA. `VELTRIX_REQUIRE_SIGNED_FORM=true` mewajibkan formulir terbaru berstatus `VALID` pada submit/resubmit. Nilai default `false` menjaga tes Assignment 1/2; contoh `.env.example` memakai `true`. Berbagi Assignment 2 untuk item `document` mengambil signed PDF terbaru yang valid bila ada.

API FastAPI yang sesuai dengan `frontend/src/lib/kyc-api.ts`. Database permanen SQLite untuk startup lokal, MySQL melalui `mysql+pymysql` untuk deployment terpisah. Alur vault lama berada di `app/main.py` sebagai referensi; entry point `app.server:app` sekarang menggunakan `kyc/main.py`.

Spesifikasi dan kontrak integrasi: [Backend PRD](../docs/prd/VELTRIX_BankKYC_BE_PRD.md). Dokumentasi lengkap: [indeks dokumentasi](../docs/README.md).

## Setup manual (Windows)

Jalankan dari folder `backend`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe setup_env.py --live
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py demo-users
.venv\Scripts\python.exe -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

`demo-users` hanya boleh berjalan dengan `APP_ENV=demo`. Password lokal dibuat acak dan akun yang sudah ada tidak diubah. Untuk membuat akun operator sendiri:

```powershell
.venv\Scripts\python.exe manage.py create-user reviewer_baru --role reviewer
.venv\Scripts\python.exe manage.py disable-user reviewer_baru
```

Password diminta melalui prompt tersembunyi. Menonaktifkan akun mencabut seluruh sesi. Tidak ada endpoint registrasi admin atau pemilihan role di form publik.

Frontend (terminal lain):

```powershell
cd ..\frontend
npm.cmd ci
npm.cmd run dev
```

Linux/macOS mengganti path interpreter dengan `.venv/bin/python` dan menggunakan `npm`. Untuk satu perintah dari root gunakan `start.bat` atau `bash start.sh`.

## Konfigurasi

`setup_env.py` hanya menambahkan nilai yang belum ada, tidak mengganti kunci yang sudah disimpan. `.env.example` adalah contoh, bukan kunci yang siap digunakan. Perintah `--live` secara eksplisit menyetel frontend; tanpa flag itu frontend tidak disentuh.

| Variabel | Fungsi |
| --- | --- |
| KYC_DATABASE_URL | Default file SQLite absolut di `backend/data/bankkyc.db`; opsional URL MySQL |
| VELTRIX_KEK_V1_BASE64 | KEK 32 byte untuk membungkus kunci setiap objek; disimpan di luar DB |
| VELTRIX_AUTH_SECRET_BASE64 | Secret 32 byte berbeda untuk CSRF/rate-limit namespace |
| COOKIE_SECURE | `false` untuk HTTP localhost; `true` di HTTPS |
| ALLOWED_ORIGINS | Origin frontend yang diizinkan, dipisahkan koma |
| APP_ENV | `demo` mengizinkan provisioning akun latihan dan cleanup eksplisit |
| FFPROBE_PATH | Nama/path executable ffprobe; default `ffprobe` |

Nama konfigurasi `KYC_DATABASE_URL` sengaja berbeda dari `DATABASE_URL` legacy agar database vault lama tidak dipakai tanpa sengaja.

## Skema dan transaksi

Alembic `0001_bankkyc` membuat tabel BankKYC terpisah: `kyc_users`, `kyc_sessions`, `applications`, `reviewer_assignments`, `encrypted_objects`, `personal_data_versions`, `evidence_versions`, `case_events`, `lab_runs`, `lab_lock`, `kyc_rate_limits`, `security_events`, `kyc_key_state`. Revisi `0002_document_review` menambah subtype bukti, referensi checklist dan analisis terenkripsi, serta field audit. Tabel Alembic mencatat revisi skema. `schema-mysql.sql` hanya referensi DDL; migrasi juga menginisialisasi lock lab dan pemeriksaan kunci.

Data profil dan bukti bersifat append-only per versi. Berkas asli tidak disimpan pada folder publik/disk upload. Seluruh byte, nama file privat, checksum dan catatan masuk envelope terenkripsi. Kolom operasional minimum menyimpan relasi, kategori, ukuran, tipe MIME terverifikasi, status, peran dan waktu.

Setiap perubahan kasus memakai transaksi, expected version dan compare-and-swap; MySQL juga memakai `SELECT FOR UPDATE`. Payload/version/event berubah bersama atau seluruhnya dibatalkan. Dua penyimpanan dengan version sama menghasilkan satu keberhasilan dan satu `409 VERSION_CONFLICT`.

Batas prototipe: 100 pengajuan per akun dan 100 versi bukti per pengajuan. Daftar tidak dipotong diam-diam. Penambahan skema berikutnya harus memakai revisi Alembic baru.

## MySQL

Buat database baru dan akun aplikasi dengan akses hanya ke database tersebut. Contoh SQL (ganti password):

```sql
CREATE DATABASE veltrix_kyc CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'veltrix_app'@'127.0.0.1' IDENTIFIED BY 'GANTI_PASSWORD_UNIK';
GRANT ALL PRIVILEGES ON veltrix_kyc.* TO 'veltrix_app'@'127.0.0.1';
```

Tambahkan ke `backend/.env`:

```dotenv
KYC_DATABASE_URL=mysql+pymysql://veltrix_app:PASSWORD_URL_ENCODED@127.0.0.1:3306/veltrix_kyc?charset=utf8mb4
```

URL-encode karakter khusus password pada URL. Atur `max_allowed_packet=128M` di MySQL (contoh `mysql.cnf.example`) lalu restart database. Jalankan `manage.py migrate` dan provisioning akun. MySQL dan SQLite merupakan database berbeda: mengganti URL tidak menyalin data antar database. Gunakan database tujuan baru sebelum mulai menginput data, atau buat migrator eksplisit jika data perlu dipindahkan.

Opsi Docker dari root proyek: atur environment `MYSQL_PASSWORD` dan `MYSQL_ROOT_PASSWORD` lalu `docker compose up -d mysql`. File compose menggunakan MySQL 8.4 dengan volume permanen dan hanya bind localhost. Jangan menjalankan `docker compose down -v` jika ingin mempertahankan data.

## Kontrak API

Prefix `/api/v1`. Swagger: `/docs`; JSON: `/openapi.json`. Salinan spesifikasi dapat dibuat dengan `python manage.py openapi`.

| Method | Path | Akses |
| --- | --- | --- |
| GET | /health, /auth/csrf | Publik; respons minimum |
| POST | /auth/register, /auth/login | CSRF; registrasi selalu applicant |
| GET / POST | /auth/me / /auth/logout | Sesi; logout mencabut token |
| GET / POST | /applications | Applicant; GET juga reviewer sesuai penugasan |
| GET | /applications/{id} | Pemilik atau reviewer ditugaskan |
| GET / PUT | /applications/{id}/personal-data | Pemilik; PUT hanya DRAFT/NEEDS_REVISION |
| GET | /applications/{id}/personal-data/download | Pemilik; attachment JSON canonical |
| POST | /applications/{id}/evidence | Pemilik; multipart file/category/version, dengan document_type opsional |
| GET | /applications/{id}/evidence/{evidenceId}/download | Pemilik; seluruh versi, parent ID harus cocok |
| GET | /applications/{id}/review/profile | Empat field profil untuk reviewer yang ditugaskan |
| GET | /applications/{id}/evidence/{evidenceId}/review-preview | Pratinjau bukti aktif untuk reviewer yang ditugaskan |
| GET / POST | /applications/{id}/review/checks | Checklist terenkripsi; perubahan hanya saat UNDER_REVIEW |
| GET / POST | /applications/{id}/evidence/{evidenceId}/analysis | Baca atau jalankan analisis untuk versi bukti dan profil aktif |
| POST | /applications/{id}/actions | Keputusan reviewer memakai checklist tersimpan dan alasan |
| GET / PUT | /admin/assignments, /admin/assignments/{id} | Admin; metadata tanpa profil/nama berkas/note |
| GET / POST | /lab/runs | Evaluator, fixture terisolasi dan hasil miliknya |
| GET | /lab/runs/{id}, /lab/runs/{id}/export | Evaluator pemilik hasil |
| GET / PUT | /keys/me | Public key RSA-SPKI aktif milik pemohon; PUT mengganti kunci lama |
| GET / POST | /share-requests | Daftar masuk/keluar (`?box=incoming|outgoing`) atau buat permintaan |
| POST | /share-requests/{id}/approve, /reject, /cancel, /revoke | Transisi permintaan sesuai peran dan status |
| GET | /share-requests/{id}/package, /items | Paket hanya untuk pemilik; metadata item hanya untuk peminta |
| POST | /share-requests/{id}/items/{itemId}/open | Peminta membuka salinan dengan kunci dari paket, respons privat no-store |

Sesi berupa token acak HttpOnly; DB hanya menyimpan hash SHA-256. CSRF signed double-submit dan Origin check berlaku pada seluruh mutation termasuk login. Login merotasi sesi dan CSRF; transport FE menghapus cache token setelah login. Respons privat no-store/nosniff; error memakai `{error:{code,message,field_errors,request_id}}`.

Alur status: DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED_DEMO/REJECTED_DEMO, atau UNDER_REVIEW → NEEDS_REVISION → RESUBMITTED → UNDER_REVIEW. Withdrawal hanya DRAFT/NEEDS_REVISION. Penugasan manual admin hanya pada SUBMITTED/RESUBMITTED. Semua transisi lain ditolak tanpa perubahan sebagian.

Rincian payload, kode respons, dan panduan demo ada pada [handoff integrasi backend](../docs/assignment-1/handoffs/HANDOFF_JAHHAZA_TO_TEAM.md).

### Assignment 2 — berbagi dokumen sintetis

Jalankan `python manage.py migrate` untuk menambah tabel `user_public_keys`, `share_requests`, dan `share_items` melalui revisi `0003_data_sharing`; migrasi 0001/0002 tetap utuh. Cadangkan database dan `.env` sebelum upgrade. Semua rute baru memakai sesi applicant dan CSRF yang sama. `PUT /keys/me` menerima `{ "public_key_pem": "-----BEGIN PUBLIC KEY-----..." }` (RSA SPKI minimal 2048 bit). Private key tidak diterima atau disimpan server. `POST /share-requests` menerima `{ "owner_username", "purpose", "items": ["profile", "identity", "document", "video", "kk"] }`. Saat approve, pemilik mengirim `{ "application_id", "items" }` dengan subset dari item yang diminta; hasilnya `package` berawalan `VELTRIX-SHARE-1.`. Peminta membuka item dengan `{ "share_key": "<base64 32 byte>" }` setelah browser membuka paket menggunakan private key lokal.

Persetujuan membuat salinan per item yang terenkripsi AES-256-GCM dengan AAD ID permintaan, item, kedua pihak, dan jenis dokumen. Kunci berbagi disimpan terbungkus KEK untuk penerbitan ulang paket saat public key peminta berubah; endpoint `open` memakai **hanya** kunci yang dikirim peminta. Pemilik dapat mencabut akses. Saat akses kedaluwarsa (7 hari) atau dicabut, baris item dan kunci terbungkus dihapus. Penolakan, pembatalan, dan percobaan `open` yang gagal masuk audit tanpa kunci atau isi dokumen. Metadata profil dan dokumen tetap berasal dari data sintetis.

Tes API Assignment 2: `python -m pytest tests/test_sharing_api.py -q`. Kontrak lengkap tersedia di `backend/openapi.json` dan rancangan tugas pada `docs/assignment-2/ASSIGNMENT_2_IMPLEMENTATION_PLAN.md`.

## Format, enkripsi dan lab

Profil delapan string wajib, maksimal 500 karakter per field; DUMMY identity, example-domain email, dummy phone dan tanggal nyata di masa lalu divalidasi ulang di server. PNG/JPEG dibaca/di-decode dan dibatasi 20 juta piksel; PDF dibaca parser, tanpa password, maksimal 500 halaman; DOCX diperiksa struktur OOXML, ukuran unpack, path dan rasio kompresi; MP4 diperiksa box container dan ffprobe, durasi 10–30 detik. Parser tetap bukan antivirus atau bukti keaslian identitas.

Request cap 34 MiB diperiksa dari stream, bukan hanya Content-Length. Multipart menerima satu file, kategori, versi pengajuan, dan subtype opsional. Threshold spool berada di atas batas request; tes melarang rollover plaintext ke disk untuk identitas 5 MiB dan video 30 MiB. Batas file per kategori mengikuti FE.

Envelope `vtx-kyc-layered-v1`: metadata privat + raw payload → RC4/drop3072 → DES-CBC/PKCS7 → AES-256-GCM. AAD mengikat ID objek/kasus/pemilik/kategori/versi serta parameter cipher. Bundle 3 kunci acak terpisah dibungkus AES-GCM dengan KEK lokal. Unique constraint key-version/wrap-nonce menolak reuse, disertai retry. Recovery mengecek wrapper/GCM/hash sebelum mengirim byte apa pun. Kehilangan KEK tidak dapat dipulihkan dari database.

Ini baseline akademik sesuai PRD, bukan klaim RC4/DES layak untuk layanan bank nyata. Pergantian interpretasi tugas berlapis/tiga representasi memerlukan perubahan suite tersendiri; backend ini menjalankan baseline berlapis yang sudah tertulis pada repo.

Lab melakukan 2 warm-up + 30–100 trial nyata, urutan kandidat diacak per trial, menyimpan raw ns, median, IQR inclusive, SD, overhead biner dan kecocokan byte. Cipher core timer mencakup konstruktor/padding/cipher/GCM-tag; tidak mencakup RNG, packing/envelope operasional, wrapping, JSON, DB atau HTTP. Scope dicatat pada result/CSV. Video fixture 8.664 byte hanya smoke test, bukan corpus performa video besar. Tidak ada angka mock yang diberi label measured. Benchmark legacy-only tidak membuktikan ciphertext authentication.

## Backup, restore dan cleanup

SQLite: `python manage.py backup PATH_BARU.db`. Command menggunakan SQLite online backup API; `.env` dicadangkan terpisah dengan akses terbatas. Restore dengan menghentikan server lalu memakai file backup bersama kunci aslinya. Detail sidecar WAL terdapat di panduan utama.

MySQL: lakukan dump konsisten menggunakan akun berizin backup, dengan password diminta interaktif:

```bash
mysqldump --single-transaction --hex-blob -h 127.0.0.1 -u veltrix_app -p veltrix_kyc > bankkyc-backup.sql
mysql -h 127.0.0.1 -u veltrix_app -p veltrix_kyc_restored < bankkyc-backup.sql
```

Simpan dump hanya pada lokasi privat, pertahankan `.env`/KEK terpisah, dan uji restore ke database baru sebelum mengganti URL aktif. Dump bukan pengganti kunci. Riwayat dan seluruh versi akan ikut backup.

Withdrawal tidak menghapus data. Operator dapat memeriksa cleanup satu kasus: `python manage.py cleanup-case CASE_ID` (dry-run). Tambahkan `--apply` hanya untuk penghapusan eksplisit data demo. Cascade menghapus versi, objek, event dan assignment; akun tidak dihapus. Salinan backup tetap perlu dikelola terpisah.

## Pengujian

```bash
python -m pytest tests/test_bankkyc.py -q
python -m pytest tests/test_api.py tests/test_crypto.py -q
```

Suite BankKYC secara default memakai file SQLite temporer, bukan database pengguna. Untuk MySQL disposable saja:

```bash
KYC_TEST_DATABASE_URL='mysql+pymysql://test_user:test_password@127.0.0.1:3306/veltrix_kyc_test?charset=utf8mb4' KYC_TEST_ALLOW_RESET=yes python -m pytest tests/test_bankkyc.py -q
```

**URL test tersebut direset oleh suite. Jangan pernah menunjuk ke database berisi pekerjaan pengguna.** Hasil aktual dan batas coverage tercatat pada [hasil verifikasi](../docs/verification/VERIFIKASI.md).
