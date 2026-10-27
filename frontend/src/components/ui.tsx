'use client';

import * as DialogPrimitive from '@radix-ui/react-dialog';
import { AlertCircle, FileText, LoaderCircle, X } from 'lucide-react';
import { useRef, type ButtonHTMLAttributes, type Ref, type RefObject } from 'react';
import { isMock } from '@/lib/contracts';

export function Button({ className = '', variant = 'primary', busy, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { ref?: Ref<HTMLButtonElement>; variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; busy?: boolean }) {
  return <button type="button" {...props} disabled={props.disabled || busy} className={`button button-${variant} ${className}`}>{busy && <LoaderCircle size={17} className="spin" aria-hidden="true" />}{children}</button>;
}
export function Modal({ open, onOpenChange, title, description, children, returnFocusRef }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; children: React.ReactNode; returnFocusRef?: RefObject<HTMLElement | null> }) {
  const returnFocus = useRef<HTMLElement | null>(null);
  return <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="modal-overlay" />
      <DialogPrimitive.Content className="modal-content"
        onOpenAutoFocus={() => { returnFocus.current = document.activeElement as HTMLElement | null; }}
        onCloseAutoFocus={event => { event.preventDefault(); const target = returnFocusRef?.current ?? returnFocus.current; if (target?.isConnected) target.focus(); }}>
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
export function SessionNotice({ compact = false }: { compact?: boolean }) {
  if (!isMock) return null;
  return <div className={`session-notice ${compact ? 'compact' : ''}`}><p>{compact ? 'Gunakan data sintetis. Data belum dienkripsi, tersimpan sementara di browser, dan hilang saat halaman dimuat ulang.' : 'Gunakan identitas dan dokumen sintetis. Data saat ini belum dienkripsi dan hanya tersimpan sementara di browser. Perubahan akan hilang saat halaman dimuat ulang. Hasil laboratorium merupakan ilustrasi yang belum diukur.'}</p></div>;
}
