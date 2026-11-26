# VELTRIX BankKYC — Assignment 3
## Digital Signature for KYC PDF Documents

> **Dokumen:** Technical Planning & Team Task Allocation  
> **Project:** VELTRIX BankKYC  
> **Assignment:** 3 — Digital Signature  
> **Scenario:** Secure digital banking onboarding and KYC evidence management  
> **Status:** Working plan — technical decisions must be validated against the lecturer's requirements and actual implementation  
> **Data policy:** Synthetic/demo data only

---

## 1. Project Context and Scope

VELTRIX BankKYC tetap menggunakan skenario yang sama seperti Assignment 2: prototipe web untuk menyimulasikan proses pengumpulan dan pengelolaan dokumen Know Your Customer (KYC) dalam proses onboarding perbankan digital.

Pada Assignment 3, fokus pengembangan diperluas. Pengguna yang memiliki dokumen PDF dalam pengajuan KYC dapat menandatangani dokumen tersebut secara digital menggunakan **private key miliknya**. Sistem juga menyediakan proses verifikasi menggunakan **public key** yang berpasangan.

Fitur baru harus memenuhi ketentuan berikut:

1. Pengguna dapat membuat key pair apabila belum memilikinya.
2. Pengguna dapat menandatangani dokumen PDF menggunakan private key miliknya.
3. Digital signature harus tertanam di dalam file PDF, bukan hanya disimpan sebagai metadata atau record database.
4. Sistem dapat memverifikasi signature menggunakan public key yang sesuai.
5. Jika memungkinkan, signature dibuat sesuai standar PDF digital signature agar dapat dikenali oleh PDF reader pihak ketiga.

### 1.1 Batasan

- VELTRIX tetap merupakan prototipe akademik, bukan sistem KYC atau pembukaan rekening bank sungguhan.
- Seluruh identitas, dokumen, dan akun yang digunakan untuk demo harus sintetis.
- Library boleh digunakan untuk key generation, hashing, operasi kriptografi dasar, serta membaca/menulis PDF.
- **Logika signing dan verification harus diimplementasikan oleh tim sendiri.** Jangan menggunakan fungsi/library yang secara otomatis mengambil alih keseluruhan proses PDF signing atau verification.
- Enkripsi file dari Assignment 2 bukan pengganti digital signature. Enkripsi menjaga kerahasiaan, sedangkan digital signature digunakan untuk memeriksa integritas dan membuktikan bahwa signature dibuat menggunakan private key yang berpasangan dengan public key tertentu.

---

## 2. Actors and Digital Signature Use Case

| Actor | Peran dalam Assignment 3 |
|---|---|
| Applicant / Document Owner | Mengunggah PDF, membuat key pair, menandatangani dokumen dengan private key sendiri, dan mengunduh signed PDF |
| Assigned KYC Reviewer | Memeriksa status dokumen dan hasil verifikasi sesuai hak akses; tidak otomatis memperoleh private key pemilik |
| Administrator | Mengelola akun dan alur aplikasi tanpa memiliki hak untuk menandatangani dokumen atas nama pengguna |
| Verification User | Memilih atau membuka signed PDF dan memeriksa signature menggunakan public key yang terdaftar/terkait |

### 2.1 Why digital signatures are needed

Dalam proses onboarding KYC, dokumen seperti formulir pembukaan rekening, surat pernyataan, atau dokumen persetujuan dapat menjadi bukti administratif yang perlu dijaga integritasnya. Setelah dokumen ditandatangani, pihak yang memeriksa perlu mengetahui apakah isi dokumen yang ditandatangani masih sesuai dengan isi yang diverifikasi.

Digital signature membantu menyediakan:

- **Integrity:** perubahan pada byte dokumen yang tercakup dalam signature dapat menyebabkan verifikasi gagal.
- **Authentication of key possession:** signature yang valid menunjukkan bahwa signature dibuat menggunakan private key yang berpasangan dengan public key verifikasi.
- **Non-repudiation support:** signature dapat menjadi bukti teknis penggunaan private key, tetapi kekuatan pembuktian identitas tetap bergantung pada proses pengikatan public key ke identitas akun, perlindungan private key, dan kebijakan operasional.

