# VELTRIX BankKYC — Assignment 3 Task Distribution (Digital Signature)

**Skenario:** sama dengan Assignment 2 — rekening organisasi mahasiswa ([ASSIGNMENT_2_SCENARIO_OPTIONS.md](../assignment-2/ASSIGNMENT_2_SCENARIO_OPTIONS.md))  
**Desain teknis, API, dan tes:** [ASSIGNMENT_3_IMPLEMENTATION_PLAN.md](ASSIGNMENT_3_IMPLEMENTATION_PLAN.md) (nomor § di bawah merujuk ke dokumen ini)  
**Implementation mode:** data sintetis saja; memperluas BankKYC yang ada, bukan membuat proyek baru.

> **Tujuan:** pemohon bisa membuat pasangan kunci tanda tangan bila belum punya, menandatangani PDF miliknya dengan private key sendiri (di browser), signature tertanam di PDF dalam format standar, dan aplikasi — serta PDF reader pihak ketiga — bisa memverifikasinya.

---

## 1. Keputusan yang dikunci

| ID | Keputusan | Status |
|---|---|---|
| DEC3-01 | Skenario tetap: Budi (bendahara HIMA, pemohon) menandatangani formulir pembukaan rekening PDF; reviewer, Andi (via berbagi A2), dan pihak ketiga memverifikasi | **Proposed** (konfirmasi asdos) |
| DEC3-02 | Pasangan kunci tanda tangan **terpisah** dari kunci RSA-OAEP A2: RSA-3072, RSASSA-PKCS1-v1_5 + SHA-256, dibuat di browser | **Proposed** |
| DEC3-03 | Penandatanganan di **browser**; private key tidak pernah dikirim ke server (konsisten DEC2-03). Server hanya `prepare` dan `complete` | **Proposed** |
| DEC3-04 | EMSA-PKCS1-v1_5, RSASP1 (CRT + blinding), RSAVP1, dan verifikasi encode-then-compare **ditulis sendiri** (TS + Python). Library hanya untuk key generation, SHA-256, PDF, DER | **Proposed** (konfirmasi asdos, §8) |
| DEC3-05 | Format PDF: signature field via incremental update, `/SubFilter /adbe.pkcs7.detached`, CMS SignedData detached, `/Contents` 8192 byte | **Proposed** |
| DEC3-06 | Kunci diikat ke akun lewat proof of possession + sertifikat X.509 dari **VELTRIX Demo CA**; kunci CA dibungkus KEK yang ada | **Proposed** |
| DEC3-07 | Verifier ketat: satu signature, ByteRange harus menutup seluruh file, allowlist algoritma, e = 65537; tujuh status hasil (§1.7) | **Proposed** |
| DEC3-08 | Signed PDF disimpan sebagai objek terenkripsi baru (envelope A1); unggahan asli tetap ada; kunci lama tidak dihapus saat diganti | **Proposed** |
| DEC3-09 | Migrasi baru `0004_digital_signature.py`; tidak mengubah `0001`–`0003` | **Locked** |
| DEC3-10 | Enkripsi berlapis A1, alur berbagi A2, dan lab benchmark tidak diubah; berbagi item `document` memakai signed PDF terbaru bila ada (P1) | **Locked** |

Status **Proposed** diubah menjadi **Locked** setelah disepakati tim di hari 1 (dan asdos untuk DEC3-01/04).

---

## 2. RACI singkat

**Lead** = penanggung jawab hasil dan penggabungan; **Support** = membantu kode, review, dan tes.

