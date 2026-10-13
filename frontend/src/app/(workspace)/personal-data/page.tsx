'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, LockKeyhole, Pencil, Plus, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import { dateLabel, isMock, type Algorithm, type PersonalFields } from '@/lib/contracts';
import { AlgorithmPicker, Button, CipherLabels, EmptyState, ErrorState, LoadingState, Modal, PageHeading } from '@/components/ui';
import { useToast } from '@/components/providers';

const emptyFields: PersonalFields = { full_name: '', email: '', phone: '', address: '', date_of_birth: '', identity_number: '' };
const dummyFields: PersonalFields = { full_name: 'Pengguna Contoh', email: 'dummy@example.com', phone: '080000000000', address: 'Alamat fiktif untuk tugas akademik', date_of_birth: '2000-01-01', identity_number: 'DUMMY-000002' };
const labels: Record<keyof PersonalFields, string> = { full_name: 'Nama lengkap', email: 'Email', phone: 'Nomor telepon', address: 'Alamat', date_of_birth: 'Tanggal lahir', identity_number: 'Nomor identitas dummy' };
const schema = z.object({ full_name: z.string().trim().min(1, 'Nama lengkap wajib diisi.').max(120, 'Maksimal 120 karakter.'), email: z.union([z.email('Format email belum sesuai.'), z.literal('')]), phone: z.string().max(24, 'Maksimal 24 karakter.'), address: z.string().max(500, 'Maksimal 500 karakter.'), date_of_birth: z.string(), identity_number: z.string().max(64, 'Maksimal 64 karakter.') });

