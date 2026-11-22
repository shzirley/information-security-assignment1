# VELTRIX BankKYC — Assignment 1 Revision Plan & Team Task Distribution

**Version:** 1.0 — 14 November 2026  
**Repository:** https://github.com/shzirley/information-security-assignment1  
**Project:** Secure digital bank-account opening & encrypted KYC evidence management (academic prototype)  
**Language:** Bahasa Indonesia (engineering terms and API contracts in English)  
**Implementation mode:** Synthetic data only. No real customer identity, real KTP/KK, government verification, real banking account creation, or production compliance claim.

> **Tujuan utama revisi:** Memperbaiki kritik asdos bahwa reviewer selama ini hanya melihat metadata. Setelah revisi, *assigned reviewer* dapat memeriksa **isi asli dokumen** secara terotorisasi, melihat ekstraksi OCR dan perbandingan dengan data form, kemudian memberi keputusan simulasi dengan alasan yang dapat diaudit. Enkripsi, otorisasi, dan pengujian tiga cipher tetap menjadi core assignment.

---

## 0. Baseline proyek yang sudah ada (jangan dibangun ulang)

Berdasarkan README dan PRD di branch `main` pada waktu rencana ini dibuat:

- **Frontend:** Next.js App Router, TypeScript, React, Tailwind; domain kode `frontend/src/features/kyc/`, API client `frontend/src/lib/kyc-api.ts`, kontrak di `frontend/src/lib/`.
- **Backend aktif:** FastAPI entry point `backend/app/server.py` → implementasi `backend/kyc/`; bukan `backend/app/main.py` (vault lama).
- **Penyimpanan lokal:** SQLite persisten pada `backend/data/bankkyc.db` melalui SQLAlchemy. MySQL adalah opsi deployment, **bukan kewajiban untuk mengganti SQLite pada revisi MVP ini**.
- **Migrasi:** Alembic pada `backend/migrations/`; skema awal mencakup `applications`, `reviewer_assignments`, `encrypted_objects`, `evidence_versions`, `personal_data_versions`, `case_events`, `security_events`, dan tabel laboratorium.
- **Alur yang telah tersedia:** register/login, wizard 5 langkah (profil, identitas, supporting document, video, final review), upload terenkripsi, assignment, request revision, download oleh pemilik, cryptography lab.
- **Titik masalah:** reviewer saat ini hanya melihat metadata penugasan, jenis, ukuran, versi, dan kelengkapan. Reviewer **belum** bisa melihat profil privat, preview isi KTP/PDF, maupun memutar video.
- **Kriptografi yang harus dipertahankan:** `RC4/drop3072 → DES-CBC/PKCS7 → AES-256-GCM`, object-specific keys, wrapped key bundle, AAD, recovery/hash checks. RC4 dan DES hanya untuk eksperimen tugas, **bukan rekomendasi keamanan perbankan**.
- **Batas saat ini:** identity PNG/JPEG/PDF 5 MiB; supporting office PDF/DOCX 10 MiB; MP4 30 MiB dengan durasi 10–30 detik. Batas baru tidak boleh melonggarkan validasi server tanpa keputusan dan tes.

**Konsekuensi:** pekerjaan dimulai dari *extending current BankKYC*, bukan membuat proyek baru, mengganti crypto engine, atau menambahkan GPT API sebagai dependency wajib.

### Keputusan yang dikunci untuk Assignment 1 Revision

| ID | Keputusan | Status |
|---|---|---|
| DEC-01 | Skenario: pemohon membuka **rekening baru** secara online pada bank simulasi, bukan sekadar aktivasi m-banking | **Locked** |
| DEC-02 | Dokumen utama: personal profile (JSON), KTP dummy, formulir pembukaan rekening (PDF/DOCX), video verifikasi sintetis (MP4) | **Locked** |
| DEC-03 | KK dummy adalah **dokumen tambahan opsional**, bukan syarat universal bagi semua pemohon dewasa | **Locked** |
| DEC-04 | Reviewer yang ditugaskan mendapat **delegated, read-only preview** untuk dokumen dan field profil yang relevan; **bukan** akses download seperti applicant | **Approved — disetujui asdos** |
| DEC-05 | OCR baseline **lokal** menggunakan PaddleOCR untuk scan/gambar; PDF digital memakai text extraction; DOCX memakai parser | **Locked for implementation planning** |
| DEC-06 | Hasil OCR membantu pemeriksaan; **tidak** otomatis mengesahkan keaslian KTP, KK, atau wajah di video | **Locked** |
| DEC-07 | SQLite dipertahankan untuk local MVP; tambah tabel/kolom memakai **migration baru**, bukan menghapus DB atau mengubah migrasi yang sudah dipakai | **Locked** |
| DEC-08 | Fitur baru tidak boleh mengganggu lab benchmark AES/DES/RC4 dan owner-only download | **Locked** |
| DEC-09 | Scope **P0** adalah review substansial manual yang aman; OCR dan grafik adalah **P1**, tidak boleh memblokir penyelesaian P0 | **Locked** |

**Catatan akademik:** PRD sebelumnya secara sengaja membatasi reviewer ke metadata demi interpretasi owner-only. Perubahan DEC-04 mengubah keputusan produk tersebut. Catat persetujuan asdos atau setidaknya alasan desain bahwa *applicant tetap satu-satunya pemilik hak download*, sedangkan reviewer hanya menerima akses preview terbatas pada kasus yang ditugaskan.

---

## 1. Daftar final input dan label frontend

Jangan menggunakan label ambigu *“Upload supporting document”* tanpa menjelaskan berkas yang diharapkan. Bedakan **data form**, **dokumen inti wajib**, dan **dokumen tambahan bersyarat**.

