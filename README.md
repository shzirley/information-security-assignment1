# VELTRIX BankKYC — Fullstack dengan database persisten

Frontend Next.js telah dihubungkan ke **backend FastAPI BankKYC** dalam mode **live**. Database lokal otomatis menggunakan **SQLite** di `backend/data/bankkyc.db`. Opsi MySQL tersedia melalui SQLAlchemy dan migrasi Alembic. Backend vault lama tetap ada sebagai referensi dan tes regresi; server default sekarang melayani kontrak BankKYC.

## Mulai di Windows

1. Ekstrak ZIP ke folder biasa, jangan menjalankannya dari dalam ZIP.
2. Pasang **Python 3.11+**, **Node.js 22+**, dan **FFmpeg** (perintah `ffprobe` diperlukan untuk unggahan video). Aktifkan PATH saat instalasi. Jika FFmpeg memakai lokasi khusus, isi `FFPROBE_PATH` di `backend/.env`.
3. Klik dua kali **`start.bat`**. Pada proses pertama diperlukan internet untuk memasang dependensi. Script membuat environment, kunci lokal, database dan tabel; menyiapkan akun demo; lalu menjalankan backend dan frontend.
4. Buka **http://127.0.0.1:3000**. Username/password demo acak ditampilkan di terminal dan disimpan pada `backend/data/demo-accounts.txt`. Pemohon juga dapat membuat akun sendiri melalui halaman Daftar.
5. Biarkan terminal terbuka. Gunakan Ctrl+C untuk menghentikan server. Data yang sudah disimpan tetap ada ketika aplikasi dijalankan kembali.

Linux/macOS: `bash start.sh` dengan prasyarat yang sama. Panduan rinci: [PANDUAN_MENJALANKAN.md](PANDUAN_MENJALANKAN.md).

## Data yang benar-benar tersimpan

| Data | Penyimpanan |
| --- | --- |
| Akun dan peran | Username unik, hash password Argon2id, label akun, status aktif |
| Sesi | Hash token dan masa berlaku; logout mencabut sesi |
| Pengajuan | Draf, nomor referensi, status, versi, konfirmasi data sintetis dan waktu |
| Profil pribadi | Delapan field lengkap; setiap penyimpanan menjadi versi terenkripsi baru |
| Bukti | Seluruh byte asli PNG/JPEG/PDF/DOCX/MP4, nama file privat, kategori dan seluruh versi |
| Penugasan | Reviewer aktif, pemberi tugas dan waktu penugasan |
| Riwayat | Event perubahan dan catatan revisi/penolakan terenkripsi |
| Lab | Hasil pengukuran aktual, ringkasan, seluruh sampel mentah dan lingkungan eksekusi |
| Audit | Unduhan, penolakan akses dan kegagalan integritas dengan metadata minimum |

Pilih **Simpan & lanjutkan** untuk profil dan **Unggah berkas** untuk bukti. Memilih file atau mengetik di form tanpa menekan simpan belum melakukan penyimpanan. Memuat ulang halaman tidak menghapus data yang sudah berhasil disimpan.

## Alur empat peran

- **Pemohon:** daftar/login → buat draf → isi profil → unggah identitas, dokumen, video → kirim → pantau/revisi. Pemilik dapat mengunduh berkas, termasuk versi lama, dengan byte yang sama.
- **Admin:** buka Penugasan → pilih reviewer untuk pengajuan terkirim. Admin tidak menerima profil, nama berkas privat, isi catatan atau unduhan pemohon.
- **Reviewer:** hanya melihat pengajuan yang ditugaskan → mulai tinjauan metadata → minta revisi, terima atau tolak. Profil/unduhan tetap khusus pemilik.
- **Evaluator:** jalankan benchmark/verifikasi terhadap fixture sintetis terpisah → riwayat dan CSV aktual. Lab tidak membaca pengajuan pemohon.

Daftar publik selalu membuat akun pemohon. Peran lain hanya dapat dibuat melalui CLI operator. Akun demo bukan akun berpassword `veltrix123`: password dibuat acak pada komputer Anda.

## Backend dan database

- [Panduan backend](backend/README.md): setup manual, API, skema, migrasi, MySQL, backup/restore dan tes.
- `backend/kyc/`: implementasi BankKYC baru; `backend/app/server.py` adalah entry point server.
- `backend/migrations/`: Alembic, migrasi awal `0001_bankkyc`.
- `backend/schema-mysql.sql`: referensi DDL MySQL; gunakan migrasi untuk inisialisasi sebenarnya.
- `backend/openapi.json`: spesifikasi API; Swagger tersedia di http://127.0.0.1:8000/docs ketika backend berjalan.
- [VERIFIKASI.md](VERIFIKASI.md): hasil pemeriksaan aktual dan batas yang belum diuji.

Profil, berkas, nama file dan catatan dienkripsi sebelum masuk database. Envelope operasional mengikuti baseline akademik PRD: RC4(drop3072) → DES-CBC → AES-256-GCM, dengan material kunci baru per objek dan key bundle terbungkus KEK. Hanya ciphertext final disimpan. RC4/DES dipertahankan untuk tugas akademik; paket ini adalah prototipe data sintetis, bukan layanan pembukaan rekening bank produksi.

## Backup yang perlu dijaga

**Jangan menghapus `backend/data/` atau mengganti kunci dalam `backend/.env`.** Database menyimpan data terenkripsi, sedangkan `.env` menyimpan kunci untuk memulihkannya. Cadangkan keduanya secara terpisah. Berkas ZIP yang dibagikan berisi source; database dan kunci lokal baru dibuat saat Anda menjalankannya.

```powershell
cd backend
.venv\Scripts\python.exe manage.py backup D:\Backup\bankkyc-2026-10-27.db
```

Perintah backup menggunakan SQLite backup API sehingga konsisten dengan WAL. Untuk MySQL gunakan prosedur pada panduan backend.

Dokumen PRD asli tetap tersedia sebagai referensi rancangan. Pernyataan status mock/legacy di dokumen historis tersebut tidak menggantikan README dan laporan verifikasi implementasi ini.