export default function PersonalData() {
  const record = useQuery({ queryKey: ['profile'], queryFn: api.profile }); const client = useQueryClient(); const toast = useToast();
  const [algorithm, setAlgorithm] = useState<Algorithm>('AES'); const [revealed, setRevealed] = useState<PersonalFields>(); const [editing, setEditing] = useState(false); const [busy, setBusy] = useState(false); const [confirm, setConfirm] = useState(false); const [error, setError] = useState<unknown>();
  const form = useForm<PersonalFields>({ resolver: zodResolver(schema), defaultValues: emptyFields });
  const reveal = async (edit = false) => {
    if (!record.data) return;
    setBusy(true); setError(undefined);
    try { const fields = await api.reveal(record.data.id, algorithm); if (edit) { form.reset(fields); setEditing(true); setRevealed(undefined); } else setRevealed(fields); }
    catch (e) { setError(e); } finally { setBusy(false); }
  };
  const save = form.handleSubmit(async fields => {
    setError(undefined);
    try { const updated = await api.saveProfile(fields, record.data?.id); client.setQueryData(['profile'], updated); await client.invalidateQueries({ queryKey: ['summary'] }); setEditing(false); setRevealed(undefined); form.reset(emptyFields); toast(isMock ? 'Profil dummy disimpan dalam demo.' : 'Data pribadi dan tiga versi berhasil disimpan.'); }
    catch (e) { setError(e); }
  });
  const remove = async () => {
    if (!record.data) return; setBusy(true); setError(undefined);
    try { await api.removeProfile(record.data.id); client.setQueryData(['profile'], null); await client.invalidateQueries({ queryKey: ['summary'] }); setRevealed(undefined); form.reset(emptyFields); setEditing(false); setConfirm(false); toast('Data pribadi dihapus.'); }
    catch (e) { setError(e); setConfirm(false); } finally { setBusy(false); }
  };
  return <><PageHeading index="02" title="Data Pribadi" description="Satu profil. Tiga representasi. Buka nilainya hanya ketika diperlukan." action={record.data && !editing ? <Button variant="secondary" busy={busy} onClick={() => reveal(true)}><Pencil size={17} aria-hidden="true" />Edit profil</Button> : undefined} />{error && <ErrorState error={error} />}{record.isPending ? <LoadingState /> : record.isError ? <ErrorState error={record.error} retry={() => record.refetch()} /> : !record.data && !editing ? <section className="panel"><EmptyState title="Belum ada data pribadi" description="Buat profil dengan informasi dummy untuk mencoba penyimpanan dan dekripsi." action={<Button onClick={() => { form.reset(emptyFields); setEditing(true); }}><Plus size={18} aria-hidden="true" />Tambah data dummy</Button>} /></section> : <div className="personal-layout"><section className="panel personal-panel"><div className="panel-heading"><div><span className="section-index">Profil / Informasi pribadi</span><h2>{editing ? record.data ? 'Ubah profil' : 'Tambah profil' : 'Profil kamu'}</h2></div>{!editing && <span className="status-label"><LockKeyhole size={13} aria-hidden="true" />{revealed ? 'Data dibuka' : 'Data disembunyikan'}</span>}</div>{editing ? <form onSubmit={save} noValidate className="personal-form"><div className="form-top-note"><p>Gunakan data fiktif untuk demonstrasi.</p><Button variant="ghost" onClick={() => form.reset(dummyFields)}>Isi contoh dummy</Button></div><div className="form-grid">{(Object.keys(labels) as (keyof PersonalFields)[]).map(key => <div className={`field ${key === 'address' ? 'field-wide' : ''}`} key={key}><label htmlFor={key}>{labels[key]}{key === 'full_name' ? ' *' : ''}</label>{key === 'address' ? <textarea id={key} {...form.register(key)} rows={3} /> : <input id={key} type={key === 'date_of_birth' ? 'date' : key === 'email' ? 'email' : 'text'} {...form.register(key)} aria-invalid={!!form.formState.errors[key]} aria-describedby={`${key}-error`} /> }<p id={`${key}-error`} className="field-error">{form.formState.errors[key]?.message}</p></div>)}</div><div className="form-actions"><Button variant="secondary" disabled={form.formState.isSubmitting} onClick={() => { setEditing(false); form.reset(emptyFields); setError(undefined); }}>Batal</Button><Button type="submit" busy={form.formState.isSubmitting}>{isMock ? 'Simpan profil demo' : 'Enkripsi & simpan'}</Button></div></form> : <><dl className="personal-values">{(Object.keys(labels) as (keyof PersonalFields)[]).map(key => <div key={key}><dt>{labels[key]}</dt><dd className={!revealed ? 'masked-value' : ''}>{revealed ? revealed[key] || 'Belum diisi' : <><span aria-hidden="true">••••••••••</span><span className="sr-only">Disembunyikan</span></>}</dd></div>)}</dl><div className="personal-meta"><span>{record.data ? `Diperbarui ${dateLabel(record.data.updated_at)}` : ''}</span><Button variant="danger" onClick={() => setConfirm(true)}><Trash2 size={16} aria-hidden="true" />Hapus profil</Button></div></>}</section><aside className="panel reveal-panel"><LockKeyhole size={25} aria-hidden="true" /><h2>{isMock ? 'Representasi demo' : 'Representasi terenkripsi'}</h2><CipherLabels /><p>Nilai profil tidak otomatis dibuka saat halaman dimuat.</p>{!editing && <><label className="standalone-label">Sumber dekripsi</label><AlgorithmPicker value={algorithm} onChange={value => { setAlgorithm(value); setRevealed(undefined); }} /><Button variant={revealed ? 'secondary' : 'primary'} className="full-width" busy={busy} onClick={() => revealed ? setRevealed(undefined) : reveal()}>{revealed ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}{revealed ? 'Sembunyikan data' : 'Tampilkan data'}</Button></>}<p className="small-note">{isMock ? 'Profil demo disimpan sementara di memori browser. Enkripsi dan pemeriksaan integritas belum dijalankan.' : 'Akses dan integritas diperiksa di server sebelum data ditampilkan.'}</p></aside></div>}<Modal open={confirm} onOpenChange={next => { if (!busy) setConfirm(next); }} title="Hapus profil pribadi?" description="Seluruh informasi profil dan ketiga representasinya akan dihapus."><div className="modal-actions"><Button variant="secondary" disabled={busy} onClick={() => setConfirm(false)}>Batal</Button><Button variant="danger" busy={busy} onClick={remove}>Hapus profil</Button></div></Modal></>;
}
