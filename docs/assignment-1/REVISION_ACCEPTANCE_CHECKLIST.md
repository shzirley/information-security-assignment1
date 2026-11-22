# Revision Acceptance & Demonstration Checklist (VELTRIX BankKYC)

> **Dokumen Verifikasi & Checklist Uji Coba Akhir Revisi Tugas 1**  
> **Repository:** `information-security-assignment1`  
> **Tanggung Jawab QA & Pelaporan:** Jorell (J-QA-05 / J-DOC-04)  
> **Status:** 18 skenario dijalankan pada 22 Nov 2026; hasil dan bukti di [bagian 3](#3-hasil-uji-end-to-end-22-november-2026)  
> **Standard Bukti:** Log eksekusi unit test, verifikasi integritas hash SHA-256, dan tangkapan layar review UI.

---

## 1. Ikhtisar Skenario Pengujian End-to-End (E2E)

Tabel berikut memetakan 18 skenario uji end-to-end yang disepakati untuk membuktikan pemenuhan seluruh catatan revisi asisten dosen:

| Case ID | Peran Pelaku | Skenario / Tindakan | Ekspektasi Hasil Sistem | Penanggung Jawab Bukti | Status (hasil diamati) |
|:-------:|:-------------|:-------------------|:------------------------|:----------------------:|:---------------:|
| **E2E-01** | Pemohon | Unggah file KTP dummy (PNG) | Validasi MIME lolos, terenkripsi envelope, versi tercatat | Angela / Caca | **PASSED** (diamati 22 Nov 2026) |
| **E2E-02** | Pemohon | Unggah formulir pembukaan rekening (PDF/DOCX) | Tipe formulir dikenali, terenkripsi saat disimpan | Angela / Caca | **PASSED** (diamati 22 Nov 2026) |
| **E2E-03** | Pemohon | Unggah video pernyataan sintetis (MP4, 10-30s) | Format MP4 diterima, terenkripsi, tersimpan aman | Angela / Caca | **PASSED** (diamati 22 Nov 2026) |
| **E2E-04** | Pemohon | Submit tanpa KTP/formulir/video wajib | Ditolak oleh validator backend (status incomplete) | Caca | **PASSED** (diamati 22 Nov 2026) |
| **E2E-05** | Pemohon | Submit tanpa dokumen Kartu Keluarga (KK) | **Diizinkan** (KK bersifat opsional) | Caca | **PASSED** (diamati 22 Nov 2026) |
| **E2E-06** | Assigned Reviewer | Buka pratinjau KTP, formulir, dan video | Konten substantif tampil di private authorized viewer | Angela / Caca / Maleka | **PASSED** (diamati 22 Nov 2026) |
| **E2E-07** | Unassigned Reviewer | Tebak URL preview bukti pemohon lain | Akses ditolak (`403 Forbidden`), tanpa kebocoran data | Caca / Maleka | **PASSED** (diamati 22 Nov 2026) |
| **E2E-08** | Admin / Evaluator | Buka pratinjau dokumen tanpa assignment | Akses ditolak (`403 Forbidden`), role admin bukan reviewer | Caca / Maleka | **PASSED** (diamati 22 Nov 2026) |
| **E2E-09** | Assigned Reviewer | Catat mismatch field & minta revisi | Catatan terenkripsi tersimpan, status berubah `REVISE` | Caca / Angela | **PASSED** (diamati 22 Nov 2026) |
| **E2E-10** | Pemohon | Unggah dokumen revisi baru & resubmit | Versi dokumen baru (v2) dibuat, riwayat audit tersimpan | Caca | **PASSED** (diamati 22 Nov 2026) |
| **E2E-11** | Sistem OCR | Baca KTP dummy jernih (`ktp_0001_clear.png`) | NIK, Nama, Tanggal Lahir terekstraksi 100% akurat | **Jorell** | **PASSED** (tes layanan) · **GAGAL** via layar reviewer (timeout) |
| **E2E-12** | Sistem OCR | Deteksi mismatch form vs KTP (`ktp_0004_mismatch`) | Status `REJECT_OR_REVISE`, tandai `has_mismatch=True` | **Jorell** | **PASSED** (tes layanan); belum diuji via layar reviewer |
| **E2E-13** | Sistem OCR | Baca dokumen sembarang / non-KTP / buram | `document_type: unknown`, `manual_review_required=True` | **Jorell** | **PASSED** (tes layanan); belum diuji via layar reviewer |
| **E2E-14** | Keamanan / Tamper | Modifikasi bit ciphertext atau AAD metadata | Dekripsi gagal diverifikasi (GCM Auth Tag Failure) | Maleka | **PASSED** (diamati 22 Nov 2026) |
| **E2E-15** | Data At Rest | Audit grep plaintext NIK/Nama di database SQLite | **Tidak ada plaintext PII** pada storage/tabel analisis | Maleka / Caca | **PASSED** (diamati 22 Nov 2026) |
| **E2E-16** | Owner / Verifier | Unduh dokumen asli setelah proses OCR | Dokumen terdekripsi identik byte-per-byte (SHA-256 cocok) | Maleka | **PASSED** (diamati 22 Nov 2026) |
| **E2E-17** | Evaluator | Buka halaman benchmark performa OCR & Cipher | Data benchmark riil terukur (bukan angka placeholder) | Angela / **Jorell** | **PASSED** (diamati 22 Nov 2026) |
| **E2E-18** | Sistem / Server | Restart server web & backend FastAPI | Seluruh riwayat analisis & status audit tetap persisten | Caca | **PASSED** (diamati 22 Nov 2026) |

---

## 2. Bukti Verifikasi Bagian Jorell (E2E-11, E2E-12, E2E-13, E2E-17)

### A. E2E-11: Ekstraksi KTP Jernih (Puput Nugroho)
* **Perintah Uji:** `pytest tests/test_document_analysis.py -k "test_service_ktp_clear_puput_match" -v`
* **Hasil:** `PASSED`
* **Bukti Ekstraksi:**
  - NIK: `2912541012827585` (Confidence: 0.999) $\rightarrow$ `MATCH`
  - Nama: `PUPUT NUGROHO` (Confidence: 0.988) $\rightarrow$ `MATCH`
  - Tanggal Lahir: `27-01-1950` / `1950-01-27` (Confidence: 0.992) $\rightarrow$ `MATCH`
  - Status Akhir: `VERIFIED_MATCH`, `manual_review_required: False`

### B. E2E-12: Deteksi Mismatch Identitas (KTP 0004 vs Form Puput)
* **Perintah Uji:** `pytest tests/test_document_analysis.py -k "test_service_ktp_intentional_mismatch" -v`
* **Hasil:** `PASSED`
* **Bukti Deteksi:**
  - KTP yang diunggah berisi NIK `3374020101910001` (Caturangga Yolanda).
  - Form permohonan berisi NIK `2912541012827585` (Puput Nugroho).
  - Sistem mendeteksi `result: "MISMATCH"` pada NIK, Nama, dan DOB.
  - Status Akhir: `REJECT_OR_REVISE`, `manual_review_required: True`, `has_mismatch: True`.

### C. E2E-13: Penolakan Dokumen Non-KTP & Foto Acak
* **Perintah Uji:** `pytest tests/test_document_analysis.py -k "test_service_non_ktp_rejection" -v`
* **Hasil:** `PASSED`
* **Bukti Rejection:**
  - Fixture: `dokumen_sembarang_1.jpeg` dan `dokumen_sembarang_2.jpeg`.
  - Sistem mengklasifikasikan dokumen sebagai `document_type: "unknown"`.
  - Tidak ada data palsu yang diloloskan (`fields: {}`).
  - Status Akhir: `manual_review_required: True` (0% False Acceptance).

### D. E2E-17: Data Benchmark Kuantitatif untuk Visualisasi Frontend
* **Sumber Data:** File evaluasi riil [`docs/assignment-1/OCR_EVALUATION.md`](OCR_EVALUATION.md).
* **Rangkuman Angka Pengukuran Asli:**
  - Akurasi Field Match KTP Jelas: **100% (3/3)**
  - Deteksi Intentional Mismatch: **100% (2/2)**
  - Rejection Dokumen Sembarang: **100% (2/2)**
  - Parsing Digital PDF Form: **100% (11/11 fields)**
  - Latensi Digital Form: **28 - 45 ms**
  - Latensi OCR KTP Gambar (Optimasi 1200px): **10 - 15 detik pada CPU lokal**

---

## 3. Hasil uji end-to-end (22 November 2026)

**Cara uji:** 18 skenario dijalankan di browser (Microsoft Edge lewat Playwright) terhadap aplikasi lokal dalam mode live: frontend Next.js di `127.0.0.1:3000`, backend FastAPI di `127.0.0.1:8001`, SQLite `backend/data/bankkyc.db`. Akun: pemohon baru `e2e_pemohon` (didaftarkan lewat halaman Register), `reviewer_demo` (ditugaskan), `reviewer_other` (tidak ditugaskan), `admin_demo`, `evaluator_demo`. Pengajuan utama: `VTX-2026-4EFA2346C21C2776`. Semua data sintetis.

**Tambahan di luar browser:** E2E-11 s.d. 13 dijalankan ulang dengan pytest (3 passed, 141,97 dtk). E2E-14 mengubah 1 bit ciphertext profil pengajuan uji terpisah langsung di SQLite, lalu pemilik mencoba membukanya lewat browser. E2E-15 memindai byte mentah `bankkyc.db` dan berkas WAL-nya; sebagai kontrol, username `e2e_pemohon` (memang disimpan sebagai teks biasa) terdeteksi oleh pemindaian yang sama. E2E-18 hanya me-restart backend; dev server frontend tetap berjalan.

| Case ID | Hasil | Yang diamati | Bukti |
|:-------:|:-----:|:-------------|:------|
| **E2E-01** | PASSED | KTP PNG diterima (mime image/png, v1, validasi format_checked); disimpan lewat jalur envelope terenkripsi | [e2e-01-ktp-uploaded](screenshots/e2e-01-ktp-uploaded.png) |
| **E2E-02** | PASSED | Formulir PDF diterima sebagai account_opening_form v1 | [e2e-02-form-uploaded](screenshots/e2e-02-form-uploaded.png) |
| **E2E-03** | PASSED | Video MP4 10 detik diterima (video/mp4, v1) | [e2e-03-video-uploaded](screenshots/e2e-03-video-uploaded.png) |
| **E2E-04** | PASSED | Submit pengajuan tanpa KTP/formulir/video ditolak backend: HTTP 422 CASE_INCOMPLETE; tombol Lanjutkan di langkah KTP terkunci sebelum berkas diunggah | [e2e-04-incomplete-step](screenshots/e2e-04-incomplete-step.png) |
| **E2E-05** | PASSED | Pengajuan VTX-2026-4EFA2346C21C2776 terkirim (status SUBMITTED) tanpa KK | [e2e-05-submitted-without-kk](screenshots/e2e-05-submitted-without-kk.png) |
| **E2E-06** | PASSED | Reviewer yang ditugaskan membuka isi asli: KTP dummy: tampil; Formulir pembukaan rekening: tampil; Video verifikasi: tampil | [e2e-06a-admin-assigns-reviewer](screenshots/e2e-06a-admin-assigns-reviewer.png), [e2e-06b-reviewer-preview-ktp](screenshots/e2e-06b-reviewer-preview-ktp.png), [e2e-06c-reviewer-preview-form](screenshots/e2e-06c-reviewer-preview-form.png), [e2e-06d-reviewer-preview-video](screenshots/e2e-06d-reviewer-preview-video.png) |
| **E2E-07** | PASSED | Reviewer lain menebak URL: review-preview HTTP 404 RESOURCE_NOT_FOUND, review/profile HTTP 404 RESOURCE_NOT_FOUND; halaman tidak menampilkan data | [e2e-07-unassigned-reviewer-denied](screenshots/e2e-07-unassigned-reviewer-denied.png) |
| **E2E-08** | PASSED | Admin tanpa penugasan: review-preview HTTP 403 ROLE_FORBIDDEN, review/profile HTTP 403 ROLE_FORBIDDEN | [e2e-08-admin-no-content](screenshots/e2e-08-admin-no-content.png) |
| **E2E-09** | PASSED | Checklist (formulir: MISMATCH + catatan) tersimpan; status menjadi NEEDS_REVISION. Catatan disimpan sebagai objek terenkripsi (dicek di E2E-15) | [e2e-09-reviewer-requests-revision](screenshots/e2e-09-reviewer-requests-revision.png) |
| **E2E-10** | PASSED | Status RESUBMITTED; versi formulir tersimpan: 1, 2; jejak: Pengajuan dibuat → Data pribadi diperbarui → Bukti identity versi 1 ditambahkan → Bukti document versi 1 ditambahkan → Bukti video versi 1 ditambahkan → Data pribadi diperbarui → Pengajuan dikirim → Reviewer ditugaskan → Tinjauan dokumen dimulai → Checklist bukti disimpan → Revisi diminta → Data pribadi diperbarui → Bukti document versi 2 ditambahkan → Pengajuan dikirim ulang | [e2e-10-resubmitted-v2](screenshots/e2e-10-resubmitted-v2.png) |
| **E2E-11** | PASSED (layanan) · **GAGAL** (UI) | `pytest -k test_service_ktp_clear_puput_match` PASSED. Diukur langsung: nama, NIK, tanggal lahir `MATCH`, tetapi butuh **53,6 dtk** (dingin) dan **37,8 dtk** (model sudah dimuat) di laptop uji. Lewat tombol *Jalankan analisis* di layar reviewer, analisis selalu gagal: worker dibatasi 60 dtk lalu dimatikan (dipanggil langsung ke backend: HTTP 200 `FAILED` setelah 60,5 dtk), dan proxy Next.js memutus request setelah 30 dtk sehingga browser menampilkan "Permintaan gagal" | [e2e-11-reviewer-ocr-analysis](screenshots/e2e-11-reviewer-ocr-analysis.png) |
| **E2E-12** | PASSED (layanan) | `pytest -k test_service_ktp_intentional_mismatch` PASSED. Tidak diuji lewat layar reviewer karena jalur UI gagal seperti E2E-11 | Log pytest |
| **E2E-13** | PASSED (layanan) | `pytest -k test_service_non_ktp_rejection` PASSED. Tidak diuji lewat layar reviewer karena jalur UI gagal seperti E2E-11 | Log pytest |
| **E2E-14** | PASSED | 1 byte ciphertext profil diubah di SQLite → pengambilan ditolak HTTP 500 INTEGRITY_CHECK_FAILED, tanpa plaintext | [e2e-14-tampered-ciphertext-rejected](screenshots/e2e-14-tampered-ciphertext-rejected.png) |
| **E2E-15** | PASSED | Pemindaian byte mentah bankkyc.db + WAL untuk nama, NIK dummy, tanggal lahir, email, dan catatan revisi: PUPUT NUGROHO=tidak ada, DUMMY-2026-0001=tidak ada, 1950-01-27=tidak ada, puput@example.com=tidak ada, Tanggal lahir pada formu=tidak ada | Pemindaian byte (lihat catatan) |
| **E2E-16** | PASSED | SHA-256 unduhan 22c4eb0af09cbe6a… vs berkas asli 22c4eb0af09cbe6a… | [e2e-16-owner-download](screenshots/e2e-16-owner-download.png) |
| **E2E-17** | PASSED | Halaman benchmark menjalankan eksperimen nyata; GET /lab/runs HTTP 200, 3 run tersimpan | [e2e-17-benchmark-live-run](screenshots/e2e-17-benchmark-live-run.png) |
| **E2E-18** | PASSED | Setelah backend di-restart: status RESUBMITTED, 14 entri jejak, 4 versi bukti tetap ada | [e2e-18-after-backend-restart](screenshots/e2e-18-after-backend-restart.png) |

### Temuan

1. **Analisis OCR tidak bisa dijalankan dari layar reviewer di laptop uji (E2E-11).** OCR-nya benar, tetapi butuh 38–54 dtk per KTP di CPU laptop ini, sedangkan catatan evaluasi menyebut 10–15 dtk. Worker analisis dibatasi 60 dtk dan dimatikan saat timeout, sehingga model selalu dimuat ulang dari awal; proxy Next.js juga memutus request setelah 30 dtk. Perlu diputuskan: naikkan batas waktu worker dan proxy, atau jalankan analisis secara asinkron.
2. **Nama berkas tampil sebagai "undefined" di layar reviewer** (terlihat di [e2e-06b](screenshots/e2e-06b-reviewer-preview-ktp.png)). Backend tidak mengirim `display_name` ke reviewer, sementara halaman detail menampilkannya untuk semua peran. Tidak membocorkan data, tetapi perlu dirapikan.
3. **Kegagalan integritas dijawab HTTP 500** (`INTEGRITY_CHECK_FAILED`, E2E-14). Perilakunya aman (gagal tertutup, tanpa plaintext), hanya kode statusnya yang perlu diperhatikan bila dosen menanyakan.
4. **Ekspektasi E2E-09** di tabel menyebut status `REVISE`; nama status sebenarnya di sistem adalah `NEEDS_REVISION`.
