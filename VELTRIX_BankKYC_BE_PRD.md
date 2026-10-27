# VELTRIX BankKYC: Backend PRD dan Panduan Handoff

**Versi:** 1.0 · **Tanggal:** 27 Oktober 2026 · **Target:** teman pengembang backend dan reviewer integrasi FE–BE.

**Status dokumen:** spesifikasi implementasi. Dokumen ini tidak menyatakan backend BankKYC sudah dibuat. Frontend baru berjalan dengan API mock; backend FastAPI di repo masih mengikuti vault lama.

## Panduan baca cepat

1. Baca keputusan dan batas pekerjaan pada bagian 1–3.
2. Implementasikan model data, otorisasi dan state machine pada bagian 4–7.
3. Cocokkan API bagian 8 dengan kode FE; perhatikan catatan integrasi bagian 9.
4. Implementasikan storage/enkripsi dan retrieval pada bagian 10–12.
5. Kerjakan benchmark, migrasi, pengujian dan handoff pada bagian 13–19.

Acuan produk: [BankKYC PRD v2.1](VELTRIX_BankKYC_PRD.md). Acuan FE: [BankKYC FE PRD](VELTRIX_BankKYC_FE_PRD.md). Identitas visual tetap mengikuti GSM lama; pekerjaan BE tidak mengubah logo/palet/typography.

## 1. Hasil akhir yang diminta

Bangun backend untuk **simulasi onboarding rekening bank**, dengan satu pengajuan yang menghubungkan:

- Profil pribadi fiktif dalam JSON.
- Scan identitas dummy.
- Dokumen administrasi/kantor sintetis.
- Video verifikasi MP4 simulasi.

Pemohon dapat menyimpan draf, melengkapi bukti, submit, merevisi ketika diminta, memantau keputusan demo, serta mengambil data miliknya secara utuh. Reviewer menilai metadata kasus yang ditugaskan. Admin mengatur penugasan. Evaluator menguji fixture lab terpisah.

**Keberhasilan utama:** empat kategori terlindungi saat disimpan, akses dicek server pada setiap permintaan, file dipulihkan byte-identical, transisi status konsisten, dan angka eksperimen benar-benar diukur.

Produk ini tidak membuka rekening nyata, melakukan transaksi, menghubungi bank, menjalankan OCR/face matching/liveness, atau mengambil data nasabah asli. `ACCEPTED_DEMO` berarti keputusan simulasi, bukan rekening aktif.

## 2. Keputusan teknis dan hal yang masih terbuka

| ID | Keputusan / pertanyaan | Arah implementasi |
| --- | --- | --- |
| BE-01 | Stack | Python + FastAPI + Pydantic + SQLAlchemy + Alembic + MySQL; PyCryptodome untuk cipher, argon2-cffi untuk password |
| BE-02 | Database | **MySQL** sebagai target integrasi/penilaian; SQLite boleh untuk tes unit tertentu, tidak menggantikan pengujian MySQL |
| BE-03 | Storage payload | Usulan MVP: ciphertext final dan wrapped keys di tabel MySQL, memakai LONGBLOB untuk payload; keputusan storage ini memperjelas D-07 produk, bukan menggambarkan kode lama |
| BE-04 | Auth | Opaque server-side session dalam cookie HttpOnly; tidak memakai token auth di localStorage |
| BE-05 | Akses | RBAC + ownership + reviewer assignment + status pengajuan |
| D-01 | Interpretasi AES/DES/RC4 masih menunggu dosen | Baseline sementara: RC4 → DES-CBC → AES-256-GCM; tiga cipher independen diuji pada fixture lab |
| D-02 | Reviewer boleh plaintext atau tidak? Masih menunggu dosen | **Strict owner-only**: reviewer metadata saja, tanpa preview/download/profil |
| D-03 | Kapasitas video | Awal: MP4 maksimum 30 MiB; ukur kebutuhan memori, codec dan waktu pada lingkungan tim |
| D-09 | Retention | Awal: pembersihan manual data sintetis setelah penilaian; jadwal akhir ditetapkan tim dan diuji |

D-01 harus dikonfirmasi sebelum finalisasi laporan dan klaim memenuhi interpretasi assignment. Simpan keputusan dosen dalam decision log. Jika diminta tiga representasi independen, revisi suite/envelope, storage, integrity protection, benchmark dan dokumentasi; jangan mengganti interpretasi diam-diam. Tidak perlu membuat dua arsitektur produksi sekaligus.

D-02 tidak membuka endpoint delegasi saat ini. Delegasi hanya ditambahkan setelah ada persetujuan dan kontrak baru, dengan scope per kasus serta audit. Implementasi auth, kasus, ownership, validasi, dan kontrak API dapat berjalan sambil kedua keputusan tersebut diklarifikasi.

Payload empat kategori, termasuk nama file/profil yang privat, berada dalam cakupan proteksi. Password memakai hash Argon2id; session menyimpan hash token. Identifier, role, status dan metadata operasional minimum mempunyai tujuan otorisasi/indexing dan tidak semuanya berupa ciphertext. Jelaskan batas ini dalam laporan; minta klarifikasi bila dosen memaknai “everything stored” mencakup seluruh metadata operasional.

## 3. Kondisi repo dan pemanfaatan kode lama

| Area | Sudah ada pada vault lama | Pekerjaan BankKYC |
| --- | --- | --- |
| Auth | Register/login/logout, password hash, session/CSRF | Tambah role/display_name, provisioning, revocation dan tes peran |
| Otorisasi | Pemeriksaan `user_id` item | Scope kasus, penugasan, status dan projection respons per role |
| Crypto | AES-CBC, DES-CBC, RC4, HKDF dan HMAC envelope v1 | Suite berlapis sementara, AES-GCM, wrapped per-object keys dan envelope versi baru |
| Data | `vault_items`, `encrypted_versions`, hasil lab lama | Applications, profil/bukti berversi, assignments, events dan lab fixture |
| Upload | Batas global 25.000.000 byte | Batas per kategori, request 34 MiB, validasi konten dan pencegahan plaintext temp |
| Lab | Membaca sumber vault milik user, 10–30 trial | Fixture terisolasi, 30–100 trial, AES-GCM dan pipeline, raw results |
| FE integration | Endpoint `/vault`, `/benchmarks` lama | Kontrak `/api/v1/applications`, `/admin/assignments`, `/lab/runs` di bawah |

File awal yang perlu dibaca: `backend/app/crypto.py`, `db.py`, `main.py`, `schemas.py`, `config.py`, `tests/`, dan `scripts/smoke_live.py`. Kode lama adalah referensi implementasi, bukan spesifikasi baru. Tes lama yang lulus tidak membuktikan BankKYC lulus.

`backend/setup_env.py` saat ini dapat membuat FE dalam mode live dan default database SQLite. Perbaiki script ketika integrasi BankKYC siap; jangan mengaktifkan live otomatis selama endpoint baru belum tersedia.

## 4. Arsitektur dan batas kepercayaan

```mermaid
flowchart LR
  F[Next.js FE / API client] -->|same-origin /api/v1| P[Next.js proxy]
  P --> A[FastAPI: session + CSRF + authorization]
  A --> S[Case / evidence / review services]
  S --> C[Crypto service + key wrapping]
  S --> DB[(MySQL: operational records + encrypted objects)]
  C --> K[KEK from protected server configuration]
  A --> L[Evaluator-only fixture lab]
  L --> R[(Measured runs + samples)]
```

Gunakan modular monolith: pemisahan router/service/repository/crypto cukup untuk ukuran tugas dan memudahkan tes konsistensi transaksi. Tidak memerlukan microservices, Redis, Celery, MinIO atau cloud KMS untuk MVP lokal. Secret manager/KMS dapat menggantikan konfigurasi KEK untuk deployment lebih lanjut.

FE tidak dipercaya untuk role, owner, assigned reviewer, status tujuan, ukuran, MIME, hasil validasi, hash, key, ataupun keberhasilan crypto. ID acak membantu referensi, tetapi bukan kontrol akses.

