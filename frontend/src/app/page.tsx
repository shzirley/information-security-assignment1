import Link from 'next/link';
import { FileText, LockKeyhole, Download } from 'lucide-react';
import { MockNote } from '@/components/ui';
import { ThemeToggle } from '@/components/app-shell';
import { BrandLogo } from '@/components/brand-logo';

export default function Landing() {
  return <div className="public-page">
    <header className="public-nav">
      <Link href="/" className="brand-link" aria-label="VELTRIX"><BrandLogo tagline /></Link>
      <div><ThemeToggle /><Link href="/login" className="button button-secondary">Masuk</Link></div>
    </header>
    <main className="landing">
      <div className="landing-copy">
        <p className="section-index">Personal data vault / Proyek akademik</p>
        <h1>Your data.<br /><span>Your control.</span></h1>
        <p className="landing-description">Simpan data pribadi dan file. Ambil kembali isinya, lalu bandingkan cara kerja AES, RC4, dan DES dalam satu workspace.</p>
        <div className="landing-actions"><Link href="/register" className="button">Buat akun</Link><Link href="/login" className="text-link">Masuk ke workspace</Link></div>
        <MockNote />
      </div>
      <div className="landing-archive">
        <div className="archive-brand"><BrandLogo inverse tagline stacked /></div>
        <div className="archive-heading"><span>Alur penyimpanan</span><span className="mono">01 / 03</span></div>
        <div className="archive-source"><FileText size={25} aria-hidden="true" /><div><strong>File sumber</strong><span>Identitas dummy, dokumen, atau video</span></div></div>
        <div className="archive-connector"><span /></div>
        <div className="archive-versions">
          {[['01', 'AES', 'Block cipher / CBC'], ['02', 'RC4', 'Stream cipher / Legacy'], ['03', 'DES', 'Block cipher / CBC / Legacy']].map(([i, name, desc]) => <div className="archive-version" key={name}><span className="mono">{i}</span><strong>{name}</strong><span>{desc}</span><LockKeyhole size={17} aria-hidden="true" /></div>)}
        </div>
        <div className="archive-download"><Download size={19} aria-hidden="true" /><p>Pilih satu versi untuk mengambil data asli.</p></div>
        <div className="archive-caption">Diagram alur, bukan bukti enkripsi. RC4 dan DES digunakan untuk pembelajaran.</div>
      </div>
    </main>
    <footer className="public-footer"><span>VELTRIX · Academic MVP</span><span>Data pribadi / File vault / Cryptography lab</span></footer>
  </div>;
}