Digital signature tidak otomatis membuktikan bahwa isi dokumen benar, bahwa identitas pemilik key telah diverifikasi secara resmi, atau bahwa sertifikat/public key dipercaya oleh pihak ketiga.

---

## 3. Proposed End-to-End Workflow

1. **Authentication:** applicant login ke akun VELTRIX.
2. **PDF upload:** applicant memilih PDF yang akan ditandatangani.
3. **Key pair check:** sistem memeriksa apakah applicant telah memiliki key pair.
4. **Key pair generation:** jika belum ada, sistem membuat public key dan private key.
5. **Key protection:** private key disimpan atau diekspor dengan perlindungan yang sesuai; private key tidak pernah dikirim ke browser atau disimpan plaintext tanpa proteksi.
6. **Signing preparation:** modul PDF menyiapkan signature field, placeholder `/Contents`, dan `/ByteRange`.
7. **Digest calculation:** sistem menghitung SHA-256 atas byte range PDF yang ditentukan, dengan placeholder `/Contents` dikecualikan sesuai mekanisme PDF signature.
8. **Signing:** modul kriptografi menandatangani digest menggunakan private key pemilik.
9. **Embedding:** signature container dimasukkan ke `/Contents` sehingga signature tertanam di dalam PDF.
10. **Storage:** signed PDF disimpan sebagai file baru; original PDF dipertahankan sesuai kebutuhan audit.
11. **Verification:** sistem membaca `/ByteRange` dan `/Contents`, menghitung ulang digest, lalu memverifikasi signature menggunakan public key.
12. **Result:** UI menampilkan status valid, invalid, atau verification error beserta alasan yang relevan.

> **Important:** Jangan menghitung hash seluruh PDF lalu menambahkan signature di akhir file tanpa mekanisme PDF signature. Penambahan signature itu sendiri mengubah file. PDF digital signature menggunakan struktur khusus seperti `/ByteRange` dan `/Contents`.

---

## 4. Team Task Allocation

Pembagian berikut mempertahankan empat area kerja utama dari Assignment 2: Frontend/UX, Backend/Workflow, Cryptography, serta QA/Research. Pembagian ini merupakan ownership utama; integrasi dan code review tetap dilakukan bersama.

| Member | Main responsibility | Supporting responsibility |
|---|---|---|
| **Angela Vania Sugiyono** | Frontend / UX | Integrasi API, document history, verification result UI |
| **Jahhaza Assiqoyah Nurul Hidayah** | Backend / API / Workflow | Authentication, document ownership, database, key-service integration |
| **Maleka Ghaniya** | Cryptography / Key Management | Key pair generation, hashing, signing, verification logic |
| **Jorell Ramos Sinaga** | PDF Engineering / QA / Report | PDF signature embedding, PDF compatibility, test plan, analysis and report |

### 4.1 Angela — Frontend / UX

**Objective:** Menyediakan antarmuka yang memudahkan applicant mengunggah PDF, membuat key pair, menandatangani dokumen, dan memeriksa hasil verifikasi.

| Task | Detail | Deliverable / evidence |
|---|---|---|
| PDF upload UI | Form upload PDF dan validasi tipe/ukuran file | Upload page |
| Key pair UI | Menampilkan status key pair dan opsi generate jika belum tersedia | Key management UI |
| Signing interface | Menampilkan dokumen yang akan ditandatangani, konfirmasi, dan status proses | Signing page |
| Verification interface | Menampilkan hasil valid/invalid/error, pemilik public key yang terdaftar, dan waktu pemeriksaan | Verification result UI |
| Document history | Menampilkan nama dokumen, pemilik, waktu signing, dan status signature | Document history |
| API integration | Menghubungkan UI dengan endpoint backend | End-to-end frontend integration |

**Acceptance criteria**
- Applicant dapat mengunggah PDF melalui UI.
- Applicant dapat memulai proses generate key pair apabila belum memiliki key.
- Applicant dapat meminta proses signing dan melihat status hasilnya.
- Applicant/verifier dapat melihat hasil verifikasi yang jelas.
- UI membedakan signature valid, invalid, dan verification error; jangan menampilkan semua kegagalan sebagai “invalid” tanpa penjelasan.