| ID | Input di UI | Required | Format & batas baseline | Isi yang diperiksa | OCR baseline |
|---|---|---|---|---|---|
| DOC-00 | **Applicant Personal Information / Data Diri** | Wajib | Form → encrypted JSON (8 field existing) | Nama, ID dummy, DOB, alamat, pekerjaan, tujuan rekening, kontak | Tidak (structured data) |
| DOC-01 | **Identity Card (KTP Dummy)** | Wajib | PNG/JPG/PDF, ≤5 MiB | Nama, nomor identitas dummy, DOB, alamat | **Ya:** image/scanned PDF |
| DOC-02 | **Bank Account Opening Form / Formulir Pembukaan Rekening** | Wajib | PDF/DOCX, ≤10 MiB | Nama, ID dummy bila tersedia, tujuan pembukaan rekening, deklarasi informasi | **Digital PDF/DOCX: text parser**; scanned PDF: OCR |
| DOC-03 | **Family Card (KK Dummy) — Additional Supporting Document** | Opsional | Disarankan PDF/JPG/PNG ≤5 MiB; final limit disepakati BE | Jika ada: nama/relasi relevan; **jangan** menganggap KK menentukan validitas untuk semua kasus | P1/P2: OCR dan manual review |
| DOC-04 | **Verification Video (Synthetic MP4)** | Wajib dalam skenario tugas | MP4 ≤30 MiB; 10–30 detik | Reviewer menyaksikan pernyataan video sesuai skenario sintetis | **Tidak untuk MVP**; manual preview, tanpa klaim liveness |

**Konsistensi dengan tugas:** ada empat **kategori perlindungan data**: (1) personal JSON, (2) scanned ID, (3) office document, (4) MP4. KK menjadi bukti ekstra tanpa mengubah empat kategori akademik tersebut. Untuk versi awal tetap gunakan satu *required office document* berupa formulir pembukaan rekening. Menambahkan slot KK memerlukan dukungan BE untuk banyak dokumen/subtype; bila migrasinya belum siap, jangan tampilkan slot KK aktif seolah sudah tersimpan.

### Copywriting FE yang disetujui

- Halaman judul: **Open a New Bank Account — Secure KYC Application (Simulation)**.
- Step 1: `Personal Information` — *Complete your synthetic applicant profile.*
- Step 2: `Identity Document — KTP Dummy (Required)` — *Upload a readable synthetic identity document; name and date of birth should match the form.*
- Step 3: `Administrative Documents` — (a) `Bank Account Opening Form (Required)`; (b) `Family Card / KK Dummy (Optional, if applicable)`.
- Step 4: `Verification Video (Required for this simulation)` — *Upload a 10–30-second synthetic MP4. This is manual evidence review, not automated liveness verification.*
- Step 5: `Review & Submit` — daftar berkas, required/optional status, file validation, confidentiality note, synthetic-data acknowledgement.
- Reviewer: `Document Verification`, `Original Preview`, `Extracted Fields`, `Consistency Checks`, `Reviewer Notes`, `Request Revision`, `Accept (Simulation)`, `Reject (Simulation)`.
- OCR status: `NOT_ANALYZED`, `PROCESSING`, `COMPLETED`, `FAILED`, `MANUAL_REVIEW_REQUIRED`.
- Field check: `MATCH`, `MISMATCH`, `NOT_DETECTED`, `UNREADABLE`, `NOT_APPLICABLE`.
- Tidak boleh menggunakan copy seperti `Government verified`, `Authentic KTP`, `Identity verified`, atau `Real bank account approved`.

---

## 2. RACI singkat dan pembagian pekerjaan

**Lead = penanggung jawab penggabungan dan acceptance; Support = membantu kode/review/test.** Semua anggota terlibat dalam diskusi, integrasi dan pengujian end-to-end; peran di bawah **bukan isolasi pekerjaan**.

| Workstream | Lead | Support | Prioritas | Target utama |
|---|---|---|---|---|
| FE applicant upload/wizard/labels | **Angela** | Caca (contract) | P0 | User tahu berkas apa yang wajib/opsional |
| FE reviewer preview/manual review | **Angela** | Caca, Maleka | P0 | Reviewer dapat memeriksa *isi* dokumen |
| FE OCR results & benchmark chart | **Angela** | Jorell | P1 | Analisis terbaca dan data benchmark asli divisualisasikan |
| API contract, reviewer authorization, workflow | **Caca** | Maleka | P0 | Secure delegated access dan keputusan berbasis bukti |
| SQLite schema + Alembic migrations | **Caca** | Jorell | P0 | Data baru persisten tanpa merusak DB lama |
| Crypto integration, preview & tamper safety | **Maleka** | Caca | P0 | Decrypt-after-authorization, no plaintext persistence |
| OCR engine, document parsing, field comparison | **Jorell** | Caca | P1 | Local OCR+parser berjalan dengan data dummy |
| QA fixtures, evaluation, report & references | **Jorell** | Semua | P0/P1 | Bukti correctness, reasoning, screenshots & measurement |
| E2E integration + final demo | **Semua** | — | P0 | Alur upload → decrypt → review → keputusan berjalan |

---

## 3. Task list per anggota — detail siap dibuat GitHub Issues

### A. ANGELA — Frontend owner

**A-FE-01 — Perjelas skenario, navigation, dan dokumen upload** `P0`

- **Scope:** revisi applicant wizard yang sudah ada, *bukan* membuat wizard baru.
- Ganti label generik *identity scan* menjadi KTP dummy dan *supporting document* menjadi formulir pembukaan rekening. Tambahkan deskripsi kegunaan, contoh konten dan aturan file type/size.
- Tentukan required/optional, dengan *KK optional* disembunyikan/disabled hingga API subtype tersedia atau ditampilkan jelas sebagai fitur belum aktif selama development, **bukan** tombol upload palsu pada demo final.
- Perlihatkan file selected vs **file uploaded successfully**; jangan menganggap memilih file sudah mengirim ke server.
- Di review step, tampilkan ringkasan data pribadi, KTP, formulir, KK (jika ada), video, version, status, dan indikator kelengkapan.
- Tambahkan peringatan **synthetic data only** dan penjelasan bahwa *Accepted (Simulation)* bukan rekening bank aktif.
- **Kemungkinan lokasi kode:** `frontend/src/features/kyc/`, `frontend/src/app/`, `frontend/src/lib/contracts.ts`, `frontend/src/lib/kyc-api.ts` (konfirmasi file konkret sebelum coding).
- **Output:** wizard update, screenshot 5 step, FE copy document.
- **DoD:** user baru tidak perlu bertanya “dokumen administrasi itu apa?”; invalid format/size tidak lanjut; submit ditolak jika item wajib belum sukses di-upload; tidak ada copy yang mengklaim verifikasi resmi.