| Workstream | Lead | Support | Prioritas | Target utama |
|---|---|---|---|---|
| Kontrak API & format sesi tanda tangan | **Caca** | Maleka, Jorell, Angela | P0 | Disepakati di hari 1–2, lalu dikunci |
| Skema DB + migrasi `0004` | **Caca** | Jorell | P0 | Tabel baru tanpa merusak DB lama |
| Endpoint kunci, sesi, verifikasi | **Caca** | Maleka | P0 | Alur prepare → complete → verify berjalan |
| RSASSA-PKCS1-v1_5 sendiri (Python) | **Maleka** | Angela | P0 | Identik dengan library pembanding |
| CMS SignedData & VELTRIX Demo CA | **Maleka** | Caca | P0 | CMS lolos `pdfsig`; sertifikat terbit setelah PoP |
| Kriptografi browser `signing-crypto.ts` | **Angela** | Maleka | P0 | Buat kunci, tanda tangani, verifikasi sendiri; tanpa mengirim private key |
| UI kunci, tanda tangan, verifikasi | **Angela** | Caca | P0 | Alur lengkap bisa didemokan |
| Penulisan & pembacaan struktur PDF | **Jorell** | Maleka | P0 | Incremental update + ByteRange benar |
| Tes keamanan & ADR | **Maleka** | Jorell | P0/P1 | T01–T19 lolos, ADR tertulis |
| Tampering, kompatibilitas reader, E2E | **Jorell** | Semua | P0 | Bukti E01–E12 + matriks §3.3 |
| Laporan (≤ 2 halaman) & presentasi | **Jorell** | Semua | P0 | Laporan sesuai bukti nyata |

> Caca = Jahhaza (penanggung jawab backend di Assignment 1 dan 2).

---

## 3. Task list per anggota — detail siap dibuat GitHub Issues

### A. ANGELA — Frontend owner

**A3-FE-01 — Modul kriptografi browser `signing-crypto.ts`** `P0`

