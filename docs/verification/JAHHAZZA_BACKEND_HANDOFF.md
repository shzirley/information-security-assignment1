# Handoff backend VELTRIX BankKYC

Pekerjaan ini melanjutkan ZIP serah terima Jorell dan mengikuti bagian B (Caca, Backend Lead & System Integration) sebagai cakupan Jahazza. Entry point aktif adalah `backend/app/server.py`. Seluruh skenario demo memakai data sintetis.

## Cara menjalankan di Windows

Untuk instalasi baru, ekstrak ZIP lalu buka `start.bat`. Launcher menjalankan setup, migrasi, provisioning akun demo, FastAPI, serta Next.js. Buka `http://127.0.0.1:3000`. Akun demo lokal tersedia di `backend/data/demo-accounts.txt` setelah provisioning.

Jika sudah memiliki instalasi dengan data, gunakan database dan `backend/.env` dari instalasi itu. Buat backup SQLite lewat CLI versi lama sebelum mengganti kode. Jalankan dari folder `backend` di terminal VS Code.

```powershell
.\.venv\Scripts\python.exe manage.py backup ..\bankkyc-sebelum-0002.db
```

Simpan salinan `.env` secara terpisah karena memuat KEK. Uji peningkatan pertama kali dengan arahkan `KYC_DATABASE_URL` ke salinan database di lingkungan lokal. Bila verifikasi berhasil, kembalikan URL ke database kerja, lalu jalankan migrasi dan start dengan kunci yang sama.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
```

Instal dependensi tambahan jika akan mendemokan OCR gambar. Model Paddle yang dipakai Jorell perlu tersedia pada cache lokal. Percobaan pertama bisa memerlukan unduhan model. Jika pemrosesan gambar gagal atau mencapai batas 60 detik, panel mengarahkan reviewer untuk meneruskan pemeriksaan manual.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
```

## Pekerjaan C-BE-01 hingga C-BE-05

| Bagian | Implementasi |
| --- | --- |
| C-BE-01 | Alembic `0002_document_review` menambah subtype, checklist, hasil analisis, dan field audit. SQLite tetap menjadi default. |
| C-BE-02 | Reviewer terotentikasi, ditugaskan, dan berada pada status aktif sebelum menerima profil minimum atau bukti versi terbaru. Endpoint unduh asli tetap memeriksa kepemilikan pemohon. |
| C-BE-03 | Keputusan mengharuskan checklist untuk setiap bukti wajib dan alasan dari reviewer. Checklist dan alasan tersimpan dalam envelope terenkripsi. Perubahan status, event keputusan, dan audit berada dalam satu transaksi dengan pemeriksaan versi. |
| C-BE-04 | Adapter memakai parser dan OCR Jorell dalam satu proses pekerja lokal per proses FastAPI. Pekerja digunakan ulang dan dihentikan jika melewati 60 detik. PDF digital dan DOCX dapat diproses dengan dependensi backend utama. |
| C-BE-05 | Tes backend mencakup subtype, role, pratinjau, analisis terenkripsi, persistensi, konflik versi, dan alur revisi. Integrasi Next.js live menyediakan pratinjau, checklist, alasan keputusan, dan tampilan perbandingan. |

## Keputusan skema

Kategori `identity`, `document`, dan `video` tetap dipakai untuk penyimpanan serta pemulihan. Tabel `evidence_document_types` menyimpan subtype tanpa mengubah indeks unik dan urutan versi lama. Formulir dan KK berbagi urutan versi kategori `document`, tetapi versi aktifnya dipilih masing-masing. Record lama `document` tampil sebagai `legacy_supporting_document` dan tetap dapat memenuhi slot formulir untuk kompatibilitas. Pada data baru, API membedakan `account_opening_form` dan `kk_optional`.

Hasil dari `document_analyses` dipilih berdasarkan ID bukti dan ID versi profil aktif. Payload sensitif dan metadata ikatan bukti/profil memakai authenticated recovery yang sama dengan berkas. Penggantian bukti atau profil membuat hasil sebelumnya tidak berlaku untuk pasangan terbaru. Checklist berlaku pada versi kasus yang disimpan dan terikat dengan identitas reviewer. Akses pratinjau diaudit menggunakan ID actor, aplikasi, bukti, waktu, dan hasil operasi.

## Kontrak API untuk tim

Prefix untuk semua path di bawah adalah `/api/v1`. `id` adalah ID pengajuan dan `eid` adalah ID bukti. Mutation menggunakan sesi dan CSRF yang sama seperti alur existing.

