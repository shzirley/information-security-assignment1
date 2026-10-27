'use client';

import { useRef } from 'react';
import { motion, useScroll, useTransform, type MotionValue } from 'framer-motion';
import { FileText, IdCard, UserRound, Video } from 'lucide-react';
import { useMotionPreference } from '@/lib/use-motion-preference';

const items = [
  { Icon: UserRound, number: '01', title: 'Data pribadi', format: 'Profil JSON', detail: 'Identitas, kontak, dan tujuan pengajuan.' },
  { Icon: IdCard, number: '02', title: 'Scan identitas', format: 'PNG / JPG / PDF', detail: 'Salinan dokumen identitas pemohon.' },
  { Icon: FileText, number: '03', title: 'Dokumen kantor', format: 'PDF / DOCX', detail: 'Formulir dan surat administrasi pendukung.' },
  { Icon: Video, number: '04', title: 'Video verifikasi', format: 'MP4', detail: 'Berkas video sebagai kelengkapan pengajuan.' },
];
function EvidenceTile({ index, progress }: { index: number; progress: MotionValue<number> }) {
  const item = items[index]; const reduce = useMotionPreference();
  const x = useTransform(progress, [0, .6], [(1.5 - index) * 12, 0]);
  const y = useTransform(progress, [0, .6], [Math.abs(index - 1.5) * 16, 0]);
  const rotate = useTransform(progress, [0, .6], [(index - 1.5) * 2, 0]);
  return <motion.li className="evidence-tile" style={reduce ? undefined : { x, y, rotate }}>
    <div className="evidence-tile-top"><item.Icon size={26} aria-hidden="true" /><span>{item.number}</span></div><h3>{item.title}</h3><p>{item.detail}</p><span className="evidence-format">{item.format}</span>
  </motion.li>;
}
// Scroll-linked assembly adapted from the user-supplied character/image animation.
// Native scrolling keeps browser anchors, touch, and keyboard navigation intact.
export function TextScrollAnimation() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'center center'] });
  return <section ref={ref} className="evidence-section landing-section" id="bukti" aria-labelledby="evidence-heading">
    <div className="section-caption"><span>01 / Isi pengajuan</span><span>Empat kategori, satu konteks</span></div>
    <div className="evidence-intro"><h2 id="evidence-heading">Bukan sekadar file.<br />Satu cerita pengajuan.</h2><p>Setiap bukti punya tempat dan versi. Lengkapi keempatnya sebelum pengajuan masuk ke antrean tinjauan.</p></div>
    <ol className="evidence-tiles">{items.map((item, index) => <EvidenceTile key={item.number} index={index} progress={scrollYProgress} />)}</ol>
    <div className="evidence-join"><span aria-hidden="true" /><p>Terhubung ke satu nomor pengajuan VELTRIX</p><span aria-hidden="true" /></div>
  </section>;
}
