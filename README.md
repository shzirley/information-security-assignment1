# VELTRIX BankKYC

Proyek akademik Information Security: simulasi onboarding rekening bank dengan profil fiktif, scan identitas dummy, dokumen administrasi, dan video sintetis. Unit kerja adalah pengajuan KYC, dengan akses pemohon, reviewer metadata, admin penugasan, dan evaluator lab.

**Status saat ini:** frontend BankKYC berjalan dengan API mock. Backend FastAPI lama tetap ada, tetapi masih menggunakan alur vault dan belum kompatibel dengan kontrak BankKYC. Enkripsi, session, dan benchmark nyata pada backend lama tidak berarti pipeline dan aturan BankKYC baru sudah terimplementasi. Gunakan data sintetis saja.

## Jalankan frontend

Perlu Node.js 22+ dan npm. Dari folder proyek:

```powershell
cd frontend
npm.cmd ci
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm.cmd run dev
```

Jika `.env.local` sudah ada, cukup atur `NEXT_PUBLIC_API_MODE=mock`; jangan menimpa konfigurasi lain tanpa memeriksanya. Buka http://127.0.0.1:3000. Di Linux/macOS gunakan `npm`, dan `cp .env.example .env.local`.

Login memakai username dan password, tanpa pemilih akun latihan atau peran. Untuk pengembangan dalam mode mock: pemohon `demo_user`, reviewer `reviewer_demo`, admin `admin_demo`, evaluator `evaluator_demo`; semua password mock `veltrix123`. Akun fixture ini hanya untuk API mock. Peran berasal dari respons login, bukan pilihan pengguna. Akun baru mendapat peran pemohon dan daftar kosong. Semua perubahan mock disimpan di memori browser dan hilang saat reload.

## Dokumentasi terbaru

- [PRD produk BankKYC v2.1](VELTRIX_BankKYC_PRD.md): skenario, assignment, kebijakan produk, dan keputusan dosen yang masih terbuka.
- [PRD frontend BankKYC v1.2](VELTRIX_BankKYC_FE_PRD.md): user flow, layar, kontrak API, GSM, bahasa antarmuka, validasi, acceptance criteria, batas implementasi, dan backlog.
- [PRD backend BankKYC v1.0](VELTRIX_BankKYC_BE_PRD.md): handoff implementasi FastAPI/MySQL, RBAC + ownership/assignment, state machine, enkripsi, kontrak FE, migrasi dan acceptance tests.
- [GSM VELTRIX](VELTRIX_GSM_v0.1.md): logo, warna, tipografi, dan aset merek yang dipertahankan.
- [Panduan frontend](frontend/README.md), [arah desain](frontend/DESIGN.md), [referensi komponen](frontend/REFERENCES.md), [QA antislop](frontend/ANTISLOP_QA.md).
- [Backend legacy](backend/README.md): implementasi vault terdahulu dan konfigurasi MySQL. Belum merupakan API BankKYC baru.

Dokumen dan screenshot alur vault yang sudah tergantikan dihapus dari direktori aktif; riwayat yang sudah dikomit tetap tersedia di Git. Aset GSM dan kode backend lama dipertahankan sebagai acuan merek dan migrasi.

## Fitur FE BankKYC

Landing dengan headline berganti tanpa tombol jeda/tulisan tambahan dan susunan bukti saat scroll yang mengikuti reduced motion; login username/password; shell per role; dashboard dan pencarian/filter kasus; wizard lima langkah; validasi dummy/ukuran/format; riwayat versi bukti; preview/download pemilik; submit/revisi/keputusan/penarikan sesuai status; antrean metadata reviewer; penugasan admin; lab fixture, riwayat, dan CSV **simulasi**; tema terang/gelap dan mobile.

Target stack tetap **Next.js + FastAPI + MySQL**. Pipeline operasional yang diusulkan sementara RC4 → DES-CBC → AES-256-GCM, hanya ciphertext final, satu retrieval. Interpretasi berlapis versus tiga representasi perlu konfirmasi dosen (D-01). Reviewer tetap strict owner-only metadata, menunggu keputusan D-02. DES/RC4 hanya untuk pembelajaran dan tidak diposisikan sebagai perlindungan data nyata.

## Pengujian frontend

```powershell
cd frontend
npm.cmd run build
npm.cmd run typecheck
npm.cmd run test:e2e
```

Build untuk tes harus dalam mode mock. Playwright memakai Microsoft Edge terpasang dan server production terisolasi di port 3100. Laporan HTML ada di `frontend/playwright-report/`; screenshot baru memakai prefix `bankkyc-` di `frontend/artifacts/`. Lihat laporan QA untuk hasil aktual dan batas coverage.

Tes backend lama dapat dijalankan dari virtualenv Python sesuai requirements di `backend/`. Tes tersebut tidak mencakup state machine/role/pipeline BankKYC baru. Hindari menjalankan `backend/setup_env.py` untuk demo FE baru karena script legacy dapat membuat `.env.local` dalam mode live.

## Yang masih perlu dikerjakan

API pengajuan/role/assignment baru; migrasi dan pengujian MySQL; pipeline/envelope/key management baru; draf persisten; validasi konten mendalam; atomic write; pengujian ownership/integritas/tampering server; benchmark nyata dan interpretasi; retention/deletion dan analisis regulasi yang diverifikasi tim. Daftar rinci terdapat dalam PRD FE.

Submission tugas memerlukan semua kode di GitHub dengan commit bermakna, laporan maksimum dua halaman A4, serta link dan screenshot percakapan AI aktual. Angka mock dan screenshot FE bukan bukti eksperimen kriptografi atau pengganti screenshot percakapan.