| Metode dan path | Input dan respons |
| --- | --- |
| `POST /applications/{id}/evidence` | Multipart `category`, `version`, `file`, dan `document_type` opsional. Category `identity` berpasangan dengan `ktp`. Category `document` menerima `account_opening_form` atau `kk_optional`. Category `video` berpasangan dengan `verification_video`. |
| `GET /applications/{id}/review/profile` | `{profile:{full_name,identity_number,date_of_birth,address}}`. |
| `GET /applications/{id}/evidence/{eid}/review-preview` | PNG/JPEG/PDF/MP4 langsung sebagai konten `inline`. DOCX dikirim sebagai `text/plain` yang dibatasi 32.000 karakter. Untuk UI PDF, tambahkan `?page=1` agar menerima `{page,pages,image_base64}` berisi hasil render PNG. Video di UI diputar dari satu Blob privat. |
| `GET /applications/{id}/review/checks` | `{version,review}`. `review` bernilai `null` sebelum checklist tersimpan untuk versi kasus aktif. |
| `POST /applications/{id}/review/checks` | `{version,checks}`. Kembalikan `{version,review:{checks}}`, dengan versi kasus baru sebagai versi untuk keputusan. |
| `GET /applications/{id}/evidence/{eid}/analysis` | Hasil tersimpan untuk pasangan bukti/profil aktif. `404 ANALYSIS_NOT_FOUND` sebelum analisis. |
| `POST /applications/{id}/evidence/{eid}/analysis` | Jalankan parser/OCR sinkron terbatas waktu, atau baca ulang hasil selesai untuk pasangan bukti/profil yang sama. `429 ANALYSIS_BUSY` saat pekerja terpakai. Hasil `FAILED` bisa dicoba lagi dan tetap mengizinkan review manual. |
| `POST /applications/{id}/actions` | Untuk `accept`, `reject`, atau `request-revision`, kirim `{action,version,note}`. Pakai versi dari checklist tersimpan dan alasan 10–500 karakter. |

Reviewer dapat membuka profil, preview, dan analisis pada `SUBMITTED`, `RESUBMITTED`, atau `UNDER_REVIEW`. Checklist baru dan keputusan tersedia pada `UNDER_REVIEW`. Peran lain ditolak dengan `403`, reviewer di luar penugasan memperoleh `404`, dan perubahan dengan versi usang memperoleh `409`. Respons privat memakai `Cache-Control: no-store` dan `X-Content-Type-Options: nosniff`.

Contoh satu item dalam array `checks` untuk KTP yang tanggal lahirnya berbeda. Payload harus juga menyertakan checklist untuk formulir dan video.

```json
{
  "evidence_id": "<id bukti KTP>",
  "evidence_version": 1,
  "readable": true,
  "correct_document_type": true,
  "matches_applicant_form": false,
  "needs_clarification": true,
  "reason_code": "MISMATCH",
  "note": "Tanggal lahir pada bukti berbeda dari profil."
}
```

`VERIFIED` cocok dengan kondisi terbaca, tipe sesuai, data cocok, dan tanpa kebutuhan klarifikasi. Kode `UNREADABLE`, `WRONG_DOCUMENT_TYPE`, `MISMATCH`, dan `CLARIFICATION` harus sesuai dengan flag terkait dan disertai catatan per dokumen. Penerimaan simulasi membutuhkan checklist yang lolos. Revisi dan penolakan membutuhkan setidaknya satu temuan.

## Bukti verifikasi

| Skenario | Hasil |
| --- | --- |
| Migrasi SQLite baru dan salinan baseline `0001` | Lulus. Profil, dua versi, dan SHA-256 kedua berkas lama dipulihkan dengan KEK yang sama. |
| Regresi pytest dengan OCR gambar dikecualikan | 79 lulus, 3 tes OCR gambar dikecualikan. |
| Next.js typecheck dan production build | Lulus. |
| `python scripts/smoke_kyc_live.py` melalui proxy Next.js dan FastAPI | Lulus. Registrasi, sesi dan rotasi CSRF, upload, unduh byte-identical PNG/PDF/MP4, profil, submit, dan logout. |
| Chromium headless pada server live | Lulus. Reviewer membuka profil dan konten PNG/PDF/MP4, membaca mismatch dari analisis PDF digital, menyimpan checklist, meminta revisi, dan akses reviewer tanpa penugasan ditolak. |
| OCR gambar PaddleOCR | Belum terverifikasi penuh. Inisialisasi model terhenti saat mengunduh model UVDoc. Tes kegagalan worker memastikan fallback manual, sementara PDF digital dan DOCX diuji dengan fixture sebenarnya. |
| MySQL, GitHub PR, dan pengujian lintas anggota | Belum dilakukan pada paket ini. |

Perintah regresi dari folder `backend`.

```powershell
python -m pytest -q -k "not service_ktp_clear_puput_match and not service_ktp_intentional_mismatch and not service_non_ktp_rejection"
python scripts/smoke_kyc_live.py
```

Gunakan `docs/guides/VELTRIX_Assignment1_Revision_Task_Distribution.md` sebagai pembagian kerja tim. Slot unggah KK sudah tersedia pada API. Form pemohon dalam ZIP ini masih memakai tiga slot unggah wajib yang sudah ada.