**A-FE-02 — Reviewer workspace untuk pemeriksaan konten** `P0`

- Tambah panel `Document Verification` pada kasus **yang ditugaskan**: thumbnail/preview KTP dan KK, PDF preview, DOCX lewat hasil ekstraksi teks atau renderer aman, MP4 video player yang mengambil data dari endpoint privat.
- Tampilkan profil relevan untuk cross-check (nama, DOB, synthetic ID, alamat); tampilkan minimum data yang perlu dibandingkan.
- Buat checklist manual per evidence: `Readable`, `Correct document type`, `Matches applicant form`, `Needs clarification`, plus alasan.
- Tampilkan status review, versi evidence, ringkasan hasil pemeriksaan, dan CTA `Request Revision` / `Accept (Simulation)` / `Reject (Simulation)`.
- Preview **tidak** boleh memakai object URL publik permanen atau direct database path. Render Blob dari API ber-credential, hapus object URL saat modal tertutup, set no-store.
- `403/404`, loading, bad ciphertext, OCR error, unsupported preview harus ada state UI yang jelas tanpa memunculkan data privat.
- **Output:** reviewer screen + video walkthrough screenshot.
- **DoD:** assigned reviewer bisa melihat isi KTP/form/video; reviewer yang tidak ditugaskan tidak dapat memperoleh data lewat manipulasi URL; applicant tidak melihat reviewer workspace.

**A-FE-03 — Panel hasil baseline OCR** `P1`

- Tampilkan pasangan `Applicant Form` versus `Extracted from Document` per field (full name, DOB, dummy identity number, address jika ditemukan).
- Badge konsistensi: MATCH/MISMATCH/NOT_DETECTED/UNREADABLE; tampilkan warning bila confidence kurang, tetapi **jangan auto-approve** berdasarkan skor OCR.
- View raw OCR lines dan bounding-box overlay *optional*, setelah extractor stabil; wajib tampilkan timestamp/model/version pengolahan.
- Jika OCR gagal, reviewer tetap bisa melakukan manual review. Hasil untuk KTP dan scan tidak otomatis menggantikan dokumen asli.
- **Output:** reviewer OCR comparison UI dan screenshot kasus match/mismatch.
- **DoD:** mismatch dummy DOB terlihat dan dapat menjadi alasan `Request Revision` yang diinput reviewer sendiri.

**A-FE-04 — Benchmark visualization page** `P1`

- Pertahankan Cryptography Laboratory dan ambil **data live** dari `GET /api/v1/lab/runs`, bukan angka mock.
- Tambah/rapikan grafik yang membandingkan AES-GCM, DES-CBC, RC4, layered pipeline untuk **median encrypt ms, median decrypt ms, IQR/variabilitas, ciphertext overhead (bytes), throughput**, serta round-trip correctness.
- Filter dataset JSON/PNG/PDF/MP4, jumlah trial, lingkungan tes, tanggal run. Label `cipher-core benchmark`, bukan waktu response endpoint keseluruhan.
- Tunjukkan catatan bahwa MP4 fixture yang ada masih sangat kecil (~8.7 KB), sehingga **tidak mewakili video dunia nyata**.
- **Output:** 1 dashboard benchmark dengan grafik + tab hasil tabel/raw CSV download.
- **DoD:** grafik sesuai row API/CSV, berubah ketika run yang dipilih berubah, tidak menampilkan angka fabricated, empty state jelas.

**A-FE-05 — Frontend verification & handoff** `P0/P1`

- Jalankan `npm.cmd run typecheck`, `npm.cmd run build`; perbarui test UI jika layout/kontrak berubah.
- Ambil screenshot per role, dokumentasi UI states, dan pertahankan responsivitas.
- PR terpisah dari backend dan minta Caca review kontrak. **Jangan mengubah auth/cookie/CSRF untuk melewati error.**
- **Output:** `docs/verification/FE_REVISION_EVIDENCE.md` atau direktori dokumentasi setara.
- **DoD:** FE live mode berhasil, tidak hanya mock mode.

### B. CACA — Backend lead & system integration

**C-BE-01 — Kontrak dokumen & perubahan skema SQLite** `P0`, *blocker untuk FE dan OCR*

- Audit model `backend/kyc/db.py`, validasi `backend/kyc/validation.py`, API `backend/kyc/main.py`, dan kontrak `frontend/src/lib/`.
- **Jangan mengganti database lokal:** tetap `backend/data/bankkyc.db`, `KYC_DATABASE_URL` default SQLite. Buat **Alembic revision baru**; jangan memodifikasi migrasi `0001_bankkyc` yang sudah berjalan.
- Buat representasi jenis dokumen lebih spesifik **tanpa memutus category existing** (`identity`, `document`, `video`): misalnya `document_type`/`subtype` dalam evidence metadata: `ktp`, `account_opening_form`, `kk_optional`, `verification_video`.
- Pada MVP, wajib `ktp + account_opening_form + verification_video + personal_profile`, KK tidak menjadi kondisi submit; bedakan bukti *required* vs *optional*.
- Jika schema saat ini membatasi satu supporting document per kategori, perluas indeks/logic dengan hati-hati agar bisa menampung `account_opening_form` dan `kk_optional` sebagai dua item yang berbeda, **tanpa merusak evidence versioning**.
- Pastikan data lama tetap terbaca: tetapkan mapping/subtype `legacy_supporting_document` untuk record lama atau migrasi mapping aman.
- **Output:** schema contract ADR singkat, Alembic migration, SQLite integration test, backup instruction.
- **DoD:** data di database sebelum migrasi tetap bisa dibaca setelah migrasi, file ciphertext tetap dapat didekripsi dengan KEK yang sama, versi bukti tidak hilang; `manage.py migrate` sukses pada SQLite bersih dan existing DB.

