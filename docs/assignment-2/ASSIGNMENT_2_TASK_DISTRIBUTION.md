# VELTRIX BankKYC — Assignment 2 Task Distribution (Key Management)

**Skenario:** rekening organisasi mahasiswa — [ASSIGNMENT_2_SCENARIO_OPTIONS.md](ASSIGNMENT_2_SCENARIO_OPTIONS.md)  
**Desain teknis, API, dan tes:** [ASSIGNMENT_2_IMPLEMENTATION_PLAN.md](ASSIGNMENT_2_IMPLEMENTATION_PLAN.md) (nomor § di bawah merujuk ke dokumen ini)  
**Implementation mode:** data sintetis saja; memperluas BankKYC yang ada, bukan membuat proyek baru.

> **Tujuan:** pemohon dapat meminta dokumen pemohon lain; pemilik menyetujui dan sistem membuat kunci simetris; kunci itu dikirim lewat email dalam bentuk terenkripsi RSA; kunci tersimpan terbungkus KEK di server.

---

## 1. Keputusan yang dikunci

| ID | Keputusan | Status |
|---|---|---|
| DEC2-01 | Skenario: ketua HIMA meminta dokumen bendahara untuk pengajuan rekening organisasi | **Locked** (disetujui asdos) |
| DEC2-02 | Hanya akun `applicant` yang bisa meminta dan memberi akses; satu permintaan = satu pemilik | **Locked** |
| DEC2-03 | Pasangan kunci RSA-OAEP 2048/SHA-256 dibuat di browser; **private key tidak pernah dikirim ke server** | **Locked** |
| DEC2-04 | Kunci berbagi AES-256 dibuat saat pemilik menyetujui; salinan dokumen dienkripsi AES-256-GCM dengan AAD | **Locked** |
| DEC2-05 | Server membuka dokumen **hanya** dengan kunci yang dikirim peminta dari paket kunci | **Locked** |
| DEC2-06 | Kunci berbagi disimpan terbungkus KEK yang sudah ada; dihapus saat dicabut/kedaluwarsa | **Locked** |
| DEC2-07 | Masa berlaku default 7 hari; pemilik bisa mencabut kapan saja | **Locked** (disetujui asdos) |
| DEC2-08 | Enkripsi berlapis Assignment 1 (RC4 → DES → AES-GCM) dan lab benchmark tidak diubah | **Locked** |
| DEC2-09 | Migrasi baru `0003_data_sharing.py`; tidak mengubah migrasi `0001`/`0002` | **Locked** |

---

## 2. RACI singkat

**Lead** = penanggung jawab hasil dan penggabungan; **Support** = membantu kode, review, dan tes.

| Workstream | Lead | Support | Prioritas | Target utama |
|---|---|---|---|---|
| Kontrak API & format paket kunci | **Caca** | Maleka, Angela | P0 | Disepakati di hari 1–2, lalu dikunci |
| Skema DB + migrasi `0003` | **Caca** | Jorell | P0 | Tabel baru tanpa merusak DB lama |
| Endpoint permintaan, persetujuan, buka dokumen | **Caca** | Maleka | P0 | Alur status dan aturan akses berjalan |
| Modul kriptografi berbagi (AES, RSA, wrap KEK) | **Maleka** | Caca | P0 | Fungsi teruji, dipakai endpoint |
| Kriptografi di browser (Web Crypto) | **Angela** | Maleka | P0 | Buat kunci, buka paket kunci, tanpa mengirim private key |
| UI Kunci saya & Berbagi dokumen | **Angela** | Caca | P0 | Alur lengkap bisa didemokan |
| Tes keamanan & ADR | **Maleka** | Jorell | P0/P1 | T01–T14 lolos, ADR tertulis |
| Uji E2E, pengiriman email, audit DB | **Jorell** | Semua | P0 | Bukti E01–E10 |
| Laporan & presentasi | **Jorell** | Semua | P0 | Laporan sesuai bukti nyata |

---

## 3. Task list per anggota — detail siap dibuat GitHub Issues

### A. ANGELA — Frontend owner

