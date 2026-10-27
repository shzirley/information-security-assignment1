# Panduan menjalankan VELTRIX BankKYC

Jalankan perintah dari root repository kecuali bagian terkait menyebut folder lain. Lokasi panduan di `docs/guides/` tidak mengubah folder kerja perintah. Lihat juga [indeks dokumentasi](../README.md) dan [panduan backend](../../backend/README.md).

## 1. Persiapan

Ekstrak seluruh isi ZIP. Disarankan lokasi singkat seperti `C:\VELTRIX_BankKYC`. Siapkan:

- Python 3.11 atau lebih baru, dengan opsi Add Python to PATH.
- Node.js 22 atau lebih baru, termasuk npm.
- FFmpeg, termasuk `ffprobe`, untuk pemeriksaan struktur dan durasi video.
- Internet pada instalasi dependensi pertama.

Periksa melalui Command Prompt:

```bat
python --version
node --version
npm.cmd --version
ffprobe -version
```

Jika `python` belum dikenali tetapi Python Launcher tersedia, gunakan `py -3 --version`. `start.bat` mendukung kedua cara tersebut. Jika FFmpeg belum tersedia, profil, gambar dan dokumen tetap dapat digunakan; unggahan video mengembalikan pesan pemeriksa belum tersedia sampai ffprobe dipasang.

## 2. Jalankan otomatis

Klik dua kali `start.bat`, atau:

```bat
cd /d C:\VELTRIX_BankKYC
start.bat
```

Proses pertama memasang dependensi; jangan menutup terminal sebelum selesai. Proses berikutnya menggunakan environment dan database yang sama. Halaman aplikasi: **http://127.0.0.1:3000**. Backend: **http://127.0.0.1:8000/docs**.

Password demo berbeda untuk setiap akun dan dibuat acak. Buka `backend/data/demo-accounts.txt` atau lihat terminal lokal. Akun yang sudah ada tidak direset oleh proses startup.

| Username | Peran |
| --- | --- |
| demo_user | Pemohon |
| reviewer_demo | Reviewer |
| reviewer_other | Reviewer kedua untuk uji penugasan |
| admin_demo | Admin penugasan |
| evaluator_demo | Evaluator lab |

Akun baru melalui halaman Daftar selalu menjadi pemohon. Username/password disimpan di database; login tidak lagi mengandalkan akun mock browser.

## 3. Contoh alur lengkap

1. Login sebagai pemohon, pilih pengajuan baru lalu Buat draf & mulai.
2. Isi seluruh delapan field dengan data sintetis. Nomor identitas misalnya `DUMMY-2026-001`; email `nara@example.com`; telepon `080000000001`; tanggal lahir valid di masa lalu.
3. Tekan **Simpan & lanjutkan**. Profil sudah masuk database saat tombol berhasil.
4. Pilih identitas PNG/JPG/PDF maksimal 5 MiB lalu tekan **Unggah berkas**.
5. Unggah dokumen PDF/DOCX maksimal 10 MiB, lalu video MP4 berdurasi 10–30 detik maksimal 30 MiB. Setiap pemilihan harus diikuti tombol Unggah.
6. Tinjau kelengkapan 4/4, centang konfirmasi data sintetis, lalu kirim.
7. Logout. Login sebagai admin lalu tugaskan pengajuan ke reviewer.
8. Logout. Login sebagai reviewer yang dipilih, buka antrean, mulai tinjauan metadata, lalu minta revisi atau berikan keputusan.
9. Jika revisi diminta, pemohon dapat memperbarui profil/berkas dan mengirim ulang. Unggah ulang menghasilkan versi tambahan; versi sebelumnya tetap tersedia.
10. Tutup dan jalankan kembali aplikasi. Login dan buka pengajuan yang sama untuk melihat data tersimpan.

Untuk video uji kecil, gunakan `backend/fixtures/verification-demo.mp4`. Untuk identitas/dokumen gunakan berkas sintetis valid milik Anda. Backend memeriksa isi format sehingga mengganti ekstensi saja akan ditolak.

## 4. Penyimpanan dan backup

Database lokal: `backend/data/bankkyc.db`. File ini menyimpan akun, sesi, pengajuan, profil, byte lengkap seluruh bukti dan versinya, catatan, penugasan, histori dan hasil lab. SQLite dapat membuat file `-wal`/`-shm` saat berjalan; jangan menyalin hanya `.db` secara manual saat server aktif.

Kunci lokal: `backend/.env`. **Simpan cadangan kunci secara terpisah. Kunci yang hilang tidak bisa dibuat ulang untuk membuka data lama.** Startup memeriksa kecocokan kunci dan database, lalu menolak jika tidak cocok.

Backup:

```bat
cd backend
.venv\Scripts\python.exe manage.py backup C:\Backup\bankkyc-backup.db
```

Gunakan nama backup baru. Perintah menolak menimpa backup lama. Cadangkan `.env` ke lokasi terlindungi yang terpisah.

Restore SQLite: hentikan kedua server, simpan database aktif ke lokasi lain dahulu, salin hasil backup menjadi `backend/data/bankkyc.db`, pertahankan `.env` yang sesuai, lalu jalankan kembali. Jika terdapat `bankkyc.db-wal`/`-shm` lama, pindahkan bersama database lama setelah server berhenti; jangan mencampurkan sidecar lama dengan file backup baru. Jangan menjalankan dua salinan aplikasi ke file database restore yang sama.

## 5. Masalah yang sering muncul

| Masalah | Tindakan |
| --- | --- |
| Port 3000 atau 8000 sedang dipakai | Tutup server lama lalu jalankan ulang; launcher tidak mengambil alih proses lain |
| npm/Python tidak dikenali | Pasang ulang atau perbaiki PATH, lalu buka terminal baru |
| Instalasi paket terputus | Perbaiki koneksi lalu jalankan `start.bat` kembali |
| Pemeriksa video belum tersedia | Pasang FFmpeg/ffprobe; atau isi `FFPROBE_PATH=C:/ffmpeg/bin/ffprobe.exe` di `backend/.env` dan restart |
| Login demo gagal | Gunakan password lokal di `backend/data/demo-accounts.txt`, bukan password mock sebelumnya |
| Database dan kunci tidak cocok | Pulihkan `.env` asli yang digunakan ketika database dibuat; jangan mengganti kunci dengan nilai acak |
| Pengajuan berubah / konflik versi | Muat ulang detail, periksa perubahan terbaru, kemudian ulangi penyimpanan |
| Profil belum tersimpan | Lengkapi seluruh field lalu tekan Simpan & lanjutkan |
| Tampilan masih mode mock | Jalankan `backend/.venv/Scripts/python.exe backend/setup_env.py --live` dari folder utama, hentikan server lama lalu jalankan ulang; production build perlu dibangun ulang |

Windows memakai `.venv\Scripts\python.exe`; Linux/macOS memakai `.venv/bin/python`. Jalankan `bash start.sh` untuk launcher di Linux/macOS.
