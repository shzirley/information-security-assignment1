# Hasil verifikasi implementasi

Tanggal: 27 Oktober 2026. Dataset seluruhnya sintetis. Pengujian dilakukan pada Linux, Python 3.12 dan Node.js 24.22.1; versi dependensi Python dicatat pada `backend/constraints-tested.txt`, dependensi frontend pada `frontend/package-lock.json`.

| Pemeriksaan | Hasil aktual |
| --- | --- |
| Seluruh tes backend dengan SQLite | **65 passed**: 37 tes BankKYC dan 28 tes regresi backend legacy |
| BankKYC pada MySQL 8.0.46 nyata | **36 passed, 1 skipped**; tes backup SQLite dilewati karena tidak berlaku pada MySQL |
| Pemeriksaan dependency Python | `pip check`: tidak ada dependency rusak |
| Frontend TypeScript | `npm run typecheck`: lulus |
| Frontend production build | `npm run build`: lulus; seluruh route BankKYC terbangun |
| HTTP live melalui Next.js → FastAPI | Lulus daftar/login/rotasi CSRF, buat draf, simpan profil, unggah/unduh ketiga kategori, submit, daftar ulang dan logout |
| Byte asli | Profil canonical serta PNG/PDF/MP4 kembali sama persis; DOCX juga diuji round-trip pada suite API |
| Persistensi | Engine/aplikasi baru membaca database yang sama; profil, semua versi, sesi dan hasil lab tetap tersedia |
| Backup SQLite | Backup konsisten via SQLite backup API dipulihkan ke aplikasi lain dengan kunci asli; profil dapat dibuka |
| Ukuran unggahan | Gambar valid 5 MiB dan MP4 valid 30 MiB diterima; lebih satu byte ditolak; tidak terjadi spool rollover plaintext ke disk |
| Batas stream | Body berlebihan tanpa Content-Length ditolak; versi kasus tidak berubah |
| Concurrency | Dua koneksi/klien dengan expected version sama: satu commit dan satu 409, tanpa versi ganda |
| Atomic rollback | Kegagalan event DB yang diinjeksi membatalkan profil, objek, versi kasus dan event sebagai satu transaksi |
| Akses | Pemilik lain, parent ID berbeda, reviewer lama setelah reassignment, admin dan evaluator tidak mendapat payload pemohon |
| State machine | Submit tidak lengkap, edit terkunci, keputusan tanpa status yang sesuai dan perubahan terminal ditolak tanpa event sebagian |
| Integritas | Ciphertext, tag, nonce, IV, wrapped bundle, key salah dan konteks owner salah ditolak; tidak mengirim plaintext sebagai HTTP 200 |
| Lab | Empat fixture × empat kandidat, masing-masing 2 warm-up + **100 trial terukur**; 400 raw samples/run tersimpan dan diekspor aktual |
| Cleanup | Dry-run tidak menghapus; apply pada satu kasus menghapus seluruh relasi kasus tersebut dan mempertahankan akun/kasus lain |

Satu peringatan deprecation berasal dari kombinasi Starlette TestClient dan httpx. Peringatan itu tidak menyebabkan kegagalan pengujian; penggunaan httpx pada tool smoke live tetap berhasil.

## Hash fixture pada uji HTTP live

- PNG: `4ab0f3fd96e64619ac50be4554183d37e7a84fbd114e2cdddcd2355a7f9fa3e3`
- PDF: `22c4eb0af09cbe6ab4b66629d8233505d4fe24a2be3b5be19cc55302e0376497`
- MP4: `696adf82406c8649d27867c404e05eba51eb6613c2bef6ad7d6b033a56be99b3`

Hash tersebut membandingkan input dan hasil download pada fixture yang sama; bukan hasil benchmark kecepatan. Script reproduksi: `backend/scripts/smoke_kyc_live.py` setelah kedua server dijalankan.

## Batas pemeriksaan

- MySQL yang benar-benar diuji adalah **8.0.46**. File Docker opsional memilih 8.4; container 8.4 tidak dijalankan dalam pemeriksaan ini.
- Windows `start.bat` dan launcher diperiksa struktur/sintaks alurnya; tidak dieksekusi pada mesin Windows. Versi Python yang dijalankan pada pengujian ini adalah 3.12, bukan 3.11.
- Alur HTTP live melalui frontend proxy diuji. Otomasi klik browser penuh tidak dijalankan karena executable browser tidak tersedia; pengunduhan browser pada lingkungan pemeriksaan gagal. Frontend UI asli tetap dipertahankan dan lulus typecheck/build.
- Restore backup MySQL, uji beban banyak pengguna, reverse proxy HTTPS produksi, crash/power-loss OS, audit keamanan independen dan corpus video 10–30 MiB representatif belum dijalankan.
- MP4 30 MiB pada tes batas merupakan video sintetis 10 detik dengan box free tambahan yang valid. Itu menguji jalur ukuran/persistensi, bukan throughput video kompleks.
- Fixture video lab berukuran kecil (8.664 byte). Hasil lab tidak mewakili performa semua dokumen/video besar.
- Validasi format bukan antivirus, pemeriksaan identitas atau biometrik. Implementasi menggunakan baseline cipher akademik berlapis dari PRD, dengan keputusan penilaian berlabel demo.

Paket source tidak menyertakan `.env` rahasia, database pengujian, akun lokal maupun virtualenv/node_modules. Konfigurasi frontend nonrahasia sudah live. Database, kunci dan password demo dibuat secara lokal ketika launcher pertama kali dijalankan.
