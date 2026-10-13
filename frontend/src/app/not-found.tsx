import Link from 'next/link';
import { BrandLogo } from '@/components/brand-logo';
export default function NotFound() { return <main className="boot-screen"><BrandLogo tagline /><h1>Halaman tidak ditemukan</h1><p>Periksa alamat atau kembali ke workspace.</p><Link href="/dashboard" className="button">Buka Dashboard</Link></main>; }
