# Architecture Decision Record (ADR): Justifikasi Kriptografi AES-256-GCM & AAD pada VELTRIX BankKYC

* **Status:** Diterima & Diimplementasikan (*Accepted*)
* **Penulis:** Maleka Ghaniya (Cryptography & Backend Security Lead)
* **Konteks Proyek:** VELTRIX BankKYC — Sistem Verifikasi Identitas Nasabah Perbankan Digital
* **Dasar Hukum & Regulasi:** UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP) Pasal 35 & Standar Keamanan OWASP ASVS v4.0.

---

## 1. Konteks dan Permasalahan (*Context & Problem Statement*)

Sistem perbankan digital BankKYC menyimpan dokumen pembuktian identitas nasabah yang sangat sensitif, meliputi foto KTP, formulir pembukaan rekening, dan video verifikasi diri. Berkas-berkas ini mengandung Data Pribadi Spesifik (Pasal 4 ayat 2 UU PDP) seperti NIK, tanggal lahir, dan rekaman visual individu.

Terdapat tiga ancaman utama (*Threat Model*) pada penyimpanan dokumen KYC di database:

1. **Ancaman Pembocoran Data (*Confidentiality Breach*):** Penyerang yang memperoleh akses fisik atau eksfiltrasi file database SQLite (`bankkyc.db`) tidak boleh dapat membaca dokumen atau data pribadi pemohon.
2. **Ancaman Manipulasi Data (*Integrity & Bit-Flipping Attacks*):** Penyerang dengan akses tulis database dapat mencoba mengubah bit data dokumen tanpa mendekripsi (misal: mengubah foto atau teks pada block cipher non-autentikasi seperti CBC/CTR biasa).
3. **Ancaman Penukaran Dokumen Antar-Nasabah (*Cross-Application Document Substitution Attack*):** Penyerang dapat menyalin ciphertext KTP milik nasabah terpercaya (Nasabah A) ke baris pengajuan nasabah penipu (Nasabah B). Jika skema enkripsi hanya mengenkripsi payload tanpa mengikat identitas pemilik secara kriptografis, sistem akan berhasil mendekripsi KTP Nasabah A di dalam akun Nasabah B, meloloskan penipuan identitas (*identity theft*).

---

## 2. Keputusan Desain (*Decision Drivers*)

Untuk mengatasi ketiga ancaman di atas, kami menetapkan arsitektur kriptografi berbasis **AEAD (*Authenticated Encryption with Associated Data*)** menggunakan **AES-256-GCM**:

1. **AES-256-GCM sebagai Lapisan Luar (*Outer Authenticated Layer*):**
   * Menggunakan Galois/Counter Mode (GCM) dengan ukuran kunci 256-bit dan tag autentikasi GMAC 128-bit (16 bytes).
   * Menjamin kerahasiaan (*Confidentiality*) dan keutuhan (*Integrity*) secara simultan dalam satu operasi terpadu.
   * Setiap objek dienkripsi dengan kunci simetris sekali pakai (*per-object ephemeral key*) dan nonce acak 96-bit (12 bytes) yang tidak pernah digunakan ulang (*unique wrap nonce*).

2. **Pengikatan Konteks Kriptografis Melalui AAD (*Additional Authenticated Data*):**
   * AAD adalah data metadata yang tidak dirahasiakan tetapi **diautentikasi secara matematis** ke dalam tag GMAC.
   * Struktur AAD kanonikal mengikat:
     ```json
     {
       "application_id": "<ID_Pengajuan_Kasus>",
       "owner_id": "<ID_Akun_Pemohon>",
       "id": "<ID_Objek_Bukti>",
       "kind": "evidence",
       "category": "identity",
       "payload_version": 1,
       "key_version": 1,
       "suite_id": "vtx-kyc-layered-v1"
     }
     ```
   * **Mitigasi Terhadap Serangan:** Jika penyerang menyalin baris ciphertext ke aplikasi atau pemilik lain, nilai AAD di header akan berbeda dari konteks kueri backend. Karena penyerang tidak memiliki KEK server, ia tidak dapat memalsukan tag autentikasi baru. Proses verifikasi tag AES-GCM akan gagal (*MAC check failed / IntegrityFailure*) sebelum data sempat didekripsi.

