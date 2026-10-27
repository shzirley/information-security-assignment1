'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, LockKeyhole } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { Button, SessionNotice } from '@/components/ui';
import { ThemeToggle } from '@/components/app-shell';
import { BrandLogo } from '@/components/brand-logo';
import { roleHome } from '@/lib/kyc';

export function AuthForm({ mode }: { mode: 'login' | 'register' }) {
  const registration = mode === 'register'; const router = useRouter(); const client = useQueryClient();
  const [show, setShow] = useState(false); const [message, setMessage] = useState(''); const [error, setError] = useState('');
  const schema = z.object({ username: z.string().min(3, 'Username minimal 3 karakter.').max(24, 'Username maksimal 24 karakter.').regex(/^[a-zA-Z0-9_]+$/, 'Gunakan huruf, angka, atau underscore.'), password: z.string().min(registration ? 8 : 1, registration ? 'Password minimal 8 karakter.' : 'Masukkan password.'), confirm: z.string() }).refine(data => !registration || data.password === data.confirm, { path: ['confirm'], message: 'Konfirmasi password belum sesuai.' });
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { username: '', password: '', confirm: '' } });
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (query.has('expired')) setMessage('Sesi berakhir. Masuk kembali untuk membuka workspace.');
    else if (query.has('registered')) setMessage('Akun berhasil dibuat. Silakan masuk.');
  }, []);
  const login = async (username: string, password: string) => { const user = await api.login(username, password); client.clear(); client.setQueryData(['session'], user); router.push(roleHome[user.role]); };
  const submit = form.handleSubmit(async values => {
    setError('');
    try {
      if (registration) { await api.register(values.username, values.password); router.push('/login?registered=1'); }
      else await login(values.username, values.password);
    } catch (e) {
      if (e instanceof ApiError) for (const [key, errors] of Object.entries(e.fields)) if (key === 'username' || key === 'password') form.setError(key, { message: errors[0] });
      setError(e instanceof Error ? e.message : 'Permintaan gagal. Coba lagi.');
    }
  });
  return <div className="auth-page">
    <div className="auth-story">
      <Link href="/" className="brand-link" aria-label="VELTRIX"><BrandLogo inverse tagline /></Link>
      <div>
        <p className="section-index">VELTRIX / BankKYC</p>
        <h1>Pengajuan jelas.<br />Bukti terhubung.<br /><span>Akses seperlunya.</span></h1>
        <p>Lengkapi profil dan dokumen, kirim pengajuan, lalu ikuti catatan dan hasil peninjauan dari satu tempat.</p>
        <div className="auth-ciphers"><span>01 <small>Lengkapi</small></span><span>02 <small>Kirim</small></span><span>03 <small>Pantau</small></span></div>
      </div>
      <p className="auth-footnote">Your data. Your control.</p>
    </div>
    <main className="auth-main">
      <div className="auth-tools"><Link href="/" className="text-link">Kembali ke beranda</Link><ThemeToggle /></div>
      <div className="auth-mobile-brand"><Link href="/" className="brand-link" aria-label="VELTRIX"><BrandLogo tagline /></Link></div>
      <div className="auth-form-wrap">
        <div className="auth-form-heading"><LockKeyhole size={27} aria-hidden="true" /><h2>{registration ? 'Buat akun pemohon' : 'Selamat datang kembali'}</h2><p>{registration ? 'Akun baru mendapat peran pemohon. Gunakan identitas sintetis.' : 'Masuk untuk melanjutkan pengajuan atau membuka workspace peranmu.'}</p></div>
        {message && <div className="inline-note" role="status">{message}</div>}
        <form onSubmit={submit} noValidate className="form-stack">
          <div className="field">
            <label htmlFor="username">Username</label>
            <input id="username" autoComplete="username" {...form.register('username')} aria-invalid={!!form.formState.errors.username} aria-describedby={form.formState.errors.username ? 'username-error' : undefined} placeholder="Username kamu" />
            <p className="field-error" id="username-error">{form.formState.errors.username?.message}</p>
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <div className="password-input">
              <input id="password" type={show ? 'text' : 'password'} autoComplete={registration ? 'new-password' : 'current-password'} {...form.register('password')} aria-invalid={!!form.formState.errors.password} aria-describedby={form.formState.errors.password ? 'password-error' : undefined} placeholder={registration ? 'Minimal 8 karakter' : 'Password kamu'} />
              <button type="button" className="icon-button" aria-label={show ? 'Sembunyikan password' : 'Tampilkan password'} onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </div>
            <p className="field-error" id="password-error">{form.formState.errors.password?.message}</p>
          </div>
          {registration && <div className="field"><label htmlFor="confirm">Konfirmasi password</label><input id="confirm" type={show ? 'text' : 'password'} autoComplete="new-password" {...form.register('confirm')} aria-invalid={!!form.formState.errors.confirm} aria-describedby="confirm-error" placeholder="Ulangi password" /><p id="confirm-error" className="field-error">{form.formState.errors.confirm?.message}</p></div>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <Button type="submit" busy={form.formState.isSubmitting} className="full-width">{registration ? 'Buat akun' : 'Masuk ke workspace'}</Button>
        </form>
        <p className="auth-switch">{registration ? 'Sudah punya akun?' : 'Belum punya akun?'} <Link href={registration ? '/login' : '/register'}>{registration ? 'Masuk' : 'Buat akun'}</Link></p><SessionNotice compact />
      </div>
    </main>
  </div>;
}
