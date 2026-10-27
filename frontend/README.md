# VELTRIX BankKYC frontend

Next.js App Router + TypeScript + Tailwind v4. Identitas GSM lama dipertahankan; alur vault diganti pengajuan KYC. Spesifikasi lengkap: [PRD frontend](../VELTRIX_BankKYC_FE_PRD.md).

## Run

```powershell
npm.cmd ci
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm.cmd run dev
```

Buka http://127.0.0.1:3000. Jika konfigurasi sudah ada, atur `NEXT_PUBLIC_API_MODE=mock` tanpa menimpa nilai lain. Restart/rebuild setelah mengganti mode. PowerShell memakai `npm.cmd` untuk menghindari pembatasan `npm.ps1`.

Mode mock memuat MSW sebelum interaksi. Untuk pengembangan, masukkan kredensial akun fixture: `demo_user`, `reviewer_demo`, `admin_demo`, atau `evaluator_demo`, password `veltrix123`. Untuk menguji batas assignment, `reviewer_other` juga tersedia; `other_applicant` adalah pemilik kasus lain. Registrasi hanya membuat pemohon. Akun baru dan perubahan upload/status hanya berada dalam memori, hilang saat full reload. Cookie demo bukan autentikasi yang aman.

Tampilan memakai bahasa tugas pengguna, animasi headline tanpa tombol/tulisan tambahan, dan login username/password tanpa pintasan akun latihan. Peran selalu mengikuti respons login. Label FE, API mock/live, akademik/tugas, dan detail implementasi tidak menjadi dekorasi antarmuka. Batas penyimpanan sementara/belum dienkripsi tetap dinyatakan pada pemberitahuan data; hasil lab dan CSV tetap ditandai simulasi.

## Routes and implementation

- `/`: landing BankKYC, headline berganti otomatis, scroll-linked assembly empat bukti, alur dan ledger hak akses. Tidak ada tombol jeda atau teks tambahan di bawah hero. Hover/fokus menghentikan rotasi sementara; reduced motion menampilkan teks tetap.
- `/register`, `/login`: registrasi, login username/password, password visibility, session expiry.
- `/applicant/dashboard`, `/applicant/applications`: ringkasan dan pengajuan sendiri, next action, cari/filter.
- `/applicant/applications/new`, `/[id]/edit`: persiapan dan wizard profil, identitas, dokumen, video, review/submit.
- `/applicant/applications/[id]`: metadata, owner-only reveal/preview/download, versi dan timeline, penarikan pada status yang diizinkan.
- `/reviewer/queue`, `/reviewer/applications/[id]`: metadata pengajuan ditugaskan, mulai/revisi/terima/tolak demo.
- `/admin/assignments`: penugasan reviewer sebelum tinjauan.
- `/lab/benchmark`, `/lab/verification`: fixture terpisah, konfigurasi, hasil/riwayat/CSV simulasi dan gate verifikasi yang belum dijalankan server.

Legacy `/dashboard` mengarahkan sesuai role; `/vault` dan `/personal-data` menuju daftar pengajuan, `/lab` menuju benchmark. Tidak ada pemilih cipher pada retrieval operasional.

`src/lib/kyc.ts` adalah domain model/validasi; `kyc-api.ts` kontrak pengajuan; `api.ts` transport/session/CSRF/error. `features/kyc/` berisi halaman interaktif. Struktur `components/ui/`, `components.json`, dan `lib/utils.ts` mendukung pola komposisi shadcn; Button memakai Slot/CVA, dialog Radix, dan motion Framer. Lihat [referensi dan provenance](REFERENCES.md).

## Mock boundaries

Blob asli berada **tanpa enkripsi** di memori browser. Retrieval mengembalikan byte tersebut untuk menguji interaksi/transport; tidak membuktikan cipher. Mock memeriksa extension/size dan signature dasar, bukan validasi DOCX mendalam atau deteksi malware. Dataset video awal adalah MP4 H.264 sintetis 10 detik yang valid. Profil dummy tidak berisi data nyata.

Role/ownership/assignment/status/version diperagakan di API mock. Hal ini bukan kontrol keamanan server. Lab menggunakan angka ilustrasi tetap; fixture/pengulangan tidak mengubah angka mock. CSV berlabel SIMULATED. Hash, raw samples, throughput, memori, lingkungan eksekusi dan tamper tests backend belum diukur. Jangan memakai hasil mock untuk laporan.

Preferensi tema saja disimpan di localStorage. Profil detail diminta ketika pemilik menekan lihat, lalu dibersihkan ketika dialog ditutup. Cache form edit sementara memakai gcTime 0; logout/session expiry menghapus query cache. Blob preview URL dicabut setelah ditutup. Navigasi link/reload memperingatkan perubahan belum disimpan; browser history belum memiliki blocking penuh.

`public/mockServiceWorker.js` mempertahankan registration ketika `CLIENT_CLOSED` untuk menghindari race `update()` pada full reload di Edge. Client yang tidak mengaktifkan MSW tetap bypass; fix ini tidak mempersist data. Metadata `msw.workerDirectory` sengaja tidak diset agar postinstall tidak menimpa worker yang dikelola di repo. Saat menaikkan versi MSW, regenerasi worker secara manual, tinjau perubahan upstream, lalu terapkan kembali penyesuaian lifecycle ini dan jalankan tes reload.

## Backend integration status

**Backend di `../backend` masih versi vault lama.** Ia tidak menyediakan role/display_name, case/assignment endpoints, AES-GCM layered envelope atau lab fixture contract baru. Jangan menyalakan mode live untuk demo baru sampai kontraknya diimplementasikan. Session legacy ditolak FE dengan pesan kontrak, bukan diasumsikan kompatibel.

Untuk implementasi BE berikutnya: prefix `/api/v1`, same-origin credentials, CSRF mutation, owner dari session, reviewer scope server, no-store, expected version/409, dan satu retrieval berlapis sementara sesuai D-01. MySQL tetap target database. Proxy FE 34 MiB mendukung rencana MP4 30 MiB plus multipart, tetapi limit BE/storage harus diselaraskan.

Mode live kelak memakai `NEXT_PUBLIC_API_MODE=live`, `API_ORIGIN=http://127.0.0.1:8000`, restart/rebuild. Ini konfigurasi integrasi, bukan klaim endpoint baru sudah tersedia.

## Verify

```powershell
npm.cmd run build
npm.cmd run typecheck
npm.cmd run test:e2e
```

Playwright memulai server production di port 3100 dan memakai Microsoft Edge terpasang. Sesuaikan channel bila browser berbeda. Harus build mock lebih dulu. HTML report di `playwright-report/`, screenshot terbaru `artifacts/bankkyc-*`; screenshot lama vault disimpan sebagai riwayat dan tidak merepresentasikan FE baru.

[DESIGN.md](DESIGN.md) mencatat alasan visual dan dials antislop. [ANTISLOP_QA.md](ANTISLOP_QA.md) mencatat hasil dan coverage aktual.

## Brand

[GSM v0.1](../VELTRIX_GSM_v0.1.md) tetap sumber warna/logo/font. Simbol SVG adalah rekonstruksi referensi PNG, bukan master artwork. `/brand/preview.html` menyediakan katalog aset. `BrandLogo` dipakai bersama pada landing/auth/sidebar/loading/not-found. Script `scripts/build-brand-assets.mjs` hanya menghasilkan turunan SVG/font merek, bukan patch UI.
