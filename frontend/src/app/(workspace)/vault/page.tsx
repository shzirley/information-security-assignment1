'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { api } from '@/lib/api';
import { categoryLabels, type Category } from '@/lib/contracts';
import { Button, EmptyState, ErrorState, LoadingState, PageHeading } from '@/components/ui';
import { FileList } from '@/features/vault/file-list';
import { UploadDialog } from '@/features/vault/upload-dialog';

export default function Vault() {
  const [category, setCategory] = useState<Category | undefined>(); const [search, setSearch] = useState(''); const [upload, setUpload] = useState(false);
  const files = useQuery({ queryKey: ['files', category ?? 'all', search], queryFn: () => api.files(category, search) });
  return <><PageHeading index="03" title="File Vault" description="Dokumen, gambar, dan video. Satu koleksi, tiga representasi." action={<Button onClick={() => setUpload(true)}><Plus size={18} aria-hidden="true" />Upload file</Button>} /><section className="panel vault-panel"><div className="vault-toolbar"><div className="category-tabs" role="group" aria-label="Filter kategori"><button aria-pressed={!category} className={!category ? 'active' : ''} onClick={() => setCategory(undefined)}>Semua file</button>{Object.entries(categoryLabels).map(([key, label]) => <button key={key} aria-pressed={category === key} className={category === key ? 'active' : ''} onClick={() => setCategory(key as Category)}>{label}</button>)}</div><div className="search-field"><Search size={18} aria-hidden="true" /><label htmlFor="file-search" className="sr-only">Cari nama file</label><input id="file-search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Cari nama file…" /></div></div>{files.isPending ? <LoadingState /> : files.isError ? <ErrorState error={files.error} retry={() => files.refetch()} /> : !files.data.items.length ? <EmptyState title={search || category ? 'Belum ada file yang cocok' : 'Mulai koleksi pertamamu'} description={search || category ? 'Coba nama lain atau pilih kategori semua file.' : 'Upload file dummy untuk mencoba alur penyimpanan dan retrieval.'} action={search || category ? <Button variant="secondary" onClick={() => { setSearch(''); setCategory(undefined); }}>Reset filter</Button> : <Button onClick={() => setUpload(true)}>Upload file pertama</Button>} /> : <FileList files={files.data.items} />}<div className="table-footer"><span>{files.data?.total ?? 0} file ditampilkan</span><span>JPG, PNG, PDF, DOC(X), XLS(X), MP4 · Maks. 25 MB</span></div></section><UploadDialog open={upload} onOpenChange={setUpload} /></>;
}