**A-FE-01 — Modul kriptografi browser `share-crypto.ts`** `P0`

- Buat `frontend/src/lib/share-crypto.ts` dengan `generateKeyPair()`, `parsePackage(text)`, dan `unwrapShareKey(packageText, privateKeyPem)` memakai Web Crypto API (RSA-OAEP, SHA-256). Format paket di §1.2.
- Hitung sidik jari SHA-256 dari SPKI dan tampilkan 16 karakter hex pertama.
- Private key hanya dibaca dari file yang dipilih user; jangan simpan di `localStorage`, state global, atau log.
- **Output:** modul + tes kecil (buat kunci → enkripsi dengan public key → buka dengan private key).
- **DoD:** paket yang dibuat backend (contoh dari Maleka) bisa dibuka; paket rusak atau untuk kunci lain menghasilkan error yang jelas.

**A-FE-02 — Halaman Kunci saya (`/keys`)** `P0`

- Tombol "Buat pasangan kunci" → unduh `veltrix-private-key-<username>.pem` → kirim public key ke `PUT /keys/me`.
- Tampilkan sidik jari, tanggal dibuat, dan peringatan untuk menyimpan file private key.
- Tombol "Ganti kunci" dengan konfirmasi bahwa paket lama perlu dikirim ulang.
- **Output:** halaman + screenshot.
- **DoD:** user tanpa kunci diarahkan ke halaman ini sebelum bisa meminta akses.

**A-FE-03 — Halaman Berbagi dokumen (`/sharing`)** `P0`

- Tab **Minta akses**: username pemilik, alasan, centang dokumen (profil, KTP, formulir, video).
- Tab **Permintaan masuk**: daftar permintaan dengan nama peminta, alasan, dan sidik jari kuncinya; modal Setujui (pilih pengajuan dan dokumen); setelah disetujui tampilkan paket kunci dengan tombol **Salin** dan **Kirim via Email** (`https://wa.me/?text=…`); tombol Tolak dan Cabut akses.
- Tab **Permintaan keluar**: status setiap permintaan; tombol Batalkan saat `PENDING`.
- **Output:** halaman tiga tab + screenshot tiap status.
- **DoD:** semua status (`PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`, `REVOKED`, `EXPIRED`) punya tampilan yang jelas.

**A-FE-04 — Alur Buka dokumen** `P0`

- Tempel paket kunci + pilih file private key → `unwrapShareKey` → panggil `POST …/items/{id}/open` dengan kunci berbagi.
- Pratinjau gambar, PDF, dan video memakai pola preview di `case-detail.tsx`; hapus object URL saat modal ditutup.
- Kunci berbagi hanya di memori selama halaman terbuka.
- **Output:** alur buka dokumen + screenshot.
- **DoD:** dokumen tampil dengan paket dan kunci yang benar; error generik saat kunci salah, akses dicabut, atau kedaluwarsa.

**A-FE-05 — Integrasi & verifikasi frontend** `P0/P1`

- Tambah fungsi API di `lib/kyc-api.ts`, tipe di `lib/kyc.ts`, menu pemohon di `components/app-shell.tsx`.
- Mode mock: tampilkan "Fitur berbagi hanya tersedia di mode live".
- Jalankan `npm run typecheck` dan `npm run build`.
- **Output:** PR frontend dengan screenshot.
- **DoD:** alur berjalan di mode live dengan backend asli.

### B. CACA — Backend lead & system integration

**C-BE-01 — Kontrak API & format paket** `P0`

- Tulis kontrak final endpoint (§1.5) dan format paket (§1.2) di `backend/openapi.json`; bagikan ke tim di hari 1–2.
- **Output:** kontrak yang disetujui Angela dan Maleka.
- **DoD:** setelah dikunci, perubahan kontrak harus diumumkan ke semua anggota.

**C-BE-02 — Migrasi `0003_data_sharing.py`** `P0`