- Buat `frontend/src/lib/signing-crypto.ts` (§1.10): `generateSigningKeyPair()` (Web Crypto RSASSA-PKCS1-v1_5, 3072-bit, e = 65537), `loadPrivateKeyParams(pem)` (impor PKCS#8 → ekspor JWK → BigInt), `emsaPkcs1v15Encode`, `rsasp1` (CRT + blinding), `rsavp1`, `signSignedAttrs`, `signPopChallenge`.
- Signature selalu diverifikasi sendiri dengan public key sebelum dikembalikan; gagal → error, tidak dikirim.
- Private key hanya dibaca dari file yang dipilih user; tidak disimpan di `localStorage`, state global, atau log; variabel BigInt dibuang setelah selesai.
- **Output:** modul + tes memakai test vector bersama dari Maleka (M3-SEC-01).
- **DoD:** signature dari TS identik byte demi byte dengan Python untuk semua test vector; kunci rusak atau bukan RSA-3072 menghasilkan error yang jelas.

**A3-FE-02 — Bagian Kunci tanda tangan** `P0`

- Di halaman kunci yang sudah ada (berdampingan dengan kunci berbagi A2): tombol "Buat kunci tanda tangan" → unduh `veltrix-signing-key-<username>.pem` → `POST /signing-keys/challenge` → `PUT /signing-keys/me` dengan PoP.
- Tampilkan fingerprint, serial, masa berlaku sertifikat, riwayat kunci yang dicabut; peringatan bahwa pemegang file bisa menandatangani atas nama user.
- Tombol "Ganti kunci" dengan konfirmasi.
- **Output:** halaman + screenshot (E01, E11).
- **DoD:** user tanpa kunci tanda tangan diarahkan ke sini saat menekan "Tanda tangani".

**A3-FE-03 — Alur Tanda tangani PDF** `P0`

- Di `applicant/applications/[id]`: lencana status signature per formulir PDF; tombol **Tanda tangani** hanya saat `DRAFT`/`NEEDS_REVISION`; formulir DOCX menampilkan petunjuk unggah PDF.
- Modal: `prepare` → pratinjau `preview` (pola preview di `case-detail.tsx`, object URL dihapus saat ditutup) → tampilkan SHA-256 dokumen + fingerprint kunci → pilih file private key → `signSignedAttrs` → `complete` → hasil.
- **P1:** hitung ulang digest dari byte pratinjau sesuai `byte_range` dan cocokkan dengan `messageDigest` di `signed_attrs`; tidak cocok → batalkan dengan peringatan.
- Tombol **Unduh PDF bertanda tangan**.
- **Output:** alur + screenshot (E02, E03).
- **DoD:** alur selesai di mode live; sesi kedaluwarsa/terpakai menampilkan pesan yang jelas.

**A3-FE-04 — UI Verifikasi** `P0`

- Halaman `/verify` (semua role): unggah PDF → kartu hasil per status §1.7 (warna dan teks berbeda untuk `VALID`, `VALID_UNTRUSTED`, `INVALID`, `MODIFIED_AFTER_SIGNING`, `KEY_REVOKED`/`SIGNER_MISMATCH`, `NOT_SIGNED`, `MALFORMED`), penandatangan dari sertifikat, fingerprint, alasan.
- Teks tetap: "Valid berarti dokumen tidak berubah sejak ditandatangani dengan kunci terdaftar — bukan berarti isinya benar."
- Panel "Tanda tangan digital" di `reviewer/applications/[id]` dengan tombol **Verifikasi ulang**.
- Tautan unduh `ca.pem` + panduan singkat impor ke Adobe Reader.
- **Output:** halaman + screenshot tiap status.
- **DoD:** semua status punya tampilan yang berbeda dan dapat dipahami tanpa membaca kode.

**A3-FE-05 — Integrasi & verifikasi frontend** `P0/P1`

- Fungsi API di `lib/kyc-api.ts`, tipe di `lib/kyc.ts`, menu "Verifikasi PDF" di `components/app-shell.tsx`.
- Mode mock: "Fitur tanda tangan hanya tersedia di mode live".
- Jalankan `npm run typecheck`, `npm run build`, dan tes `signing-crypto`.
- **Output:** PR frontend dengan screenshot.
- **DoD:** alur berjalan di mode live dengan backend asli.

### B. CACA — Backend lead & system integration

**C3-BE-01 — Kontrak API & format sesi** `P0`

- Tulis kontrak final §1.9 dan bentuk respons `prepare` (`session_id`, `signed_attrs_der`, `digest`, `byte_range`, `key_fingerprint`, `expires_at`) serta hasil verifikasi (`status`, `reasons[]`, `signer`, `fingerprint`, `signed_at`) di `backend/openapi.json`.
- **Output:** kontrak yang disetujui Angela, Maleka, Jorell.
- **DoD:** setelah dikunci, perubahan kontrak harus diumumkan ke semua anggota.

**C3-BE-02 — Migrasi `0004_digital_signature.py`** `P0`

- Tabel `user_signing_keys`, `signing_key_challenges`, `pki_authority`, `signature_sessions`, `document_signatures` (§1.8) di `kyc/db.py` dan migrasi baru; indeks satu kunci aktif per user mengikuti pola `user_public_keys` (termasuk catatan MySQL).
- **Output:** migrasi + tes fresh install dan upgrade dari DB Assignment 2.
- **DoD:** `manage.py migrate` berhasil di DB baru dan DB yang sudah berisi data A1/A2 (SQLite dan MySQL).

**C3-BE-03 — Endpoint kunci tanda tangan & CA** `P0`

- `POST /signing-keys/challenge`, `GET/PUT /signing-keys/me`, `GET /pki/ca.pem`; memanggil `verify_pop` dan `issue_certificate` dari M3-SEC-03.
- Challenge sekali pakai, 5 menit; kunci lama diberi `revoked_at` + alasan dalam transaksi yang mengunci baris user.
- Pembuatan CA di `provision.py` bila belum ada.
- **DoD:** PEM rusak, RSA < 3072, e ≠ 65537, PoP salah, atau challenge dipakai ulang ditolak 422 (T15).

**C3-BE-04 — Endpoint sesi tanda tangan** `P0`

- `prepare`, `preview`, `complete` (§1.6): cek pemilik, status editable, PDF kategori `document`, belum bertanda tangan, kunci aktif; simpan prepared PDF lewat `store_object`; ikat sesi ke `evidence_id`, `case_version`, `signer_id`, `signing_key_id`.
- `complete`: verifikasi signature → `build_signed_data` (Maleka) → `embed_cms` (Jorell) → verifikasi penuh → simpan signed PDF + `document_signatures`; hapus objek sesi.
- `preview` dengan `Cache-Control: no-store`.
- **DoD:** T13 dan T14 lolos; sesi gagal tidak meninggalkan objek terenkripsi yatim.

**C3-BE-05 — Endpoint verifikasi & unduh** `P0`

- `GET /applications/{id}/signatures`, `POST …/verify`, `GET …/download`, `GET …/review-preview`, `POST /signatures/verify` (upload, ≤ 10 MB, tidak disimpan).
- Aturan akses: pemilik + reviewer yang ditugaskan; admin tidak melihat isi (sesuai A1).
- Simpan `last_status` dan `last_verified_at`.
- **DoD:** reviewer yang tidak ditugaskan ditolak; respons verifikasi tidak pernah berisi byte dokumen.

**C3-BE-06 — Aturan alur, integrasi A2, audit, dokumentasi** `P1`

- `VELTRIX_REQUIRE_SIGNED_FORM`: `submit`/`resubmit` ditolak bila formulir PDF terbaru belum `VALID`.
- Approve berbagi A2 untuk item `document` memakai signed PDF terbaru bila ada.
- `rate_limit` untuk challenge, prepare, complete, verify; event `SIGN_*`/`SIG_*` (§1.9) tanpa kunci, signature mentah, atau isi dokumen.
- Perbarui `backend/README.md` dan `.env.example`.
- **DoD:** setiap aksi tercatat; tes A1/A2 tetap lolos dengan flag `false`.

### C. MALEKA — Cryptography & security

**M3-SEC-01 — Modul `kyc/signature_rsa.py`** `P0`

- `emsa_pkcs1_v15_encode(hash, k)`, `rsasp1` (CRT + blinding, dipakai CA), `rsavp1`, `verify_pkcs1_v15(public, message_hash, signature)` dengan encode-then-compare dan `hmac.compare_digest`, `validate_public_key` (≥ 3072 untuk kunci user, e = 65537, `s < n`).
- Script `scripts/make_signature_vectors.py` → `tests/fixtures/signature_vectors.json` untuk dipakai Angela.
- **Output:** modul + unit test.
- **DoD:** T02 (identik dengan `pycryptodome` `pkcs1_15`) dan T09 (Bleichenbacher e = 3) lolos.

**M3-SEC-02 — Modul `kyc/cms.py`** `P0`

- `build_signed_attrs(digest, cert, signing_time)` → DER bertag `SET OF` (0x31); `build_signed_data(signed_attrs, signature, cert_chain)`; `parse_and_verify(cms_der, byte_range_digest)` sesuai langkah 5–9 §1.7. `asn1crypto` hanya untuk encode/decode DER.
- **Output:** modul + unit test.
- **DoD:** CMS buatan tim lolos `pdfsig` (dengan J3-PDF-01); SHA-1/MD5 ditolak (T10); sertifikat asing → `VALID_UNTRUSTED` (T11).

**M3-SEC-03 — Modul `kyc/pki.py` (VELTRIX Demo CA)** `P0`

- `create_authority(kek)` (RSA-3072, sertifikat root self-signed, private key dibungkus KEK dengan AAD `purpose='ca-key'`), `verify_pop(public, user_id, challenge, signature)`, `issue_certificate(public, user)` (X.509 v3, ekstensi §1.3, tbsCertificate ditandatangani `rsasp1` sendiri), `verify_chain(cert)`.
- **DoD:** sertifikat terbaca oleh `openssl x509 -text` dan diterima `pdfsig`; private key CA tidak pernah ada di DB dalam plaintext.

**M3-SEC-04 — Tes keamanan `tests/test_signature_security.py`** `P0`

- Kasus T01–T17 dan T19 di §3.1 (T18 bersama Jorell), termasuk pemeriksaan DB/log bahwa tidak ada private key, signature mentah di log, atau PDF plaintext.
- **Output:** tes + ringkasan hasil di PR.
- **DoD:** semua lolos; tes A1 dan A2 tetap lolos.

**M3-SEC-05 — ADR `docs/decisions/ADR_DIGITAL_SIGNATURE.md`** `P1`

- Kenapa signing di browser, kenapa kunci terpisah dari A2, kenapa RSA-3072 dan PKCS#1 v1.5 (bukan PSS), kenapa encode-then-compare, kenapa CA lokal + PoP, kenapa `/adbe.pkcs7.detached` (bukan `ETSI.CAdES.detached`), apa yang dilindungi dan tidak (§6, §7).
- **DoD:** setiap alasan dikaitkan dengan ancaman nyata (R1–R10), bukan sekadar "lebih aman".

### D. JORELL — PDF engineering, QA & report

**J3-PDF-01 — Modul `kyc/pdf_signing.py` (prepare)** `P0`

- `normalize(pdf_bytes)` (pypdf, xref klasik); `assert_signable` (tolak terenkripsi, sudah ada `/Sig`, `/SigFlags`); `prepare_incremental_update(pdf, signer_name, reason)` menulis objek §1.4 secara manual; `patch_byte_range`; `digest_byte_range`.
- **Hari 1–2:** proof of concept bersama Maleka — PDF fixture `bank_account_form_digital.pdf` ditandatangani CMS buatan tim dan lolos `pdfsig`.
- **Output:** modul + unit test.
- **DoD:** PDF hasil prepare tetap terbuka di `pypdf`, Chrome, dan Adobe; offset ByteRange benar untuk 3 fixture berbeda.

**J3-PDF-02 — Embed & extract** `P0`

- `embed_cms(prepared, cms_der)` (hex + padding nol, tolak > 8192 byte); `extract_signature(pdf)` membaca `/ByteRange` dan `/Contents` dari byte mentah **dan** dari pypdf lalu mencocokkannya; pemeriksaan langkah 1–4 §1.7.
- **DoD:** T05, T06, T07 lolos; tambahan byte setelah signature → `MODIFIED_AFTER_SIGNING`.

**J3-QA-03 — Generator tampering `scripts/make_tampered_pdfs.py`** `P0`

- Dari satu signed PDF hasilkan: byte isi diubah, hex `/Contents` diubah, ByteRange digeser, incremental update tambahan (ganti teks halaman), `/Contents` dari dokumen lain, file terpotong.
- **DoD:** setiap file punya status yang diharapkan dan dipakai di tes T04–T08 serta demo E07.

**J3-QA-04 — Kompatibilitas PDF reader (bonus)** `P0`

- Isi matriks §3.3: Adobe Acrobat Reader, Foxit, Okular/`pdfsig`, viewer Chrome/Edge — sebelum dan sesudah impor `ca.pem`, dan setelah dokumen diubah. Bersama Maleka buat T18 (`pdfsig` + NSS db sementara).
- **DoD:** setiap sel diisi dengan hasil yang diamati + screenshot; tidak ada klaim tanpa bukti.

**J3-QA-05 — Uji end-to-end E01–E12** `P0`

- Siapkan akun Budi, Andi, Citra, dan reviewer beserta pengajuan dummy dengan formulir PDF; jalankan §3.2 dengan screenshot.
- **Output:** `docs/assignment-3/VERIFICATION.md` berisi langkah, hasil, dan screenshot di `docs/assignment-3/screenshots/`.
- **DoD:** setiap langkah punya hasil yang diamati, bukan hanya "siap uji".

**J3-DOC-06 — Laporan (maks. 2 halaman A4) & presentasi** `P0`

- Terpisah dari laporan A1/A2. Isi: kenapa digital signature dibutuhkan di skenario, siapa menandatangani/memverifikasi apa (tabel §0), justifikasi setiap keputusan (DEC3-01..10, dari ADR), analisis (R1–R10 dengan bukti T/E, dan alasan analisis ini yang dipilih), batasan (§7).
- Lampirkan link + screenshot percakapan AI.
- **DoD:** ≤ 2 halaman; setiap klaim didukung bukti dari J3-QA-03..05 atau tes otomatis.

| Bagian laporan | Penulis draf | Bahan |
|---|---|---|
| Kenapa digital signature & siapa sign/verify apa | Caca | §0 |
| Keputusan kriptografi & kunci | Maleka | ADR, DEC3-02..04, 06 |
| Keputusan format PDF & verifikasi | Jorell | DEC3-05, 07, §1.4, §1.7 |
| Keputusan UI & alur | Angela | §1.6, §1.10 |
| Analisis & batasan | Semua; Jorell menyatukan | §6, §7, hasil uji |

---

## 4. Urutan dan dependensi

| Hari | Kegiatan | Bergantung pada |
|---|---|---|
| 1–2 | C3-BE-01 kontrak, C3-BE-02 migrasi, M3-SEC-01 RSA sendiri, J3-PDF-01 PoC `pdfsig`, A3-FE-01 `signing-crypto.ts` | — |
| 3–4 | M3-SEC-02..03 CMS & CA, J3-PDF-02 embed/extract, C3-BE-03..05 endpoint, A3-FE-02..04 halaman | Kontrak C3-BE-01, PoC J3-PDF-01 |
| 5 | Integrasi FE + BE, M3-SEC-04 tes, J3-QA-03..05 tampering, reader, E2E | Endpoint dan halaman selesai |
| 6–7 | C3-BE-06 (P1), M3-SEC-05 ADR, J3-DOC-06 laporan, latihan demo | Hasil uji |

**Titik risiko terbesar:** bila PoC hari 1–2 belum lolos `pdfsig`, Jorell dan Maleka berpasangan sampai lolos sebelum fitur lain dikerjakan — format PDF/CMS yang salah membatalkan bonus dan memaksa ulang embed/verify.

**Go / No-Go sebelum demo:** T01–T19 lolos, E01–E12 punya bukti, matriks §3.3 terisi, dan tes Assignment 1 & 2 tetap lolos.

---

## 5. GitHub collaboration

| Person | Branch | PR minimum yang bisa direview sendiri |
|---|---|---|
| Angela | `feat/a3-signing-frontend` | `signing-crypto.ts` + Kunci tanda tangan + Tanda tangani + `/verify` |
| Caca | `feat/a3-signing-api` | Migrasi `0004` + endpoint + kontrak API |
| Maleka | `feat/a3-signing-crypto` | `signature_rsa.py` + `cms.py` + `pki.py` + tes keamanan + ADR |
| Jorell | `feat/a3-pdf-signing` | `pdf_signing.py` + generator tampering + `VERIFICATION.md` + laporan |

**Praktik PR & commit (commit history dinilai):**

- Commit kecil dan bermakna sejak hari 1, bukan satu commit besar di akhir. Contoh:
  - `feat(crypto): implement EMSA-PKCS1-v1_5 encoding and RSASP1 with blinding`
  - `test(crypto): compare own RSASSA output with pycryptodome vectors`
  - `feat(pdf): write incremental update with signature placeholder`
  - `feat(pdf): patch ByteRange and embed detached CMS`
  - `feat(pki): issue X.509 certificates after proof of possession`
  - `feat(api): add signature session prepare and complete endpoints`
  - `feat(frontend): sign PDF in browser with own RSASSA implementation`
  - `test(pdf): detect incremental saving attack as modified after signing`
  - `docs(assignment-3): record third-party reader compatibility results`
- PR berisi ringkasan, screenshot/respons, perintah tes beserta hasilnya, batasan, dan ID tugas.
- Jangan commit `.env`, `bankkyc.db`, KEK, private key CA, file `.pem` private key user, atau signed PDF berisi data selain fixture sintetis.
- Caca menggabungkan migrasi dan kontrak lebih dulu; Maleka dan Jorell bekerja di modul terpisah (`signature_rsa.py`, `cms.py`, `pki.py`, `pdf_signing.py`) supaya tidak saling menimpa `backend/kyc/main.py`; Angela rebase ke kontrak final.
- Setiap anggota mereview minimal satu PR di luar area utamanya.
- Saran dari AI harus dicek, dites, dan dipahami sebelum masuk; simpan link percakapan untuk laporan.

### Contoh format GitHub issue

```md
## [J3-PDF-02] Embed & extract signature
Owner: Jorell | Support: Maleka | Priority: P0

### Problem
Signature harus tertanam di PDF, dan verifier harus menolak dokumen yang diberi tambahan
setelah ditandatangani walaupun bagian yang ditandatangani masih utuh.

### Scope
- `embed_cms` menulis CMS hex ke celah `/Contents` tanpa menggeser offset.
- `extract_signature` membaca `/ByteRange` + `/Contents` dari byte mentah dan pypdf, lalu mencocokkan.
- `b + c != panjang file` → `MODIFIED_AFTER_SIGNING`.

### Acceptance criteria
- [ ] Signed PDF terbuka di pypdf, Chrome, Adobe; `pdfsig` melaporkan signature valid.
- [ ] CMS > 8192 byte ditolak.
- [ ] Tes T05, T06, T07 lolos.

### Dependencies
J3-PDF-01, M3-SEC-02
```