**C-BE-02 — Secure reviewer content-review permission** `P0`

- Tambah service authorization: role reviewer + assigned case + valid workflow state + explicit content preview permission. Access by **per-case scope**, bukan semua reviewer bisa membaca semua KTP.
- Rancang endpoint proposal (disesuaikan pola FastAPI repo):
  - `GET /api/v1/applications/{id}/review/profile` → field profil minimum yang boleh diperiksa assigned reviewer.
  - `GET /api/v1/applications/{id}/evidence/{eid}/review-preview` → *read-only* decrypted preview, bukan attachment download.
  - `POST /api/v1/applications/{id}/review/checks` → reviewer checklist, reason code, note, expected version.
- Original owner-only endpoint `/evidence/{eid}/download` **tetap owner-only**. Jangan melonggarkannya agar reviewer dapat mengunduh berkas.
- Pastikan CSRF/Origin pada mutation, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, dan periksa content-type. Untuk MP4, jika player butuh HTTP Range, implementasikan Range yang **tetap melewati auth per request**.
- Log minimal: actor_id, application_id, evidence_id, action, time, outcome, no plaintext/NIK/OCR text. Admin dan evaluator tetap tidak berhak membaca data applicant.
- **Output:** API, OpenAPI/contract docs, tests positive/negative.
- **DoD:** assigned reviewer dapat preview; unassigned reviewer mendapat 403/404 konsisten; admin, evaluator dan applicant lintas user ditolak; no unrestricted public URL; replay stale state/version ditolak.

**C-BE-03 — Substantive decision workflow & audit** `P0`

- Reviewer tidak boleh menekan keputusan tanpa mencatat checklist + alasan yang berkaitan dengan bukti aktual. Keep existing `request-revision`/`accept`/`reject` state transitions; tambahkan validasi evidence review checklist sesuai scope.
- Simpan reviewer notes sensitif sebagai **encrypted objects** menggunakan mekanisme yang ada, bukan kolom text plaintext. Simpan event/status metadata seminimal mungkin.
- Perubahan status dan penulisan review outcome dalam **satu transaction** dengan expected version untuk hindari partial update dan `409 VERSION_CONFLICT`.
- Bedakan `Accepted (Simulation)` dari akun bank yang benar-benar dibuka.
- **Output:** reviewer workflow API + test transition.
- **DoD:** satu contoh mismatch menghasilkan review reason lalu request revision; resubmission menambah evidence version; old evidence tetap tersedia untuk owner sesuai akses; rollback jika transaksi gagal.

**C-BE-04 — OCR service integration & encrypted results persistence** `P1`, *integrasi dengan Jorell/Maleka*

- Sepakati service interface terisolasi yang menerima **validated bytes + MIME + document_type**, mengembalikan struktur typed result; jangan memuat PaddleOCR di setiap request.
- Tawarkan endpoint `POST .../analysis` atau job server setelah upload (pilih satu setelah kontrak FE–BE); `GET .../analysis` untuk assigned reviewer. Proses hanya setelah permission/authenticated recovery sesuai model worker yang dipilih.
- Simpan OCR text, raw extracted fields, confidence dan nilai perbandingan sensitif **terenkripsi**. SQLite boleh menyimpan ciphertext BLOB; metadata non-PII `analysis_status`, `model_version`, `processed_at`, `evidence_version` boleh untuk indexing.
- Implementasikan timeout / bounded concurrency / ukuran file dan halaman / error recovery; model inference tidak boleh menjatuhkan FastAPI untuk login dan upload.
- **Output:** API adapter, migration tambahan jika perlu, status codes, integration test.
- **DoD:** OCR failure → status gagal/manual review yang aman; data asli utuh; restart server tidak menghilangkan analisis yang tersimpan; tidak ada plaintext OCR di tabel/logs.

**C-BE-05 — Regression suite & integration review** `P0/P1`

- Jalankan existing `pytest` suite serta `scripts/smoke_kyc_live.py` dan cek FE live mode.
- Tambahkan tests authorization, subtype, preview, migration, OCR workflow, and review actions.
- PR reviews FE dan crypto/OCR. Resolve schema conflicts centrally; **Caca satu-satunya owner akhir migrasi/kontrak API**.
- **Output:** passing test logs, regression matrix, API docs.
- **DoD:** no security regression pada owner retrieval, encryption, uploads, session/CSRF, assignment.

### C. MALEKA — Cryptography & backend security support

**M-SEC-01 — Authorized decrypt-for-preview service** `P0`

- Bantu Caca membuat service yang memanggil **existing authenticated recovery path**, bukan implementasi cipher kedua.
- Alur wajib: authenticate → authorize assigned reviewer → verify object owner/application/category/version & AAD → unwrap keys & verify AES-GCM tag → decrypt → serve bounded preview.
- Scope read-only untuk reviewer. Download original tetap hak owner; jangan simpan hasil dekripsi ke `public/`, temp folder yang tidak aman, atau storage tanpa enkripsi.
- Untuk video, koordinasikan streaming/chunk handling dan pemakaian memori; tidak semua lingkungan mampu memproses 30 MiB dalam memori sekaligus.
- **Output:** integrated preview crypto service, tests for valid/invalid context.
- **DoD:** ciphertext tampering/wrong AAD/wrong wrapped key gagal sebelum ada plaintext terkirim; tidak ada perbedaan pesan error yang membocorkan stage decryption.

