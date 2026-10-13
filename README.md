# VELTRIX — Front-end + Back-end

Proyek tugas keamanan informasi: vault data pribadi/file dan perbandingan AES, RC4, serta DES. Front-end Next.js dari proyek awal sekarang tersambung ke **FastAPI + SQLAlchemy**, dengan enkripsi nyata dan database persisten.

## Menjalankan di Windows

Ekstrak ZIP. Buka terminal di folder proyek. Perlu Python 3.11+ dan Node.js 22+.

**Terminal 1 — back-end:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_env.py
.\.venv\Scripts\python.exe -m uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — front-end, mulai dari folder proyek:**

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Buka **http://127.0.0.1:3000/register**, buat akun baru, lalu login. Mode live tidak menyediakan akun/password demo. Upload file atau buat profil untuk mengisi dashboard dan menjalankan Lab.

`setup_env.py` membuat kunci rahasia lokal di `backend/.env` dan menyiapkan `frontend/.env.local` dengan mode `live`. File konfigurasi yang sudah ada tidak ditimpa. Jika sebelumnya menggunakan mock, ubah `NEXT_PUBLIC_API_MODE=live` di `.env.local` lalu restart Next.js.

## Menjalankan di Linux/macOS

Terminal back-end:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python setup_env.py
.venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload
```

Terminal front-end:

```bash
cd frontend
npm ci
npm run dev
```

## Fitur yang tersambung

- Register, login, logout, sesi cookie HttpOnly, Argon2id, proteksi CSRF, dan pembatasan percobaan login.
- Dashboard menghitung file, ukuran asli, ukuran ciphertext, dan status profil dari database.
- Upload, cari/filter, detail, download dan hapus file dengan pemeriksaan pemilik.
- Setiap file/profil memiliki AES-256-CBC, RC4, dan DES-CBC; integritas diperiksa sebelum dekripsi.
- Nama file dan konten profil juga terenkripsi saat disimpan. Payload asli tidak disimpan ke disk oleh back-end.
- Profil: buat, edit, tampilkan dengan pilihan algoritma, dan hapus.
- Benchmark nyata: 10–30 pengulangan, 2 warm-up per algoritma, mean/median/sample SD, pemeriksaan round trip, histori persisten, dan CSV.
- Uji download berulang menggunakan pengukuran browser dan ekspor CSV.

## Database

**Default SQLite** langsung berjalan tanpa instalasi database tambahan. Database dibuat di `backend/data/veltrix.db`. **MySQL** didukung melalui konfigurasi `DATABASE_URL`; petunjuk ada di [backend/README.md](backend/README.md). Tabel dibuat otomatis saat server dimulai.

Jangan menghapus/mengganti `VELTRIX_MASTER_KEY` setelah menyimpan data. Kunci lama diperlukan untuk dekripsi dan harus dicadangkan bersama database. ZIP ini tidak menyertakan kunci rahasia, akun uji, database, atau `node_modules`.

## Pengujian

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd frontend
npm.cmd run build
npm.cmd run typecheck
```

Pengujian integrasi melalui kedua server yang sudah berjalan:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts/smoke_live.py --large-upload
```

Pengujian ini membuat akun dummy baru di database pengujian/lokal. Rincian hasil dan batas verifikasi ada di [BACKEND_VERIFICATION.md](BACKEND_VERIFICATION.md).

API interaktif: **http://127.0.0.1:8000/docs**. Kontrak front-end tetap di `frontend/src/lib/api.ts` dan `contracts.ts`.

## Konteks tugas

RC4 dan DES tetap tersedia untuk kebutuhan perbandingan akademik. Aplikasi adalah MVP tugas, dengan enkripsi di sisi server; gunakan data dummy. File upload dibatasi berdasarkan ekstensi/kategori dan ukuran; tidak mencakup antivirus atau validasi mendalam format file.

Dokumen PRD/blueprint dan aset desain asli tetap disertakan. Dokumen tersebut mencatat rencana awal; README dan kode back-end menjelaskan implementasi yang tersedia saat ini. Mode mock masih dapat digunakan dengan `NEXT_PUBLIC_API_MODE=mock`, tetapi hasilnya tetap simulasi.
