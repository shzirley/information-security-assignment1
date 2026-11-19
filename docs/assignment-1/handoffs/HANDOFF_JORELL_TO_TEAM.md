# Dokumen Serah Terima Teknis (Handoff Note) — Peran Jorell
## Proyek: VELTRIX BankKYC (Revisi Assignment 1 Keamanan Informasi)

> **Penulis:** Jorell (Backend OCR, Document Parsing, Synthetic QA Fixtures, & Evaluation Matrix)  
> **Penerima:** Caca (Backend Lead), Angela (Frontend Lead), Maleka (Crypto Lead)  
> **Tanggal Selesai:** 16 November 2026  
> **Status Komponen:** **100% Selesai & Terverifikasi (15/15 Pytest Passed)**  
> **Prinsip Kepatuhan:** 100% Data Sintetis (Bebas PII/KTP Asli sesuai UU No. 27/2022 UU PDP).

---

## 1. Ringkasan yang Sudah Dikerjakan & Siap Dipakai

Sesuai pembagian tugas pada [`VELTRIX_Assignment1_Revision_Task_Distribution.md`](../VELTRIX_Assignment1_Revision_Task_Distribution.md), seluruh tugas Jorell (`J-BE-01`, `J-BE-02`, `J-QA-03`, `J-DOC-04`, `J-QA-05`) telah selesai dibangun dan diuji.

Semua kode bersifat modular, tidak mengubah cipher pipeline inti, dan siap dipanggil langsung oleh modul backend lainnya:

```
information-security-assignment1/
├── HANDOFF_JORELL_TO_TEAM.md                 <-- Dokumen panduan serah terima ini
├── JORELL_WORK_INSTRUCTIONS_AND_REFERENCE.md <-- Log dan panduan kerja Jorell
├── docs/
│   └── verification/
│       ├── OCR_EVALUATION.md                 <-- Matriks akurasi riil, latensi, & dasar hukum UU PDP
│       └── REVISION_ACCEPTANCE_CHECKLIST.md  <-- Checklist 18 skenario E2E siap demo
└── backend/
    ├── fixtures/synthetic_kyc/               <-- 13 Fixture sintetis + ground_truth.json
    │   ├── ktp_0001_clear.png ... ktp_0007_rotated.png
    │   ├── dokumen_sembarang_1.jpeg & _2.jpeg
    │   ├── bank_account_form_digital.pdf & _scanned.pdf
    │   ├── bank_account_form_puput.docx
    │   └── ground_truth.json
    ├── kyc/document_analysis/                <-- Paket Analisis Dokumen Utama
    │   ├── __init__.py                       <-- Export public interface
    │   ├── service.py                        <-- Facade utama analyze_document()
    │   ├── ocr_engine.py                     <-- Adapter PaddleOCR lokal (CPU)
    │   ├── pdf_parser.py                     <-- Parser digital PDF (pypdf) & scanned renderer
    │   ├── docx_parser.py                    <-- Parser formulir rekening Word (python-docx)
    │   └── comparator.py                     <-- Aturan pencocokan deterministik & normalisasi
    └── tests/
        └── test_document_analysis.py         <-- Test suite otomatis (15 test lolos)
```

---

## 2. Panduan Integrasi Khusus untuk Masing-Masing Anggota

### A. Untuk CACA (Backend Lead & Database)

Anda tidak perlu memikirkan parsing PDF, regex teks KTP, atau inferensi PaddleOCR. Cukup panggil **satu fungsi facade utama**:

```python
from kyc.document_analysis import analyze_document

# Panggil fungsi ini di controller endpoint Anda
result = analyze_document(
    content_bytes=decrypted_bytes,      # Bytes dokumen setelah didekripsi
    mime_type=evidence.mime_type,        # Contoh: 'image/png', 'application/pdf', 'application/vnd.openxmlformats...'
    document_type="ktp",                 # Ekspektasi tipe: 'ktp' atau 'account_opening_form'
    submitted_form=applicant_form_dict,  # Dictionary data form pemohon (Nama, NIK, Tgl Lahir, dsb.)
    evidence_id=str(evidence.id),
    evidence_version=evidence.version
)
```

#### Skema Return JSON yang Dihasilkan:
Return value sudah persis memenuhi kontrak API yang disepakati untuk `GET /api/v1/applications/{id}/evidence/{eid}/analysis`:

