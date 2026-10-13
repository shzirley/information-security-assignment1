# VELTRIX Graphic Standard Manual

Versi 0.1 • 13 Oktober 2026 • Untuk frontend academic MVP

Sumber identitas: [Veltrix Secure Brand Identity Board.png](<Veltrix Secure Brand Identity Board.png>). Logo, nama warna, hex palette, Montserrat, Inter, dan tagline mengikuti board tersebut. Aturan ukuran, clear space, dan pemetaan komponen di bawah adalah turunan implementasi web, karena detail ukurannya belum ditetapkan dalam board.

## 1. Identitas

Nama: **VELTRIX**

Tagline: **YOUR DATA. YOUR CONTROL.**

Karakter visual: terstruktur, jelas, profesional, dengan aksen teknologi melalui simbol V berlapis. Simbol menyatukan huruf V, pelindung data, keyhole, dan lapisan. Lapisan dalam logo merupakan identitas visual; aplikasi menyimpan tiga representasi independen, bukan mengenkripsi file tiga kali secara berantai.

Brand memberi arah tampilan. Pernyataan keamanan di produk tetap harus sesuai implementasi. Versi FE saat ini memakai mock API dan selalu memberi label demo/simulasi.

## 2. Logo dan aset

Karena sumber yang diberikan berupa board PNG, simbol dibuat ulang sebagai SVG menggunakan referensi bentuk dan warnanya. **Aset ini adalah rekonstruksi web v0.1, bukan hasil ekstraksi pixel-exact atau file master desain asli.** Jika master AI/SVG dari desainer tersedia, simbol dapat diganti tanpa mengganti komponen/flow aplikasi.

| Varian | File | Penggunaan |
| --- | --- | --- |
| Simbol full color | `frontend/public/brand/veltrix-symbol.svg` | Header, sidebar, loading, favicon |
| Simbol monochrome dark | `frontend/public/brand/veltrix-symbol-dark.svg` | Satu warna pada latar terang |
| Simbol monochrome light | `frontend/public/brand/veltrix-symbol-light.svg` | Satu warna pada Midnight Blue/Charcoal |
| Primary full color | `frontend/public/brand/veltrix-primary-color.svg` | Lockup horizontal untuk latar terang |
| Primary dark | `frontend/public/brand/veltrix-primary-dark.svg` | Horizontal monochrome dark |
| Primary light | `frontend/public/brand/veltrix-primary-light.svg` | Horizontal monochrome light pada latar gelap |
| Stacked full color | `frontend/public/brand/veltrix-stacked-color.svg` | Komposisi vertikal, hero/cover |
| Stacked dark/light | `frontend/public/brand/veltrix-stacked-dark.svg`, `veltrix-stacked-light.svg` | Komposisi vertikal monochrome |
| App icon full color | `frontend/public/brand/veltrix-app-color.svg` | Simbol warna pada kotak Midnight Blue |
| App icon monochrome | `frontend/public/brand/veltrix-app-monochrome.svg` | Simbol putih pada kotak Midnight Blue |
| App icon Cloud | `frontend/public/brand/veltrix-app-cloud.svg` | Simbol warna pada kotak Cloud |
| Browser icon | `frontend/src/app/icon.svg` | Next.js favicon/app metadata route |

Lockup SVG menyertakan font Montserrat dan Inter sebagai data font tertanam. Browser modern dapat menampilkannya tanpa font eksternal. Untuk alur cetak/desain yang memerlukan outline glyph, gunakan master berkurva dari desainer; aset ini belum dikonversi menjadi outline huruf.

Preview dan download aset: setelah aplikasi dijalankan, buka **http://127.0.0.1:3000/brand/preview.html**. Halaman ini adalah katalog aset dan tidak masuk navigasi produk.

### Aturan penggunaan web

- Pertahankan proporsi SVG; jangan stretch, rotate, atau memotong simbol/keyhole.
- Sisakan area kosong luar sekurangnya seperempat tinggi simbol. Ini aturan usulan untuk web, bukan ukuran yang tertulis di board.
- Ukuran simbol minimum untuk UI: 28 px; standar header 44 px; sidebar 32 px; hero 94 px.
- Wordmark menggunakan Montserrat Bold, uppercase, tracking terukur. Tracking lebar hanya untuk lockup brand dan tagline, bukan seluruh label UI.
- Tagline boleh disembunyikan di header mobile dan logo berukuran kecil agar tetap terbaca. Wordmark/simbol tetap ada.
- Gradient Royal Blue/Indigo/Cyan digunakan untuk membentuk lapisan simbol. Jangan menambahkan glow/dekorasi pada semua panel.
- Wordmark putih digunakan pada latar Midnight Blue; Charcoal/Midnight pada latar Cloud/putih.
- Foto profil tidak dibuat sebagai bagian brand. UI tetap memakai inisial akun.

