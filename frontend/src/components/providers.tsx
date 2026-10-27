'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { createContext, useContext, useEffect, useState } from 'react';
import { Check, X } from 'lucide-react';
import { isMock } from '@/lib/contracts';
import { clearApiSession } from '@/lib/api';
import { BrandLogo } from './brand-logo';

const ToastContext = createContext<(message: string) => void>(() => {});
export const useToast = () => useContext(ToastContext);
let mockStart: Promise<unknown> | undefined;

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 10_000, refetchOnWindowFocus: false } } }));
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState(false);
  const [toast, setToast] = useState('');
  const router = useRouter();

  useEffect(() => {
    let mounted = true;
    const boot = async () => {
      if (isMock) {
        mockStart ??= import('@/mocks/browser').then(({ worker }) => worker.start({ onUnhandledRequest: 'bypass', quiet: true }));
        await mockStart;
      } else if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.filter(registration => (registration.active ?? registration.waiting ?? registration.installing)?.scriptURL.endsWith('/mockServiceWorker.js')).map(registration => registration.unregister()));
      }
      if (mounted) setReady(true);
    };
    boot().catch(() => { if (mounted) setFailure(true); });
    const expire = () => { client.clear(); clearApiSession(); router.replace('/login?expired=1'); };
    window.addEventListener('veltrix:session-expired', expire);
    return () => { mounted = false; window.removeEventListener('veltrix:session-expired', expire); };
  }, [client, router]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 4500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  if (failure) return <main className="boot-screen"><h1>Halaman belum dapat disiapkan</h1><p>Muat ulang halaman untuk mencoba kembali. Jika masalah berlanjut, periksa izin situs pada browser.</p><button className="button" onClick={() => window.location.reload()}>Muat ulang</button></main>;
  if (!ready) return <main className="boot-screen" aria-busy="true"><BrandLogo tagline /><p>Menyiapkan workspace…</p><span className="spinner" aria-hidden="true" /></main>;
  return <QueryClientProvider client={client}><ToastContext.Provider value={setToast}>{children}<div className="toast-region" aria-live="polite">{toast && <div className="toast"><Check size={18} aria-hidden="true" /><span>{toast}</span><button className="icon-button" aria-label="Tutup pesan" onClick={() => setToast('')}><X size={18} /></button></div>}</div></ToastContext.Provider></QueryClientProvider>;
}