3. **Prinsip *Fail-Closed*:**
   * Jika verifikasi tag AES-GCM gagal (baik karena 1 bit ciphertext rusak atau AAD tidak cocok), sistem secara instan menghentikan eksekusi dan melempar pengecualian `IntegrityFailure`.
   * **Zero Partial Plaintext:** Tidak ada satu byte pun data perantara yang dialirkan atau disimpan ke disk/memori klien saat verifikasi integritas gagal.

---

## 3. Justifikasi Keberadaan Algoritma Warisan (RC4 dan DES-CBC)

Dalam implementasi sistem VELTRIX, terdapat pipeline bertingkat:  
$$\text{Payload} \xrightarrow{\text{RC4-Drop3072}} \xrightarrow{\text{DES-CBC}} \xrightarrow{\text{AES-256-GCM}} \text{Ciphertext}$$

### Mengapa RC4 dan DES Masih Ada?
* **Pemenuhan Syarat Akademik & Pembelajaran Praktikum:** RC4 (stream cipher) dan DES (block cipher klasik berukuran blok 64-bit) diikutsertakan secara spesifik untuk memfasilitasi modul perbandingan di **Laboratorium Evaluator Kriptografi (`/lab/benchmark`)**. Hal ini memungkinkan mahasiswa dan dosen mengamati secara empiris perbedaan *throughput*, *latency*, dan *ciphertext overhead* antara algoritma klasik dan modern.
* **Drop 3072 Bytes pada RC4:** Diterapkan untuk memitigasi kerentanan statistik awal (*Fluhrer-Mantin-Shamir / bias keystream*).

### Batasan dan Rekomendasi Perbankan Riil:
* Tim menegaskan bahwa dalam sistem perbankan komersial riil (*production-grade*), **RC4 dan Single DES dilarang digunakan** karena telah usang (*deprecated* oleh NIST SP 800-131A). 
* Perlindungan keamanan sesungguhnya pada VELTRIX BankKYC bersandar sepenuhnya pada lapisan **AES-256-GCM** dan skema *Envelope Wrapping* berbasis KEK server.

---

## 4. Konsekuensi Desain (*Consequences*)

### Keuntungan (*Positive*):
1. **Perlindungan Terhadap Modifikasi Bit:** Setiap perubahan bit pada ciphertext di storage SQLite langsung terdeteksi dan digagalkan sebelum dekripsi.
2. **Kekebalan dari Penukaran Dokumen:** Serangan substitusi berkas antar-kasus KYC gagal total karena `application_id` dan `owner_id` terikat kuat dalam GMAC tag.
3. **Kepatuhan Audit:** Memenuhi kewajiban pasal 35 UU PDP bahwa pengendali data pribadi wajib menerapkan langkah teknis untuk melindungi data pribadi dari pengubahan tanpa hak.

### Konsekuensi Operasional (*Trade-offs*):
1. **Manajemen KEK Server:** Kunci pembungkus (*Key-Encryption-Key*) yang disimpan pada konfigurasi server (`backend/.env`) menjadi aset paling kritis. Kehilangan KEK menyebabkan seluruh data historis tidak dapat dipulihkan (*irrecoverable*).
2. **Overhead Komputasi:** Pipeline bertingkat memerlukan sedikit siklus CPU tambahan dibanding AES-GCM murni, namun tetap berada dalam batas toleransi aman (< 15 ms untuk berkas gambar 5 MiB).

---

## 5. Ringkasan Kesimpulan

Penggunaan **AES-256-GCM dengan pengikatan AAD** pada VELTRIX BankKYC bukan sekadar preferensi kecepatan, melainkan kebutuhan arsitektural wajib untuk menangkal ancaman manipulasi bit dan substitusi dokumen identitas dalam lingkungan perbankan digital.