```json
{
  "evidence_id": "synthetic-evidence-id",
  "evidence_version": 1,
  "document_type": "ktp",
  "status": "COMPLETED",
  "engine": "paddleocr-local",
  "model_version": "PP-OCRv6_medium",
  "confidence": 0.988,
  "checks": [
    {
      "field": "full_name",
      "submitted_value": "PUPUT NUGROHO",
      "extracted_value": "PUPUT NUGROHO",
      "result": "MATCH",
      "confidence": 0.988,
      "reason": "Exact text match."
    },
    {
      "field": "identity_number",
      "submitted_value": "2912541012827585",
      "extracted_value": "2912541012827585",
      "result": "MATCH",
      "confidence": 0.999,
      "reason": "Exact NIK match verified."
    },
    {
      "field": "date_of_birth",
      "submitted_value": "1950-01-27",
      "extracted_value": "27-01-1950",
      "normalized_submitted": "1950-01-27",
      "normalized_extracted": "1950-01-27",
      "result": "MATCH",
      "confidence": 0.992,
      "reason": "Date match (1950-01-27)"
    }
  ],
  "extracted_fields": {
    "identity_number": "2912541012827585",
    "full_name": "PUPUT NUGROHO",
    "birth_date_raw": "27-01-1950",
    "gender": "PEREMPUAN",
    "address_street": "GANG PHH. MUSTOFA NO. 2",
    "occupation": "TIDAK BEKERJA"
  },
  "has_mismatch": false,
  "manual_review_required": false,
  "overall_status": "VERIFIED_MATCH",
  "processed_at": "2026-11-16T04:22:30.123456Z"
}
```

#### Catatan Database untuk Caca:
* Simpan raw JSON hasil analisis dalam bentuk **ciphertext terenkripsi** di database jika disimpan permanen.
* Hanya simpan metadata non-PII (`analysis_status`, `model_version`, `processed_at`) sebagai kolom plaintext untuk keperluan indexing.

---

### B. Untuk MALEKA (Kriptografi & Security)

1. **Alur Dekripsi Aman (In-Memory Processing):**
   - File dokumen KTP/formulir yang ada di database terenkripsi (`RC4/drop3072 -> DES-CBC -> AES-256-GCM`).
   - Saat reviewer meminta review konten, lakukan otentikasi & otorisasi assigned reviewer terlebih dahulu.
   - Dekripsi ciphertext menjadi bytes **hanya di memory (RAM)**, lalu langsung teruskan `content_bytes` ke fungsi `analyze_document()`.
   - **PENTING:** Jangan pernah menyimpan decrypted bytes sebagai file fisik sementara (*temp file*) di disk, agar memenuhi prinsip *Confidentiality at Rest* (Pasal 35 UU PDP).
2. **Integritas AAD (Additional Authenticated Data):**
   - Pastikan AAD tetap mengikat `application_id`, `evidence_id`, dan `version`. Skenario E2E-14 membuktikan bahwa modifikasi bit sekecil apa pun pada ciphertext atau AAD akan menggagalkan tag otentikasi GCM sebelum dokumen sempat diproses.

---

### C. Untuk ANGELA (Frontend Lead)

1. **UI Reviewer Konten Substantif:**
   - Anda sekarang memiliki payload lengkap dari API analisis untuk menampilkan perbandingan berdampingan (*side-by-side comparison*):
     - Kolom Kiri: Nilai input form pemohon (`submitted_value`).
     - Kolom Kanan: Nilai hasil bacaan OCR/Parser (`extracted_value`).
     - Indikator: Badge hijau untuk `MATCH`, badge merah untuk `MISMATCH`, badge kuning untuk `NOT_DETECTED` atau `MANUAL_REVIEW_REQUIRED`.
2. **Grafik & Tabel Benchmark Riil (E2E-17):**
   - Asdos meminta agar halaman benchmark sistem menampilkan angka pengujian asli, bukan dummy mock.
   - Anda dapat mengambil seluruh data matriks kuantitatif dari dokumen [`docs/assignment-1/OCR_EVALUATION.md`](../OCR_EVALUATION.md):
     - Akurasi Field KTP Jelas: **100% (3/3)**
     - Intentional Mismatch Catch: **100% (2/2)**
     - Non-KTP Rejection: **100% (2/2)**
     - Kecepatan Ekstraksi Form Digital: **28 - 45 ms**
     - Kecepatan OCR CPU Gambar: **10 - 15 detik**

---

## 3. Cara Menjalankan Test Suite Mandiri

Untuk memverifikasi bahwa semua berjalan normal di komputer Anda:

```bash
# Pindah ke direktori backend
cd backend

# Aktifkan virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependensi OCR & Parser (jika belum terpasang di venv rekan tim)
pip install -r requirements-ocr.txt

# Jalankan pengujian otomatis
pytest tests/test_document_analysis.py -v
```

Hasil yang diharapkan: **15 passed** tanpa error.

---

## 4. Status Kesiapan Skenario Demo E2E

Detail lengkap 18 skenario E2E dapat dilihat di [`docs/assignment-1/REVISION_ACCEPTANCE_CHECKLIST.md`](../REVISION_ACCEPTANCE_CHECKLIST.md).

* Bagian **Jorell** (E2E-11, E2E-12, E2E-13, E2E-17) sudah berstatus **VERIFIED (PASSED)**.
* Skenario flow pemohon dan reviewer siap diintegrasikan bersama Caca, Angela, dan Maleka saat PR digabungkan.

Semangat teman-teman! Modul ini siap digunakan kapan saja. Jika ada pertanyaan seputar format input/output parser, silakan colek Jorell.
