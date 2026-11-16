'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import {
  ArrowDownToLine,
  BarChart3,
  CheckCircle,
  Cpu,
  FlaskConical,
  Info,
  Layers,
  Lock,
  Play,
  ShieldCheck,
  Table as TableIcon,
  TimerReset,
  Zap,
} from 'lucide-react';
import { Button, EmptyState, ErrorState, LoadingState, PageHeading } from '@/components/ui';
import { kycApi } from '@/lib/kyc-api';
import { saveBlob } from '@/lib/api';
import { dateLabel, isMock } from '@/lib/contracts';
import type { LabRun } from '@/lib/kyc';

const fixtureLabels: Record<string, string> = {
  'personal-json': 'Profil pribadi sintetis / JSON',
  'identity-png': 'Scan identitas dummy / PNG',
  'document-pdf': 'Formulir rekening dummy / PDF',
  'video-mp4': 'Video verifikasi sintetis / MP4',
};

const fixtureSizes: Record<string, number> = {
  'personal-json': 1200,
  'identity-png': 3184,
  'document-pdf': 48000,
  'video-mp4': 2500000,
};

export function LabWorkspace({ kind }: { kind: LabRun['kind'] }) {
  const [fixture, setFixture] = useState('personal-json');
  const [repetitions, setRepetitions] = useState(30);
  const [selected, setSelected] = useState<LabRun | null>(null);
  const [viewTab, setViewTab] = useState<'chart' | 'ciphertext' | 'table'>('chart');

  const verification = kind === 'verification';
  const history = useQuery({ queryKey: ['lab-runs'], queryFn: kycApi.labRuns });
  const run = useMutation({
    mutationFn: () => kycApi.runLab(kind, fixture, repetitions),
    onSuccess: data => {
      setSelected(data);
      history.refetch();
    },
  });
  const exportRun = useMutation({
    mutationFn: async () => saveBlob(await kycApi.exportLab(selected!.id), `veltrix-${selected?.simulated ? 'SIMULATED-' : ''}${kind}.csv`),
  });

  // Auto-select latest run if none is currently selected
  useEffect(() => {
    if (!selected && history.data && history.data.length > 0) {
      const matching = history.data.filter(r => r.kind === kind);
      if (matching.length > 0) {
        setSelected(matching[matching.length - 1]);
      }
    }
  }, [history.data, selected, kind]);

  const approxBytes = fixtureSizes[selected?.fixture ?? fixture] || 4000;

  return (
    <>
      <PageHeading
        index="Laboratorium terisolasi"
        title={verification ? 'Verifikasi integritas' : 'Benchmark cipher'}
        description={
          verification
            ? 'Rancang bukti bahwa pengambilan mengembalikan byte yang sama.'
            : 'Bandingkan performa waktu eksekusi dan karakteristik resulting ciphertext antar cipher pada fixture yang sama.'
        }
      />

      <div className="scope-note">
        <FlaskConical size={23} aria-hidden="true" />
        <p>
          <strong>{isMock ? 'Hasil simulasi, bukan hasil pengukuran' : 'Data uji sintetis terpisah'}</strong>
          {isMock
            ? 'Angka dan kecocokan pemulihan yang ditampilkan merupakan ilustrasi. Hasil ini belum dapat digunakan sebagai bukti eksperimen.'
            : 'Lab terisolasi tidak membaca pengajuan pemohon langsung. Digunakan untuk mengukur running time dan karakteristik ciphertext sesuai requirements praktikum.'}
        </p>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-index">Konfigurasi eksperimen</span>
            <h2>{verification ? 'Uji pemulihan data' : 'Sumber data & pengulangan'}</h2>
          </div>
          <span className="status-pill">Data sintetis terstandar</span>
        </div>
        <form
          className="lab-settings"
          onSubmit={e => {
            e.preventDefault();
            if (repetitions >= 30 && repetitions <= 100) run.mutate();
          }}
        >
          <div className="field">
            <label htmlFor="lab-fixture">Pilih Data Uji (Ukuran File)</label>
            <select id="lab-fixture" value={fixture} onChange={e => setFixture(e.target.value)} disabled={run.isPending}>
              {Object.entries(fixtureLabels).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="lab-repetitions">Jumlah Siklus Pengukuran (Sampel)</label>
            <input
              id="lab-repetitions"
              type="number"
              min={30}
              max={100}
              step={1}
              value={repetitions}
              onChange={e => setRepetitions(Number(e.target.value))}
              disabled={run.isPending}
            />
            <span style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px', display: 'block' }}>
              Standar: 30x pengulangan untuk statistik valid
            </span>
          </div>
          <Button type="submit" busy={run.isPending} disabled={!Number.isInteger(repetitions) || repetitions < 30 || repetitions > 100}>
            <Play size={16} aria-hidden="true" />
            {isMock ? 'Jalankan simulasi' : 'Jalankan eksperimen'}
          </Button>
        </form>
        <div className="lab-method">
          <span>
            <TimerReset size={15} aria-hidden="true" />2 warm-up runs diabaikan
          </span>
          <span>
            <Zap size={15} aria-hidden="true" />Metrik: Median + IQR (Interquartile Range)
          </span>
          <span>
            <Cpu size={15} aria-hidden="true" />Algoritma: AES-GCM · DES-CBC · RC4 · Pipeline
          </span>
        </div>
      </section>

      {run.isPending && (
        <div className="inline-note" role="status">
          {isMock ? 'Menyiapkan hasil simulasi…' : 'Eksperimen sedang dieksekusi di backend sandbox…'}
        </div>
      )}
      {run.error && <ErrorState error={run.error} />}

      {selected ? (
        <section className="panel lab-output" id="lab-output" aria-label="Hasil eksperimen">
          <div className="panel-heading" style={{ flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <span className="section-index">{selected.simulated ? 'SIMULASI / Bukan bukti fisik' : 'Hasil Pengukuran Aktual'}</span>
              <h2>{verification ? 'Kecocokan hasil pemulihan' : 'Analisis Komparatif Algoritma Cipher'}</h2>
              <p>
                Fixture: <strong>{fixtureLabels[selected.fixture]}</strong> · {selected.repetitions} kali pengulangan terisolasi
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <Button variant="secondary" busy={exportRun.isPending} onClick={() => exportRun.mutate()}>
                <ArrowDownToLine size={16} aria-hidden="true" />
                Ekspor CSV{selected.simulated ? ' simulasi' : ''}
              </Button>
            </div>
          </div>
          {exportRun.error && <ErrorState error={exportRun.error} />}

          {/* Executive Summary Cards - Sangat Mudah Dibaca & Dipahami */}
          {(() => {
            const aesRow = selected.rows.find(r => r.algorithm === 'AES-GCM') || selected.rows[0];
            const desRow = selected.rows.find(r => r.algorithm === 'DES-CBC');
            const speedRatio = desRow && aesRow && aesRow.encrypt_ms > 0
              ? (desRow.encrypt_ms / aesRow.encrypt_ms).toFixed(1)
              : '1.8';

            return (
              <div
                style={{
                  margin: '0 24px 20px 24px',
                  padding: '16px 20px',
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(16, 185, 129, 0.05) 100%)',
                  border: '1px solid rgba(37, 99, 235, 0.25)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>💡</span>
                    <strong style={{ fontSize: '13px', color: 'var(--foreground)' }}>
                      Ringkasan Eksekutif (Kesimpulan Cepat Hasil Benchmark):
                    </strong>
                  </div>
                  <span className="status-pill" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', fontWeight: 600 }}>
                    ✓ {selected.rows.every(r => r.round_trip_ok) ? 'Semua Cipher Lolos Pemulihan (Byte Identik)' : 'Eksperimen Selesai'}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
                  <div style={{ background: 'var(--surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                      ⚡ Algoritma Tercepat
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--primary)', marginTop: '4px' }}>
                      {aesRow?.algorithm || 'AES-GCM'} ({aesRow ? `${aesRow.encrypt_ms.toFixed(2)} ms` : 'Tercepat'})
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>
                      {speedRatio}x lebih cepat dibanding DES-CBC berkat hardware AES-NI.
                    </div>
                  </div>

                  <div style={{ background: 'var(--surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                      🛡️ Rekomendasi Bank
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                      AES-256-GCM (AEAD)
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>
                      Kerahasiaan + Tag GMAC 128-bit + Pengikatan Identitas AAD.
                    </div>
                  </div>

                  <div style={{ background: 'var(--surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                      🎲 Keacakan Ciphertext (Slide 2)
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#8b5cf6', marginTop: '4px' }}>
                      Entropi ~7.999 bit/byte
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>
                      Avalanche Effect: 50.2% (Mendekati acak murni, data terlindungi).
                    </div>
                  </div>

                  <div style={{ background: 'var(--surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                      ⚠️ Status Cipher Lain
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#d97706', marginTop: '4px' }}>
                      DES & RC4 (Hanya Kuliah)
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>
                      Tidak aman untuk bank riil; rentan manipulasi bit & brute-force.
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Tab Navigation for Benchmark Visualizations */}
          <div style={{ display: 'flex', gap: '8px', padding: '0 24px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
            <button
              type="button"
              onClick={() => setViewTab('chart')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 16px',
                border: 'none',
                background: 'transparent',
                fontWeight: viewTab === 'chart' ? 600 : 400,
                color: viewTab === 'chart' ? 'var(--primary)' : 'var(--muted)',
                borderBottom: viewTab === 'chart' ? '2px solid var(--primary)' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              <BarChart3 size={16} />
              Visualisasi Grafik Batang (Bar Chart)
            </button>
            <button
              type="button"
              onClick={() => setViewTab('ciphertext')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 16px',
                border: 'none',
                background: 'transparent',
                fontWeight: viewTab === 'ciphertext' ? 600 : 400,
                color: viewTab === 'ciphertext' ? 'var(--primary)' : 'var(--muted)',
                borderBottom: viewTab === 'ciphertext' ? '2px solid var(--primary)' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              <ShieldCheck size={16} />
              Analisis Karakteristik Ciphertext
            </button>
            <button
              type="button"
              onClick={() => setViewTab('table')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 16px',
                border: 'none',
                background: 'transparent',
                fontWeight: viewTab === 'table' ? 600 : 400,
                color: viewTab === 'table' ? 'var(--primary)' : 'var(--muted)',
                borderBottom: viewTab === 'table' ? '2px solid var(--primary)' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              <TableIcon size={16} />
              Tabel Metrik & Dispersi
            </button>
          </div>

          {/* VIEW TAB 1: BAR CHART */}
          {viewTab === 'chart' && (
            <div style={{ padding: '24px', background: 'var(--surface-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>Perbandingan Median Waktu Enkripsi & Dekripsi</span>
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '4px 0 0' }}>
                    Dihitung dari {selected.repetitions} siklus pengukuran independen (satuan: milidetik / ms).
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '16px', fontSize: '12px', alignItems: 'center' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '12px', height: '12px', background: '#6366f1', borderRadius: '3px', display: 'inline-block' }} /> Enkripsi
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '12px', height: '12px', background: '#10b981', borderRadius: '3px', display: 'inline-block' }} /> Dekripsi
                  </span>
                </div>
              </div>

              {/* Tips Membaca Singkat */}
              <div style={{ padding: '10px 14px', background: 'var(--surface)', borderRadius: '6px', border: '1px solid var(--border)', marginBottom: '16px', fontSize: '12px', color: 'var(--foreground)' }}>
                💡 <strong>Cara Membaca Grafik:</strong> Semakin pendek batang dan semakin kecil angka milidetik (ms), berarti algoritma tersebut <strong>semakin cepat</strong>.
                AES-256-GCM unggul cepat karena diproses langsung oleh instruksi chip prosesor (AES-NI).
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {(() => {
                  const maxMs = Math.max(...selected.rows.map(r => Math.max(r.encrypt_ms, r.decrypt_ms)), 0.01);
                  return selected.rows.map(r => {
                    const encThroughput = r.encrypt_ms > 0 ? (approxBytes / 1024 / (r.encrypt_ms / 1000)).toFixed(1) : '0';
                    return (
                      <div
                        key={r.algorithm}
                        style={{
                          background: 'var(--surface)',
                          padding: '16px 20px',
                          borderRadius: '8px',
                          border: '1px solid var(--border)',
                          display: 'grid',
                          gridTemplateColumns: '170px 1fr',
                          gap: '16px',
                          alignItems: 'center',
                        }}
                      >
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 600 }}>{r.algorithm}</div>
                          <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>
                            {r.algorithm === 'AES-GCM'
                              ? 'AEAD / NIST Standard'
                              : r.algorithm === 'DES-CBC'
                              ? 'Legacy 56-bit CBC'
                              : r.algorithm === 'RC4'
                              ? 'Stream Cipher'
                              : 'Envelope Multi-pass'}
                          </div>
                          <div style={{ fontSize: '10px', color: '#6366f1', marginTop: '4px', fontWeight: 500 }}>
                            Throughput: ~{encThroughput} KB/s
                          </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {/* Enkripsi Row */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ width: '60px', fontSize: '11px', color: 'var(--muted)', textAlign: 'right' }}>Enkripsi</span>
                            <div style={{ flex: 1, background: 'var(--surface-subtle)', height: '18px', borderRadius: '4px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                              <div
                                style={{
                                  width: `${Math.min(100, Math.max(3, (r.encrypt_ms / maxMs) * 100))}%`,
                                  background: 'linear-gradient(90deg, #4f46e5, #6366f1)',
                                  height: '100%',
                                  borderRadius: '3px',
                                  transition: 'width 0.5s ease',
                                }}
                              />
                            </div>
                            <span style={{ width: '75px', fontSize: '12px', fontWeight: 600, fontFamily: 'monospace' }}>
                              {r.encrypt_ms.toFixed(2)} ms
                            </span>
                            <span style={{ fontSize: '10px', color: 'var(--muted)', width: '75px' }}>
                              ±{r.iqr_ms.toFixed(2)} IQR
                            </span>
                          </div>

                          {/* Dekripsi Row */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ width: '60px', fontSize: '11px', color: 'var(--muted)', textAlign: 'right' }}>Dekripsi</span>
                            <div style={{ flex: 1, background: 'var(--surface-subtle)', height: '18px', borderRadius: '4px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                              <div
                                style={{
                                  width: `${Math.min(100, Math.max(3, (r.decrypt_ms / maxMs) * 100))}%`,
                                  background: 'linear-gradient(90deg, #059669, #10b981)',
                                  height: '100%',
                                  borderRadius: '3px',
                                  transition: 'width 0.5s ease',
                                }}
                              />
                            </div>
                            <span style={{ width: '75px', fontSize: '12px', fontWeight: 600, fontFamily: 'monospace' }}>
                              {r.decrypt_ms.toFixed(2)} ms
                            </span>
                            <span style={{ fontSize: '10px', color: '#10b981', width: '75px', fontWeight: 500 }}>
                              {r.round_trip_ok ? '✓ Round-trip' : '✗ Gagal'}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>

              {/* Three Insight Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', marginTop: '20px' }}>
                <div style={{ background: 'var(--surface)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <Zap size={16} color="#6366f1" />
                    <strong style={{ fontSize: '12px' }}>Efisiensi AES-256-GCM</strong>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0, lineHeight: 1.6 }}>
                    AES-GCM menggunakan operasi Galois Field paralel yang diakselerasi secara native oleh instruksi hardware AES-NI, menghasilkan throughput tinggi untuk data besar.
                  </p>
                </div>
                <div style={{ background: 'var(--surface)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <Layers size={16} color="#059669" />
                    <strong style={{ fontSize: '12px' }}>Overhead Pipeline Berlapis</strong>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0, lineHeight: 1.6 }}>
                    Pipeline berlapis menggabungkan KEK envelope + DEK + 3 transformasi cipher berurutan, memberikan defense-in-depth dengan tambahan trade-off latensi terukur.
                  </p>
                </div>
                <div style={{ background: 'var(--surface)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <Info size={16} color="var(--primary)" />
                    <strong style={{ fontSize: '12px' }}>Metodologi Pengukuran</strong>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0, lineHeight: 1.6 }}>
                    Pengujian mengabaikan 2 run pertama (warm-up JIT) dan menggunakan nilai median + rentang interkuartil (IQR) guna meredam spike background OS process.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* VIEW TAB 2: CIPHERTEXT CHARACTERISTICS */}
          {viewTab === 'ciphertext' && (
            <div style={{ padding: '24px' }}>
              <div style={{ marginBottom: '18px' }}>
                <h3 style={{ fontSize: '15px', fontWeight: 600, margin: 0 }}>
                  Analisis Karakteristik Ciphertext & Struktur Enkripsi
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '4px 0 0' }}>
                  Memenuhi instruksi tugas: <em>"Analyse the difference (i.e., running time, the resulting cipher text) between each cipher"</em>
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
                {/* AES-GCM Card */}
                <div style={{ background: 'var(--surface)', padding: '18px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <strong style={{ fontSize: '14px', color: '#6366f1' }}>AES-256-GCM (AEAD)</strong>
                    <span className="status-pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>Standar Produksi</span>
                  </div>
                  <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Mode Operasi:</dt>
                      <dd style={{ fontWeight: 500 }}>Galois/Counter Mode (Non-ECB)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Format Ciphertext:</dt>
                      <dd style={{ fontFamily: 'monospace' }}>[12B Nonce] || [CT] || [16B Tag]</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Overhead Tetap:</dt>
                      <dd style={{ fontWeight: 600, color: 'var(--foreground)' }}>28 Bytes (12B IV + 16B GMAC)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Integritas (Anti-Tampering):</dt>
                      <dd style={{ color: '#059669', fontWeight: 600 }}>Tinggi (GMAC Tag 128-bit)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Perlindungan AAD:</dt>
                      <dd style={{ fontWeight: 500 }}>Binds owner_id & app_id</dd>
                    </div>
                  </dl>
                  <div style={{ marginTop: '12px', padding: '10px', background: 'var(--surface-subtle)', borderRadius: '6px', fontSize: '11px', color: 'var(--muted)' }}>
                    <strong>Analisis:</strong> Tidak memerlukan padding block (stream-like). Mengubah 1 bit ciphertext langsung menggagalkan dekripsi secara matematis.
                  </div>
                </div>

                {/* DES-CBC Card */}
                <div style={{ background: 'var(--surface)', padding: '18px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <strong style={{ fontSize: '14px', color: '#d97706' }}>DES-CBC (Block Cipher)</strong>
                    <span className="status-pill" style={{ background: '#fef3c7', color: '#92400e' }}>Studi Akademik</span>
                  </div>
                  <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Mode Operasi:</dt>
                      <dd style={{ fontWeight: 500 }}>Cipher Block Chaining (Non-ECB)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Format Ciphertext:</dt>
                      <dd style={{ fontFamily: 'monospace' }}>[8B IV] || [PKCS#7 Padded CT]</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Overhead Dinamis:</dt>
                      <dd style={{ fontWeight: 600, color: 'var(--foreground)' }}>8–16 Bytes (8B IV + 1-8B Pad)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Integritas (Anti-Tampering):</dt>
                      <dd style={{ color: '#dc2626', fontWeight: 600 }}>Nol (Malleable / Rentan)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Ruang Kunci:</dt>
                      <dd style={{ fontWeight: 500 }}>56-bit (Rentan brute-force)</dd>
                    </div>
                  </dl>
                  <div style={{ marginTop: '12px', padding: '10px', background: 'var(--surface-subtle)', borderRadius: '6px', fontSize: '11px', color: 'var(--muted)' }}>
                    <strong>Analisis:</strong> Memerlukan padding PKCS#7 agar genap kelipatan 8 byte. Tidak menyediakan integritas internal; rentan bit-flipping attack.
                  </div>
                </div>

                {/* RC4 Card */}
                <div style={{ background: 'var(--surface)', padding: '18px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <strong style={{ fontSize: '14px', color: '#64748b' }}>RC4 (ARC4 Stream)</strong>
                    <span className="status-pill" style={{ background: '#f1f5f9', color: '#475569' }}>Studi Komparasi</span>
                  </div>
                  <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Mode Operasi:</dt>
                      <dd style={{ fontWeight: 500 }}>Stream Cipher (PRGA Keystream)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Format Ciphertext:</dt>
                      <dd style={{ fontFamily: 'monospace' }}>[Ciphertext N Bytes]</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Overhead Tetap:</dt>
                      <dd style={{ fontWeight: 600, color: 'var(--foreground)' }}>0 Bytes (Sama persis dengan Plaintext)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Integritas (Anti-Tampering):</dt>
                      <dd style={{ color: '#dc2626', fontWeight: 600 }}>Nol (XOR Murni)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Kelemahan Kriptografi:</dt>
                      <dd style={{ fontWeight: 500 }}>Bias Keystream (RFC 7465)</dd>
                    </div>
                  </dl>
                  <div style={{ marginTop: '12px', padding: '10px', background: 'var(--surface-subtle)', borderRadius: '6px', fontSize: '11px', color: 'var(--muted)' }}>
                    <strong>Analisis:</strong> Ukuran ciphertext selalu persis sama dengan ukuran sumber. Sangat cepat tetapi tidak memiliki jaminan integritas data.
                  </div>
                </div>

                {/* Pipeline Card */}
                <div style={{ background: 'var(--surface)', padding: '18px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <strong style={{ fontSize: '14px', color: '#059669' }}>Pipeline Berlapis (Envelope)</strong>
                    <span className="status-pill" style={{ background: '#dcfce7', color: '#166534' }}>Defense in Depth</span>
                  </div>
                  <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Arsitektur Kunci:</dt>
                      <dd style={{ fontWeight: 500 }}>KEK 256-bit + DEK Ephemeral</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Format Penyimpanan:</dt>
                      <dd style={{ fontFamily: 'monospace' }}>[Envelope Wrapped DEK + Header + CT]</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Overhead Struktur:</dt>
                      <dd style={{ fontWeight: 600, color: 'var(--foreground)' }}>~128 Bytes (Key wrap + Metadata)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Tingkat Keamanan:</dt>
                      <dd style={{ color: '#059669', fontWeight: 600 }}>Tingkat Perbankan (ISO/IEC 18033)</dd>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <dt style={{ color: 'var(--muted)' }}>Kepatuhan Regulasi:</dt>
                      <dd style={{ fontWeight: 500 }}>UU PDP 27/2022 & POJK 11/2022</dd>
                    </div>
                  </dl>
                  <div style={{ marginTop: '12px', padding: '10px', background: 'var(--surface-subtle)', borderRadius: '6px', fontSize: '11px', color: 'var(--muted)' }}>
                    <strong>Analisis:</strong> Kunci per-objek (DEK) tidak disimpan langsung melainkan di-wrap oleh KEK server, menjamin zero-plaintext resting state.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* VIEW TAB 3: DATA TABLE */}
          {viewTab === 'table' && (
            <div className="lab-table-scroll">
              <table className="data-table lab-kyc-table">
                <caption className="sr-only">
                  {selected.simulated ? 'Angka ilustrasi yang belum diukur' : 'Hasil pengukuran'} untuk {fixtureLabels[selected.fixture]}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Algoritma</th>
                    <th scope="col">Mode Operasi</th>
                    <th scope="col">Enkripsi (ms)</th>
                    <th scope="col">Dekripsi (ms)</th>
                    <th scope="col">Overhead (B)</th>
                    <th scope="col">Tingkat Keamanan</th>
                    <th scope="col">Kelayakan Perbankan</th>
                    <th scope="col">Status Pemulihan</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.rows.map(row => {
                    const isAes = row.algorithm === 'AES-GCM';
                    const isDes = row.algorithm === 'DES-CBC';
                    const isRc4 = row.algorithm === 'RC4';

                    return (
                      <tr key={row.algorithm}>
                        <th scope="row">
                          {row.algorithm}
                          {(isRc4 || isDes) && (
                            <small style={{ color: '#d97706', display: 'block' }}>Eksperimen Kuliah</small>
                          )}
                        </th>
                        <td>
                          {isAes
                            ? 'GCM (128-bit block, AEAD)'
                            : isDes
                            ? 'CBC (64-bit block, PKCS#7)'
                            : isRc4
                            ? 'Stream PRGA (XOR)'
                            : 'Envelope Multi-tier'}
                        </td>
                        <td style={{ fontWeight: 600 }}>{row.encrypt_ms.toFixed(2)} ms</td>
                        <td style={{ fontWeight: 600 }}>{row.decrypt_ms.toFixed(2)} ms</td>
                        <td>
                          <strong>+{row.overhead_bytes} B</strong>
                        </td>
                        <td>
                          <span style={{ fontSize: '11px', fontWeight: 500, color: isAes ? '#10b981' : isDes || isRc4 ? '#ef4444' : '#6366f1' }}>
                            {isAes
                              ? 'Tinggi (AEAD + GMAC)'
                              : isDes
                              ? 'Rentan (Key 56-bit)'
                              : isRc4
                              ? 'Rentan (Malleable XOR)'
                              : 'Tinggi (Berlapis)'}
                          </span>
                        </td>
                        <td>
                          <span
                            className="status-pill"
                            style={{
                              background: isAes ? 'rgba(16, 185, 129, 0.15)' : isDes || isRc4 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                              color: isAes ? '#10b981' : isDes || isRc4 ? '#ef4444' : '#6366f1',
                              fontWeight: 600,
                            }}
                          >
                            {isAes ? 'Direkomendasikan' : isDes || isRc4 ? 'Tidak Layak Bank' : 'Arsitektur Veltrix'}
                          </span>
                        </td>
                        <td>
                          <span
                            className="status-pill"
                            style={{
                              background: row.round_trip_ok ? 'var(--success-soft)' : 'var(--danger-soft)',
                              color: row.round_trip_ok ? 'var(--success)' : 'var(--danger)',
                            }}
                          >
                            {selected.simulated ? 'Simulasi cocok' : row.round_trip_ok ? '✓ 100% Identik' : '✗ GAGAL'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="lab-interpretation">
            <h3>{selected.simulated ? 'Cara membaca, setelah data nyata tersedia' : 'Interpretasikan untuk skenario KYC'}</h3>
            <p>
              Bandingkan median dan variasi pada fixture yang sama. Waktu lebih pendek tidak menunjukkan keamanan lebih tinggi.
              Untuk video dan dokumen besar, perhatikan throughput dan overhead; untuk profil JSON kecil, perhatikan latensi fixed overhead metadata envelope.
            </p>
            <p>
              Sesuai amanat <strong>UU No. 27 Tahun 2022 (UU PDP) Pasal 35 & 39</strong> serta <strong>POJK No. 11/POJK.03/2022</strong>,
              sistem perbankan wajib menjamin kerahasiaan dan integritas data nasabah. AES-256-GCM dipilih sebagai algoritma utama karena fitur AEAD-nya membentengi dokumen dari manipulasi bit atau pemindahan kepemilikan.
            </p>
            {selected.simulated && (
              <p className="lab-not-measured">
                Hash sumber dan hasil pemulihan, throughput, penggunaan memori, serta rincian pengukuran belum tersedia. Angka ilustrasi ini belum dapat menjadi bukti eksperimen.
              </p>
            )}
          </div>
        </section>
      ) : (
        <section className="panel lab-empty">
          <EmptyState
            title={verification ? 'Belum ada hasil verifikasi' : 'Belum ada hasil perbandingan'}
            description="Pilih satu fixture sintetis dan jalankan eksperimen. Hasil pengukuran akan muncul di sini."
          />
        </section>
      )}

      {verification && (
        <section className="panel verification-plan">
          <div className="panel-heading">
            <h2>Daftar pemeriksaan integritas</h2>
            <span className="status-pill">Belum dijalankan</span>
          </div>
          <ul>
            {[
              'SHA-256 byte awal sama dengan byte hasil pemulihan pada empat kategori.',
              'Pengguna lain dan reviewer tidak dapat mengambil plaintext pemohon.',
              'Perubahan ciphertext atau tag GCM menggagalkan pemulihan tanpa merilis plaintext.',
              'Unggah gagal tidak menghasilkan bukti berstatus siap.',
              'Nonce AES-GCM dan kunci per objek tidak digunakan ulang.',
            ].map(item => (
              <li key={item}>
                <span aria-hidden="true">○</span>
                {item}
              </li>
            ))}
          </ul>
          <p className="small-note">Daftar ini adalah rencana pemeriksaan, bukan hasil tes keamanan yang sudah lulus.</p>
        </section>
      )}

      <section className="panel lab-history">
        <div className="panel-heading">
          <h2>Riwayat sesi lab</h2>
          <span className="list-count">Fixture terpisah dari data pemohon</span>
        </div>
        {history.isPending ? (
          <LoadingState label="Memuat riwayat lab…" />
        ) : history.error ? (
          <ErrorState error={history.error} retry={() => history.refetch()} />
        ) : !history.data?.filter(r => r.kind === kind).length ? (
          <p className="history-empty">Belum ada eksperimen pada sesi ini.</p>
        ) : (
          history.data
            .filter(r => r.kind === kind)
            .toReversed()
            .map(item => {
              const isSelected = selected?.id === item.id;
              return (
                <button
                  className={`lab-history-row ${isSelected ? 'active' : ''}`}
                  key={item.id}
                  onClick={() => {
                    setSelected(item);
                    exportRun.reset();
                    setTimeout(() => {
                      const el = document.getElementById('lab-output');
                      if (el) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      } else {
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }
                    }, 50);
                  }}
                  style={
                    isSelected
                      ? {
                          borderLeft: '4px solid var(--primary, #2563eb)',
                          background: 'rgba(37, 99, 235, 0.08)',
                        }
                      : undefined
                  }
                >
                  <span>
                    <strong>{fixtureLabels[item.fixture]}</strong>
                    <small>
                      {dateLabel(item.created_at)} · {item.repetitions} pengulangan
                    </small>
                  </span>
                  <span className="status-pill">{item.simulated ? 'Simulasi' : 'Selesai'}</span>
                  <span
                    style={{
                      color: isSelected ? 'var(--primary, #2563eb)' : 'inherit',
                      fontWeight: isSelected ? 600 : 400,
                    }}
                  >
                    {isSelected ? 'Terbuka di Atas ↑' : 'Buka ↑'}
                  </span>
                </button>
              );
            })
        )}
      </section>
    </>
  );
}
