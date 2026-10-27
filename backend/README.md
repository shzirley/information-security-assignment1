# Backend BankKYC v2

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

Alembic `0001_bankkyc` membuat tabel BankKYC terpisah: `kyc_users`, `kyc_sessions`, `applications`, `reviewer_assignments`, `encrypted_objects`, `personal_data_versions`, `evidence_versions`, `case_events`, `lab_runs`, `lab_lock`, `kyc_rate_limits`, `security_events`, `kyc_key_state`. Tabel Alembic mencatat revisi skema. `schema-mysql.sql` hanya referensi DDL; migrasi juga menginisialisasi lock lab dan pemeriksaan kunci.

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
| POST | /applications/{id}/evidence | Pemilik; multipart file/category/version |
| GET | /applications/{id}/evidence/{evidenceId}/download | Pemilik; seluruh versi, parent ID harus cocok |
| POST | /applications/{id}/actions | Status/peran/assignment diperiksa server |
| GET / PUT | /admin/assignments, /admin/assignments/{id} | Admin; metadata tanpa profil/nama berkas/note |
| GET / POST | /lab/runs | Evaluator, fixture terisolasi dan hasil miliknya |
| GET | /lab/runs/{id}, /lab/runs/{id}/export | Evaluator pemilik hasil |

Sesi berupa token acak HttpOnly; DB hanya menyimpan hash SHA-256. CSRF signed double-submit dan Origin check berlaku pada seluruh mutation termasuk login. Login merotasi sesi dan CSRF; transport FE menghapus cache token setelah login. Respons privat no-store/nosniff; error memakai `{error:{code,message,field_errors,request_id}}`.

Alur status: DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED_DEMO/REJECTED_DEMO, atau UNDER_REVIEW → NEEDS_REVISION → RESUBMITTED → UNDER_REVIEW. Withdrawal hanya DRAFT/NEEDS_REVISION. Penugasan manual admin hanya pada SUBMITTED/RESUBMITTED. Semua transisi lain ditolak tanpa perubahan sebagian.

## Format, enkripsi dan lab

Profil delapan string wajib, maksimal 500 karakter per field; DUMMY identity, example-domain email, dummy phone dan tanggal nyata di masa lalu divalidasi ulang di server. PNG/JPEG dibaca/di-decode dan dibatasi 20 juta piksel; PDF dibaca parser, tanpa password, maksimal 500 halaman; DOCX diperiksa struktur OOXML, ukuran unpack, path dan rasio kompresi; MP4 diperiksa box container dan ffprobe, durasi 10–30 detik. Parser tetap bukan antivirus atau bukti keaslian identitas.

Request cap 34 MiB diperiksa dari stream, bukan hanya Content-Length. Multipart hanya menerima satu file dan dua field metadata. Threshold spool berada di atas batas request; tes melarang rollover plaintext ke disk untuk identitas 5 MiB dan video 30 MiB. Batas file per kategori mengikuti FE.

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
