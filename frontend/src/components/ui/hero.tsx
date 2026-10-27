'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useInView } from 'framer-motion';
import { ArrowDown, ArrowUpRight } from 'lucide-react';
import { Button } from './button';
import { useMotionPreference } from '@/lib/use-motion-preference';

const words = ['identitasmu.', 'dokumenmu.', 'bukti KYC-mu.'];
export function Hero() {
  const root = useRef<HTMLElement>(null);
  const inView = useInView(root);
  const reduce = useMotionPreference();
  const [word, setWord] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    update();
    document.addEventListener('visibilitychange', update);
    return () => document.removeEventListener('visibilitychange', update);
  }, []);
  useEffect(() => {
    if (reduce || hovered || focused || !visible || !inView) return;
    const timer = window.setInterval(() => setWord(value => (value + 1) % words.length), 3600);
    return () => window.clearInterval(timer);
  }, [reduce, hovered, focused, visible, inView]);
  return <section ref={root} className="hero-copy" aria-labelledby="hero-title"
    onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
    onFocusCapture={() => setFocused(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false); }}>
    <div className="hero-eyebrow"><span className="eyebrow-dot" />Pengelolaan bukti KYC</div>
    <h1 id="hero-title">Satu alur untuk<br />
      <span className="sr-only">identitas, dokumen, dan bukti KYC-mu.</span>
      <span className="hero-rotating" aria-hidden="true">
        {reduce ? <span>bukti KYC-mu.</span> : <AnimatePresence mode="wait" initial={false}><motion.span key={word} initial={{ y: 32 }} animate={{ y: 0 }} exit={{ y: -28 }} transition={{ duration: .32 }}>{words[word]}</motion.span></AnimatePresence>}
      </span>
    </h1>
    <p className="hero-description">Siapkan identitas, lengkapi dokumen, dan ikuti setiap tahap pengajuan. Profil dan bukti tersusun dalam satu berkas pengajuan.</p>
    <div className="hero-actions"><Button asChild size="lg"><Link href="/register">Mulai pengajuan <ArrowUpRight size={19} aria-hidden="true" /></Link></Button><a href="#alur" className="text-link">Lihat alurnya <ArrowDown size={16} aria-hidden="true" /></a></div>
  </section>;
}
