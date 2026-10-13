'use client';
import { ErrorState } from '@/components/ui';
export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) { return <main className="boot-screen"><ErrorState error={new Error('Halaman belum dapat ditampilkan. Muat ulang untuk mencoba kembali.')} retry={reset} /></main>; }