- Tabel `user_public_keys`, `share_requests`, `share_items` (§1.4) di `kyc/db.py` dan migrasi baru.
- **Output:** migrasi + tes fresh install dan upgrade dari DB lama.
- **DoD:** `manage.py migrate` berhasil di DB baru dan DB yang sudah berisi data Assignment 1.

**C-BE-03 — Endpoint kunci publik** `P0`

- `GET/PUT /keys/me`: validasi PEM, RSA ≥ 2048-bit, satu kunci aktif per user, kunci lama diberi `revoked_at`.
- **DoD:** PEM rusak, kunci terlalu kecil, atau bukan RSA ditolak dengan 422.

**C-BE-04 — Endpoint permintaan & status** `P0`

- Buat, daftar masuk/keluar, tolak, batalkan (§1.5) dengan transisi status di §1.3.
- Aturan: hanya `applicant`; tidak boleh ke diri sendiri; peminta wajib punya public key aktif.
- **DoD:** transisi status yang tidak sah ditolak dengan 409.

**C-BE-05 — Endpoint approve, package, revoke, items, open** `P0`

- Memanggil fungsi dari M-SEC-01/02/03.
- Cek kedaluwarsa setiap kali permintaan diakses; saat `REVOKED`/`EXPIRED` hapus `share_items` dan kunci terbungkus.
- `open` mengirim respons dengan `Cache-Control: no-store`.
- **DoD:** hanya pemilik yang bisa approve/revoke/package; hanya peminta yang bisa items/open.

**C-BE-06 — Rate limit, audit, dokumentasi** `P1`

- `rate_limit` untuk pembuatan permintaan dan `open`.
- Event `SHARE_*` ke `security_events` (§1.5), tanpa kunci atau isi dokumen.
- Perbarui `backend/README.md`.
- **DoD:** setiap aksi tercatat; tidak ada data rahasia di log.

### C. MALEKA — Cryptography & security

**M-SEC-01 — Modul `kyc/sharing_crypto.py`** `P0`

- `new_share_key`, `encrypt_item`/`decrypt_item` (AES-256-GCM dengan AAD §1.1), `wrap_share_key`/`unwrap_share_key` (KEK), `rsa_encrypt_share_key` (RSA-OAEP SHA-256, library `cryptography`), `build_package`, `fingerprint`.
- **Output:** modul + unit test.
- **DoD:** round-trip lolos; AAD atau tag yang diubah gagal tanpa plaintext.

**M-SEC-02 — Enkripsi ulang saat approve** `P0`

- Buka dokumen pemilik lewat `open_object` yang sudah ada, lalu enkripsi ulang dengan kunci berbagi. Plaintext hanya di memori, tidak ditulis ke disk atau temp file.
- **DoD:** salinan di `share_items` hanya bisa dibuka dengan kunci berbagi yang benar.

**M-SEC-03 — Logika `open` yang aman** `P0`

- Hanya memakai kunci dari peminta, bukan salinan di server.
- Semua kegagalan memakai pesan dan kode yang sama, tanpa membocorkan tahap yang gagal.
- **DoD:** kunci acak, kunci permintaan lain, dan ciphertext yang diubah menghasilkan respons identik.

**M-SEC-04 — Tes keamanan `tests/test_sharing_security.py`** `P0`

- Kasus T01–T14 di §3.1, termasuk pemeriksaan SQLite bahwa tidak ada kunci atau dokumen dalam plaintext.
- **Output:** tes + ringkasan hasil di PR.
- **DoD:** semua lolos; tes Assignment 1 tetap lolos.

**M-SEC-05 — ADR `docs/decisions/ADR_KEY_SHARING.md`** `P1`

