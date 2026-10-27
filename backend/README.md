# VELTRIX back-end

> Status 27 Oktober 2026: backend ini adalah implementasi **vault legacy**. Frontend terbaru memakai skenario BankKYC dan API mock. Role/session response, endpoint pengajuan/assignment, pipeline AES-GCM, dan lab fixture BankKYC belum diimplementasikan di sini. Kontrak terbaru ada di `../VELTRIX_BankKYC_FE_PRD.md`. Pernyataan kompatibilitas frontend di bawah berlaku untuk versi vault terdahulu. `setup_env.py` dapat membuat frontend mode live; gunakan mode mock untuk FE BankKYC sampai migrasi selesai.

**Panduan pengerjaan backend baru:** [VELTRIX BankKYC BE PRD](../VELTRIX_BankKYC_BE_PRD.md). Dokumen tersebut menetapkan MySQL, aturan role/owner/assignment/status, endpoint yang cocok dengan FE, pipeline sementara, key handling, benchmark nyata, migrasi dan kriteria lulus. Ikuti itu untuk handoff BankKYC; bagian di bawah mendokumentasikan implementasi vault yang sudah ada.

Implementasi vault lama menggunakan FastAPI + SQLAlchemy + PyCryptodome dan prefix `/api/v1`. Endpoint-nya cocok dengan frontend vault terdahulu. Frontend BankKYC baru memerlukan kontrak pengajuan/peran yang berbeda dan belum dapat dihubungkan hanya dengan mengganti env ke live.

## Struktur

| File | Fungsi |
| --- | --- |
| `app/config.py` | Konfigurasi database, master key, cookie, origin |
| `app/db.py` | Skema SQLAlchemy, SQLite dan MySQL |
| `app/crypto.py` | AES/RC4/DES, HKDF, envelope dan HMAC |
| `app/schemas.py` | Validasi request |
| `app/main.py` | API, autentikasi, ownership, CRUD, benchmark, CSV |
| `app/server.py` | Entry point Uvicorn |
| `setup_env.py` | Membuat konfigurasi/kunci lokal sekali |
| `tests/` | Pengujian API dan kriptografi |
| `scripts/smoke_live.py` | Uji integrasi melalui Next.js proxy |

Cara menjalankan lengkap untuk Windows/Linux ada di README utama.

## Menggunakan MySQL

SQLite adalah default untuk pengembangan. Untuk MySQL 8, buat database dan akun aplikasi terlebih dahulu, misalnya melalui MySQL Workbench:

```sql
CREATE DATABASE veltrix CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'veltrix'@'localhost' IDENTIFIED BY 'GANTI_PASSWORD_KUAT';
GRANT ALL PRIVILEGES ON veltrix.* TO 'veltrix'@'localhost';
```

Tambahkan ke `backend/.env`:

```dotenv
DATABASE_URL=mysql+pymysql://veltrix:GANTI_PASSWORD_KUAT@127.0.0.1:3306/veltrix?charset=utf8mb4
```

URL-encode karakter khusus dalam username/password URL. Restart back-end. Database harus sudah ada; tabel akan dibuat otomatis. Kolom ciphertext menggunakan **LONGBLOB** pada MySQL sehingga bisa menampung upload 25 MB. `utf8mb4_bin` menjaga perilaku username case-sensitive seperti SQLite. Gunakan konfigurasi server MySQL `max_allowed_packet=128M` untuk transaksi yang memuat tiga ciphertext file 25 MB; contoh di `mysql.cnf.example`. Akun database aplikasi perlu izin DDL saat inisialisasi tabel.

Mengganti `DATABASE_URL` memilih database lain; script ini tidak memigrasikan data SQLite ke MySQL. MySQL belum diuji dengan server nyata dalam lingkungan pengerjaan ini.

## Konfigurasi

| Variabel | Nilai/perilaku |
| --- | --- |
| `VELTRIX_MASTER_KEY` | Wajib, base64 dari 32 byte acak; dibuat oleh setup_env.py |
| `DATABASE_URL` | Default SQLite di backend/data/veltrix.db |
| `COOKIE_SECURE` | `false` untuk HTTP lokal; `true` untuk HTTPS |
| `ALLOWED_ORIGINS` | Origin front-end dipisahkan koma; default localhost/127.0.0.1 port 3000 |

Kunci rahasia dan database tidak dimasukkan ke ZIP. Simpan kunci dengan aman: perubahan master key membuat ciphertext/sesi CSRF lama tidak dapat dipakai. `key_version=1` dicatat dalam envelope, tetapi rotasi/migrasi kunci otomatis belum tersedia.

Next.js melakukan rewrite same-origin sehingga tidak perlu membuka CORS secara luas. Jika memakai port front-end lain, tambahkan origin yang sesuai. Jangan percaya header proxy IP dari klien: rate limit IP memakai peer langsung; di belakang Next.js semua klien berbagi bucket proxy, ditambah bucket username untuk login.

## Endpoint