Gunakan session DB yang pendek per request. Operasi crypto/DB yang blocking jangan dijalankan langsung pada event loop async; gunakan endpoint sync atau executor yang terkontrol. Batasi concurrency upload, retrieval dan lab setelah mengukur kebutuhan memori. Pemisahan layanan tetap berada dalam satu proses/deployment MVP.

## 5. Model akses: RBAC + ownership + assignment + state

| Operasi | Pemohon pemilik | Pemohon lain | Assigned reviewer | Admin | Evaluator |
| --- | --- | --- | --- | --- | --- |
| Membuat draf | Ya, untuk dirinya | Ya, untuk dirinya | Tidak | Tidak | Tidak |
| Membaca metadata kasus | Miliknya | Tidak | Kasus ditugaskan, selain DRAFT/WITHDRAWN | Melalui daftar penugasan | Tidak |
| Edit profil/upload | DRAFT / NEEDS_REVISION | Tidak | Tidak | Tidak | Tidak |
| Submit/resubmit/withdraw | Sesuai transisi | Tidak | Tidak | Tidak | Tidak |
| Reveal/download profil/bukti | Miliknya, termasuk versi lama dan terminal | Tidak | Tidak | Tidak | Tidak |
| Mulai tinjauan/keputusan | Tidak | Tidak | Sesuai transisi dan penugasan aktif | Tidak | Tidak |
| Menugaskan reviewer | Tidak | Tidak | Tidak | SUBMITTED / RESUBMITTED | Tidak |
| Menjalankan/mengambil hasil lab | Tidak | Tidak | Tidak | Tidak | Hasil miliknya sendiri |

Implementasikan dependency/policy terpusat seperti `require_session`, `require_role`, `require_owner`, `require_assigned_reviewer`, dan `require_editable_case`. Otorisasi objek harus diterapkan pada query atau sebelum membaca ciphertext/dekripsi. Download harus mengecek bahwa evidence benar-benar merupakan anak dari application pada URL.

