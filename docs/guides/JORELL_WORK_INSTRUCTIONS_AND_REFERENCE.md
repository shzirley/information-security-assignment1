# Panduan Kerja & Referensi Pengerjaan — Peran: JORELL
## Proyek: VELTRIX BankKYC (Revisi Assignment 1 Keamanan Informasi)

> **File Referensi Utama:** `VELTRIX_Assignment1_Revision_Task_Distribution.md`  
> **Peran:** JORELL (Backend OCR, Document Parsing, Synthetic QA Fixtures, & Technical Report)  
> **Prinsip Kerja:** Tepat sasaran, modular, bebas data asli (100% sintetis), dan hemat kuota AI.

---

## 1. Protokol Efisiensi Kuota Agent (Agent Token & Quota Conservation)

Agar kuota AI tidak cepat terkuras dan proses kerja tetap efektif, pembagian peran antara **User (Anda)** dan **Agent (AI)** diatur secara ketat:

### A. Hal yang Dilakukan USER (Jangan diserahkan ke Agent):
1. **Menjalankan Web Server & Dev Server:**
   - Menjalankan FastAPI (`uvicorn app.server:app` / `python launcher.py`).
   - Menjalankan Next.js (`npm run dev`).
2. **Browser & UI Testing:**
   - Membuka halaman web di browser, navigasi klik form, upload manual via web browser.
   - Menilai kenyamanan visual UI atau alur interaktif di browser.
3. **Download Manual & Instalasi Berat:**
   - Mengunduh model biner besar atau menjalankan setup environment sistem jika membutuhkan interaksi GUI/lama.
4. **Git Operations:**
   - `git add`, `git commit`, `git push`, buat PR di GitHub (bisa dibantu draft pesannya oleh agent).

### B. Hal yang Dilakukan AGENT (AI):
1. **Pengerjaan Logika & Kode Modul:**
   - Menulis adapter OCR, document parser (PDF & DOCX), normalizer data, dan comparison rules.
2. **Pembuatan Generator Fixture Sintetis:**
   - Menulis skrip Python untuk generate 12 fixture sintetis (KTP dummy, formulir rekening dummy, ground truth JSON).
3. **Automated Unit Testing Spesifik:**
   - Menjalankan unit test *targeted* dan cepat (contoh: `pytest tests/test_ocr_parser.py -q`), bukan running daemon server.
4. **Drafting Laporan & Dokumentasi Teknis:**
   - Menyusun draf `OCR_EVALUATION.md`, `REVISION_ACCEPTANCE_CHECKLIST.md`, dan justifikasi hukum/kriptografi.

### C. Aturan Praktis Menghemat Kuota (Tips & Best Practices):
- **Gunakan Targeted Command:** Jangan jalankan seluruh test suite jika hanya menguji satu fungsi parser. Gunakan filter pytest spesifik: `pytest tests/test_parser.py -k "test_ktp" -q`.
- **Hindari Daemon Processes:** Jangan biarkan agent memanggil process yang berjalan terus menerus (seperti web server background atau browser headless crawler).
- **Edit Spesifik (Targeted Edits):** Agent hanya mengedit blok fungsi yang berubah, bukan menulis ulang file ribuan baris dari nol.
- **Instruksi Terkumpul (Batching):** Satukan instruksi terkait ke dalam satu prompt daripada bolak-balik perintah mikro.

---

## 2. Rincian Tugas Jorell (Scope of Work)

Berdasarkan dokumen distribusi tugas revisi, Jorell memiliki 5 task:

```
[J-QA-03] Fixtures Sintetis & Ground Truth (P0/P1)
   │
   ├──► [J-BE-02] Document Parser (PDF/DOCX) & Comparison Rules (P1)
   │       │
   ├──► [J-BE-01] Local OCR Adapter (PaddleOCR) (P1)
   │       │
   └───────┴──► Evaluasi Akurasi (OCR_EVALUATION.md)
                   │
                   ├──► [J-DOC-04] Laporan Teknis & Justifikasi (P0/P1)
                   └──► [J-QA-05] Acceptance Checklist (P0/P1)
```

