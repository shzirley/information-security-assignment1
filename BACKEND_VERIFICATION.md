# Verifikasi penambahan back-end VELTRIX

## Hasil

| Pemeriksaan | Hasil |
| --- | --- |
| `python -m pytest -q` dari backend | 28 passed |
| `npm run build` dengan mode live | Berhasil |
| `npm run typecheck` | Berhasil |
| FastAPI + Next.js proxy same-origin | Berhasil |
| Upload 1.000 byte, download AES/RC4/DES, SHA-256 cocok | Berhasil |
| Upload penuh 25.000.000 byte, download AES/RC4/DES, SHA-256 cocok | Berhasil |
| Register/login/sesi/logout melalui proxy | Berhasil |
| Buat/buka/hapus profil melalui proxy | Berhasil |
| Benchmark nyata 10 pengulangan × 3 algoritma, 2 warm-up | Berhasil, 30 sample round-trip benar |
| CSV benchmark dan uji download melalui proxy | Berhasil |

28 pengujian mencakup ukuran input cipher 0/1/16/32.768 byte, randomisasi ciphertext, penolakan salah kunci/item, payload terpotong, manipulasi tag HMAC, autentikasi, CSRF, pembatasan login, akses pengguna lain, CRUD profil/file, batas upload, validasi sample download, penghapusan tiga versi, serta persistensi data dan sesi setelah aplikasi dibuat ulang.

Dependensi langsung yang digunakan saat pengujian dicatat di `backend/constraints-tested.txt`. Jika ingin menggunakan versi yang sama:

```bash
python -m pip install -r requirements.txt -c constraints-tested.txt
```

Satu deprecation warning berasal dari Starlette TestClient yang masih memakai httpx; tidak ada pengujian gagal.

## Batas verifikasi

- Database runtime yang diuji adalah SQLite. Dukungan MySQL memakai SQLAlchemy/PyMySQL dan tipe LONGBLOB, tetapi belum diuji dengan server MySQL nyata.
- Uji integrasi memanggil API melalui server Next.js produksi, termasuk cookie, CSRF dan multipart. Pengujian klik UI browser belum dijalankan: unduhan browser Playwright tidak menghasilkan arsip yang valid di lingkungan ini. Build dan typecheck front-end berhasil.
- Test Playwright awal adalah test mock dan memerlukan build mode mock serta Microsoft Edge sesuai konfigurasi awal. Label/akun fixture yang diharapkan test tersebut berbeda dengan live.
- Tidak dilakukan deployment, load test multi-user, audit keamanan independen, atau pengukuran hardware penelitian terkontrol. Benchmark menampilkan waktu aktual mesin yang menjalankan server; gunakan data eksperimen dari mesin penelitian sendiri untuk laporan.

## Isi hasil

Back-end baru, integrasi mode live, batas proxy untuk upload 25 MB, dokumentasi API/MySQL, panduan Windows/Linux, pengujian, dan script smoke disertakan bersama kode/aset awal. Kunci, konfigurasi rahasia, database, akun uji, cache, dan dependensi hasil instalasi tidak dimasukkan ke ZIP.