**M-SEC-02 — Encryption of OCR-derived data & review notes** `P0/P1`

- Buat helper menyimpan analisis dan notes sebagai encrypted payload menggunakan envelope/versioning existing; bind AAD ke `application_id`, `evidence_id`, `evidence_version`, `analysis_version`, `owner/reviewer context` yang memang diautentikasi.
- Tetapkan rotation/re-analysis policy: bila evidence diganti, hasil OCR versi lama tidak otomatis dianggap hasil versi baru.
- Jangan log decryption key, base64 keystore, original image, extracted name/NIK, video frame, atau full request payload.
- **Output:** encrypted analysis persistence tests dan at-rest inspection.
- **DoD:** query SQLite menunjukkan ciphertext (bukan plaintext names/NIK), hasil bisa dibaca ulang oleh assigned reviewer setelah decrypt, dan gagal saat konteks mismatch.

**M-SEC-03 — AES-GCM justification specific to BankKYC** `P1`

- Tulis 1 paragraf teknis di docs/laporan: **GCM dipakai karena KYC evidence harus rahasia sekaligus utuh, dan AAD mengikat dokumen ke pemilik, kasus, tipe, versi.** GCM tidak membuktikan keaslian dokumen atau validitas identitas.
- Jelaskan DES/RC4 dipertahankan **untuk pemenuhan akademik dan perbandingan**, tidak meningkatkan keamanan AES secara otomatis dan tidak cocok untuk bank nyata.
- **Output:** `docs/decisions/ADR_AAD_AND_GCM.md` atau tambahan pada report.
- **DoD:** alasan keputusan terkait threat model *cross-application document substitution*, bukan sekadar “GCM faster/stronger”.

**M-SEC-04 — Security regression & threat scenarios** `P0/P1`

- Unit/integration test: unassigned preview, forged ID, wrong case/evidence linkage, modified GCM tag, corrupted DES padding inside outer GCM, stale evidence analysis, cache-control, logging leak, file byte recovery.
- Jalankan evidence integrity check dengan fixture sintetis; jangan melibatkan KTP asli.
- **Output:** security test report dan perubahan kode jika ditemukan kelemahan.
- **DoD:** setiap case memiliki observed response dan status pass/fail yang dapat dibuktikan.

### D. JORELL — Backend OCR, validation, QA & technical report

**J-BE-01 — Local OCR proof-of-concept (PaddleOCR)** `P1`

- Buat modul terpisah dalam `backend/kyc/document_analysis/` (lokasi usulan; konfirmasi layout repo). Implementasikan adapter `extract_text(image_bytes, mime)` yang mengembalikan `text`, `confidence`, `bounding_box`, `model_version`.
- Gunakan **PaddleOCR secara lokal** (CPU baseline). Pin versi Python/Paddle/PaddleOCR setelah diuji dengan Windows environment tim; unduh model saat setup, **jangan upload KTP ke API pihak ketiga**.
- Handle KTP dummy PNG/JPEG dan scanned PDF yang di-render terbatas; tolak corrupt image, oversized page, unsupported input dengan error aman.
- Jangan menyamakan confidence OCR dengan probabilitas “KTP asli”.
- **Output:** runnable OCR POC command, dependency notes/versions, 3 contoh output sintetis, unit tests.
- **DoD:** hasil OCR berasal dari dokumen dummy sungguhan (bukan placeholder), satu request tidak memuat model berulang, failure ditangani, tanpa raw plaintext yang tersimpan permanen.

**J-BE-02 — Document parser & transparent rules** `P1`

- Gunakan PyMuPDF untuk **digital PDF**; bila halaman tidak memiliki text layer, render halaman terkontrol untuk OCR. Gunakan python-docx untuk DOCX.
- Tambahkan simple document-type hints: `ktp_like`, `kk_like`, `account_form_like`, `unknown` berdasarkan kombinasi label/struktur; label ini **indikasi**, bukan sertifikasi keaslian dokumen.
- Field extractor KTP dummy: `full_name`, `identity_number` (format `DUMMY-...` sesuai fixture), `date_of_birth`, `address` bila terdeteksi. Account-opening form: `full_name`, `account_purpose`, `identity_number` jika ada. KK opsional: hanya field relevan yang dapat ditentukan; hindari asumsi otomatis bahwa struktur setiap KK sama.
- Field comparison gunakan normalisasi yang eksplisit, tanggal dalam format standar, **identity number exact-match**. Jika field tidak ditemukan, gunakan `NOT_DETECTED`—bukan `MATCH` default.
- **Output:** typed parser/validator result, deterministic tests, rules doc.
- **DoD:** sample match dan mismatch keluar sesuai expected; unrelated PDF tidak otomatis lolos sebagai formulir; OCR low confidence diarahkan manual review.

**J-QA-03 — Dataset sintetis & evaluation matrix** `P0/P1`

- Siapkan minimal **12 fixture sintetis**: 3 KTP clear, 2 blur/rotated, 2 nama/DOB mismatch, 2 wrong document type, 1 PDF digital form, 1 PDF scanned form, 1 DOCX form. Video sintetis tambah 1 fixture terpisah untuk preview smoke test.
- Untuk setiap fixture: input, ground-truth field, expected status, expected reason. Jangan pakai foto KTP asli atau NIK orang asli.
- Ukur *field exact-match rate* terhadap ground truth, coverage/NOT_DETECTED, false-match/false-accept dalam konteks aturan, inference time (terpisah dari cipher lab), dan jelaskan ukuran sampel terlalu kecil untuk klaim generalisasi.
- **Output:** fixture pack (tanpa PII), `docs/assignment-1/OCR_EVALUATION.md`, test code.
- **DoD:** hasil reproducible, tiap angka ada jumlah pembilang/penyebut, failure case tidak disembunyikan.