- Kenapa RSA-OAEP (bukan PKCS#1 v1.5), kenapa private key di browser, kenapa server tidak memakai salinan kuncinya, apa yang dilindungi dan apa yang tidak (§6).
- **DoD:** alasan dikaitkan dengan ancaman nyata (chat disadap, akun dicuri, DB bocor), bukan sekadar "lebih kuat".

### D. JORELL — QA, demo & report

**J-QA-01 — Data uji & akun demo** `P0`

- Siapkan akun Andi, Budi, dan Citra (pihak ketiga) beserta pengajuan dummy Budi (profil, KTP, formulir).
- **DoD:** siapa pun di tim bisa mengulang demo dari awal.

**J-QA-02 — Uji end-to-end E01–E10** `P0`

- Jalankan skenario di §3.2 dengan bukti screenshot, termasuk pengiriman paket lewat email sungguhan.
- **Output:** `docs/assignment-2/VERIFICATION.md` berisi langkah, hasil, dan screenshot.
- **DoD:** setiap langkah punya hasil yang diamati, bukan hanya "siap uji".

**J-QA-03 — Audit penyimpanan** `P0`

- Buka `bankkyc.db` dan tunjukkan isi `share_requests` dan `share_items` hanya ciphertext; tunjukkan baris terhapus setelah dicabut.
- **DoD:** screenshot sebelum dan sesudah pencabutan.

**J-QA-04 — Tes Playwright alur utama** `P2`

- Opsional bila waktu cukup: minta → setujui → buka.

**J-DOC-05 — Laporan & presentasi** `P0`

- Skenario, alur, keputusan desain (ambil dari ADR), hasil uji, batasan (§6), dan kontribusi tiap anggota sesuai PR.
- **DoD:** setiap klaim di laporan didukung bukti dari J-QA-02/03 atau tes otomatis.

---

## 4. Urutan dan dependensi

| Hari | Kegiatan | Bergantung pada |
|---|---|---|
| 1–2 | C-BE-01 kontrak, C-BE-02 migrasi, M-SEC-01 modul kripto, A-FE-01 kripto browser, J-QA-01 data uji | — |
| 3–4 | C-BE-03..05 endpoint, M-SEC-02..03 integrasi, A-FE-02..04 halaman | Kontrak C-BE-01 |
| 5 | Integrasi FE + BE, M-SEC-04 tes keamanan, J-QA-02..03 uji & audit | Endpoint dan halaman selesai |
| 6–7 | M-SEC-05 ADR, J-DOC-05 laporan, latihan demo | Hasil uji |

**Go / No-Go sebelum demo:** T01–T14 lolos, E01–E10 punya bukti, dan tes Assignment 1 tetap lolos.

---

## 5. GitHub collaboration

| Person | Branch | PR minimum yang bisa direview sendiri |
|---|---|---|
| Angela | `feat/a2-sharing-frontend` | `share-crypto.ts` + halaman Kunci saya + Berbagi dokumen |
| Caca | `feat/a2-sharing-api` | Migrasi `0003` + endpoint + kontrak API |
| Maleka | `feat/a2-sharing-crypto` | `sharing_crypto.py` + tes keamanan + ADR |
| Jorell | `feat/a2-sharing-qa` | Data uji + `VERIFICATION.md` + laporan |

**Praktik PR:**

- Commit menjelaskan pekerjaan yang benar-benar dilakukan.
- PR berisi ringkasan, screenshot/respons, perintah tes beserta hasilnya, batasan, dan ID tugas.
- Jangan commit `.env`, `bankkyc.db`, KEK, file private key `.pem`, atau paket kunci sungguhan.
- Caca menggabungkan migrasi dan kontrak lebih dulu; Maleka membuat modul kripto terpisah supaya tidak saling menimpa `backend/kyc/main.py`; Angela rebase ke kontrak final.

### Contoh format GitHub issue

```md
## [M-SEC-03] Logika open yang aman
Owner: Maleka | Support: Caca | Priority: P0

### Problem
Peminta harus membuktikan bahwa ia menerima paket kunci dari pemilik; akun saja tidak cukup.

### Scope
- `open` hanya mendekripsi dengan kunci yang dikirim peminta.
- Kegagalan apa pun memberi respons yang sama.

### Acceptance criteria
- [x] Kunci benar → dokumen identik byte demi byte.
- [x] Kunci acak / kunci permintaan lain / ciphertext diubah → respons identik dan tanpa plaintext.
- [x] Tes T02, T08, T09 lolos.

### Dependencies
M-SEC-01, C-BE-05
```
