'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { Upload, FileUp, X } from 'lucide-react';
import { api } from '@/lib/api';
import { bytes, categoryLabels, isMock, type Category } from '@/lib/contracts';
import { Button, CipherLabels, ErrorState, Modal } from '@/components/ui';
import { useToast } from '@/components/providers';

export function UploadDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [category, setCategory] = useState<Category>('document'); const [file, setFile] = useState<File>();
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null); const client = useQueryClient(); const toast = useToast();
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities });
  const extensions = category === 'identity' ? ['jpg', 'jpeg', 'png'] : category === 'video' ? ['mp4'] : ['pdf', 'doc', 'docx', 'xls', 'xlsx'];
  const select = (selected?: File) => {
    setError(''); setFile(undefined); if (!selected) return;
    if (!extensions.includes(selected.name.split('.').pop()?.toLowerCase() ?? '')) { setError(`Format tidak sesuai. Pilih ${extensions.join(', ').toUpperCase()}.`); return; }
    if (selected.size === 0) { setError('File kosong. Pilih file yang memiliki isi.'); return; }
    if (selected.size > (capabilities.data?.max_file_bytes ?? 25_000_000)) { setError('Ukuran file melebihi batas 25 MB.'); return; }
    setFile(selected);
  };
  const close = (next: boolean) => { if (busy) return; if (!next) { setFile(undefined); setError(''); } onOpenChange(next); };
  const upload = async () => {
    if (!file) { setError('Pilih file terlebih dahulu.'); return; }
    setBusy(true); setError('');
    try { await api.upload(file, category); await Promise.all([client.invalidateQueries({ queryKey: ['files'] }), client.invalidateQueries({ queryKey: ['summary'] })]); toast(isMock ? 'File ditambahkan ke vault demo.' : 'Tiga versi file berhasil disimpan.'); setFile(undefined); onOpenChange(false); }
    catch (e) { setError(e instanceof Error ? e.message : 'Upload belum berhasil.'); }
    finally { setBusy(false); }
  };
  return <Modal open={open} onOpenChange={close} title="Tambahkan file ke vault" description="Satu file diproses menjadi versi AES, RC4, dan DES."><div className="field"><label htmlFor="upload-category">Kategori file</label><select id="upload-category" value={category} disabled={busy} onChange={e => { setCategory(e.target.value as Category); setFile(undefined); setError(''); }}>{Object.entries(categoryLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div><div className={`upload-zone ${drag ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); if (!busy) setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); if (!busy) select(e.dataTransfer.files[0]); }}><FileUp size={31} aria-hidden="true" /><strong>Tarik file ke sini</strong><span>atau pilih dari perangkatmu</span><input ref={input} type="file" accept={extensions.map(e => `.${e}`).join(',')} onChange={e => { select(e.target.files?.[0]); e.target.value = ''; }} className="sr-only" tabIndex={-1} aria-label="Pilih file untuk upload" /><Button variant="secondary" onClick={() => input.current?.click()} disabled={busy}>Pilih file</Button><small>{extensions.join(', ').toUpperCase()} · Maksimal {bytes(capabilities.data?.max_file_bytes ?? 25_000_000)}</small></div>{file && <div className="selected-file"><FileUp size={20} aria-hidden="true" /><div><strong>{file.name}</strong><span>{bytes(file.size)}</span></div><button className="icon-button" aria-label="Hapus pilihan file" disabled={busy} onClick={() => setFile(undefined)}><X size={18} /></button></div>}{capabilities.isError && <ErrorState error={capabilities.error} retry={() => capabilities.refetch()} />}{error && <p className="form-error" role="alert">{error}</p>}<div className="upload-summary"><span>{isMock ? 'Versi simulasi' : 'Versi yang disimpan'}</span><CipherLabels /></div>{busy && <p role="status" className="muted">{isMock ? 'Menambahkan file ke memori demo…' : 'Mengunggah, mengenkripsi, dan menyimpan file…'}</p>}{isMock && <p className="small-note">Mode demo menyimpan file asli di memori browser untuk menguji alur, tanpa enkripsi nyata.</p>}<div className="modal-actions"><Button variant="secondary" disabled={busy} onClick={() => close(false)}>Batal</Button><Button busy={busy} disabled={!file || !capabilities.data} onClick={upload}><Upload size={17} aria-hidden="true" />{isMock ? 'Simulasikan enkripsi & simpan' : 'Enkripsi & simpan'}</Button></div></Modal>;
}
