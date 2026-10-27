import Link from 'next/link';
import { ArrowUpRight, Check, ChevronRight, FileCheck2, Fingerprint, LockKeyhole, ShieldCheck } from 'lucide-react';
import { ThemeToggle } from '@/components/app-shell';
import { BrandLogo } from '@/components/brand-logo';
import { Hero } from '@/components/ui/hero';
import { TextScrollAnimation } from '@/components/ui/text-scroll-animation';
import { SessionNotice } from '@/components/ui';

export default function Landing() {
  return <div className="bank-landing"><a className="skip-link" href="#landing-main">Langsung ke konten</a>
    <header className="bank-nav"><div className="landing-container nav-inner"><Link href="/" className="brand-link" aria-label="VELTRIX beranda"><BrandLogo tagline /></Link><nav aria-label="Navigasi beranda"><a href="#alur">Alur pengajuan</a><a href="#akses">Hak akses</a><Link href="/login?role=evaluator">Laboratorium</Link></nav><div className="nav-actions"><ThemeToggle /><Link href="/login" className="button button-secondary">Masuk <ArrowUpRight size={16} aria-hidden="true" /></Link></div></div></header>
    <main id="landing-main">
      <div className="landing-container hero-layout"><Hero /><div className="case-preview" aria-label="Ilustrasi pengajuan sintetis, bukan data nasabah nyata">
        <div className="preview-top"><span><span className="preview-dot" />Ringkasan pengajuan</span><span className="preview-tag">4 kategori</span></div>
        <div className="preview-case"><span className="section-index">Nomor pengajuan</span><strong>VTX-2026-1001</strong><span className="status-pill status-NEEDS_REVISION">Perlu revisi</span></div>
        <div className="preview-progress"><span>Kelengkapan bukti</span><strong>4 / 4 kategori</strong><div><span /></div></div>
        <div className="preview-evidence">{[['Data pribadi', 'Profil pemohon'], ['Scan identitas', 'identitas.pdf'], ['Dokumen administrasi', 'formulir-rekening.pdf'], ['Video verifikasi', 'verifikasi.mp4']].map(([title, value]) => <div key={title}><span className="preview-check"><Check size={15} aria-hidden="true" /></span><div><strong>{title}</strong><small>{value}</small></div><span className="preview-version">v1</span></div>)}</div>
        <div className="preview-note"><FileCheck2 size={19} aria-hidden="true" /><p><strong>Ada catatan reviewer</strong><span>Perbarui dokumen administrasi, lalu kirim ulang.</span></p><ChevronRight size={18} aria-hidden="true" /></div>
        <div className="preview-bottom"><LockKeyhole size={14} aria-hidden="true" />Ilustrasi alur pengajuan</div>
      </div></div>
      <div className="landing-container scenario-strip"><span>Alur</span><strong>Pengajuan & peninjauan KYC</strong><span className="strip-divider" /><span>Dipakai oleh</span><strong>Pemohon & tim peninjau</strong></div>
      <div className="landing-container"><TextScrollAnimation /></div>
      <section className="flow-section" id="alur" aria-labelledby="flow-heading"><div className="landing-container flow-grid"><div><span className="section-caption">02 / Dari draf ke keputusan</span><h2 id="flow-heading">Tahu harus<br />melakukan apa.<br /><span>Di setiap tahap.</span></h2><p>Pengajuan yang jelas dimulai dari bukti yang lengkap. Bila perlu revisi, catatan reviewer menjadi langkah berikutnya.</p><Link href="/login?role=applicant" className="text-link">Lihat alur pemohon <ArrowUpRight size={17} aria-hidden="true" /></Link></div><ol className="flow-steps">{[
        ['Siapkan profil & bukti', 'Isi profil, unggah scan identitas, dokumen administrasi, dan video verifikasi. Simpan tiap langkah sebelum melanjutkan.'],
        ['Tinjau, lalu kirim', 'Periksa kelengkapan empat kategori sebelum mengirim. Pengajuan terkunci setelah dikirim.'],
        ['Ikuti tinjauan metadata', 'Reviewer yang ditugaskan memeriksa kelengkapan. Catatan revisi muncul di detail pengajuan.'],
        ['Simpan hasil & ambil berkasmu', 'Lihat hasil peninjauan dan unduh bukti milikmu. Versi lama tetap tersedia saat kamu memperbarui bukti.'],
      ].map(([title, description], i) => <li key={title}><span className="flow-number">0{i + 1}</span><div><h3>{title}</h3><p>{description}</p></div></li>)}</ol></div></section>
      <section className="landing-container access-section landing-section" id="akses" aria-labelledby="access-heading"><div className="section-caption"><span>03 / Batas akses yang jelas</span><ShieldCheck size={20} aria-hidden="true" /></div><div className="access-heading"><h2 id="access-heading">Peran berbeda.<br />Akses seperlunya.</h2><p>Model awal mengikuti akses pemilik saja. Reviewer meninjau metadata operasional; isi dokumen tetap menjadi hak pemohon.</p></div><div className="permissions-ledger">{[
        ['01', 'Pemohon', 'Membuat, melengkapi, dan mengambil bukti miliknya sendiri.', 'applicant'],
        ['02', 'Reviewer', 'Meninjau kelengkapan pengajuan yang ditugaskan dan memberi keputusan.', 'reviewer'],
        ['03', 'Admin', 'Mengatur penugasan reviewer tanpa membuka isi bukti.', 'admin'],
        ['04', 'Evaluator', 'Membandingkan cipher dengan data uji sintetis yang terpisah.', 'evaluator'],
      ].map(([index, title, description, role]) => <Link href={`/login?role=${role}`} key={role} className="permission-row"><span className="permission-index">{index}</span><h3>{title}</h3><p>{description}</p><ArrowUpRight size={21} aria-label={`Masuk sebagai ${title}`} /></Link>)}</div></section>
      <section className="crypto-section"><div className="landing-container crypto-grid"><div className="crypto-symbol"><Fingerprint size={45} strokeWidth={1.3} aria-hidden="true" /><span>Laboratorium kriptografi</span></div><div><h2>Pelajari perlindungannya.<br />Uji, lalu jelaskan hasilnya.</h2><p>Bandingkan AES, DES, dan RC4 pada data uji sintetis, lalu ukur pipeline penyimpanan secara terpisah. DES dan RC4 hanya untuk pembelajaran; pelapisan bukan klaim lebih aman daripada AES saja.</p><div className="pipeline-strip" aria-label="Rancangan pipeline enkripsi"><span>RC4</span><ChevronRight size={15} /><span>DES-CBC</span><ChevronRight size={15} /><span>AES-256-GCM</span></div><p className="small-note">Angka laboratorium saat ini merupakan ilustrasi dan belum diukur.</p><Link href="/login?role=evaluator" className="text-link">Buka laboratorium <ArrowUpRight size={17} aria-hidden="true" /></Link></div></div></section>
      <section className="landing-container landing-close"><div><span className="section-caption">Mulai pengajuanmu</span><h2>Siap merapikan<br />pengajuan pertamamu?</h2></div><div><Link href="/register" className="button button-lg">Buat akun pemohon <ArrowUpRight size={19} aria-hidden="true" /></Link><p>Lengkapi profil, lalu siapkan bukti yang diperlukan.</p></div></section>
      <div className="landing-container landing-disclosure"><SessionNotice /></div>
    </main><footer className="landing-container bank-footer"><Link href="/" aria-label="VELTRIX beranda" className="brand-link"><BrandLogo /></Link><p>VELTRIX BankKYC<br />Your data. Your control.</p><a href="#landing-main" className="text-link">Kembali ke atas ↑</a></footer>
  </div>;
}