### 4.2 Jahhaza — Backend / API / Workflow

**Objective:** Mengatur alur aplikasi, autentikasi, kepemilikan dokumen, penyimpanan, dan komunikasi antarmodul.

| Task | Detail | Deliverable / evidence |
|---|---|---|
| API development | Endpoint upload, key generation, signing, verification, dan download | REST API |
| Authentication | Memastikan tindakan signing dilakukan oleh pengguna yang login | Authentication middleware |
| Ownership validation | Memeriksa kepemilikan dokumen sebelum signing atau retrieval | Ownership checks |
| Key-service integration | Menghubungkan akun dengan public key dan mekanisme private-key protection | Key management integration |
| Signing workflow | Mengatur alur upload → prepare → sign → embed → save | Signing workflow |
| Verification workflow | Mengirim signed PDF dan public key yang relevan ke modul verifikasi | Verification workflow |
| Database | Menyimpan metadata dokumen, pemilik, public key, dan status signature | Database schema and migrations |

**Acceptance criteria**
- Pengguna tidak dapat menandatangani dokumen milik pengguna lain.
- Private key tidak dikirim ke frontend.
- API memeriksa autentikasi dan otorisasi sebelum menjalankan signing.
- Signed PDF dapat disimpan dan diunduh.
- Record dokumen menyimpan relasi pemilik dan public key yang digunakan.
- Error dari modul signing/verification ditangani secara konsisten.

### 4.3 Maleka — Cryptography / Key Management

**Objective:** Mengimplementasikan proses kriptografi inti untuk pembuatan key pair, hashing, digital signing, dan signature verification.

| Task | Detail | Deliverable / evidence |
|---|---|---|
| Key pair generation | Menghasilkan pasangan public key dan private key | Key generation module |
| Hashing | Menghitung digest dokumen sesuai byte range yang diberikan modul PDF | SHA-256 hashing module |
| Signing logic | Menghasilkan signature dengan private key pemilik | Own signing implementation |
| Verification logic | Memverifikasi signature dengan public key yang sesuai | Own verification implementation |
| Key protection | Menentukan format dan perlindungan private key | Key handling module and design notes |
| Cryptography tests | Menguji key mismatch, signature corruption, dan perubahan digest | Unit tests |

**Proposed cryptographic design**
- Asymmetric algorithm: RSA, minimal 2048-bit; pertimbangkan 3072-bit bila performa demo memadai.
- Hash algorithm: SHA-256.
- Untuk interoperabilitas PDF/CMS, pertimbangkan RSA PKCS#1 v1.5 dengan SHA-256 sebagai pilihan awal yang luas didukung. RSA-PSS dapat dipertimbangkan untuk skema internal, tetapi dukungan PDF reader/CMS harus diuji sebelum dipilih.
- Private key hanya digunakan untuk signing dan harus dilindungi saat disimpan atau diekspor.
- Public key digunakan untuk verification dan dikaitkan dengan akun pemilik.
- Randomness untuk key generation harus berasal dari cryptographic secure random generator.

**Important implementation rule:** Library seperti `cryptography` boleh digunakan untuk operasi dasar key generation, hashing, dan primitive signing/verification sesuai batas tugas. Tim tetap harus menulis sendiri alur yang menghubungkan digest PDF, signature, proses embedding, pembacaan signature, dan pemeriksaan hasilnya. Konfirmasi interpretasi batas penggunaan library kepada dosen jika diperlukan.

**Acceptance criteria**
- Key pair dapat dibuat dan disimpan/dikelola dengan aman.
- Signature valid dengan public key pasangannya.
- Verifikasi gagal jika public key tidak cocok.
- Verifikasi gagal jika digest atau signature diubah.
- Private key tidak muncul pada response API, log, screenshot, atau repository.

### 4.4 Jorell — PDF Engineering / QA / Research

