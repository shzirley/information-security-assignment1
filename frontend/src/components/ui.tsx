'use client';

import * as DialogPrimitive from '@radix-ui/react-dialog';
import { AlertCircle, FileText, Film, Image, LoaderCircle, X } from 'lucide-react';
import { useRef, type ButtonHTMLAttributes } from 'react';
import { ALGORITHMS, categoryLabels, type Algorithm, type Category, isMock } from '@/lib/contracts';

export function Button({ className = '', variant = 'primary', busy, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; busy?: boolean }) {
  return <button type="button" {...props} disabled={props.disabled || busy} className={`button button-${variant} ${className}`}>{busy && <LoaderCircle size={17} className="spin" aria-hidden="true" />}{children}</button>;
}
export function Modal({ open, onOpenChange, title, description, children }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; children: React.ReactNode }) {
  const returnFocus = useRef<HTMLElement | null>(null);
  return <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="modal-overlay" />
      <DialogPrimitive.Content className="modal-content"
        onOpenAutoFocus={() => { returnFocus.current = document.activeElement as HTMLElement | null; }}
        onCloseAutoFocus={event => { event.preventDefault(); if (returnFocus.current?.isConnected) returnFocus.current.focus(); }}>
        <div className="modal-heading">
          <div><DialogPrimitive.Title>{title}</DialogPrimitive.Title><DialogPrimitive.Description>{description}</DialogPrimitive.Description></div>
          <DialogPrimitive.Close asChild><button className="icon-button" aria-label="Tutup dialog"><X size={20} /></button></DialogPrimitive.Close>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  </DialogPrimitive.Root>;
}
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return <div className="error-state" role="alert"><AlertCircle size={22} aria-hidden="true" /><div><strong>Permintaan belum berhasil</strong><p>{error instanceof Error ? error.message : 'Terjadi masalah. Coba lagi.'}</p>{retry && <Button variant="secondary" onClick={retry}>Coba lagi</Button>}</div></div>;
}
export function LoadingState({ label = 'Memuat data…' }: { label?: string }) {
  return <div className="loading-state" role="status"><LoaderCircle size={22} className="spin" aria-hidden="true" />{label}</div>;
}
export function EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <div className="empty-state"><div className="empty-mark"><FileText size={26} aria-hidden="true" /></div><h2>{title}</h2><p>{description}</p>{action}</div>;
}
export function PageHeading({ index, title, description, action }: { index: string; title: string; description: string; action?: React.ReactNode }) {
  return <header className="page-heading"><div><div className="section-index">Workspace / {index}</div><h1>{title}</h1><p>{description}</p></div>{action && <div className="page-action">{action}</div>}</header>;
}
export function FileGlyph({ category }: { category: Category }) {
  const Icon = category === 'identity' ? Image : category === 'video' ? Film : FileText;
  return <span className={`file-glyph file-glyph-${category}`}><Icon size={21} aria-hidden="true" /></span>;
}
export function CipherLabels() {
  return <span className="cipher-labels" aria-label="Versi AES, RC4, dan DES">{ALGORITHMS.map(a => <span key={a}>{a}</span>)}</span>;
}
export function AlgorithmPicker({ value, onChange }: { value: Algorithm; onChange: (value: Algorithm) => void }) {
  return <div className="algorithm-picker" role="group" aria-label="Sumber dekripsi">{ALGORITHMS.map(a => <button key={a} type="button" aria-pressed={value === a} className={value === a ? 'selected' : ''} onClick={() => onChange(a)}><strong>{a}</strong><span>{a === 'AES' ? 'CBC' : a === 'DES' ? 'CBC · Legacy' : 'Stream · Legacy'}</span></button>)}</div>;
}
export function MockNote({ compact = false }: { compact?: boolean }) {
  if (!isMock) return null;
  return <div className={`mock-note ${compact ? 'compact' : ''}`}><span className="demo-label">Demo FE</span><p>{compact ? 'Data dan proses enkripsi disimulasikan.' : 'Data, ciphertext, dan waktu crypto adalah simulasi. File demo berada di memori browser dan perubahan direset ketika halaman dimuat ulang. Gunakan data dummy.'}</p></div>;
}
export function CategoryLabel({ category }: { category: Category }) { return <span className="muted">{categoryLabels[category]}</span>; }