**J-DOC-04 — Revisi laporan dan evidence untuk asdos** `P0/P1`

- Update PRD/README/revisi report agar skenario baru jelas: pemohon **membuka rekening baru**, reviewer authorized content review, OCR assisting, private encryption at rest.
- Tambahkan sumber hukum yang relevan seperti **UU No. 27 Tahun 2022 (Perlindungan Data Pribadi)** dan aturan CDD/AML OJK yang relevan; tulis dasar kewajiban **secara akurat** tanpa mengklaim bahwa semua detail implementasi diwajibkan satu pasal tertentu.
- Jelaskan mengapa AES-GCM + AAD cocok untuk evidence KYC; bedakan OCR accuracy, integrity, identity authenticity, dan benchmark cipher.
- Sertakan screenshot: applicant upload labels; reviewer original preview; OCR match/mismatch; authorized access denial; benchmark chart; CLI test results. Jangan memalsukan output tes.
- Pertahankan batas **maksimal 2 halaman A4** jika mengupdate laporan submission; lampiran bukti bisa dipisah bila aturan mengizinkan.
- **Output:** report/PRD revisions, bibliography, screenshot evidence register, demo speaking notes.
- **DoD:** klaim report dapat ditelusuri ke source code/test, tugas tiap anggota tercatat di GitHub PR/commit.

**J-QA-05 — End-to-end acceptance & GitHub evidence** `P0/P1`

- Susun test plan untuk semua role (applicant, reviewer assigned/unassigned, admin, evaluator).
- Verifikasi bahwa browser mock tidak menjadi sumber angka benchmark atau keberhasilan crypto; demo memakai **live backend**.
- Lakukan review akhir bersama Caca/Maleka dan tandai `Pass`, `Fail`, `Not tested` secara eksplisit.
- **Output:** `docs/assignment-1/REVISION_ACCEPTANCE_CHECKLIST.md`, PR summaries dan recorded demo evidence.
- **DoD:** semua P0 selesai, semua P1 yang diklaim selesai punya bukti; yang tidak selesai jujur tercatat.

---

## 4. Kontrak FE–BE yang harus disepakati sebelum membuat UI OCR

**Caca owner kontrak, Angela konsumen, Maleka reviewer keamanan, Jorell produsen analysis.** Nama endpoint berikut **usulan** yang harus diputuskan setelah mengaudit nama existing router—jangan dianggap sudah ada di GitHub.

| API proposed | Method | Who | Response utama | Security rule |
|---|---|---|---|---|
| `/api/v1/applications/{id}/review/profile` | GET | Assigned reviewer | Relevan subset profile | No-store, scoped fields |
| `/api/v1/applications/{id}/evidence/{eid}/review-preview` | GET | Assigned reviewer | Image/PDF/MP4 bytes untuk read-only preview | Every request checks assignment+state; no public link |
| `/api/v1/applications/{id}/evidence/{eid}/analysis` | POST | Authorized internal processing/reviewer | Status `PROCESSING`/`COMPLETED` sesuai mode | CSRF, throttling, validate evidence/version |
| `/api/v1/applications/{id}/evidence/{eid}/analysis` | GET | Assigned reviewer | OCR fields/checks setelah decrypt | No-store, only assigned case |
| `/api/v1/applications/{id}/review/checks` | POST | Assigned reviewer | Saved checklist, event/version | Version conflict, encrypted notes |

**Proposed response `GET analysis`:**

```json
{
  "evidence_id": "synthetic-evidence-id",
  "evidence_version": 2,
  "document_type": "ktp",
  "status": "COMPLETED",
  "engine": "paddleocr-local",
  "model_version": "<pinned-version>",
  "checks": [
    {
      "field": "full_name",
      "submitted_value": "Budi Pratama",
      "extracted_value": "Budi Pratama",
      "result": "MATCH",
      "confidence": null
    },
    {
      "field": "date_of_birth",
      "submitted_value": "2002-05-12",
      "extracted_value": "2002-05-13",
      "result": "MISMATCH",
      "confidence": null
    }
  ],
  "manual_review_required": true
}
```

Nilai di atas **data dummy ilustratif**, bukan hasil OCR/test aktual. Response hanya boleh dikirim setelah authorization; seluruh nilai sensitif berada dalam payload terenkripsi saat *at rest*. Confidence boleh `null` jika parser field tidak bisa mengaitkan skor OCR dengan field secara benar.

### Database schema — rekomendasi, bukan perubahan yang sudah ada

Gunakan migration baru, misalnya `0002_document_review_ocr` (penamaan final sesuai rantai revisi Alembic), berisi penambahan minimum:

1. `evidence_versions.document_type` atau tabel metadata subtype terpisah bila mapping existing lebih aman: `ktp`, `account_opening_form`, `kk`, `verification_video`.
2. `document_analyses`: opaque `analysis_id`, `application_id`, `evidence_id`, `evidence_version`, `status`, `engine`, `model_version`, `processed_at`, `encrypted_object_id` (mengarah ke encrypted payload existing). **Tidak ada kolom plaintext extracted_name/nik/dob**.
3. `review_checks` atau encrypted review result object yang terhubung ke `case_events`: reviewer ID, evidence-version references, reason codes non-sensitif, encrypted detailed notes.
4. `security_events`/audit existing dipakai ulang untuk `CONTENT_PREVIEWED`, `DOCUMENT_ANALYZED`, `REVIEW_DECISION_RECORDED`, tanpa menyalin konten dokumen.
5. Index pada `(application_id, evidence_id, evidence_version)` dan constraint aman untuk idempotency/retry analysis.

**SQLite guardrails:**