**Objective:** Memastikan signature benar-benar tertanam di PDF dan melakukan pengujian struktur PDF, manipulasi dokumen, serta kompatibilitas.

| Task | Detail | Deliverable / evidence |
|---|---|---|
| PDF inspection | Memeriksa struktur PDF dan menentukan lokasi signature dictionary/field | PDF inspection notes |
| Signature preparation | Menyiapkan signature field, `/ByteRange`, dan placeholder `/Contents` | PDF preparation module |
| Signature embedding | Memasukkan signature container ke `/Contents` tanpa merusak struktur PDF | Signed PDF output |
| PDF verification integration | Mengambil `/ByteRange` dan `/Contents` untuk diteruskan ke logika verifikasi buatan tim | PDF verification module |
| Tampering tests | Menguji perubahan konten, signature contents, dan byte range | Test results |
| Third-party compatibility | Menguji signed PDF di PDF reader pihak ketiga bila implementasi standar sudah tersedia | Compatibility evidence |
| Report | Menyusun analisis risiko, hasil uji, dan justifikasi PDF design | Assignment 3 report draft |

**Acceptance criteria**
- Signature tertanam di dalam file PDF.
- PDF hasil signing tetap dapat dibuka.
- Sistem dapat membaca signature dan byte range dari signed PDF.
- Perubahan pada bagian yang ditandatangani terdeteksi.
- Hasil pengujian kompatibilitas dicatat; jangan mengklaim kompatibel sebelum benar-benar diuji.

---

## 5. Technical Design and Architecture

### 5.1 Proposed module structure

```text
veltrix-bankkyc/
├── frontend/
│   ├── components/
│   ├── pages/
│   └── services/
│
├── backend/
│   ├── auth/
│   ├── documents/
│   ├── keys/
│   ├── signatures/
│   │   ├── key_generation.py
│   │   ├── hashing.py
│   │   ├── signing.py
│   │   └── verification.py
│   ├── pdf/
│   │   ├── signature_field.py
│   │   ├── byte_range.py
│   │   ├── embedding.py
│   │   └── parsing.py
│   └── database/
│
├── tests/
│   ├── key_generation/
│   ├── cryptography/
│   ├── pdf_signing/
│   ├── verification/
│   ├── tampering/
│   └── authorization/
│
├── docs/
│   ├── architecture.md
│   ├── design-decisions.md
│   ├── test-plan.md
│   └── ai-usage.md
│
├── requirements.txt
├── .env.example
└── README.md
```

Nama file dan folder dapat disesuaikan dengan repository Assignment 2. Hindari membuat ulang struktur yang sudah ada apabila modul lama masih dapat digunakan.

