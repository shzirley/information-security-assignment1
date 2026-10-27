'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { ChartNoAxesCombined, ClipboardCheck, FlaskConical, LayoutDashboard, ListChecks, LogOut, Menu, Moon, Sun, UsersRound, X } from 'lucide-react';
import { api, clearApiSession } from '@/lib/api';
import { roleHome, roleLabels } from '@/lib/kyc';
import { ErrorState, LoadingState } from './ui';
import { BrandLogo } from './brand-logo';

const navigationByRole = {
  applicant: [{ href: '/applicant/dashboard', label: 'Ringkasan', icon: LayoutDashboard, index: '01' }, { href: '/applicant/applications', label: 'Pengajuan saya', icon: ListChecks, index: '02' }],
  reviewer: [{ href: '/reviewer/queue', label: 'Antrean tinjauan', icon: ClipboardCheck, index: '01' }],
  admin: [{ href: '/admin/assignments', label: 'Penugasan reviewer', icon: UsersRound, index: '01' }],
  evaluator: [{ href: '/lab/benchmark', label: 'Benchmark cipher', icon: ChartNoAxesCombined, index: '01' }, { href: '/lab/verification', label: 'Verifikasi integritas', icon: FlaskConical, index: '02' }],
};
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
  const navigation = navigationByRole[session.data.role];
  const current = navigation.find(n => path.startsWith(n.href));
  const requiredRole = path.startsWith('/applicant') ? 'applicant' : path.startsWith('/reviewer') ? 'reviewer' : path.startsWith('/admin') ? 'admin' : path.startsWith('/lab') ? 'evaluator' : null;
  const permitted = !requiredRole || requiredRole === session.data.role;
  return <div className="app-shell"><a className="skip-link" href="#main-content">Langsung ke konten</a>
    {menu && <button className="sidebar-scrim" aria-label="Tutup menu navigasi" onClick={() => setMenu(false)} />}
    <aside ref={sidebar} id="workspace-navigation" className={`sidebar ${menu ? 'sidebar-open' : ''}`}>
      <div className="sidebar-brand">
        <Link href={roleHome[session.data.role]} className="brand-link" aria-label="VELTRIX"><BrandLogo inverse /></Link>
        <button className="icon-button mobile-only" aria-label="Tutup menu" onClick={() => setMenu(false)}><X size={20} /></button>
      </div>
      <p className="sidebar-caption">Pengajuan BankKYC</p>
      <div className="nav-heading">{roleLabels[session.data.role]}</div>
      <nav aria-label="Navigasi utama">
        {navigation.map(n => <Link key={n.href} href={n.href} className={`nav-item ${path.startsWith(n.href) ? 'active' : ''}`} aria-current={path.startsWith(n.href) ? 'page' : undefined}>
          <n.icon size={19} aria-hidden="true" /><span>{n.label}</span><span className="nav-index" aria-hidden="true">{n.index}</span>
        </Link>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="cipher-ledger"><span>RC4</span><span>DES</span><span>AES</span></div>
        <p>Satu pengajuan.<br />Bukti yang terhubung.</p>
        <Link href="/" className="sidebar-home">Tentang VELTRIX ↗</Link>
        <div className="sidebar-caption-bottom">Pengelolaan pengajuan KYC</div>
      </div>
    </aside>
    <div className="workspace"><div className="topbar"><div className="topbar-start"><button className="icon-button mobile-only" aria-label="Buka menu" aria-controls="workspace-navigation" aria-expanded={menu} onClick={() => setMenu(true)}><Menu size={21} /></button><span className="breadcrumb">{roleLabels[session.data.role]} <span>/</span> <strong>{current?.label ?? 'Detail pengajuan'}</strong></span></div><div className="topbar-actions"><ThemeToggle /><div className="user-identity"><span className="avatar-initial">{session.data.display_name.slice(0, 1).toUpperCase()}</span><span>{session.data.display_name}</span></div><button className="icon-button" disabled={loggingOut} aria-label="Keluar" onClick={logout}><LogOut size={19} /></button></div></div><main id="main-content" className="main-content">{logoutError && <ErrorState error={logoutError} retry={logout} />}{permitted ? children : <section className="panel access-denied"><h1>Akses dibatasi</h1><p>Halaman ini tersedia untuk peran {requiredRole && roleLabels[requiredRole]}. Kamu masuk sebagai {roleLabels[session.data.role]}.</p><Link href={roleHome[session.data.role]} className="button">Kembali ke halaman saya</Link></section>}<footer className="workspace-footer"><span>VELTRIX / BankKYC</span><span>Data sintetis · Akses sesuai peran</span></footer></main></div>
  </div>;
}