### 1. `J-QA-03` — Dataset Sintetis (Minimal 12 Fixtures) & Ground Truth `[Prioritas Awal]`
- **Tujuan:** Menyiapkan dataset dummy aman untuk menguji OCR, parser, dan demo tim tanpa menyentuh KTP/data asli siapa pun.
- **Daftar Fixtures yang Wajib Dibuat:**
  1. `ktp_dummy_01_clear.png` — KTP dummy jernih (Nama: "BUDI PRATAMA", NIK: "DUMMY-3578-010203-0001", DOB: "1995-05-12", Alamat).
  2. `ktp_dummy_02_clear.jpg` — KTP dummy jernih kedua.
  3. `ktp_dummy_03_clear.png` — KTP dummy jernih ketiga.
  4. `ktp_dummy_04_blurred.jpg` — KTP dengan efek blur / noise (uji batas confidence).
  5. `ktp_dummy_05_rotated.png` — KTP dengan sedikit rotasi/skew.
  6. `ktp_dummy_06_dob_mismatch.png` — Tanggal lahir di KTP berbeda dengan data yang diisi di formulir.
  7. `ktp_dummy_07_name_typo.png` — Nama sedikit typo dibanding formulir.
  8. `doc_invalid_01_receipt.jpg` — Bukti struk/gambar sembarang (bukan KTP/form) -> deteksi `unknown` / `NOT_DETECTED`.
  9. `doc_invalid_02_random.pdf` — Dokumen acak non-perbankan.
  10. `bank_account_form_digital.pdf` — Formulir pembukaan rekening bank sintetis (digital text layer).
  11. `bank_account_form_scanned.pdf` — Formulir pembukaan rekening versi scan/gambar.
  12. `bank_account_form_template.docx` — Formulir pembukaan rekening format DOCX.
  - *Plus 1 file video sintetis:* `verification_video_sample.mp4` (sudah ada baseline di `fixtures/verification-demo.mp4`).
- **File Metadata:** `ground_truth.json` berisi expected text, expected fields, dan status perbandingan per fixture.

### 2. `J-BE-02` — Document Parser & Transparent Rules `[P1]`
- **Lokasi Usulan:** `backend/kyc/document_analysis/`
- **Komponen:**
  - `pdf_parser.py`: Ekstraksi teks digital PDF menggunakan `pypdf` / `PyMuPDF`.
  - `docx_parser.py`: Ekstraksi teks/tabel DOCX menggunakan `python-docx`.
  - `comparator.py`: Logika pencocokan field:
    - Normalisasi string (hilangkan spasi ganda, case-insensitive).
    - Normalisasi tanggal ke format ISO `YYYY-MM-DD`.
    - Exact match untuk ID dummy.
    - Status hasil: `MATCH`, `MISMATCH`, `NOT_DETECTED`, `UNREADABLE`.

### 3. `J-BE-01` — Local OCR Engine (PaddleOCR) `[P1]`
- **Lokasi Usulan:** `backend/kyc/document_analysis/ocr_engine.py`
- **Spesifikasi:**
  - Fungsi antarmuka:
    ```python
    def extract_text_from_image(image_bytes: bytes, mime: str) -> dict:
        # Mengembalikan: {"text": str, "confidence": float, "boxes": list, "model_version": str}
    ```
  - Bersifat **lokal** (tidak mengirim gambar ke cloud API / GPT pihak ketiga).
  - Model dimuat secara **lazy-singleton** agar tidak membebani memory jika endpoint lain dipanggil.
  - Error handling aman jika gambar corrupt atau format tidak didukung (mengembalikan status `FAILED` / `MANUAL_REVIEW_REQUIRED` tanpa melempar crash server).

