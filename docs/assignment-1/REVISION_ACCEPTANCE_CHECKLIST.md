# Revision Acceptance & Demonstration Checklist (VELTRIX BankKYC)

> **Dokumen Verifikasi & Checklist Uji Coba Akhir Revisi Tugas 1**  
> **Repository:** `information-security-assignment1`  
> **Tanggung Jawab QA & Pelaporan:** Jorell (J-QA-05 / J-DOC-04)  
> **Status:** Siap Digunakan untuk Validasi Kolaboratif Tim & Asisten Dosen  
> **Standard Bukti:** Log eksekusi unit test, verifikasi integritas hash SHA-256, dan tangkapan layar review UI.

---

## 1. Ikhtisar Skenario Pengujian End-to-End (E2E)

Tabel berikut memetakan 18 skenario uji end-to-end yang disepakati untuk membuktikan pemenuhan seluruh catatan revisi asisten dosen:

| Case ID | Peran Pelaku | Skenario / Tindakan | Ekspektasi Hasil Sistem | Penanggung Jawab Bukti | Status Kesiapan |
|:-------:|:-------------|:-------------------|:------------------------|:----------------------:|:---------------:|
| **E2E-01** | Pemohon | Unggah file KTP dummy (PNG) | Validasi MIME lolos, terenkripsi envelope, versi tercatat | Angela / Caca | Siap Uji Tim |
| **E2E-02** | Pemohon | Unggah formulir pembukaan rekening (PDF/DOCX) | Tipe formulir dikenali, terenkripsi saat disimpan | Angela / Caca | Siap Uji Tim |
| **E2E-03** | Pemohon | Unggah video pernyataan sintetis (MP4, 10-30s) | Format MP4 diterima, terenkripsi, tersimpan aman | Angela / Caca | Siap Uji Tim |
| **E2E-04** | Pemohon | Submit tanpa KTP/formulir/video wajib | Ditolak oleh validator backend (status incomplete) | Caca | Siap Uji Tim |
| **E2E-05** | Pemohon | Submit tanpa dokumen Kartu Keluarga (KK) | **Diizinkan** (KK bersifat opsional) | Caca | Siap Uji Tim |
| **E2E-06** | Assigned Reviewer | Buka pratinjau KTP, formulir, dan video | Konten substantif tampil di private authorized viewer | Angela / Caca / Maleka | Siap Uji Tim |
| **E2E-07** | Unassigned Reviewer | Tebak URL preview bukti pemohon lain | Akses ditolak (`403 Forbidden`), tanpa kebocoran data | Caca / Maleka | Siap Uji Tim |
| **E2E-08** | Admin / Evaluator | Buka pratinjau dokumen tanpa assignment | Akses ditolak (`403 Forbidden`), role admin bukan reviewer | Caca / Maleka | Siap Uji Tim |
| **E2E-09** | Assigned Reviewer | Catat mismatch field & minta revisi | Catatan terenkripsi tersimpan, status berubah `REVISE` | Caca / Angela | Siap Uji Tim |
| **E2E-10** | Pemohon | Unggah dokumen revisi baru & resubmit | Versi dokumen baru (v2) dibuat, riwayat audit tersimpan | Caca | Siap Uji Tim |
| **E2E-11** | Sistem OCR | Baca KTP dummy jernih (`ktp_0001_clear.png`) | NIK, Nama, Tanggal Lahir terekstraksi 100% akurat | **Jorell** | **VERIFIED (PASSED)** |
| **E2E-12** | Sistem OCR | Deteksi mismatch form vs KTP (`ktp_0004_mismatch`) | Status `REJECT_OR_REVISE`, tandai `has_mismatch=True` | **Jorell** | **VERIFIED (PASSED)** |
| **E2E-13** | Sistem OCR | Baca dokumen sembarang / non-KTP / buram | `document_type: unknown`, `manual_review_required=True` | **Jorell** | **VERIFIED (PASSED)** |
| **E2E-14** | Keamanan / Tamper | Modifikasi bit ciphertext atau AAD metadata | Dekripsi gagal diverifikasi (GCM Auth Tag Failure) | Maleka | Siap Uji Tim |
| **E2E-15** | Data At Rest | Audit grep plaintext NIK/Nama di database SQLite | **Tidak ada plaintext PII** pada storage/tabel analisis | Maleka / Caca | Siap Uji Tim |
| **E2E-16** | Owner / Verifier | Unduh dokumen asli setelah proses OCR | Dokumen terdekripsi identik byte-per-byte (SHA-256 cocok) | Maleka | Siap Uji Tim |
| **E2E-17** | Evaluator | Buka halaman benchmark performa OCR & Cipher | Data benchmark riil terukur (bukan angka placeholder) | Angela / **Jorell** | **VERIFIED (PASSED)** |
| **E2E-18** | Sistem / Server | Restart server web & backend FastAPI | Seluruh riwayat analisis & status audit tetap persisten | Caca | Siap Uji Tim |

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
