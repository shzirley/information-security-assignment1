'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Download, Trash2, ChartNoAxesCombined, LockKeyhole } from 'lucide-react';
import { api, saveBlob } from '@/lib/api';
import { bytes, categoryLabels, dateLabel, isMock, type Algorithm } from '@/lib/contracts';
import { AlgorithmPicker, Button, ErrorState, FileGlyph, LoadingState, Modal, PageHeading } from '@/components/ui';
import { useToast } from '@/components/providers';

export default function FileDetail() {
  const { fileId } = useParams<{ fileId: string }>(); const router = useRouter(); const client = useQueryClient(); const toast = useToast();
  const file = useQuery({ queryKey: ['file', fileId], queryFn: () => api.file(fileId) });
  const [algorithm, setAlgorithm] = useState<Algorithm>('AES'); const [downloading, setDownloading] = useState(false); const [deleting, setDeleting] = useState(false); const [confirm, setConfirm] = useState(false); const [error, setError] = useState<unknown>();
  const download = async () => {
    setDownloading(true); setError(undefined);
    try { const blob = await api.download(fileId, algorithm); saveBlob(blob, file.data!.display_name); toast(isMock ? `Download file demo melalui jalur ${algorithm} selesai.` : `File berhasil didekripsi dengan ${algorithm}.`); }
    catch (e) { setError(e); } finally { setDownloading(false); }
  };
  const remove = async () => {
    setDeleting(true); setError(undefined);
    try { await api.removeFile(fileId); await Promise.all([client.invalidateQueries({ queryKey: ['files'] }), client.invalidateQueries({ queryKey: ['summary'] })]); client.removeQueries({ queryKey: ['file', fileId] }); toast('File dihapus dari vault.'); router.push('/vault'); }
    catch (e) { setError(e); setConfirm(false); } finally { setDeleting(false); }
  };
  if (file.isPending) return <LoadingState label="Memuat detail file…" />;
  if (file.isError) return <><PageHeading index="03 / Detail" title="Detail file" description="Metadata dan sumber dekripsi file." /><ErrorState error={file.error} retry={() => file.refetch()} /><Link href="/vault" className="button button-secondary">Kembali ke Vault</Link></>;
  const item = file.data;
  return <><Link href="/vault" className="back-link">Kembali ke File Vault</Link><PageHeading index="03 / Detail" title={item.display_name} description={`${categoryLabels[item.category]} · Ditambahkan ${dateLabel(item.created_at)}`} action={<Button variant="danger" onClick={() => setConfirm(true)}><Trash2 size={17} aria-hidden="true" />Hapus file</Button>} />{error && <ErrorState error={error} />}
    <div className="detail-layout"><div><section className="panel file-overview"><FileGlyph category={item.category} /><dl><div><dt>Ukuran asli</dt><dd className="mono">{bytes(item.original_bytes)}</dd></div><div><dt>{isMock ? 'Estimasi tiga versi demo' : 'Total storage terenkripsi'}</dt><dd className="mono">{bytes(item.total_stored_bytes)}</dd></div><div><dt>Format</dt><dd>{item.mime_type}</dd></div></dl></section><section className="panel cipher-panel"><div className="panel-heading"><div><span className="section-index">Representasi file</span><h2>{isMock ? 'Tiga ciphertext simulasi' : 'Tiga ciphertext tersimpan'}</h2></div><LockKeyhole size={21} aria-hidden="true" /></div><div className="cipher-detail-list">{item.versions.map((v, i) => <div className="cipher-detail" key={v.algorithm}><div className="cipher-detail-heading"><span className="mono muted">0{i + 1}</span><strong>{v.algorithm}</strong><span className="status-label">{v.mode ?? 'Stream'}</span>{v.algorithm !== 'AES' && <span className="legacy-label">Legacy / pembelajaran</span>}</div><dl><div><dt>Ciphertext</dt><dd className="mono">{bytes(v.ciphertext_bytes)}</dd></div><div><dt>Objek tersimpan</dt><dd className="mono">{bytes(v.stored_bytes)}</dd></div></dl>{v.ciphertext_sample_hex && <div className="hex-sample"><span>Sampel hex{isMock ? ' simulasi' : ''} · 32 bytes</span><code>{v.ciphertext_sample_hex}</code></div>}</div>)}</div></section></div><aside><section className="panel download-panel"><span className="section-index">Ambil data asli</span><h2>{isMock ? 'Coba alur download' : 'Dekripsi & download'}</h2><p>Pilih representasi yang menjadi sumber retrieval.</p><AlgorithmPicker value={algorithm} onChange={setAlgorithm} /><Button className="full-width" busy={downloading} disabled={deleting} onClick={download}><Download size={18} aria-hidden="true" />{isMock ? 'Download file demo' : 'Dekripsi & download'}</Button><p className="small-note">{isMock ? 'File asli dikembalikan dari memori browser. Pemilihan cipher hanya mensimulasikan jalur API.' : 'Server memeriksa akses dan integritas sebelum mengembalikan file.'}</p></section><Link href={`/lab?file=${item.id}`} className="lab-detail-link"><ChartNoAxesCombined size={21} aria-hidden="true" /><span><strong>Uji file ini di Lab</strong><small>Waktu, ukuran, dan retrieval berulang</small></span></Link></aside></div><Modal open={confirm} onOpenChange={next => { if (!deleting) setConfirm(next); }} title="Hapus file ini?" description="File dan ketiga representasinya akan dihapus dari vault."><p className="delete-filename">{item.display_name}</p><div className="modal-actions"><Button variant="secondary" disabled={deleting} onClick={() => setConfirm(false)}>Batal</Button><Button variant="danger" busy={deleting} onClick={remove}>Hapus file</Button></div></Modal></>;
}
