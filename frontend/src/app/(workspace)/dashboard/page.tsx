'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Plus, UserRound, ChartNoAxesCombined, FolderClosed } from 'lucide-react';
import { api } from '@/lib/api';
import { bytes, isMock } from '@/lib/contracts';
import { Button, CipherLabels, EmptyState, ErrorState, LoadingState, PageHeading } from '@/components/ui';
import { FileList } from '@/features/vault/file-list';
import { UploadDialog } from '@/features/vault/upload-dialog';

export default function Dashboard() {
  const [upload, setUpload] = useState(false);
  const summary = useQuery({ queryKey: ['summary'], queryFn: api.summary });
  const files = useQuery({ queryKey: ['files', 'all', ''], queryFn: () => api.files() });
  return <><PageHeading index="01" title="Dashboard" description="Data kamu, tersusun dalam satu workspace." action={<Button onClick={() => setUpload(true)}><Plus size={18} aria-hidden="true" />Upload file</Button>} />
    {summary.isPending ? <LoadingState /> : summary.isError ? <ErrorState error={summary.error} retry={() => summary.refetch()} /> : <section className="summary-ledger" aria-label="Ringkasan vault"><div><span>File tersimpan</span><strong>{String(summary.data.file_count).padStart(2, '0')}<small>file</small></strong></div><div><span>Total ukuran asli</span><strong>{bytes(summary.data.original_bytes)}</strong></div><div><span>{isMock ? 'Estimasi storage demo' : 'Storage terenkripsi'}</span><strong>{bytes(summary.data.stored_bytes)}</strong></div><div className="summary-cipher"><span>Representasi per item</span><CipherLabels /><small>{isMock ? 'Simulasi tiga versi' : 'Tiga versi independen'}</small></div></section>}
    <div className="dashboard-body"><section className="panel recent-panel"><div className="panel-heading"><div><span className="section-index">01 / Koleksi</span><h2>File terbaru</h2></div><Link href="/vault" className="text-link">Semua file</Link></div>{files.isPending ? <LoadingState /> : files.isError ? <ErrorState error={files.error} retry={() => files.refetch()} /> : !files.data.items.length ? <EmptyState title="Vault kamu masih kosong" description="Tambahkan dokumen, gambar identitas dummy, atau video pertama." action={<Button onClick={() => setUpload(true)}>Upload file pertama</Button>} /> : <FileList files={files.data.items.slice(0, 5)} recent />}</section><aside className="dashboard-aside"><section className="panel profile-summary"><UserRound size={23} aria-hidden="true" /><span className="section-index">02 / Profil</span><h2>Data Pribadi</h2><p>{summary.data?.personal_data_exists ? 'Profil tersedia. Buka hanya ketika kamu perlu melihat isinya.' : 'Simpan nama dan informasi kontak dummy sebagai satu profil.'}</p><Link className="button button-secondary" href="/personal-data">{summary.data?.personal_data_exists ? 'Buka data pribadi' : 'Tambahkan profil'}</Link></section><section className="lab-invitation"><ChartNoAxesCombined size={23} aria-hidden="true" /><h2>Satu input.<br />Bandingkan tiga cipher.</h2><p>Amati waktu, ukuran ciphertext, dan hasil retrieval di Lab.</p><Link href="/lab" className="text-link">Buka Cryptography Lab</Link></section></aside></div><div className="vault-explanation"><FolderClosed size={19} aria-hidden="true" /><p>Satu baris file mewakili tiga versi. Pilih sumber dekripsi dari halaman detail file.</p></div><UploadDialog open={upload} onOpenChange={setUpload} /></>;
}