| Metode | Path setelah /api/v1 | Fungsi |
| --- | --- | --- |
| GET | `/health`, `/capabilities` | Kesehatan DB dan batas input |
| GET | `/auth/csrf`, `/auth/me` | Token CSRF dan sesi aktif |
| POST | `/auth/register`, `/auth/login`, `/auth/logout` | Akun/sesi |
| GET | `/vault/summary` | Dashboard |
| GET/POST | `/vault/files` | Daftar/unggah multipart file dan category |
| GET/DELETE | `/vault/files/{id}` | Detail/hapus |
| GET | `/vault/files/{id}/download?algorithm=AES` | Download hasil dekripsi; juga RC4/DES |
| GET/POST | `/vault/personal-data` | Metadata profil/buat profil |
| PUT/DELETE | `/vault/personal-data/{id}` | Edit/hapus profil |
| POST | `/vault/personal-data/{id}/decrypt` | Buka profil dengan algorithm |
| GET/POST | `/benchmarks` | Histori/jalankan eksperimen |
| GET | `/benchmarks/{id}`, `/benchmarks/{id}/export` | Hasil/CSV |
| POST | `/download-tests` | Mulai uji download |
| POST | `/download-tests/{id}/results` | Simpan sample dari browser |
| GET | `/download-tests/{id}/export` | CSV uji download |

Semua operasi tulis memerlukan cookie CSRF dan header `X-CSRF-Token` yang diperoleh dari `/auth/csrf`, termasuk registrasi/login. API dokumen otomatis ada di `/docs` dan `/openapi.json`. Swagger tidak menambahkan header CSRF otomatis; untuk alur lengkap gunakan aplikasi atau script smoke.

Error mengikuti `{ "error": { "code", "message", "field_errors", "request_id" } }`. Resource milik pengguna lain diperlakukan sebagai 404. Tidak ada akun demo live yang dibuat otomatis.

## Penyimpanan dan kriptografi

File asli hanya berada di memori request dan tidak di-spool ke file sementara; parser multipart memakai batas spool di atas batas total request. Upload maksimum 25.000.000 byte. ASGI membatasi request sebelum parsing; request JSON maksimum 128 KB. Ukuran memori lebih besar dari file karena tiga ciphertext diproses bersamaan; ini sesuai lingkup MVP dengan request terbatas.

Data dan metadata filename dienkripsi sebelum transaksi commit. Database memuat identifier, pemilik, kategori, waktu, metadata terenkripsi, dan tiga envelope biner. Perubahan profil memakai salt/IV baru; penghapusan menghapus tiga versi dalam transaksi yang sama. Back-up database tetap memiliki data historis sesuai kebijakan back-up pengguna.

- AES-256-CBC memakai IV 16 byte; DES-CBC memakai IV 8 byte; padding PKCS#7.
- RC4 menggunakan derived key 32 byte dan drop 3072 byte untuk setiap setup cipher.
- HKDF-SHA256 memisahkan key berdasarkan item, algoritma, dan tujuan enkripsi/MAC. Salt 32 byte selalu acak.
- HMAC-SHA256 mengikat format, versi kunci, algoritma, item, salt, IV, drop, dan ciphertext. HMAC diverifikasi sebelum dekripsi/unpadding.
- Envelope: panjang header 4 byte big-endian, header JSON deterministik, ciphertext, tag 32 byte. `stored_bytes` adalah panjang envelope aktual.
- Argon2id untuk password; cookie sesi HttpOnly, hash token sesi di database, expiry 8 jam. Logout mencabut sesi tersebut.

RC4/DES adalah cipher legacy untuk demonstrasi perbandingan; tiga representasi memperbesar storage dan keamanan keseluruhan tetap dibatasi representasi terlemah. Sistem bukan end-to-end/zero-knowledge: server memiliki kunci dan mendekripsi data yang diotorisasi.

## Metode benchmark

Input dipulihkan sekali sebelum pengukuran; seluruh algoritma mendapat bytes identik. Dua warm-up per algoritma dikeluarkan dari sample. Urutan algoritma diacak setiap pengulangan dan disimpan di environment.

`encrypt_ns`: konstruksi cipher, padding, enkripsi. `decrypt_ns`: konstruksi cipher, dekripsi, unpadding. Random/derivasi key awal dan storage di luar timer inti. `integrity_ns` memuat pembuatan envelope/HMAC serta verifikasi envelope/HMAC/derivasi key untuk pemeriksaan. `correctness_ns` adalah pembandingan hasil dengan input. Semua diukur menggunakan `time.perf_counter_ns`.

Hasil menyimpan Python, PyCryptodome, platform, konfigurasi cipher, resolusi timer, urutan algoritma, dan scope timer. Standard deviation menggunakan sample SD (n−1). Waktu download diukur oleh browser dan dapat dilaporkan oleh klien; bukan ukuran crypto inti yang dipercaya dari server. Histori benchmark/download tetap disimpan setelah sumber dihapus, tanpa plaintext sumber.

Benchmark sinkron dibatasi 10–30 pengulangan, file maksimum 25 MB, dan 5 benchmark per menit per akun. Untuk beban besar perlu antrean/background worker, quota storage, dan paginasi histori. Tidak tersedia antivirus, pemulihan password, atau deployment otomatis.

Referensi implementasi: [FastAPI multipart](https://fastapi.tiangolo.com/tutorial/request-forms-and-files/), [PyCryptodome classic modes](https://www.pycryptodome.org/src/cipher/classic), [ARC4](https://www.pycryptodome.org/src/cipher/arc4), [HKDF](https://www.pycryptodome.org/src/protocol/kdf).
