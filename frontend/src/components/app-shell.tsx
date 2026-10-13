'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { ChartNoAxesCombined, FolderClosed, LayoutDashboard, LogOut, Menu, Moon, Sun, UserRound, X } from 'lucide-react';
import { api, clearApiSession } from '@/lib/api';
import { isMock } from '@/lib/contracts';
import { ErrorState, LoadingState, MockNote } from './ui';
import { BrandLogo } from './brand-logo';

const navigation = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, index: '01' },
  { href: '/personal-data', label: 'Data Pribadi', icon: UserRound, index: '02' },
  { href: '/vault', label: 'File Vault', icon: FolderClosed, index: '03' },
  { href: '/lab', label: 'Cryptography Lab', icon: ChartNoAxesCombined, index: '04' },
];
export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => { setDark(document.documentElement.dataset.theme === 'dark'); }, []);
  return <button className="icon-button" aria-label={dark ? 'Gunakan tema terang' : 'Gunakan tema gelap'} onClick={() => { const next = !dark; setDark(next); document.documentElement.dataset.theme = next ? 'dark' : 'light'; localStorage.setItem('veltrix-theme', next ? 'dark' : 'light'); }}>{dark ? <Sun size={19} /> : <Moon size={19} />}</button>;
}
export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname(); const router = useRouter(); const client = useQueryClient();
  const session = useQuery({ queryKey: ['session'], queryFn: api.me, staleTime: 0 });
  const [menu, setMenu] = useState(false); const [loggingOut, setLoggingOut] = useState(false); const [logoutError, setLogoutError] = useState<Error>();
  const sidebar = useRef<HTMLElement>(null);
  useEffect(() => { if (session.error && 'status' in session.error && session.error.status === 401) router.replace('/login?expired=1'); }, [session.error, router]);
  useEffect(() => { setMenu(false); }, [path]);
  useEffect(() => {
    if (!menu) return;
    const previous = document.activeElement as HTMLElement | null;
    const focusable = sidebar.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
    focusable?.[0]?.focus();
    const close = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenu(false);
      if (e.key === 'Tab' && focusable?.length) {
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener('keydown', close);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', close); document.body.style.overflow = previousOverflow; previous?.focus(); };
  }, [menu]);
  if (session.isPending) return <LoadingState label="Memeriksa sesi…" />;
  if (session.isError) return <main className="boot-screen"><ErrorState error={session.error} retry={() => session.refetch()} /></main>;
  const logout = async () => {
    setLoggingOut(true); setLogoutError(undefined);
    try { await api.logout(); client.clear(); clearApiSession(); router.replace('/login'); }
    catch (e) { setLogoutError(e instanceof Error ? e : new Error('Logout gagal. Coba lagi.')); setLoggingOut(false); }
  };
  const current = navigation.find(n => path.startsWith(n.href));
  return <div className="app-shell"><a className="skip-link" href="#main-content">Langsung ke konten</a>
    {menu && <button className="sidebar-scrim" aria-label="Tutup menu navigasi" onClick={() => setMenu(false)} />}
    <aside ref={sidebar} id="workspace-navigation" className={`sidebar ${menu ? 'sidebar-open' : ''}`}>
      <div className="sidebar-brand">
        <Link href="/dashboard" className="brand-link" aria-label="VELTRIX"><BrandLogo inverse /></Link>
        <button className="icon-button mobile-only" aria-label="Tutup menu" onClick={() => setMenu(false)}><X size={20} /></button>
      </div>
      <p className="sidebar-caption">Personal data vault</p>
      <div className="nav-heading">Workspace</div>
      <nav aria-label="Navigasi utama">
        {navigation.map(n => <Link key={n.href} href={n.href} className={`nav-item ${path.startsWith(n.href) ? 'active' : ''}`} aria-current={path.startsWith(n.href) ? 'page' : undefined}>
          <n.icon size={19} aria-hidden="true" /><span>{n.label}</span><span className="nav-index" aria-hidden="true">{n.index}</span>
        </Link>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="cipher-ledger"><span>AES</span><span>RC4</span><span>DES</span></div>
        <p>Tiga representasi.<br />Satu sumber data.</p>
        <div className="academic-label">Proyek akademik · v0.1</div>
      </div>
    </aside>
    <div className="workspace"><div className="topbar"><div className="topbar-start"><button className="icon-button mobile-only" aria-label="Buka menu" aria-controls="workspace-navigation" aria-expanded={menu} onClick={() => setMenu(true)}><Menu size={21} /></button><span className="breadcrumb">Workspace <span>/</span> <strong>{current?.label ?? 'Detail'}</strong></span></div><div className="topbar-actions">{isMock && <span className="mode-indicator">Mode demo</span>}<ThemeToggle /><div className="user-identity"><span className="avatar-initial">{session.data.username.slice(0, 1).toUpperCase()}</span><span>{session.data.username}</span></div><button className="icon-button" disabled={loggingOut} aria-label="Keluar" onClick={logout}><LogOut size={19} /></button></div></div><main id="main-content" className="main-content">{logoutError && <ErrorState error={logoutError} retry={logout} />}{children}<footer className="workspace-footer"><span>VELTRIX / Academic cryptography project</span><span>AES-CBC · RC4 · DES-CBC</span></footer></main><div className="workspace-demo-footer"><MockNote compact /></div></div>
  </div>;
}
