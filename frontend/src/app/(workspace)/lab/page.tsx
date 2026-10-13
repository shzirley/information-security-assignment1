'use client';

import Link from 'next/link';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Download, Play, RotateCcw, Timer, Square } from 'lucide-react';
import { api, ApiError, saveBlob } from '@/lib/api';
import { ALGORITHMS, bytes, dateLabel, isMock, type BenchmarkResult, type DownloadAttempt } from '@/lib/contracts';
import { Button, EmptyState, ErrorState, LoadingState, MockNote, PageHeading } from '@/components/ui';
import { BenchmarkView } from '@/features/lab/benchmark-view';
import { useToast } from '@/components/providers';

export default function Lab() {
  const files = useQuery({ queryKey: ['files', 'all', ''], queryFn: () => api.files() });
  const profile = useQuery({ queryKey: ['profile'], queryFn: api.profile });
  const history = useQuery({ queryKey: ['benchmarks'], queryFn: api.history });
  const client = useQueryClient(); const toast = useToast();
  const [tab, setTab] = useState<'crypto' | 'download'>('crypto'); const [source, setSource] = useState(''); const [repetitions, setRepetitions] = useState(10); const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BenchmarkResult>(); const [error, setError] = useState<unknown>(); const [attempts, setAttempts] = useState<DownloadAttempt[]>([]); const [downloadId, setDownloadId] = useState(''); const [exporting, setExporting] = useState(false);
  const controller = useRef<AbortController | null>(null); const mounted = useRef(true);
  useEffect(() => { const file = new URLSearchParams(window.location.search).get('file'); if (file) setSource(`file:${file}`); mounted.current = true; return () => { mounted.current = false; controller.current?.abort(); }; }, []);
  const runCrypto = async () => {
    if (!source) { setError(new Error('Pilih sumber data terlebih dahulu.')); return; }
    setBusy(true); setError(undefined); setResult(undefined);
    try { const [type, id] = source.split(':'); const run = await api.benchmark({ type: type as 'file' | 'personal_data', id }, repetitions); if (!mounted.current) return; setResult(run); await client.invalidateQueries({ queryKey: ['benchmarks'] }); toast(isMock ? 'Benchmark simulasi selesai.' : 'Benchmark selesai.'); }
    catch (e) { if (mounted.current) setError(e); } finally { if (mounted.current) setBusy(false); }
  };
  const runDownloads = async () => {
    if (!source.startsWith('file:')) { setError(new Error('Pilih file untuk uji download.')); return; }
    setBusy(true); setError(undefined); setAttempts([]); setDownloadId('');
    const abort = new AbortController(); controller.current = abort; const rows: DownloadAttempt[] = [];
    try {
      const fileId = source.slice(5); const test = await api.createDownloadTest(fileId, repetitions);
      for (let repetition = 1; repetition <= repetitions; repetition++) {
        for (const algorithm of ALGORITHMS) {
          if (abort.signal.aborted) break;
          const start = performance.now();
          try {
            const blob = await api.download(fileId, algorithm, abort.signal);
            rows.push({ algorithm, repetition, elapsed_ms: performance.now() - start, received_bytes: blob.size, success: true });
          } catch (e) {
            if (abort.signal.aborted) break;
            rows.push({ algorithm, repetition, elapsed_ms: performance.now() - start, received_bytes: 0, success: false, error_code: e instanceof ApiError ? e.code : 'REQUEST_FAILED' });
            if (e instanceof ApiError && e.status === 401) { abort.abort(); break; }
          }
          if (mounted.current) setAttempts([...rows]);
        }
        if (abort.signal.aborted) break;
      }
      if (!mounted.current) return;
      await api.saveDownloadTest(test.id, rows); setDownloadId(test.id);
      toast(abort.signal.aborted ? 'Uji dihentikan. Hasil yang selesai tetap dicatat.' : 'Uji download selesai.');
    } catch (e) { if (mounted.current) setError(e); }
    finally { if (mounted.current) setBusy(false); }
  };
  const exportDownloads = async () => { setExporting(true); setError(undefined); try { saveBlob(await api.exportDownloadTest(downloadId), `veltrix-${isMock ? 'mock-' : ''}download.csv`); } catch (e) { setError(e); } finally { setExporting(false); } };
  const stats = ALGORITHMS.map(algorithm => {
    const rows = attempts.filter(a => a.algorithm === algorithm); const successful = rows.filter(a => a.success); const timings = successful.map(a => a.elapsed_ms).sort((a, b) => a - b); const mean = successful.length ? timings.reduce((s, n) => s + n, 0) / successful.length : 0; const middle = Math.floor(timings.length / 2);
    return { algorithm, count: rows.length, successes: successful.length, mean, median: timings.length ? timings.length % 2 ? timings[middle] : (timings[middle - 1] + timings[middle]) / 2 : 0, sd: timings.length > 1 ? Math.sqrt(timings.reduce((s, n) => s + (n - mean) ** 2, 0) / (timings.length - 1)) : 0 };
  });
  const hasSource = !!files.data?.items.length || (tab === 'crypto' && !!profile.data);
  return <><PageHeading index="04" title="Cryptography Lab" description="Input yang sama. Eksperimen yang bisa ditelusuri." /><div className="lab-tabs" role="group" aria-label="Jenis eksperimen"><button disabled={busy} aria-pressed={tab === 'crypto'} className={tab === 'crypto' ? 'active' : ''} onClick={() => { setTab('crypto'); setError(undefined); }}>Benchmark Crypto</button><button disabled={busy} aria-pressed={tab === 'download'} className={tab === 'download' ? 'active' : ''} onClick={() => { setTab('download'); setError(undefined); if (source.startsWith('personal_data:')) setSource(''); }}>Uji Download</button></div>
    {files.isPending || profile.isPending ? <LoadingState label="Menyiapkan sumber eksperimen…" /> : files.isError ? <ErrorState error={files.error} retry={() => files.refetch()} /> : profile.isError ? <ErrorState error={profile.error} retry={() => profile.refetch()} /> : !hasSource ? <section className="panel"><EmptyState title="Belum ada sumber eksperimen" description="Tambahkan file atau profil dummy sebelum menjalankan perbandingan." action={<Link className="button" href="/vault">Buka File Vault</Link>} /></section> : <section className="panel"><div className="lab-settings"><div className="field"><label htmlFor="lab-source">Sumber data</label><select id="lab-source" value={source} disabled={busy} onChange={e => setSource(e.target.value)}><option value="">Pilih sumber data…</option>{files.data?.items.map(file => <option key={file.id} value={`file:${file.id}`}>{file.display_name} ({bytes(file.original_bytes)})</option>)}{tab === 'crypto' && profile.data && <option value={`personal_data:${profile.data.id}`}>Profil pribadi dummy</option>}</select></div><div className="field"><label htmlFor="repetitions">Pengulangan</label><select id="repetitions" value={repetitions} disabled={busy} onChange={e => setRepetitions(Number(e.target.value))}>{[10, 20, 30].map(n => <option value={n} key={n}>{n} kali</option>)}</select></div><Button busy={busy} disabled={!source} onClick={tab === 'crypto' ? runCrypto : runDownloads}><Play size={17} aria-hidden="true" />{tab === 'crypto' ? 'Jalankan benchmark' : 'Mulai uji download'}</Button></div><div className="lab-method"><span><RotateCcw size={15} aria-hidden="true" />{tab === 'crypto' ? '2 warm-up, tidak dihitung' : 'Request berurutan, tanpa cache'}</span><span><Timer size={15} aria-hidden="true" />{tab === 'crypto' ? 'Crypto time terpisah dari I/O' : 'Request sampai seluruh Blob diterima'}</span><span>AES · RC4 · DES</span></div></section>}
    <div className="lab-mock-note"><MockNote /></div>{error && <ErrorState error={error} />}{busy && tab === 'crypto' && <LoadingState label={isMock ? 'Menyiapkan hasil simulasi crypto…' : 'Menjalankan eksperimen berulang…'} />}
    {tab === 'crypto' && result && <BenchmarkView result={result} />}
    {tab === 'download' && busy && <section className="panel download-progress"><h3>Uji download berjalan</h3><progress max={repetitions * 3} value={attempts.length} aria-label="Progress uji download" /><p>{attempts.length} dari {repetitions * 3} request selesai</p><Button variant="secondary" onClick={() => controller.current?.abort()}><Square size={14} aria-hidden="true" />Hentikan uji</Button></section>}
    {tab === 'download' && attempts.length > 0 && <section className="download-results"><div className="lab-result-heading"><div><h2>Waktu penerimaan file</h2><p>{isMock ? 'Diukur pada jalur mock browser. Bukan waktu server crypto nyata.' : 'Diukur di browser, termasuk pemrosesan server dan transfer.'}</p></div><Button variant="secondary" busy={exporting} disabled={!downloadId || busy} onClick={exportDownloads}><Download size={17} aria-hidden="true" />Ekspor CSV</Button></div><div className="panel result-table-wrap" tabIndex={0} role="region" aria-label="Tabel uji download"><table className="data-table result-table"><thead><tr><th>Algoritma</th><th>Mean</th><th>Median</th><th>SD</th><th>Berhasil / request</th></tr></thead><tbody>{stats.map(row => <tr key={row.algorithm}><td><strong>{row.algorithm}</strong></td><td>{row.successes ? `${row.mean.toFixed(2)} ms` : 'Belum ada'}</td><td>{row.successes ? `${row.median.toFixed(2)} ms` : 'Belum ada'}</td><td>{row.successes ? `${row.sd.toFixed(2)} ms` : 'Belum ada'}</td><td>{row.successes}/{row.count}</td></tr>)}</tbody></table></div><p className="small-note">Durasi berakhir ketika seluruh payload diterima browser. Tidak termasuk dialog save atau penulisan final ke disk. Request gagal dicatat, tetapi tidak masuk rata-rata sukses.</p></section>}
    {tab === 'crypto' && !result && !busy && hasSource && <section className="panel lab-results"><EmptyState title="Perbandingan dimulai dari satu input" description="Pilih sumber dan jalankan benchmark untuk melihat tabel, chart, dan ukuran output ketiga algoritma." /></section>}
    {tab === 'crypto' && <section className="panel history-panel"><div className="panel-heading"><div><span className="section-index">Eksperimen / Histori sesi</span><h2>Benchmark sebelumnya</h2></div></div>{history.isPending ? <LoadingState /> : history.isError ? <ErrorState error={history.error} retry={() => history.refetch()} /> : !history.data.length ? <div className="history-row"><p className="small-note" style={{ margin: 0 }}>Belum ada benchmark pada sesi ini.</p></div> : history.data.map((run, i) => <Link className="history-row" href={`/lab/${run.id}`} key={run.id}><div><span className="mono muted">{String(history.data.length - i).padStart(2, '0')}</span><strong>{bytes(run.input_bytes)} · {run.repetitions} pengulangan</strong><small>{dateLabel(run.created_at)}{isMock ? ' · Simulasi' : ''}</small></div><ArrowUpRight size={18} aria-hidden="true" /></Link>)}</section>}
  </>;
}