- Gunakan file SQLite persisten **yang sudah ada**; backup dulu sebelum migration.
- Gunakan Alembic; jalankan migrasi pada database **salinan** terlebih dahulu. Hindari `drop_all`, menghapus `bankkyc.db`, atau mengganti KEK demi menyelesaikan error.
- `encrypted_objects` dan `evidence_versions` tetap source of truth; OCR analysis menunjuk ke versi evidence tertentu.
- Semua operasi tulis lewat SQLAlchemy session/transaction; gunakan optimistic version check seperti implementasi existing.
- **Tidak harus pindah ke MySQL** untuk nilai tugas ini. Migrasi harus tetap kompatibel MySQL sejauh feasible, tetapi fokus pengujian revisi adalah SQLite live lokal.
- Simpan DB, `.env`, keys, dump dan kredensial demo di luar Git; hanya fixture sintetis yang aman untuk di-commit.

---

## 5. Urutan implementasi dan dependensi (sprint 7 hari usulan)

Ini **rencana estimasi**, bukan deadline yang sudah ditetapkan dosen. Jika waktu terbatas, selesaikan P0 terlebih dahulu.

| Hari | Gate / pekerjaan terpenting | PIC |
|---|---|---|
| **D1 — Freeze contract** | Sepakati upload schema, required/optional, reviewer permission, route/response, dataset dummy, backup SQLite | Semua; Caca lead |
| **D2 — Data + FE copy** | Alembic subtype/multi-doc, revisi wizard/labels, baseline preview crypto interface | Caca + Angela + Maleka |
| **D3 — Substantive review P0** | Authorized preview KTP/form/video, reviewer profile subset, checklist, recorded revision reason | Caca + Maleka + Angela |
| **D4 — P0 E2E proof** | Match/mismatch **manual**, unassigned denial, verify no plaintext, regression suite | Semua; Jorell QA |
| **D5 — OCR P1** | PaddleOCR image/scanned PDF, PDF/DOCX parsing, field rules, encrypted analysis persistence | Jorell + Caca + Maleka |
| **D6 — OCR UI + benchmark UI** | Comparison panel, errors, selected lab charts using real data | Angela + Jorell |
| **D7 — Freeze & submission** | Regression, screenshots, demo, legal/GCM explanation, PR merge, report, verified results | Semua; Jorell docs |

**Dependency chain (critical path):** `C-BE-01 contract/schema` → `C-BE-02 auth review` + `M-SEC-01 decrypt` → `A-FE-02 reviewer preview` → `P0 demo`. OCR branch bisa dikerjakan paralel setelah kontrak (`J-BE-01/02`) kemudian disambungkan ke `C-BE-04` dan `A-FE-03`.

### Go / No-Go gate

**Go untuk demo skenario nyata (P0) jika:** reviewer assigned dapat membuka isi 3 kategori dokumen (KTP/form/video), menilai mismatch manual, membuat alasan keputusan, akses lintas kasus ditolak, ciphertext tetap terlindungi. Ini langsung menjawab kritik asdos **walaupun OCR belum selesai**.

**Go untuk mengklaim OCR baseline (P1) jika:** hasil OCR sungguhan diproses lokal, perbandingan data terhubung ke dokumen dan versi yang benar, reviewer mendapat hasil yang dapat diverifikasi pada preview, hasil sensitif tersimpan terenkripsi, dan pengujian sintetis tercatat.

**No-Go jika:** file hanya diberi status `OCR passed` tanpa proses, frontend mock dianggap backend live, reviewer mendapat direct download semua KTP, hasil OCR plaintext tersimpan di DB/log, atau angka benchmark dibuat manual.

---

## 6. End-to-end acceptance scenarios (wajib ada bukti)

| Case | Role | Action | Expected outcome | Owner bukti |
|---|---|---|---|---|
| E2E-01 | Applicant | Upload KTP dummy PNG | Content validated, ciphertext stored, version recorded | Angela/Caca |
| E2E-02 | Applicant | Upload PDF/DOCX account-opening form | Required office document recognized and encrypted | Angela/Caca |
| E2E-03 | Applicant | Upload MP4 synthetic 10–30 sec | Accepted if within supported format, encrypted | Angela/Caca |
| E2E-04 | Applicant | Submit tanpa KTP/form/video | Rejected as incomplete | Caca |
| E2E-05 | Applicant | Submit tanpa KK | **Allowed** (optional) | Caca |
| E2E-06 | Assigned reviewer | Preview KTP/form/video | Visible **substantive content** in private viewer | Angela/Caca/Maleka |
| E2E-07 | Unassigned reviewer | Guess URL case/evidence | Denied with no data leakage | Caca/Maleka |
| E2E-08 | Admin / evaluator | Open applicant document preview | Denied | Caca/Maleka |
| E2E-09 | Assigned reviewer | Record mismatch + request revision | Saved encrypted note and workflow transition | Caca/Angela |
| E2E-10 | Applicant | Re-upload correction + resubmit | New evidence version, old version tracked | Caca |
| E2E-11 | OCR | Read clear dummy KTP | Extracted fields based on actual bytes; version recorded | Jorell |
| E2E-12 | OCR | Mismatch form DOB vs document DOB | `MISMATCH`, manual review required | Jorell/Angela |
| E2E-13 | OCR | Blurred/wrong file | NOT_DETECTED/UNREADABLE/manual review, no fake success | Jorell |
| E2E-14 | Security | Modify ciphertext/AAD | Reject before releasing plaintext | Maleka |
| E2E-15 | Data at rest | Search SQLite/raw logs for dummy NIK/name/OCR text | Sensitive payload **not stored as readable plaintext** in analysis tables/logs | Maleka/Caca |
| E2E-16 | Owner | Download original after OCR | Byte-identical to original (SHA-256) | Maleka |
| E2E-17 | Evaluator | Open benchmark page | Actual measured rows and chart, no mock numbers | Angela/Jorell |
| E2E-18 | All | Restart application | Data, assignments, encrypted results persist | Caca |

**Proof standard:** screenshot/UI video **plus** test command/output/log where appropriate, commit hash/PR. A screenshot of a nice UI alone does not prove authorization, encrypted storage, or real OCR.

---

## 7. GitHub collaboration & evidence of individual contributions