### 5.2 Suggested API contract

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/documents` | Upload PDF |
| `POST` | `/api/keys/generate` | Generate key pair untuk akun |
| `GET` | `/api/keys/status` | Memeriksa status key pair |
| `GET` | `/api/keys/public` | Mengambil public key pengguna |
| `POST` | `/api/documents/{id}/sign` | Memulai signing PDF milik pengguna |
| `POST` | `/api/documents/{id}/verify` | Memverifikasi signature dokumen |
| `GET` | `/api/documents/{id}/download` | Mengunduh PDF sesuai hak akses |
| `GET` | `/api/documents/{id}/history` | Melihat riwayat signing/verifikasi |

Endpoint di atas adalah rancangan awal, bukan kontrak final. Sesuaikan dengan framework, routing, dan pola API repository yang sudah ada.

### 5.3 Suggested libraries

| Need | Candidate | Limitation |
|---|---|---|
| Key generation and cryptographic primitives | Python `cryptography` | Jangan memakai wrapper yang mengambil alih keseluruhan PDF signing/verification |
| PDF reading/writing | `pypdf` atau `pikepdf` | Gunakan untuk manipulasi/inspeksi PDF, bukan otomatisasi seluruh signing |
| ASN.1/CMS encoding support | `asn1crypto` | Dapat membantu struktur data CMS; tim tetap bertanggung jawab atas alur signing dan verification |
| PDF inspection | `pikepdf` | Untuk memeriksa struktur PDF dan debugging |

Library final harus dipilih setelah proof-of-concept. Pastikan versi library dicatat dalam `requirements.txt` dan laporan.

### 5.4 PDF signature concepts

- **Signature dictionary:** struktur PDF yang menyimpan informasi signature.
- **`/ByteRange`:** menentukan rentang byte PDF yang dihitung dalam digest.
- **`/Contents`:** tempat signature value atau CMS signature container disimpan.
- **Digest:** hash dari byte range yang ditentukan.
- **Detached signature:** signature disimpan terpisah dari byte dokumen yang di-hash, tetapi signature container tertanam dalam PDF.
- **Incremental update:** mekanisme PDF untuk menambahkan perubahan tanpa menulis ulang seluruh file; perlu dipahami agar proses signing tidak merusak dokumen atau signature sebelumnya.

Untuk bonus third-party PDF reader, arahkan implementasi ke PDF digital signature yang mengikuti standar PDF dan CMS (misalnya detached CMS dengan subfilter yang sesuai, seperti `/adbe.pkcs7.detached`). Verifikasi kompatibilitas secara nyata menggunakan beberapa PDF reader. Keberhasilan verifikasi internal saja belum membuktikan kompatibilitas pihak ketiga.

---

## 6. Design Decisions to Justify

Setiap keputusan berikut harus dicatat beserta alasan, alternatif yang dipertimbangkan, dan konsekuensinya.

| Decision | Proposed direction | Why it matters |
|---|---|---|
| Digital signature algorithm | RSA, minimal 2048-bit | Asymmetric signature; public key dapat digunakan untuk verifikasi tanpa membagikan private key |
| Hash function | SHA-256 | Menghasilkan digest tetap dan umum digunakan |
| Signature padding/format | Pilih skema yang sesuai dengan target PDF/CMS; evaluasi RSA PKCS#1 v1.5 untuk interoperabilitas | Tidak semua skema signature didukung secara seragam oleh PDF readers |
| PDF embedding | `/ByteRange` + `/Contents` | Signature harus menjadi bagian dari struktur PDF |
| Key ownership | Public key terikat pada akun pemilik | Verifikasi perlu mengetahui public key mana yang relevan |
| Private key protection | Tidak menyimpan plaintext tanpa proteksi; gunakan proteksi saat at-rest/in-transit | Mencegah penyalahgunaan private key |
| Original file retention | Simpan original dan signed copy secara terpisah bila ruang lingkup memungkinkan | Memudahkan audit dan perbandingan |
| Verification result | Valid / invalid / error dengan alasan | Membedakan signature mismatch, file rusak, dan kegagalan teknis |
| Third-party compatibility | Target CMS/PDF standard dan uji reader eksternal | Menjadi dasar klaim bonus interoperability |

### 6.1 Key management considerations

- Private key tidak boleh disimpan di GitHub, frontend bundle, log, atau response API.
- Jika private key disimpan di server untuk kebutuhan prototype, lindungi dengan mekanisme enkripsi dan batasi aksesnya. Dokumentasikan keterbatasan model ini.
- Alternatif yang lebih kuat adalah private key dibuat dan disimpan pada sisi pengguna, lalu hanya digunakan untuk signing melalui alur yang aman. Pilihan ini memerlukan desain tambahan dan harus disesuaikan dengan arsitektur aplikasi.
- Public key boleh disimpan sebagai bagian dari profil/key record, tetapi perubahan public key harus memiliki mekanisme pengelolaan yang jelas.
- Key pair baru tidak boleh diam-diam menggantikan key lama tanpa memperhatikan dokumen yang telah ditandatangani dengan key sebelumnya.

---

## 7. Test Plan and Failure Analysis

Pengujian harus menunjukkan bukan hanya happy path, tetapi juga kondisi ketika signing atau verification dapat gagal.

| Test case | Procedure | Expected result |
|---|---|---|
| Key generation | Generate key pair untuk akun baru | Public/private key pair berhasil dibuat |
| Key pair reuse | Generate key untuk akun yang sudah punya key | Sistem mencegah overwrite tanpa konfirmasi/prosedur rotasi |
| Valid signing | Sign PDF menggunakan private key pemilik | Signed PDF terbentuk |
| Valid verification | Verify signed PDF dengan public key pasangannya | Valid |
| Wrong public key | Verify dengan public key akun lain | Invalid |
| Content tampering | Ubah byte/konten pada bagian yang ditandatangani | Invalid |
| Signature tampering | Ubah nilai `/Contents` | Invalid |
| ByteRange tampering | Ubah nilai `/ByteRange` | Invalid atau parsing/verification error |
| Corrupted PDF | Upload file PDF rusak/tidak valid | Ditolak atau error yang aman |
| Unauthorized signing | User A mencoba sign dokumen User B | Access denied |
| Unauthorized retrieval | User A mencoba download dokumen User B | Access denied |
| Private key unavailable | User tidak memiliki akses ke private key | Signing tidak dapat dilakukan |
| PDF reader compatibility | Buka signed PDF pada reader pihak ketiga | Catat apakah signature dikenali dan hasil validasinya |

### 7.1 Risks and limitations to discuss

1. **Private key compromise:** pihak lain yang memperoleh private key dapat membuat signature yang tampak sah. Mitigasi: key protection, akses terbatas, dan prosedur revoke/rotate.
2. **Wrong public key association:** signature dapat valid secara matematis tetapi public key tidak benar-benar milik orang yang diklaim. Mitigasi: kaitkan public key dengan akun terautentikasi dan jelaskan batas verifikasi identitas.
3. **Document modification:** perubahan pada bagian yang ditandatangani harus terdeteksi. Perubahan incremental setelah signature perlu dianalisis sesuai aturan PDF; jangan menyamakan semua perubahan file dengan pemalsuan.
4. **Signature stripping or malformed PDF:** struktur PDF dapat rusak atau signature dihapus. Mitigasi: parsing defensif dan test terhadap file rusak.
5. **Replay or wrong-document signing:** signature harus terikat pada byte range dokumen yang benar. Pastikan verifier membaca struktur dari PDF yang diperiksa, bukan metadata yang tidak tepercaya.
6. **Third-party incompatibility:** implementasi internal mungkin valid tetapi tidak dikenali PDF reader. Mitigasi: gunakan struktur PDF/CMS yang sesuai standar dan uji secara terpisah.
7. **False trust claims:** status “signature valid” tidak otomatis berarti dokumen benar, identitas telah diverifikasi oleh CA, atau sertifikat dipercaya. UI dan laporan harus menjelaskan cakupannya.

---

## 8. Sprint Plan and Integration Milestones

| Sprint | Main focus | Deliverables | Completion evidence |
|---|---|---|---|
| **Sprint 1 — Foundation** | Repository review, API/DB design, PDF upload, key generation proof-of-concept | Upload PDF, key pair generation, schema, agreed interfaces | Demo upload and key generation |
| **Sprint 2 — Cryptography** | SHA-256 digest, signing, verification primitives, key protection | Signing/verification module and unit tests | Correct key succeeds; wrong key fails |
| **Sprint 3 — PDF Integration** | Signature field, ByteRange, Contents, embedding and parsing | Signed PDF and internal PDF verification | PDF opens and embedded signature verifies |
| **Sprint 4 — QA & Delivery** | Tampering, authorization, compatibility, report and demo | Test evidence, final report, README, AI disclosure | Reproducible end-to-end demonstration |

### 8.1 Integration ownership

- Angela integrates frontend screens with backend endpoints.
- Jahhaza owns API contracts and integration of backend modules.
- Maleka provides documented function interfaces for key generation, signing, and verification.
- Jorell coordinates PDF structure integration and cross-module tests.
- All members review at least one module outside their primary ownership.

---

## 9. Final Report Allocation (Maximum 2 A4 Pages)

The Assignment 3 report is separate from previous assignment reports. It must be concise and focus on the new digital signature feature.

| Report section | Primary owner | Required content |
|---|---|---|
| Scenario and need for digital signatures | Jorell | Why KYC PDFs need integrity/authenticity checks |
| Who signs and verifies what | Jahhaza | Actors, ownership, workflow |
| Significant design decisions | Maleka | Algorithm, hash, key management, signing/verification logic |
| PDF design decisions | Jorell | ByteRange, Contents, embedding, interoperability |
| Design analysis | All members; Jorell consolidates | Failure scenarios, tests, limitations, why selected analyses fit the scenario |
| Final editing and page limit | Jorell | Maximum 2 A4 pages, consistency and evidence |

**Report checklist**
- [ ] Explain why digital signatures are needed in the VELTRIX BankKYC scenario.
- [ ] Explicitly identify who signs which PDF and who verifies it.
- [ ] Justify every significant design decision.
- [ ] Explain the PDF embedding mechanism.
- [ ] Analyze relevant failure scenarios and show test evidence.
- [ ] State limitations honestly, especially identity binding and third-party compatibility.
- [ ] Keep the report within two A4 pages and submit it separately from previous assignment reports.

---

## 10. GitHub, Evidence, and AI Disclosure

The lecturer uses commit history as part of the assessment. Work should therefore be committed regularly with meaningful messages.

Suggested commit examples:

```text
feat(frontend): add PDF upload and signing interface
feat(keys): implement RSA key pair generation
feat(crypto): implement SHA-256 digest and signature verification
feat(pdf): prepare PDF signature dictionary and ByteRange
feat(pdf): embed detached signature into PDF Contents
test(crypto): add wrong-key and tampering test cases
test(pdf): add malformed PDF and compatibility checks
docs(report): document design decisions and failure analysis
```

Avoid one large final commit containing the entire assignment. Do not commit private keys, real personal data, `.env` files, or secrets.

### 10.1 Required evidence

- [ ] Screenshot of PDF upload.
- [ ] Screenshot/output of key pair generation without exposing private key material.
- [ ] Screenshot of successful signing.
- [ ] Example signed PDF.
- [ ] Screenshot/output of successful internal verification.
- [ ] Wrong-key verification result.
- [ ] Tampered-document verification result.
- [ ] Authorization test result.
- [ ] Third-party PDF reader result, if attempted.
- [ ] Meaningful GitHub commit history.
- [ ] AI conversation link and screenshot, as required by the assignment.
- [ ] AI-generated suggestions must be checked, tested, and understood by the team before inclusion.

---

## 11. Definition of Done

Assignment 3 is ready for submission when:

- [ ] The original VELTRIX BankKYC scenario is retained.
- [ ] A user without a key pair can generate one.
- [ ] A user can sign their own uploaded PDF using their private key.
- [ ] The signature is embedded in the PDF.
- [ ] The application can verify the signature using the corresponding public key.
- [ ] A wrong public key or modified signed content causes verification to fail.
- [ ] Private key material is not exposed in frontend responses, logs, or GitHub.
- [ ] The PDF remains readable after signing.
- [ ] The team has documented design decisions and relevant failure analysis.
- [ ] The separate report is no longer than two A4 pages.
- [ ] All code is pushed to GitHub with meaningful commit history.
- [ ] AI usage is disclosed with a conversation link and screenshot.

**Bonus target:** A third-party PDF reader recognizes the embedded signature and reports its cryptographic validity. This must be demonstrated with actual test evidence; do not claim success based only on the application's own verifier.

---

## 12. Open Decisions to Confirm

| Question | Proposed action |
|---|---|
| Will private keys be stored server-side or remain client-side? | Decide after evaluating security, usability, and implementation time |
| Which exact RSA signature scheme will be used? | Prototype PDF/CMS compatibility before finalizing |
| Is CMS detached signature required for the bonus target? | Treat as the preferred interoperability direction and verify against the PDF reader |
| Which PDF library will be used? | Test PDF writing and incremental update behavior before committing |
| Should users be able to sign a PDF more than once? | Define whether multiple signatures/approval stages are in scope |
| How will public keys be trusted/associated with accounts? | Document account binding and its limitations |

---

**Document note:** This file is the team's working implementation plan, not a claim that all features have already been implemented. Update the status, library choices, test results, and ownership if the actual implementation changes.