## 3. Palette dari board

| Nama | Hex | Penerapan FE |
| --- | --- | --- |
| Midnight Blue | `#0B132B` | Sidebar, panel brand pada landing/login, background dark mode |
| Royal Blue | `#2563EB` | Primary action, focus ring, link/selected pada light mode |
| Indigo | `#6366F1` | Bagian lapisan simbol; aksen brand, bukan warna semua teks |
| Cyan | `#22D3EE` | Bagian permukaan simbol; aksen brand terbatas |
| Cloud | `#F1F5F9` | Background light mode, surface pendukung |
| Charcoal | `#1F2937` | Teks utama light mode, surface pendukung dark mode |

Neutral putih dan abu-abu digunakan untuk permukaan, border, dan teks sekunder. Error, warning, success memiliki token semantik tersendiri dan tidak mengubah palette identitas.

### Kontras dan theme

Royal Blue dengan teks putih dipakai untuk tombol pada light mode. Indigo/Cyan tidak otomatis dipakai untuk teks kecil pada background terang. Dark mode memakai tint biru `#93BAFF` untuk link/aksi agar kontras terhadap background gelap memadai; hex inti brand tetap tersimpan sebagai token terpisah.

Kontras teks normal ditargetkan sekurangnya 4.5:1. Badge “Legacy” memakai teks gelap pada amber muda; error memakai pasangan merah yang berbeda untuk setiap theme. Tooltip chart memakai token foreground, bukan warna seri chart.

## 4. Typography

| Peran | Font | Bobot / ukuran awal |
| --- | --- | --- |
| Wordmark | Montserrat | 700; tracking mengikuti lockup |
| Heading halaman | Montserrat | 600; 34 px desktop, 29 px mobile |
| Heading bagian | Montserrat | 600; 19–22 px |
| Body, form, nav, button | Inter | 400/500/600; body 16 px |
| Teks pendukung | Inter | 12–14 px; label logo memiliki skala optik tersendiri |
| Hex/bytes/indeks teknis | Fira Code | 400; font pendukung teknis, bukan primary brand font |

Montserrat dan Inter di-host oleh aplikasi melalui package `@fontsource`, tidak mengambil font dari Google saat pengguna membuka aplikasi. Fira Code dipertahankan untuk membedakan representasi biner dan angka teknis. Line height body sekitar 1.5; heading 1.2–1.4.

## 5. Penerapan antarmuka

- Header/landing: lockup horizontal full color dan tagline; hero memakai tagline board “Your data. Your control.”.
- Panel brand landing: stacked lockup pada Midnight Blue di atas diagram source/tiga representasi.
- Login/register: lockup horizontal dengan wordmark putih pada panel gelap; mobile mendapat lockup tersendiri ketika panel samping disembunyikan.
- Sidebar: simbol 32 px + wordmark putih; tidak memakai titik dekoratif dari wordmark prototype lama.
- Loading/not-found: logo yang sama melalui komponen `BrandLogo`.
- Dashboard/form/Vault: Montserrat untuk heading, Inter untuk interaksi; Cloud/Charcoal/Midnight mengikuti theme.
- Chart: seri diwarnai untuk membedakan metrik; tabel tetap menjadi alternatif pembacaan angka.
- Navigasi, upload, profil, retrieval, Lab, dan label demo mengikuti scope PRD.

Implementasi pusat: `frontend/src/components/brand-logo.tsx`, token di `frontend/src/app/globals.css`, font di `frontend/src/app/layout.tsx`.

## 6. Antislop dan prinsip desain

Design Read: workspace penyimpanan akademik dengan identitas VELTRIX dari board. **ENERGY 2 / RHYTHM 2 / MOTION 1.**

Gradient dan tracked wordmark memiliki tujuan khusus: merepresentasikan bentuk berlapis dan identitas yang diminta pengguna. Keduanya tidak diterapkan sebagai dekorasi default untuk seluruh UI. Halaman tetap berpusat pada penyimpanan, retrieval, dan eksperimen; tidak menambahkan testimonial, klaim compliance, atau statistik pemasaran.

## 7. Pemeliharaan aset

Untuk menghasilkan ulang lockup dan app icon setelah memperbarui simbol:

```powershell
cd frontend
node scripts/build-brand-assets.mjs
```

Generator hanya menghasilkan aset brand dan font katalog, bukan mengubah source/CSS fitur UI. Perubahan geometri simbol dilakukan langsung pada SVG sumber. `src/app/icon.svg` memakai geometri yang sama dan diperbarui bersama simbol bila bentuknya berubah.