Gunakan **4 working branches / PR** yang dipisah berdasarkan kepemilikan utama, lalu integrasikan bertahap:

| Person | Branch recommendation | Minimum independently reviewable PR |
|---|---|---|
| Angela | `feat/kyc-frontend-review-ui` | Wizard labels/document upload UI + reviewer preview/benchmark chart |
| Caca | `feat/kyc-be-review-api` | SQLite migration + reviewer authorization + review APIs |
| Maleka | `feat/kyc-secure-preview` | Authenticated recovery integration + encrypted analysis safety/tests |
| Jorell | `feat/kyc-local-ocr-evaluation` | PaddleOCR/parser + validation tests + documentation |

**Praktik PR:**

- Setiap commit menjelaskan pekerjaan yang *benar-benar* dilakukan, bukan commit kosmetik untuk menambah angka aktivitas.
- PR berisi summary, screenshot/response, test command + hasil, known limitations, dan kaitan Issue ID.
- Jangan commit `.env`, `bankkyc.db`, KEK, seed user passwords, dokumen asli, atau OCR hasil data pribadi.
- Caca menggabungkan migration/API contract; Angela rebase terhadap contract final; Maleka/Jorell membuka PR modular agar tidak saling menimpa `backend/kyc/main.py`.
- Seluruh anggota melakukan integration review, tetapi klaim kontribusi saat presentasi harus sesuai PR, hasil pengerjaan, dan commit aktual.

### Contoh format GitHub issue

```md
## [C-BE-02] Authorized reviewer document preview
Owner: Caca | Support: Maleka, Angela | Priority: P0

### Problem
Reviewers currently see metadata only, not document contents.

### Scope
- Permit per-case read-only preview for assigned reviewers.
- Preserve applicant-only download.
- Audit every access.

### Acceptance criteria
- [ ] Assigned reviewer can preview KTP/form/MP4.
- [ ] Unassigned reviewer receives 403/404 and no plaintext.
- [ ] No public storage URL or plaintext disk persistence.
- [ ] Tests and screenshots attached.

### Dependencies
M-SEC-01, A-FE-02, C-BE-01
```

---

## 8. Apa yang sengaja tidak dikerjakan pada revisi ini?

- **Tidak** membuat atau melatih model KTP sendiri dari dataset kecil.
- **Tidak** mengirim KTP/KK ke GPT/Claude API pihak ketiga untuk baseline.
- **Tidak** membuat OCR untuk video atau mengklaim face match/liveness detection.
- **Tidak** menghubungkan ke Dukcapil/bank sungguhan atau membuat rekening riil.
- **Tidak** mengganti SQLite secara terburu-buru atau menghapus bukti/migrasi existing.
- **Tidak** mengubah DES/RC4/AES jadi cipher lain demi mempercepat OCR.
- **Tidak** mengganti hasil benchmark dengan angka ilustrasi, apalagi mengklaim keamanan produksi.

---

## 9. Definition of Done (DoD) — revisi dianggap selesai jika

- [ ] Scenario bank account opening jelas di landing/wizard/README; user tahu apa yang diunggah.
- [ ] KTP dummy + account-opening form + MP4 wajib; KK dummy opsional; personal form wajib.
- [ ] Reviewer assigned bisa memeriksa **isi asli** dan mencatat alasan, bukan hanya metadata.
- [ ] Reviewer bukan penerima tugas dan admin/evaluator **tidak** dapat membuka plaintext.
- [ ] Applicant tetap pemilik hak original download dan dapat memulihkan file byte-identical.
- [ ] Hasil OCR yang diklaim memang berasal dari PaddleOCR/parser lokal, dengan evaluasi field-match dummy.
- [ ] Derived sensitive OCR output/review notes terenkripsi di SQLite dan tidak muncul pada logs.
- [ ] Alembic migration aman bagi SQLite existing, schema/test fresh install berhasil.
- [ ] Lab AES/DES/RC4/layered masih berfungsi; grafik memakai real lab outputs dan hasil diinterpretasikan.
- [ ] GCM dijustifikasi berdasarkan confidentiality, integrity, dan AAD binding pada KYC evidence.
- [ ] Semua anggota punya kode/dokumen/test/screenshot dan PR yang dapat menjelaskan kontribusinya.
- [ ] Test matrix, remaining limitations, dan final demo tersimpan di docs.

---

## 10. Source of truth & referensi kerja

**Repo saat dokumen disusun:**

1. [VELTRIX BankKYC README — implementation status, schema, workflow, validation, crypto, testing](https://github.com/shzirley/information-security-assignment1)
2. [Backend PRD — API contract, reviewer boundary, design decisions](https://github.com/shzirley/information-security-assignment1/blob/main/docs/prd/VELTRIX_BankKYC_BE_PRD.md)
3. [Frontend PRD — interface, roles, UX constraints](https://github.com/shzirley/information-security-assignment1/blob/main/docs/prd/VELTRIX_BankKYC_FE_PRD.md)
4. [Backend README — SQLite configuration, Alembic, API, test instructions](https://github.com/shzirley/information-security-assignment1/blob/main/backend/README.md)
5. [Verification evidence in repository](https://github.com/shzirley/information-security-assignment1/blob/main/docs/verification/VERIFIKASI.md)
6. [PaddleOCR — OCR library selected for local baseline](https://github.com/PaddlePaddle/PaddleOCR)
7. [UU No. 27 Tahun 2022 — Perlindungan Data Pribadi](https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022)

**Pemisahan fakta dan rencana:** bagian **Baseline** merangkum isi repository yang terdokumentasi; endpoint baru, tabel OCR, UI review, timeline, dan pembagian kerja adalah **usulan implementasi** untuk revisi Assignment 1 dan belum otomatis tersedia di branch `main`. Jika ada perubahan kode terbaru setelah 14 November 2026, sinkronkan kontrak dan branch sebelum membuka PR.