Pemeriksaan akses mencakup endpoint GET, mutation, export, versi lama, dan histori. Akun nonaktif/session kedaluwarsa → 401. Role tidak boleh mengakses fungsi umum → 403. Kasus/berkas di luar scope → 404 umum. Detail ID/owner tidak bocor melalui pesan error. Prinsip ini mengikuti [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

Reviewer/admin menerima response model eksplisit, bukan object ORM yang kemudian disembunyikan CSS. Hilangkan profil, nama file asli, hash plaintext, ciphertext, envelope, key, token, dan identitas pemohon dari projection metadata mereka. Jangan menyediakan `include_sensitive=true` atau mode debug yang melewati kebijakan.

Catatan operasional boleh dibuka untuk pemohon pemilik dan reviewer yang ditugaskan. Admin tidak memerlukan isi note untuk menugaskan reviewer: hilangkan `revision_note` dan `events[].note` dari projection admin; pertahankan event code/role/time seperlunya. Field note bersifat optional pada kontrak FE, sehingga pembatasan ini tidak memerlukan halaman baru.

Admin aplikasi bukan batas terhadap administrator OS/database yang menguasai server dan KEK. Threat model mengurangi akses melalui aplikasi dan kebocoran storage; ini bukan zero-knowledge atau end-to-end encryption.

## 6. State machine dan concurrency

| Status awal | Tindakan API | Pelaku | Status hasil / syarat |
| --- | --- | --- | --- |
| DRAFT | `submit` | Pemilik | SUBMITTED; empat kategori lengkap dan acknowledgement true |
| DRAFT | `withdraw` | Pemilik | WITHDRAWN |
| SUBMITTED / RESUBMITTED | `start-review` | Reviewer aktif yang ditugaskan | UNDER_REVIEW |
| UNDER_REVIEW | `request-revision` | Reviewer ditugaskan | NEEDS_REVISION; note 10–500 karakter |
| UNDER_REVIEW | `accept` | Reviewer ditugaskan | ACCEPTED_DEMO |
| UNDER_REVIEW | `reject` | Reviewer ditugaskan | REJECTED_DEMO; note 10–500 karakter |
| NEEDS_REVISION | `resubmit` | Pemilik | RESUBMITTED; empat kategori lengkap dan acknowledgement true |
| NEEDS_REVISION | `withdraw` | Pemilik | WITHDRAWN |

Selain tabel ini ditolak. SUBMITTED/RESUBMITTED/UNDER_REVIEW dan status terminal terkunci bagi edit pemohon. Withdrawal hanya tersedia pada DRAFT/NEEDS_REVISION. Status terminal tidak dapat dibuka ulang; penghapusan/retention proses terpisah. Reviewer menilai kelengkapan metadata, bukan keaslian konten identitas.

Penugasan reviewer boleh dibuat/diubah hanya pada SUBMITTED/RESUBMITTED; target harus akun reviewer aktif. Penugasan awal bersifat manual oleh admin, tidak otomatis memilih reviewer. `start-review` memerlukan penugasan. Ganti penugasan tidak memberi akses ke profil/unduhan.

`applications.version` adalah counter optimistic concurrency. Semua save profile, upload, assignment dan action menerima expected `version`. Mutasi berhasil menaikkan counter tepat satu dan mengubah updated_at. Versi kategori bukti/profil adalah counter terpisah, tidak sama dengan versi kasus.

Dalam transaksi, lock baris aplikasi (`SELECT ... FOR UPDATE`) lalu periksa ulang owner/assignment, expected version dan status. Alternatif compare-and-swap harus menjamin atomicity setara. Jangan hanya membaca versi sebelum crypto lalu menulis tanpa cek kedua. Dua mutation dengan versi sama hanya boleh menghasilkan satu keberhasilan; lainnya 409. Penugasan yang berubah tidak boleh lolos melalui hasil authorization lama.

Untuk upload, validasi/enkripsi bisa dilakukan sebelum transaksi pendek; alokasikan object ID dan material crypto saat persiapan, kemudian lock kasus dan revalidasi sebelum insert. Jika versi/status berubah, buang hasil persiapan tanpa menulis object. Hindari transaksi DB terkunci sepanjang membaca video dan menjalankan cipher.

SQLAlchemy ORM version counter membantu optimistic locking tetapi tidak otomatis melindungi semua bulk update. Gunakan pemeriksaan eksplisit untuk operasi Core/bulk dan uji dua koneksi MySQL. Lihat [SQLAlchemy versioning](https://docs.sqlalchemy.org/en/20/orm/versioning.html).

## 7. Skema MySQL target

Gunakan migrasi Alembic yang dapat membuat database aplikasi kosong dan upgrade skema versi BankKYC. InnoDB, foreign keys aktif, UTC, dan collation username case-sensitive yang diuji. `username` hanya 3–24 ASCII alfanumerik/underscore; display_name akun adalah label operasional/pseudonim, bukan nama lengkap KYC.

| Tabel | Kolom pokok dan constraint |
| --- | --- |
| `users` | id UUID PK, username UNIQUE, password_hash, display_name, role CHECK/validated enum, is_active, created_at; registrasi selalu applicant |
| `sessions` | token_hash PK, user_id FK, created_at, expires_at, revoked_at; tidak menyimpan raw token |
| `applications` | id PK, reference UNIQUE, owner_id FK, status, version NOT NULL, synthetic_acknowledged, created_at, updated_at; kelengkapan diturunkan dari object valid |
| `reviewer_assignments` | application_id PK/FK sebagai penugasan aktif, reviewer_id FK, assigned_by FK, assigned_at; histori perubahan melalui events |
| `personal_data_versions` | id PK, application_id FK, version, encrypted_object_id UNIQUE FK, created_at; UNIQUE(application_id,version) |
| `evidence_versions` | id PK, application_id FK, category, version, encrypted_object_id UNIQUE FK, original_bytes, validated_mime, validation, created_at; UNIQUE(application_id,category,version) |
| `encrypted_objects` | id PK, application_id/owner FK yang terikat, payload_kind, category nullable, payload_version, envelope_version, suite_id, key_version, ciphertext LONGBLOB, crypto_header, wrapped_key_bundle, wrap_nonce/tag, created_at; UNIQUE(key_version,wrap_nonce) untuk namespace KEK wrapping |
| `case_events` | id PK, application_id FK, actor_id/role, action_code, at; projection menghasilkan action label; note privat di encrypted object bila ada |
| `lab_runs` | id PK, evaluator_id FK, kind, fixture_id/hash, input_bytes, repetitions, warmups, methodology_version, status, simulated=false, environment JSON, summaries JSON, created_at |
| `lab_samples` | run_id FK, trial, algorithm, execution_order, encrypt_ns, decrypt_ns, correctness_ns, payload/storage bytes, round_trip_ok; UNIQUE(run_id,trial,algorithm) |
| `rate_limits` | bucket/window/count atau implementasi terpusat setara; jangan menyimpan identitas/password mentah dalam bucket |

Tambahkan indeks owner+updated_at, status+updated_at, reviewer assignment, application+category+version, evaluator+created_at, session user+expiry. Application ID dari URL dan parent foreign key harus cocok. Tetapkan aturan delete eksplisit; jangan memakai cascade yang tanpa sengaja menghapus histori ketika akun dinonaktifkan.

Nama file asli, seluruh nilai profil, catatan bebas reviewer, checksum plaintext dan metadata privat disimpan di dalam payload terenkripsi. `case_events.action_code` dan relasi actor adalah metadata operasional yang dibatasi akses. Ringkasan note pada response dibuka oleh service hanya setelah scope pemeriksaan lolos; tidak menjadi kolom note plaintext.

Catatan revisi juga merupakan user-authored data: gunakan encrypted object dengan suite yang sama, kind `review_note`, terkait event. Tidak ditampilkan sebagai kategori bukti kelima. Hindari menyimpan salinan plaintext `revision_note` di tabel applications; response field tersebut diproyeksikan dari catatan terakhir yang relevan.

`original_bytes`, validated MIME, kategori, status, waktu, dan completeness adalah metadata operasional minimum yang diperlukan reviewer. `personal_data_complete`/daftar versi terkini harus konsisten dengan object committed. Jangan menyimpan nama lengkap/email/NIK sebagai kolom pencarian operasional.

Keputusan LONGBLOB memberi satu transaksi untuk ciphertext + pointer versi + event sehingga tidak ada koordinasi DB/disk untuk MVP. Selaraskan MySQL `max_allowed_packet` dengan envelope terbesar dan driver; 64 MiB adalah titik awal konfigurasi, wajib diuji dengan file batas 30 MiB. Ini bukan klaim throughput. Backup database tetap berisi ciphertext dan wrapped keys; backup KEK disimpan terpisah dengan akses terbatas.

## 8. Kontrak API yang harus cocok dengan FE

Prefix **`/api/v1`**, bukan contoh path awal `/api` pada PRD produk. Sumber kontrak aktual: `frontend/src/lib/contracts.ts`, `kyc.ts`, `api.ts`, dan `kyc-api.ts`. Seluruh waktu ISO 8601 UTC, ID opaque string, JSON UTF-8, respons privat `Cache-Control: no-store`.

### 8.1 Auth dan operasional

| Method | Path | Request | Response sukses |
| --- | --- | --- | --- |
| GET | `/health` | Publik, informasi minimum | 200 `{status:"ok"}`; 503 bila DB tidak siap, tanpa secrets |
| GET | `/auth/csrf` | Boleh sebelum login | 200 `{token}` + cookie/state CSRF |
| POST | `/auth/register` | `{username,password}` | 201 User dengan role applicant; FE lanjut ke login, tidak auto-login |
| POST | `/auth/login` | `{username,password}` | 200 User + cookie session baru |
| GET | `/auth/me` | Session | 200 User |
| POST | `/auth/logout` | Session/CSRF | 204, cabut session dan hapus cookie |

User wajib berbentuk:

```json
{"id":"opaque-user-id","username":"pemohon_dummy","display_name":"pemohon_dummy","role":"applicant"}
```

`role` hanya applicant/reviewer/admin/evaluator. Jangan mengembalikan password_hash atau session token di JSON. FE menolak response auth legacy yang tidak mempunyai role/display_name.

### 8.2 Pengajuan, profil, dan bukti

| Method | Path | Input / akses | Response sukses |
| --- | --- | --- | --- |
| GET | `/applications` | Applicant owner scope / reviewer assignment scope | 200 `{items:Application[],total}` |
| POST | `/applications` | Applicant, body `{}` | 201 Application DRAFT, version 1 |
| GET | `/applications/{id}` | Owner / assigned reviewer | 200 Application sesuai projection role |
| GET | `/applications/{id}/personal-data` | Owner saja | 200 `{profile:ApplicantProfile|null}` |
| PUT | `/applications/{id}/personal-data` | Owner editable, `{profile,version}` | 200 Application versi baru |
| POST | `/applications/{id}/evidence` | Owner editable; multipart `file,category,version` | 201 Application versi baru |
| POST | `/applications/{id}/actions` | Action actor sesuai bagian 6 | 200 Application versi baru |
| GET | `/applications/{id}/evidence/{evidenceId}/download` | Owner, termasuk versi lama | 200 attachment byte asli, bukan JSON |
| GET | `/applications/{id}/personal-data/download` | Owner | 200 attachment JSON canonical, content type octet-stream untuk FE saat ini |

Application wajib mempunyai:

```text
id, reference, status, version, created_at, updated_at,
personal_data_complete, evidence[], events[], synthetic_acknowledged,
assigned_reviewer_id?, revision_note?
```

`reference` diawali `VTX-` dan unik tanpa identitas pribadi. Case ID/reference dibuat ketika draf dibuat, bukan saat submit. `evidence[]` memuat seluruh versi, bukan hanya latest. Evidence `{id,category,version,original_bytes,mime_type,created_at,validation,display_name?}`; category identity/document/video. `display_name` hanya untuk pemilik dan baru dibuka setelah authorization. `validation:"format_checked"` berarti format awal telah dicek, bukan verifikasi keaslian identitas.

Event `{id,at,action,actor_role,note?}`; urut ascending di API karena FE membalik untuk tampilan terbaru. Tidak mengirim actor applicant full name, nama berkas, ciphertext, atau kunci. `revision_note` terakhir boleh tetap tampil setelah resubmit sebagai konteks historis, tetapi UI tidak boleh mengartikannya sebagai status NEEDS_REVISION jika status sudah berubah.

Profil wajib berisi delapan string:

```json
{
  "full_name":"Nara Contoh",
  "identity_number":"DUMMY-2026-001",
  "date_of_birth":"2000-01-15",
  "email":"nara@example.com",
  "phone":"080000000001",
  "address":"Jalan Simulasi 12, Kota Contoh",
  "occupation":"Pekerjaan fiktif",
  "account_purpose":"Tabungan pribadi (simulasi)"
}
```

Request action:

```json
{"action":"submit","version":5,"synthetic_acknowledged":true}
```

```json
{"action":"request-revision","version":6,"note":"Lengkapi halaman tujuan rekening pada dokumen dummy."}
```

### 8.3 Admin dan lab

| Method | Path | Input / akses | Response sukses |
| --- | --- | --- | --- |
| GET | `/admin/assignments` | Admin | 200 `{items:Application[],reviewers:[{id,display_name}]}` |
| PUT | `/admin/assignments/{id}` | Admin, `{reviewer_id,version}` | 200 projection Application tanpa plaintext |
| GET | `/lab/runs` | Evaluator | 200 `LabRun[]` milik evaluator |
| POST | `/lab/runs` | Evaluator, `{kind,fixture,repetitions,warmups:2}` | 201 completed LabRun pada mode sinkron MVP |
| GET | `/lab/runs/{id}/export` | Evaluator pemilik hasil | 200 CSV berisi metadata dan raw measurements |

Daftar admin hanya pengajuan yang telah dikirim; DRAFT/WITHDRAWN tidak muncul pada baseline FE. Reviewer list hanya reviewer aktif. Admin tetap tidak menggunakan endpoint personal-data/download.

LabRun minimal `{id,kind,fixture,repetitions,warmups,status:"completed",simulated:false,created_at,rows[]}`. Kind benchmark/verification; fixture personal-json/identity-png/document-pdf/video-mp4. Tiap row `{algorithm,encrypt_ms,decrypt_ms,iqr_ms,overhead_bytes,round_trip_ok}`. Enkripsi/dekripsi ms adalah **median**, `iqr_ms` adalah IQR enkripsi. Nama algorithm harus `AES-256-GCM`, `DES-CBC`, `RC4`, `Pipeline berlapis` agar label FE saat ini sesuai.

Field tambahan nonbreaking untuk raw samples, throughput, environment dan methodology dijelaskan pada bagian 13. Jangan mengembalikan 202/queued ke FE saat ini: client hanya memahami completed. Job async memerlukan perubahan kontrak FE terlebih dahulu.

### 8.4 Error dan perilaku HTTP

```json
{"error":{"code":"VERSION_CONFLICT","message":"Pengajuan berubah. Muat ulang sebelum melanjutkan.","field_errors":{},"request_id":"opaque-request-id"}}
```

| HTTP | Code contoh | Makna |
| --- | --- | --- |
| 400 | INVALID_REQUEST | Body/multipart tidak dapat diparse |
| 401 | INVALID_CREDENTIALS / SESSION_EXPIRED | Login gagal atau session tidak valid |
| 403 | ROLE_FORBIDDEN / CSRF_INVALID | Fungsi salah role atau token CSRF tidak sesuai |
| 404 | RESOURCE_NOT_FOUND | Resource hilang atau di luar scope; pesan sama |
| 409 | VERSION_CONFLICT / CASE_READ_ONLY / INVALID_TRANSITION / ASSIGNMENT_LOCKED | Konflik tanpa mutasi sebagian |
| 413 | PAYLOAD_TOO_LARGE | Batas byte terlampaui |
| 415 | UNSUPPORTED_MEDIA_TYPE | Request/content encoding atau media tidak didukung |
| 422 | VALIDATION_ERROR / INVALID_UPLOAD / SIGNATURE_MISMATCH / CASE_INCOMPLETE / NOTE_REQUIRED | Input tidak memenuhi aturan |
| 429 | RATE_LIMITED / LAB_BUSY | Batas operasi; sertakan Retry-After bila diketahui |
| 500 | INTEGRITY_CHECK_FAILED / INTERNAL_ERROR | Object rusak/internal error, tanpa plaintext/stack trace |
| 503 | STORAGE_UNAVAILABLE / KEY_UNAVAILABLE | DB/KEK tidak siap; tidak menulis object ready |

Integrity failure setelah owner check memakai respons umum yang sama bagi seluruh kegagalan envelope/unwrap/tag/padding/hash agar tidak membedakan tahap crypto melalui pesan. FE boleh menerima pesan aman bahwa berkas belum dapat dipulihkan. `field_errors` adalah mapping nama field ke array string, bukan detail Pydantic mentah. Intercept error FastAPI standar supaya semua endpoint konsisten.

Daftar P0 kompatibel FE mengembalikan kumpulan demo terbatas tanpa pagination tersembunyi. Batasi jumlah kasus/bukti per akun untuk MVP dan tangani kapasitas penuh dengan error jelas. Pagination/search server adalah pengembangan terkoordinasi, bukan memotong `items` diam-diam ketika FE mengira sudah mendapat semua kasus.

## 9. Catatan integrasi FE yang wajib disepakati

| Masalah | Keputusan handoff |
| --- | --- |
| Respons download profil | `api.call` saat ini memparse `application/json` menjadi object. Kembalikan **application/octet-stream + Content-Disposition attachment** untuk endpoint download profil, walaupun isinya JSON. Endpoint GET personal-data biasa tetap JSON. Alternatif perbaikan FE: transport Blob eksplisit, disepakati bersama |
| Rotasi CSRF sesudah login | Target auth merotasi session dan CSRF pada login. FE saat ini masih menyimpan token pre-login. **Pekerjaan integrasi FE P0:** panggil `clearApiSession()` setelah login berhasil, sehingga mutation berikutnya mengambil token baru. Bila registration merotasi CSRF, lakukan reset setelah register juga. Jangan mematikan CSRF untuk menutupi mismatch |
| Lab sementara | FE mock selalu menghasilkan angka statis. BE tidak boleh menyalin angka itu atau mengirim `simulated:false` untuk hasil buatan |
| Status job lab | P0 adalah request sinkron bounded. API queued/running membutuhkan polling/UI baru; tidak plug-and-play |
| Input profil | BE wajib mengulang validasi. Beberapa batas FE saat ini 500 karakter untuk semua string; field limit BE lebih spesifik harus disinkronkan ke FE bila dipilih |
| Case metadata vs plaintext | Isi profil diminta explicit oleh pemilik. Daftar/detail reviewer/admin tidak boleh berisi field sensitif yang hanya disembunyikan FE |
| Session expiry | FE menghapus query cache dan kembali login pada 401 request privat. Gunakan 403/404 untuk role/scope agar tidak memaksa logout akun yang sebenarnya masih valid |
| Canonical profil | JSON form adalah object, bukan berkas mentah unggahan. Tetapkan canonical bytes saat write dan kembalikan bytes tersebut saat download; jangan menyatakan raw whitespace/key order dari request dipertahankan |

Tabel ini mencatat pekerjaan koordinasi, **bukan** perubahan kode FE yang sudah dilakukan oleh penyusunan PRD ini. Teman BE harus memberitahu pengembang FE ketika implementasi token rotation/validation/job mode siap diuji.

## 10. Validasi, batas payload dan pencegahan plaintext temp

### 10.1 Profil dan catatan

Semua delapan field wajib nonempty, strip whitespace tepi sebelum canonicalization; maksimal 500 karakter per field agar cocok dengan baseline FE. Email harus domain example.com/example.org/example.net; identity_number `^DUMMY-[A-Z0-9-]{3,40}$` case-insensitive; phone `^0800\d{6,10}$`; tanggal benar-benar valid dan di masa lalu. Jangan memakai panjang 16 digit atau menghubungi validasi NIK nyata.

Pydantic menolak extra fields. Server tidak menerima role, owner_id, assigned_reviewer_id atau crypto material dari payload profil. Note revisi/tolak: 10–500 karakter, trim, plain text, tanpa HTML rendering. Reviewer diberi instruksi tidak menulis PII; guard panjang/regex tidak boleh diklaim menghapus seluruh PII. Catatan tetap terenkripsi saat disimpan.

### 10.2 Berkas

| Kategori | Format yang diterima | Maksimum file | Pemeriksaan minimum |
| --- | --- | --- | --- |
| identity | PNG/JPG/JPEG/PDF | 5 × 1024² byte | Extension + signature + parse struktur yang relevan |
| document | PDF/DOCX | 10 × 1024² byte | PDF terparse; DOCX adalah OOXML valid, bukan ZIP sembarang |
| video | MP4 | 30 × 1024² byte | Kontainer valid dan metadata terparse; dataset target 10–30 detik, codec preview diuji |

Ukuran nol ditolak. MIME dari browser tidak dipercaya; MIME response berasal dari hasil validasi. Jangan hanya memakai extension atau empat byte magic. PDF rusak/password-protected ditolak untuk dataset demo. DOCX harus memuat struktur OOXML yang diperlukan; jangan mengekstrak arsip ke disk, tolak path traversal/arsip terenkripsi/macro-enabled format, batasi jumlah entry dan ukuran setelah dekompresi sebelum membaca XML. XML external entities/network access tidak boleh aktif. PNG/JPEG dicek decoding/dimensi dengan batas resource, bukan hanya header. MP4 dapat diperiksa dengan ffprobe subprocess arg-list tanpa shell, timeout dan output terbatas; tidak menjalankan nama file sebagai command.

Pilih library parser yang dipin dan uji fixture valid/invalid. Batas ZIP/dimensi/timeout parser harus dinyatakan di konfigurasi dan diuji, bukan diasumsikan aman karena file di bawah 10 MiB. Antivirus/sandbox menyeluruh bukan fitur MVP yang sudah dijanjikan; catat keterbatasan tersebut. Semua dataset tetap sintetis.

### 10.3 Request dan temp files

Total request multipart dibatasi **34 MiB**, termasuk overhead; form metadata dibatasi kecil dan hanya satu file per request. Terapkan batas ketika membaca ASGI stream, bukan hanya Content-Length yang dapat dipalsukan. Batasi jumlah part dan header; tolak Content-Encoding terkompresi bila tidak didukung, agar batas tidak dapat dilewati melalui dekompresi.

`UploadFile` FastAPI memakai spooled file yang dapat berpindah ke disk. Membaca `await file.read()` di route tidak membuktikan plaintext sebelumnya belum ditulis ke temp. Gunakan parser bounded yang tetap di RAM untuk limit MVP, atau konfigurasi spooling yang diverifikasi pada versi Starlette terpasang dengan request cap yang lebih ketat. Jangan bergantung pada private attribute library tanpa tes. Lihat [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/).

Original filename bukan filesystem path. Tidak ada payload plaintext di `public/`, temp upload, direktori project, task queue, log, crash dump yang sengaja dibuat aplikasi, atau backup output dekripsi. RAM plaintext selama proses diperlukan; jangan mengklaim secure wiping semua salinan Python. Jika tidak dapat menjamin jalur in-memory, fitur belum memenuhi gate plaintext-at-rest dan harus diperbaiki sebelum demo.

## 11. Enkripsi, envelope dan key handling

**Seluruh rancangan bagian ini adalah baseline sementara D-01 untuk dataset sintetis.** DES/RC4 hanya tahap akademik. Layering tidak boleh dijelaskan sebagai lebih aman daripada AES-GCM saja.

### 11.1 Suite sementara

| Komponen | Parameter yang harus dicatat dan diuji |
| --- | --- |
| RC4 / ARC4 | Key independen 32 byte, `drop=3072`, parameter sama pada encrypt/decrypt; stream cipher, tanpa CBC/ECB |
| DES | Key independen 8 byte, effective key 56 bit, CBC, IV acak 8 byte, PKCS#7 block size 8; ECB dilarang |
| AES | Key independen 32 byte, GCM, nonce 12 byte unik untuk key tersebut, tag 16 byte, AAD; ECB dilarang |
| RNG | `secrets`/CSPRNG library; tidak memakai random biasa, timestamp, username atau password sebagai key |

Parameter mengacu pada [AES](https://www.pycryptodome.org/src/cipher/aes), [GCM](https://www.pycryptodome.org/src/cipher/modern#gcm-mode), [DES](https://www.pycryptodome.org/src/cipher/des), dan [ARC4](https://www.pycryptodome.org/src/cipher/arc4) di dokumentasi PyCryptodome. ARC4 drop mengurangi bias awal yang dikenal, tidak membuat RC4 layak untuk data sensitif nyata.

Gunakan suite ID versioned, misalnya `vtx-kyc-layered-v1`. Jangan mendekripsi envelope baru dengan class `veltrix-v1` lama berdasarkan tebakan. Salah suite, versi tak dikenal, ukuran header tidak wajar atau parameter di luar allowlist ditolak.

### 11.2 Payload packing dan pipeline

Tetapkan satu format biner dengan parser bounded: panjang metadata (uint32 big-endian) + canonical metadata JSON UTF-8 + raw payload bytes. Metadata mencakup kind, nama file asli yang aman, verified MIME, original length dan SHA-256 sumber. Batas metadata ditetapkan kecil, misalnya 16 KiB. Profil memakai canonical JSON sebagai raw payload; file memakai byte upload asli. Metadata note juga dipack sebagai payload privat.

```text
packed private metadata + original payload bytes
  → RC4(K_rc4, drop=3072)
  → PKCS#7 padding dan DES-CBC(K_des, IV_des)
  → AES-256-GCM(K_aes, nonce, AAD)
  → simpan final ciphertext + authenticated crypto header + wrapped key bundle
```

Hanya ciphertext final dipersist sebagai object resmi. Tidak ada file asli, intermediate RC4-only/DES-only, atau JSON metadata privat terpisah yang plaintext. Pada replacement profil/file, buat versi baru beserta object ID, keys, nonce dan IV baru; jangan mengenkripsi ulang dengan material lama atau memperbarui ciphertext in-place.

AAD harus mempunyai canonical serialization yang sama saat encrypt/decrypt. Bind minimal envelope_version, suite_id, application_id, owner_id, object_id, kind/category, payload_version, DES IV dan RC4 drop. Nilai relasi penting diperoleh dari konteks server/DB dan dibandingkan dengan envelope, bukan dipercaya dari request. Tujuannya agar ciphertext atau wrapped keys yang dipindahkan ke baris/owner/versi lain gagal diverifikasi.

### 11.3 Key bundle dan KEK

Generate tiga data-encryption keys secara independen untuk setiap encrypted object. Bungkus bundle ketiganya menggunakan KEK 32 byte di luar database, misalnya AES-GCM dengan nonce wrapping baru, tag dan AAD terpisah yang memuat purpose `key-wrap` + object identity + key_version. Nonce wrapping tidak boleh digunakan ulang di bawah KEK yang sama; jaminan uniqueness harus dirancang/dites, misalnya register nonce dengan unique constraint per KEK version serta retry saat collision.

Raw bundle tidak disimpan di DB, source, response, log atau fixture. Hanya wrapped bundle dan parameter nonrahasia yang dipersist. Master/KEK berasal dari konfigurasi server terlindungi/secret store, bukan nilai contoh di repo. Auth signing/CSRF memakai secret terpisah atau derivasi domain-separated yang terdokumentasi; jangan memakai data-encryption key sebagai session token.

Setiap object menyimpan `key_version`. Saat KEK tidak ada/salah, fail closed tanpa membuat key pengganti otomatis. Cadangkan KEK terpisah dari database dan uji restore. Kehilangan key berarti object tidak dapat dipulihkan. Jangan menghapus KEK versi lama sampai semua object telah direwrap/retention selesai. Rotasi otomatis bukan syarat P0, tetapi format key_version dan prosedur pemulihan wajib.

## 12. Write/retrieval yang atomic dan intact

### 12.1 Write

1. Verifikasi session/CSRF, role, scope dan status awal.
2. Baca request dengan cap; validasi field dan konten file dalam batas resource.
3. Tentukan original bytes/canonical profile bytes, metadata privat dan checksum referensi.
4. Siapkan encrypted object dengan kunci/parameter baru; lakukan internal round-trip sesuai kebijakan pengujian, bukan menganggap enkripsi sukses karena fungsi tidak error.
5. Mulai transaksi; lock kasus; cek ulang version/status/assignment/ownership yang relevan.
6. Insert encrypted object, row versi, increment case.version, updated_at dan event dalam satu commit.
7. Jika gagal, rollback seluruh transaksi; tidak ada versi setengah jadi, ciphertext orphan atau completeness true tanpa object valid.
8. Respons memuat metadata terbaru. Tidak ada field `encrypted:true` yang diisi tanpa proses dan persistence yang berhasil.

### 12.2 Retrieval

1. Session valid → owner check → parent application/evidence membership check, termasuk versi lama.
2. Load envelope dan wrapped keys; validasi format/batas header.
3. Unwrap bundle dengan verifikasi tag dan AAD key-wrap.
4. AES-GCM `decrypt_and_verify`; jangan mengirim output decrypt sebelum verifikasi tag.
5. DES-CBC decrypt/unpad, lalu RC4 recovery dengan drop yang tercatat.
6. Parse packed metadata dengan batas ketat; periksa length, kind/versi yang terikat, dan checksum terhadap raw bytes yang dipulihkan.
7. Hanya setelah seluruh pemeriksaan berhasil, kirim **raw original file bytes**, bukan wrapper metadata, sebagai attachment dengan nama aman. Catat retrieval event operasional tanpa plaintext.

Untuk profil, GET personal-data mengembalikan object JSON dari canonical bytes; download mengembalikan bytes canonical yang disimpan pada versi terbaru. Definisikan canonicalization sebagai sorted keys, separators tanpa spasi dan UTF-8 `ensure_ascii=False`, setelah validasi/normalisasi write. Uji hash canonical bytes sebelum encrypt dan setelah decrypt; jangan membandingkan dengan raw body JSON browser yang belum dinormalisasi.

File tidak dinormalisasi, dikompres, diberi watermark ulang, ditranskode atau disimpan kembali oleh parser. Pengambilan harus byte-identical, bukan sekadar dapat dibuka. Parser melakukan pemeriksaan, tidak mengubah source bytes.

MVP memverifikasi seluruh object di RAM sebelum response. Tidak ada plaintext partial streaming, range video atau chunk decryption yang dapat melewati final authentication. Jika browser memerlukan range, tambahkan setelah desain authenticated retrieval/range tervalidasi dan FE sepakat; baseline dapat mengirim attachment penuh 200.

Attachment memakai Content-Disposition yang menghindari CR/LF/path injection, MIME terverifikasi, no-store dan `X-Content-Type-Options: nosniff`. Tidak ada cache CDN untuk respons privat. Integrity error tidak mengirim berkas kosong/parsial sebagai HTTP 200. API tidak mengembalikan AES/DES/RC4 key, sample plaintext atau raw envelope dalam response biasa.

## 13. Benchmark dan verification nyata

### 13.1 Dataset dan scope

Evaluator hanya memilih fixture allowlist di direktori/manifest server, tidak memberikan application_id, path arbitrary atau URL. Fixture berisi data sintetis untuk JSON, PNG, PDF dan MP4; catat SHA-256/ukuran/format aktual. Video 10 detik 8,664 byte yang sekarang dipakai FE berguna untuk smoke test, tetapi tidak mewakili benchmark 10–30 MiB. Siapkan corpus eksperimen terpisah pada beberapa ukuran dan dokumentasikan cara mendapatkannya tanpa data nyata.

Fixture sumber lab boleh berupa plaintext sintetis yang sengaja disediakan untuk repeatability, dengan direktori allowlist dan manifest yang jelas. Itu bukan lokasi persistence unggahan pemohon. Inspeksi plaintext-at-rest membedakan fixture sumber yang disengaja dari database/storage/temp/log operasional; jangan menyamarkan salinan upload sebagai fixture untuk melewati gate tersebut.

AES-256-GCM, DES-CBC, RC4 dan pipeline berlapis mendapat **input byte identik** untuk perbandingan cipher. Gunakan 2 warm-up dan default 30 trial terukur, rentang request 30–100. Acak urutan empat kandidat setiap trial dan simpan urutannya. Kunci/IV/nonce disiapkan dengan aturan yang benar, tidak reuse cipher object/state untuk trial berikutnya.

Tiga cipher independen hanya lab. Plaintext/intermediate/ciphertext legacy-only hasil lab tidak dimasukkan sebagai bukti KYC operasional. Jangan menyebut DES/RC4 standalone menyediakan ciphertext authentication; wrong-key/tamper pada DES/RC4 mungkin tidak menghasilkan exception. Laporkan kegagalan correctness melalui perbandingan byte/hash secara terpisah dari autentikasi GCM.

### 13.2 Definisi timer

| Metrik | Definisi |
| --- | --- |
| `encrypt_ns` AES | Pembuatan cipher, AAD dan encrypt+tag; mencakup biaya GCM authentication |
| `decrypt_ns` AES | Pembuatan cipher, AAD dan decrypt+verify |
| DES | Pembuatan cipher + pad/encrypt atau decrypt/unpad |
| RC4 | Pembuatan cipher + drop3072 + transform; setup tidak disembunyikan |
| Pipeline cipher | Ketiga tahap pada payload sumber identik, termasuk DES padding dan outer GCM authentication |
| Storage end-to-end | Ukuran/waktu operasi aplikasi packed metadata + key generation/wrapping + crypto + transaksi DB; diukur terpisah dari tabel cipher |
| Correctness | Pembandingan original/recovered bytes dan SHA-256, di luar timer cipher; simpan durasi bila diperlukan |
| Throughput | input_bytes / (median_ns / 1e9) / 1024², dilabeli MiB/s; duration nol di-handle sebagai resolusi timer tidak cukup, bukan infinity |
| Overhead | Untuk tabel cipher: encoded cipher payload + IV/nonce/tag/header wajib dikurangi input_bytes. Laporkan ciphertext-only dan envelope bytes terpisah; storage operational juga menghitung wrapped keys/private packing |

Random generation/key wrapping/HTTP/I/O bukan bagian timer cipher murni; biaya tersebut dicatat terpisah. Jangan mengurangkan biaya authentication AES supaya seolah setara algoritma tanpa authentication. Sertakan scope timer pada semua hasil. Pakai monotonic high-resolution `perf_counter_ns`, bukan jam kalender.

Hitung median, IQR dan sample SD. Definisikan IQR secara deterministik, misalnya kuartil metode inclusive dengan Q3−Q1; simpan method dalam metadata. Raw samples disimpan agar ringkasan dapat dihitung ulang. Untuk verification kind, jalankan round-trip nyata dengan fixture yang sama; jangan hard-code success. Ketidakcocokan menghasilkan `round_trip_ok:false` dengan hasil yang ditandai gagal, bukan successful verification yang direkayasa.

`status:completed` berarti pengukuran selesai, bukan seluruh correctness lulus; keberhasilan pemulihan ditentukan dari hasil tiap sample/row. Gangguan operasional seperti fixture tidak tersedia, kehabisan resource atau DB gagal tidak boleh diubah menjadi angka nol/row sukses; kembalikan error yang sesuai dan simpan metadata run gagal untuk diagnosis yang aman bila diperlukan.

Simpan environment: OS/CPU/RAM bila dapat diperoleh, Python, PyCryptodome, FastAPI/SQLAlchemy, MySQL server, timer resolution, concurrency, fixture hash, suite parameters dan methodology_version. Peak RSS/tracemalloc hanya dimasukkan dengan metode yang menjelaskan keterbatasan alokasi native; jika tidak reliable, pakai null dan alasan, bukan nol.

### 13.3 API dan ekspor

MVP mempertahankan request sinkron sesuai FE. Batasi satu run lab aktif pada deployment demo dan kembalikan LAB_BUSY untuk run tambahan; pada multiworker gunakan koordinasi lintas proses, bukan semaphore per worker saja. Atur timeout server/proxy berdasarkan pengukuran; tidak menjanjikan SLA tanpa baseline. Jika video/trial tidak stabil dalam request sinkron, selesaikan kontrak job+polling bersama FE sebelum beralih ke 202.

LabRun boleh menambahkan `input_bytes`, `environment`, `methodology_version`, `samples`/`summary` atau endpoint detail tambahan untuk raw data, tanpa mengubah field minimal FE. CSV wajib membawa fixture/hash, ukuran, satuan, suite/mode/drop, repetitions/warmups, execution order dan raw values; quote/escape CSV dengan benar dan hindari formula injection pada field teks.

`simulated:false` hanya ketika pengukuran selesai dijalankan. Hasil dummy untuk UI tetap `simulated:true` dan dilarang menjadi bukti laporan. Gate tampering/authorization diuji melalui test suite dan evidence CLI; label “belum dijalankan” pada FE tidak otomatis berubah hanya karena backend ada. Penampilan status gate aktual membutuhkan endpoint dan perubahan FE terkoordinasi.

Interpretasi laporan harus menghubungkan median/variasi, throughput video, overhead profil kecil, biaya pipeline dan keterbatasan cipher legacy ke skenario KYC. Angka tercepat tidak menjadi kesimpulan paling aman.

## 14. Auth, CSRF, provisioning dan konfigurasi

Password hanya hash Argon2id dengan salt, tidak dienkripsi reversibel. Gunakan parameter yang diuji pada mesin tim; minimal awal dari [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) adalah memory 19 MiB, iterations 2, parallelism 1, atau konfigurasi yang lebih kuat dan terukur. Pertahankan kebijakan FE minimal 8 karakter untuk kompatibilitas prototipe; batas maksimum dan validasi backend harus didokumentasikan. Jangan log password atau memakainya sebagai key data.

Session opaque CSPRNG minimal 32 byte entropy, raw token hanya dalam cookie; simpan SHA-256 token di DB. Absolute expiry awal 8 jam, revocation saat logout/nonaktif/perubahan role, rotasi ketika login. Cookie HttpOnly, SameSite=Lax atau Strict sesuai deployment, Secure pada HTTPS; HTTP localhost hanya konfigurasi development. Proteksi session dan CSRF adalah kontrol terpisah. Lihat [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

GET csrf harus dapat dipanggil sebelum login/register. Implementasikan synchronizer token atau signed double-submit yang benar, validasi header `X-CSRF-Token` pada seluruh mutation termasuk auth, dan cek Origin/allowed hosts. Jangan menganggap SameSite menggantikan CSRF. Rotasi CSRF pada login disertai reset cache FE di bagian 9; tes alur register→login→create draft dengan token nyata. Panduan: [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

Public registration tidak menerima role atau is_active. Sediakan CLI administrasi untuk membuat akun reviewer/admin/evaluator dan menonaktifkan akun; jangan menyediakan self-promotion endpoint atau default password bersama. Seed test hanya lewat explicit development/test command, menolak berjalan pada environment non-demo. Role perubahan dilakukan operator tepercaya, diaudit dan mencabut session lama. Halaman kelola pengguna tidak diperlukan agar FE existing terhubung.

Contoh konfigurasi yang harus disediakan di `.env.example` baru, dengan nilai rahasia hanya placeholder:

```dotenv
DATABASE_URL=mysql+pymysql://veltrix_app:CHANGE_ME@127.0.0.1:3306/veltrix_kyc?charset=utf8mb4
VELTRIX_KEK_V1_BASE64=GENERATE_LOCALLY_DO_NOT_COMMIT
VELTRIX_AUTH_SECRET_BASE64=GENERATE_SEPARATELY_DO_NOT_COMMIT
COOKIE_SECURE=false
ALLOWED_ORIGINS=http://127.0.0.1:3000
MAX_REQUEST_BYTES=35651584
```

Tidak menghapus `VELTRIX_MASTER_KEY` lama bila database vault perlu dibaca untuk migrasi; KEK/suite baru mempunyai namespace/versi berbeda. Script init hanya membuat secret jika belum ada dan tidak menimpa env pengguna. Jangan auto-switch FE live dari script setup.

Rate limits login per IP+username terhash, upload/retrieval per user, dan lab terpusat. Nilai awal ditentukan dari smoke/resource tests, dikonfigurasi dan diuji sebagai 429. Jangan mempercayai X-Forwarded-For dari klien; trust hanya reverse proxy yang dikonfigurasi. CORS memakai allowlist exact jika diperlukan; same-origin proxy lebih sederhana untuk cookie FE ini.

## 15. Privasi, audit dan retention

| Data | Perlakuan untuk skenario |
| --- | --- |
| Profil, identitas scan, dokumen, video | Private karena dapat mengidentifikasi/mengungkap informasi seseorang jika memakai data nyata; dalam demo semua sintetis dan tetap diuji proteksinya |
| Nama file, catatan bebas, plaintext hash | Metadata privat, terenkripsi dan dibatasi scope |
| ID kasus/objek, kategori, status, ukuran dan waktu | Metadata operasional minimum; tetap bukan endpoint publik |
| Password / session / key | Secrets; hash token/password dan wrapped keys, tanpa exposure lewat JSON/log |
| Fixture lab | Sintetis, terisolasi dari kasus; hasil eksperimen tidak memuat plaintext pemohon |

Dasar analisis tugas: definisi/jenis data dan prinsip keamanan pemrosesan dalam [UU PDP No. 27/2022](https://peraturan.bpk.go.id/Home/Download/224884/UU%20Nomor%2027%20Tahun%202022.pdf), terutama Pasal 1, 4 dan 16; serta pemetaan GDPR pada PRD produk. Video/foto tidak otomatis berarti aplikasi melakukan pemrosesan biometrik untuk identifikasi; fitur tersebut di luar scope. Keputusan menerapkan proteksi untuk seluruh empat payload adalah desain proyek, bukan klaim aplikasi telah patuh seluruh regulasi atau mendapat persetujuan penggunaan data nyata.

Audit business events untuk create/save/upload/submit/review/assign/withdraw dan catat retrieval/denied operation melalui log keamanan minimal. Pisahkan business event yang menaikkan case.version dari read-access log; download tidak mengubah version/status. Jangan menaruh key, token, body, profil, raw filename atau ciphertext dalam log. Catatan bebas tetap dienkripsi.

Withdrawal tidak menghapus payload/audit. Sediakan CLI cleanup terkontrol untuk data demo sesudah masa penilaian: dry-run default menampilkan ID/count saja; apply eksplisit menghapus seluruh versi, wrapped bundles dan relasi sesuai kebijakan. Uji referential integrity, session invalidation bila akun dihapus, dan dampak backup. Penghapusan di DB utama bukan jaminan salinan backup turut hilang; prosedur backup/restore harus memperhitungkan retention. Retention final dan hak subjek data nyata bukan scope yang boleh diklaim selesai oleh prototipe ini.

## 16. Strategi migrasi dan live cutover

Paling aman untuk demo sintetis: buat schema/database BankKYC baru (`veltrix_kyc`), jalankan migrasi, provision akun tepercaya, dan isi fixture sintetis. Jangan otomatis menghapus/mengonversi database vault lama. Dapatkan persetujuan pemilik data sebelum melakukan migrasi atau deletion yang nyata.

Jika data vault lama benar-benar perlu dipindahkan, buat migrator terpisah: baca hanya dengan master key lama, verifikasi HMAC/round-trip, kaitkan ke application/role yang eksplisit, encrypt ulang ke envelope baru dan cocokkan bytes; laporkan count/hash tanpa PII. Ciphertext CBC lama tidak diberi label GCM tanpa dekripsi dan enkripsi ulang. Jangan menganggap ID file lama adalah ID kasus.

Urutan cutover:

1. Jalankan server MySQL test dan migrasi dari kosong; pin dependencies yang telah dites.
2. Jalankan suite unit/integration MySQL dan provisioning CLI di environment demo.
3. Pastikan API `/api/v1/auth/me` mengembalikan User baru, seluruh endpoint pengajuan/role/lab tersedia.
4. Selesaikan koordinasi FE CSRF dan konfirmasi semua data response sesuai kontrak.
5. Jalankan integrasi browser dengan `NEXT_PUBLIC_API_MODE=live`, origin API lokal, lalu rebuild/restart FE. Tidak ada akun demo otomatis di live.
6. Jalankan smoke live dengan cookie/CSRF sungguhan dan inspect storage/temp/log tanpa menampilkan secrets.
7. Simpan bukti hash/tamper/authorization/benchmark untuk laporan. Hentikan cutover jika gate gagal; jangan fallback diam-diam ke mock.

Setiap hasil tes harus mencatat mode live/mock. Tes Playwright mock yang sudah ada tetap berguna untuk UI, tetapi bukan pengganti integration test BE, MySQL, crypto dan session asli.

## 17. Acceptance criteria dan test matrix

| ID | Uji | Kriteria lulus |
| --- | --- | --- |
| BE-T01 | Migrasi MySQL kosong | Seluruh tabel/constraint dibuat; rollback/upgrade migration sesuai prosedur yang didukung |
| BE-T02 | Register/login/logout/expiry | Hash password, session rotation/revocation, User response dan 401 benar |
| BE-T03 | CSRF nyata | Mutation tanpa/salah token dan Origin salah ditolak; register→login→mutation dengan token baru berhasil |
| BE-T04 | Mass assignment | Payload role/owner/status/key/unknown fields ditolak; registrasi tidak bisa membuat admin |
| BE-T05 | Dua applicant | Daftar/GET/reveal/upload/action/download/versi lama milik user lain ditolak, termasuk mismatched parent IDs |
| BE-T06 | Dua reviewer | Hanya assignment aktif dapat ditinjau; reassignment mencabut scope reviewer lama; profil/download tetap ditolak untuk reviewer assigned |
| BE-T07 | Admin/evaluator | Admin tidak dapat plaintext atau keputusan; evaluator hanya fixture dan run miliknya |
| BE-T08 | State machine | Semua transisi legal berhasil; seluruh transisi lain gagal tanpa mutasi/event sebagian |
| BE-T09 | Kelengkapan | Submit tanpa profil/identitas/dokumen/video atau ack ditolak; metadata file gagal tidak dihitung lengkap |
| BE-T10 | Validasi profil/file | Dummy rules, malformed dates, batas byte tepat/lebih satu byte, empty, signature palsu, ZIP non-DOCX/bomb, MP4 rusak ditangani |
| BE-T11 | Payload besar | Request cap diuji lewat Content-Length dan stream tanpa header; file valid batas 30 MiB tetap dapat diproses |
| BE-T12 | At-rest inspection | Empat payload, filename, note dan checksum privat tidak muncul plaintext di DB/temp/log; material key hanya wrapped |
| BE-T13 | Round-trip | JSON canonical dan file PNG/PDF/DOCX/MP4 kembali sesuai definisi bytes; sumber SHA-256 cocok, video/dokumen masih dapat dibuka |
| BE-T14 | Crypto boundary | Byte lengths 0/1/7/8/9/15/16/17 dan data biner/non-ASCII pada layer crypto pulih; file ukuran nol tetap ditolak API |
| BE-T15 | Fresh material | Dua object/versi dari plaintext identik memakai key/nonce/IV baru dan final ciphertext berbeda |
| BE-T16 | Tampering | Flip ciphertext/tag/nonce/DES IV/drop/AAD, swapped object/wrapped key, wrong key dan truncation gagal tanpa plaintext atau HTTP 200 |
| BE-T17 | Atomic failure | Inject DB/encryption failure dan konflik concurrent: tidak ada orphan/versi setengah jadi, completeness/version tetap konsisten |
| BE-T18 | Version/revision | Unggah ulang menambah versi, v1 tetap bisa diambil pemilik; resubmit mengunci edit lagi |
| BE-T19 | Concurrent writes | Dua koneksi MySQL dengan expected version sama: satu commit, satu 409; reviewer start vs admin assign tidak melewati scope/state |
| BE-T20 | Lab correctness | 2 warm-up tidak masuk 30+ samples, input sama, scope timer jelas, summary dapat dihitung ulang dari raw CSV |
| BE-T21 | Honest results | Tidak ada angka mock disimpan sebagai measured; DES/RC4 failure tidak diklaim authenticated rejection |
| BE-T22 | Restore/cleanup | Backup DB+KEK terpisah dapat dipulihkan; missing key fail closed; cleanup tidak melampaui dataset target |
| BE-T23 | FE live integration | Seluruh flow empat role berjalan memakai backend baru tanpa MSW; token cache, profile attachment, field/status enums cocok |

Test suite mencakup unit crypto/policy dan integration API dengan database MySQL nyata yang terisolasi. Gunakan pytest/httpx atau stack testing yang sudah ada; test yang hanya mengulang mock tidak cukup. Fixture test tidak memakai data asli. Fail injection harus aman untuk database test, tidak dijalankan pada data pengguna.

## 18. Urutan pekerjaan dan deliverable per milestone

| Tahap | Pekerjaan | Bukti selesai |
| --- | --- | --- |
| M1 | Review D-01/D-02, finalisasi API, pilih parameter parser/limits | Decision log + kontrak disepakati tim |
| M2 | MySQL/Alembic/config/provisioning/auth/CSRF | Migrate fresh DB, auth/role tests dan seed tanpa default production password |
| M3 | Case model, scopes dan state machine | Dua applicant/reviewer, incomplete submit, transitions dan race tests lulus |
| M4 | Encrypted object service + file validation + profil/bukti versions | At-rest inspection dan round-trip empat kategori lulus |
| M5 | Retrieval, metadata projection, note/audit, assignments | Strict owner-only, admin/reviewer privacy dan tampering tests lulus |
| M6 | Fixture lab nyata, raw samples, CSV dan interpretasi | Run reproducible dengan environment tercatat, tidak memakai angka mock |
| M7 | FE live cutover dan dokumentasi operasional | Browser flow nyata, CSRF rotation dan download biner lulus |
| M8 | Evidence/report package | Git history bermakna, artefak pengujian, laporan ≤2 A4 dan bukti AI aktual |

Tidak menetapkan estimasi hari atau latency yang belum diukur. Jika BE dikerjakan satu teman, kerjakan milestone berurutan; koordinasi FE untuk M1/M7 dan review silang crypto/authorization wajib dijadwalkan tim. Fitur job async/pagination/server-side search/key rotation otomatis/delegated plaintext adalah pengembangan berikutnya, bukan menu kosong atau klaim selesai.

## 19. Definition of Done dan paket handoff

Backend baru boleh dinyatakan selesai untuk demo assignment jika:

- [ ] D-01 tercatat dari dosen; keputusan D-02/default metadata-only jelas dan diikuti.
- [ ] MySQL berjalan dengan migration; skema dan parameter deployment terdokumentasi.
- [ ] Empat kategori benar-benar terenkripsi sebelum persistence dan pulih sesuai definisi original/canonical bytes.
- [ ] Key bundle terlindungi; tidak ada plaintext sensitif atau key di repo/temp/log/backup hasil dekripsi.
- [ ] Session, CSRF, role, owner, assignment dan status divalidasi server, termasuk endpoint versi lama/export.
- [ ] State transitions, version conflicts dan atomic failures mempunyai test MySQL nyata.
- [ ] Reviewer/admin tidak mendapat plaintext; keputusan tetap berlabel demo.
- [ ] Benchmark mempunyai raw data, metadata lingkungan, metode dan interpretasi, bukan angka hard-code.
- [ ] FE mode live lulus alur pemohon/reviewer/admin/evaluator setelah koordinasi CSRF dan response download.
- [ ] README baru memuat setup fresh DB, migrate, provision, start, test, benchmark, backup/restore, retention dan batas prototipe.
- [ ] OpenAPI spec dan contoh HTTP sesuai kontrak di bagian 8.
- [ ] Laporan hasil verifikasi membedakan PASS/FAIL aktual dan pekerjaan belum diuji; tidak menyalin status mock sebagai bukti BE.

Paket yang diserahkan teman BE: source+migrations+tests, requirements/lock atau tested constraints, `.env.example` tanpa rahasia, dokumentasi CLI/setup, OpenAPI, fixture manifest, hash round-trip, tamper/authorization evidence, hasil benchmark CSV/JSON dan catatan interpretasi. Jangan mengirim `.env`, raw keys, akun pribadi atau database dengan data asli.

Submission GitHub memerlukan commit bermakna dan semua kode tugas. Laporan akhir maksimum dua halaman A4 terpisah dari PRD ini. Link percakapan AI dan screenshot percakapan aktual disediakan pengguna sesuai assignment; screenshot UI atau percakapan buatan bukan penggantinya.

## 20. Referensi dan alasan sumber

Dokumen internal yang mengatur skenario/FE: [PRD produk](VELTRIX_BankKYC_PRD.md), [PRD FE](VELTRIX_BankKYC_FE_PRD.md), dan kontrak TypeScript di `frontend/src/lib/`. Jika contoh awal produk berbeda dengan API yang sudah dipakai FE, gunakan bagian 8 dan catat perubahan lintas dokumen.

Sumber primer teknis yang diperiksa pada 27 Oktober 2026:

- [PyCryptodome AES](https://www.pycryptodome.org/src/cipher/aes), [GCM](https://www.pycryptodome.org/src/cipher/modern#gcm-mode), [DES](https://www.pycryptodome.org/src/cipher/des), [ARC4](https://www.pycryptodome.org/src/cipher/arc4): parameter API dan batas cipher legacy, bukan pengesahan arsitektur bank.
- [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html): rujukan kontrol aplikasi; penerapannya tetap harus diuji pada repo ini.
- [SQLAlchemy version counter](https://docs.sqlalchemy.org/en/20/orm/versioning.html): scope optimistic locking, khususnya keterbatasan bulk update.
- [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/): perilaku UploadFile/spooling yang relevan terhadap plaintext temp.
- [UU PDP No. 27/2022, naskah resmi BPK](https://peraturan.bpk.go.id/Home/Download/224884/UU%20Nomor%2027%20Tahun%202022.pdf): rujukan dasar klasifikasi/prinsip privasi tugas. Pemetaan GDPR mengikuti sumber pada PRD produk; tidak ada klaim audit kepatuhan baru dari dokumen ini.

Semua contoh identitas dan request adalah sintetis. Angka batas/config adalah keputusan/rencana implementasi yang perlu diuji; tidak ada angka benchmark atau sertifikasi keamanan yang direkayasa.
