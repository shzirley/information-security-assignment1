# ADR: Tanda Tangan Digital pada Formulir PDF KYC (Assignment 3)

* **Status:** Diterima dan diimplementasikan untuk kriptografi (`kyc/signature_rsa.py`, `kyc/cms.py`, `kyc/pki.py`, `frontend/src/lib/signing-crypto.ts`). Modul PDF (`kyc/pdf_signing.py`, `kyc/pdf_verify.py`) belum digabung.
* **Tanggal:** 28 November 2026
* **Bagian:** M3-SEC-05 (Maleka, kriptografi dan keamanan)
* **Rujukan:** [rencana pengerjaan](../assignment-3/ASSIGNMENT_3_IMPLEMENTATION_PLAN.md) §1 dan §6 (ancaman R1–R10)

## Konteks

Budi (bendahara HIMA) menandatangani formulir pembukaan rekening PDF miliknya. Reviewer, Andi (lewat berbagi Assignment 2), dan PDF reader pihak ketiga harus bisa memastikan formulir tidak berubah sejak ditandatangani, dan bahwa tanda tangan dibuat dengan kunci yang terdaftar di akun Budi. Tugas mewajibkan logika signing dan verifikasi buatan tim sendiri; library hanya boleh untuk pembuatan kunci, hash, dan membaca/menulis PDF.

## Keputusan

| # | Keputusan | Alasan | Ancaman |
|---|---|---|---|
| D1 | Penandatanganan dilakukan **di browser**; private key hanya ada di file `.pem` milik pemohon | Kalau server memegang private key, admin atau penyerang yang menguasai server bisa menandatangani atas nama Budi, sehingga tanda tangan tidak membuktikan apa pun tentang Budi | R1 |
| D2 | Kunci tanda tangan **terpisah** dari kunci RSA-OAEP Assignment 2 | Satu kunci satu tujuan. Mengganti kunci berbagi tidak boleh membatalkan tanda tangan lama, dan sebaliknya | R7 |
| D3 | **RSA-3072**, e = 65537 | Menurut NIST SP 800-57, RSA-2048 hanya dianjurkan sampai 2030. Arsip KYC disimpan bertahun-tahun, jadi tanda tangan harus tahan lebih lama | R8 |
| D4 | **RSASSA-PKCS1-v1_5 dengan SHA-256**, bukan PSS | Paling luas didukung untuk `/adbe.pkcs7.detached` (Adobe, Foxit, poppler). Skemanya deterministik, sehingga implementasi tim bisa dibandingkan byte demi byte dengan library pembanding | Bonus pembaca PDF |
| D5 | Logika RSA ditulis sendiri: EMSA-PKCS1-v1_5, RSASP1 dengan CRT dan **blinding**, RSAVP1 | Syarat tugas. Blinding mengurangi kebocoran waktu dari aritmetika bilangan besar; setiap tanda tangan diperiksa ulang sebelum dikirim agar kesalahan CRT tidak membocorkan faktor n | R6 |
| D6 | Verifikasi **encode-then-compare**: blok yang diharapkan dibangun ulang dari hash lalu dibandingkan utuh dengan `hmac.compare_digest`; e ≠ 65537, kunci < 2048 bit, dan s ≥ n ditolak | Verifier yang mem-parsing padding dengan longgar bisa dipalsukan (Bleichenbacher 2006, e = 3) | R6 |
| D7 | Wadah **CMS SignedData detached** dengan atribut `contentType`, `signingTime`, `messageDigest`, `signingCertificateV2`; atribut diurutkan sesuai DER | `/adbe.pkcs7.detached` mensyaratkan CMS. `signingCertificateV2` mengikat tanda tangan ke satu sertifikat sehingga sertifikat tidak bisa ditukar. Urutan DER penting karena verifier seperti OpenSSL meng-encode ulang SET OF sebelum menghitung hash | R3 |
| D8 | **VELTRIX Demo CA** menerbitkan sertifikat X.509 v3 setelah **proof of possession** (browser menandatangani tantangan sekali pakai) | Pembaca PDF pihak ketiga hanya bisa menampilkan nama penandatangan bila ada sertifikat. PoP mencegah orang mendaftarkan public key milik orang lain atas namanya | R4 |
| D9 | Private key CA dibungkus AES-256-GCM dengan KEK yang sudah ada (AAD `purpose='ca-key'` dan id CA) | Tidak menambah rahasia baru di `.env`; salinan database saja tidak cukup untuk menerbitkan sertifikat | R1 |
| D10 | Library hanya untuk: pembuatan kunci (Web Crypto di browser, `cryptography` untuk kunci CA), SHA-256, dan encode/decode DER (`asn1crypto`) | Batas tugas. `cryptography` dipakai untuk kunci CA karena pembuatan RSA-3072 dengan `pycryptodome` butuh sekitar 11 detik, padahal CA dibuat di setiap migrasi tes; OpenSSL butuh sekitar 0,13 detik | — |
| D11 | Hasil verifikasi dibedakan: `VALID`, `VALID_UNTRUSTED`, `INVALID`, `MODIFIED_AFTER_SIGNING`, `KEY_REVOKED`, `SIGNER_MISMATCH`, `NOT_SIGNED`, `MALFORMED` | Pengguna tidak boleh menyamakan "valid" dengan "isi benar"; setiap kegagalan punya penyebab berbeda | R9 |

## Bukti

| Klaim | Bukti |
|---|---|
| RSA buatan tim sama dengan library | `test_t02_own_rsassa_matches_pycryptodome` (Python, 50 pesan) dan `npm run test:signing` (browser vs OpenSSL, 30 pesan): identik byte demi byte |
| Pemalsuan padding longgar dan e = 3 ditolak | `test_t09_lenient_padding_and_small_exponent_are_rejected` |
| Sertifikat dan CMS sesuai standar | `test_openssl_accepts_our_certificate_and_cms`: `openssl cms -verify` menerima CMS buatan tim, dan rantai sertifikat lolos |
| Status hasil dibedakan | `test_cms_statuses`, `test_t05_t10_tampered_signature_and_weak_digest_algorithm` |
| PoP dan rotasi kunci | `test_t15_proof_of_possession`, `test_t12_t15_key_registration_api` |

## Konsekuensi dan batasan

- **Server adalah CA.** Server yang jahat bisa menerbitkan sertifikat untuk kunci palsu atas nama Budi dan menandatangani ulang dokumen yang diubah. Hasilnya tetap terdeteksi dari fingerprint kunci yang berbeda dan event `SIGN_KEY_REGISTERED`. Bank sungguhan memakai CA tepercaya atau HSM.
- **Tidak ada Time-Stamp Authority.** `signingTime` di PDF adalah klaim penandatangan; waktu yang dipercaya hanya `signed_at` di database.
- **Tidak ada CRL/OCSP.** Pembaca PDF pihak ketiga tidak tahu bila kunci sudah dicabut.
- **BigInt di browser tidak constant-time.** Blinding mengurangi risiko, tidak menghilangkannya.
- **File private key tanpa password**, mengikuti kebijakan Assignment 2.
- Kompatibilitas dengan Adobe Reader dan `pdfsig` baru bisa diuji setelah modul PDF digabung; uji OpenSSL di atas hanya membuktikan CMS dan sertifikatnya.