### 4. `J-DOC-04` — Revisi Laporan & Justifikasi Teknis `[P0/P1]`
- Update dokumen laporan tugas / PRD:
  - Skenario pembukaan rekening baru simulasi (**BankKYC**).
  - Landasan hukum: **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)** pasal relevan untuk data pribadi spesifik (biometrik/identitas) dan umum.
  - Justifikasi teknis: Mengapa **AES-256-GCM + AAD** ideal untuk data KYC (mengikat `application_id`, `evidence_id`, `version` sehingga mencegah serangan *cross-application document substitution*).
  - Posisi RC4 dan DES: Hanya sebagai pembanding akademik, bukan cipher perbankan riil.

### 5. `J-QA-05` — Evaluasi & Acceptance Checklist `[P0/P1]`
- Generate dokumen `docs/verification/OCR_EVALUATION.md`:
  - Tabel evaluasi 12 fixture terhadap ground truth (field exact-match rate, coverage, runtime ms per dokumen).
- Generate dokumen `docs/verification/REVISION_ACCEPTANCE_CHECKLIST.md`:
  - Checklist pengujian skenario E2E (E2E-01 s/d E2E-18) yang siap di-check bersama tim sebelum demo akhir.

---

## 3. Format Kontrak Interface untuk Caca (Backend Lead)

Agar integrasi mulus dengan endpoint API yang dibuat Caca (`GET/POST .../analysis`), modul yang dibangun Jorell harus mengembalikan skema data standar berikut:

```python
# Output dari modul kyc.document_analysis.service.analyze_document()
{
    "evidence_id": "str",
    "evidence_version": int,
    "document_type": "ktp" | "account_opening_form" | "kk_optional" | "unknown",
    "status": "COMPLETED" | "FAILED" | "MANUAL_REVIEW_REQUIRED",
    "engine": "paddleocr-local" | "pypdf-extractor" | "docx-parser",
    "model_version": "v1.0",
    "checks": [
        {
            "field": "full_name",
            "submitted_value": "BUDI PRATAMA",
            "extracted_value": "BUDI PRATAMA",
            "result": "MATCH",       # MATCH | MISMATCH | NOT_DETECTED | UNREADABLE
            "confidence": 0.94
        },
        {
            "field": "date_of_birth",
            "submitted_value": "1995-05-12",
            "extracted_value": "1995-05-13",
            "result": "MISMATCH",
            "confidence": 0.88
        }
    ],
    "manual_review_required": bool
}
```

---

## 4. Checklist Langkah Kerja (Work Execution Tracker)

Tandai progres di sini saat pengerjaan berlangsung:

- [x] **Langkah 1:** Buat generator skrip untuk 12 Fixture Sintetis & `ground_truth.json`.
- [x] **Langkah 2:** Generate file-file fixture ke dalam `backend/fixtures/synthetic_kyc/` (13 fixtures selesai).
- [x] **Langkah 3:** Bangun modul parser dokumen digital: PDF (`pdf_parser.py`) dan DOCX (`docx_parser.py`).
- [x] **Langkah 4:** Bangun modul pembanding data form vs extracted (`comparator.py`).
- [x] **Langkah 5:** Bangun modul OCR lokal (`ocr_engine.py`) dengan error handling & singleton.
- [x] **Langkah 6:** Satukan dalam satu service facade `analyze_document(bytes, mime, doc_type, form_data)`.
- [x] **Langkah 7:** Buat targeted unit test `tests/test_document_analysis.py` dan jalankan via pytest (15/15 passed).
- [x] **Langkah 8:** Generate laporan evaluasi akurasi `docs/verification/OCR_EVALUATION.md`.
- [x] **Langkah 9:** Siapkan ringkasan justifikasi hukum (UU PDP) & kriptografi (AES-GCM AAD) untuk laporan akhir (`docs/verification/REVISION_ACCEPTANCE_CHECKLIST.md`).
