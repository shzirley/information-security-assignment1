# Frontend VELTRIX BankKYC

Frontend Next.js menggunakan backend FastAPI BankKYC dalam mode live secara default. UI dan aset desain asli dipertahankan. Backend mengelola akun, peran, sesi, pengajuan, bukti, versi, catatan, penugasan dan hasil lab di database permanen.

Dari root gunakan `start.bat` (Windows) atau `bash start.sh` (Linux/macOS). Petunjuk lengkap: `../PANDUAN_MENJALANKAN.md`.

Untuk startup manual, jalankan backend sesuai `../backend/README.md`, lalu:

```bash
npm ci
npm run dev
```

`.env.local`:

```dotenv
NEXT_PUBLIC_API_MODE=live
API_ORIGIN=http://127.0.0.1:8000
```

Buka http://127.0.0.1:3000. Next.js memproxy `/api/v1/*` ke backend; cookie dan CSRF tetap same-origin. Setelah login, cache CSRF dibersihkan sehingga mutation mengambil token baru dari backend. Pengunduhan profil memakai attachment octet-stream sesuai transport Blob yang sudah ada.

Pemeriksaan:

```bash
npm run typecheck
npm run build
```

Tes API melalui proxy nyata: nyalakan backend pada port 8000 dan frontend pada 3000, lalu dari root jalankan `python backend/scripts/smoke_kyc_live.py`. Script membuat satu akun dan satu kasus sintetis; gunakan environment demo.

Mock masih tersedia hanya jika secara eksplisit memilih `NEXT_PUBLIC_API_MODE=mock`; data mock sementara dan bukan database. Registrasi dalam mode live membuat akun pemohon sesungguhnya di DB lokal. Akun operator dibuat melalui CLI backend; password demo acak ditampilkan oleh launcher.

Tes `tests/flows.spec.ts` adalah tes mock UI historis dan membutuhkan build mock serta Edge lokal. Hasil tes itu tidak dianggap bukti integrasi backend live. Lihat `../VERIFIKASI.md` untuk pemeriksaan yang benar-benar dijalankan pada paket ini.
