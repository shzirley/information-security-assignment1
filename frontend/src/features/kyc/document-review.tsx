'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, ErrorState, Modal } from '@/components/ui';
import { ApiError } from '@/lib/api';
import { kycApi } from '@/lib/kyc-api';
import {
  categories, evidenceFor, profileLabels, type Application, type DocumentAnalysis,
  type Evidence, type EvidenceCheck,
} from '@/lib/kyc';

const checkLabels = {
  readable: 'Terbaca',
  correct_document_type: 'Jenis dokumen sesuai',
  matches_applicant_form: 'Sesuai profil pemohon',
  needs_clarification: 'Perlu klarifikasi',
} as const;
const checkKeys = Object.keys(checkLabels) as (keyof typeof checkLabels)[];
const reasonLabels = {
  VERIFIED: 'Sesuai',
  UNREADABLE: 'Tidak terbaca',
  WRONG_DOCUMENT_TYPE: 'Jenis dokumen keliru',
  MISMATCH: 'Data berbeda',
  CLARIFICATION: 'Perlu klarifikasi',
};
const documentLabel = (item: Evidence) => ({
  identity: 'KTP dummy', document: 'Formulir pembukaan rekening', video: 'Video verifikasi',
})[item.category] + ' · v' + item.version;

function initialCheck(item: Evidence): EvidenceCheck {
  return {
    evidence_id: item.id, evidence_version: item.version, readable: false,
    correct_document_type: false, matches_applicant_form: false, needs_clarification: false,
    reason_code: 'CLARIFICATION', note: '',
  };
}

export function DocumentReview({ application, onSaved }: { application: Application; onSaved: () => void }) {
  const { id, version, status } = application;
  const items = categories.map(category => evidenceFor(application, category)).filter(Boolean);
  const optional = application.evidence.filter(item => item.document_type === 'kk_optional').sort((a, b) => b.version - a.version)[0];
  const [draft, setDraft] = useState<Record<string, EvidenceCheck>>({});
  const [selected, setSelected] = useState<Evidence | null>(null);
  const [showProfile, setShowProfile] = useState(false);
  const profile = useQuery({
    queryKey: ['review-profile', id, version], queryFn: ({ signal }) => kycApi.reviewProfile(id, signal),
    enabled: showProfile, gcTime: 0, retry: false,
  });
  const saved = useQuery({
    queryKey: ['review-checks', id, version], queryFn: ({ signal }) => kycApi.reviewChecks(id, signal),
    enabled: status === 'UNDER_REVIEW', gcTime: 0, retry: false,
  });
  function checkFor(item: Evidence) {
    return draft[item.id] ?? saved.data?.review?.checks.find(check => check.evidence_id === item.id) ?? initialCheck(item);
  }
  function change(item: Evidence, patch: Partial<EvidenceCheck>) {
    setDraft(current => ({ ...current, [item.id]: { ...checkFor(item), ...patch } }));
  }
  const save = useMutation({
    mutationFn: () => kycApi.saveReviewChecks(id, version, items.map(checkFor)),
    onSuccess: onSaved,
  });
  const hasIssues = items.some(item => checkFor(item).reason_code !== 'VERIFIED');
  return <section className="panel">
    <div className="panel-heading"><h2>Pemeriksaan dokumen</h2></div>
    <Button variant="secondary" onClick={() => setShowProfile(open => !open)}>{showProfile ? 'Tutup profil' : 'Lihat profil pemohon'}</Button>
    {showProfile && profile.isPending && <p role="status">Memuat profil…</p>}
    {showProfile && profile.error && <ErrorState error={profile.error} />}
    {showProfile && profile.data && <dl className="profile-reveal">
      {Object.entries(profile.data.profile).map(([field, value]) => <div key={field}><dt>{profileLabels[field as keyof typeof profileLabels]}</dt><dd>{value}</dd></div>)}
    </dl>}
    {items.map(item => {
      const check = checkFor(item);
      return <fieldset className="field document-check" key={item.id}>
        <legend>{documentLabel(item)}</legend>
        <Button variant="secondary" type="button" onClick={() => setSelected(item)}>Buka pratinjau</Button>
        {status === 'UNDER_REVIEW' && <>
          {checkKeys.map(key => <label key={key}>
            <input type="checkbox" checked={check[key]} onChange={event => change(item, { [key]: event.target.checked })} /> {checkLabels[key]}
          </label>)}
          <label>Kode alasan <select value={check.reason_code} onChange={event => change(item, { reason_code: event.target.value as EvidenceCheck['reason_code'] })}>
            {Object.entries(reasonLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select></label>
          <label>Catatan untuk bukti <textarea rows={2} maxLength={500} value={check.note ?? ''} onChange={event => change(item, { note: event.target.value })} /></label>
        </>}
      </fieldset>;
    })}
    {optional && <div className="field document-check"><strong>KK opsional · v{optional.version}</strong>
      <Button variant="secondary" onClick={() => setSelected(optional)}>Buka pratinjau KK</Button></div>}
    {status === 'UNDER_REVIEW' && <>
      {saved.error && <ErrorState error={saved.error} />}
      {Object.keys(draft).length > 0 ? <p>Perubahan checklist belum disimpan.</p>
        : saved.data?.review && <p role="status">{hasIssues ? 'Checklist tersimpan. Periksa alasan sebelum meminta revisi atau menolak.' : 'Checklist tersimpan.'}</p>}
      {save.error && <ErrorState error={save.error} />}
      <Button busy={save.isPending} disabled={saved.isPending} onClick={() => save.mutate()}>Simpan checklist</Button>
    </>}
    {selected && <PrivatePreview id={id} item={selected} close={() => setSelected(null)} />}
  </section>;
}

function PrivatePreview({ id, item, close }: { id: string; item: Evidence; close: () => void }) {
  const [url, setUrl] = useState('');
  const [page, setPage] = useState(1);
  const isPdf = item.mime_type === 'application/pdf';
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [analysisError, setAnalysisError] = useState<Error | null>(null);
  const [running, setRunning] = useState(false);
  const preview = useQuery({
    queryKey: ['review-preview', id, item.id],
    queryFn: ({ signal }) => kycApi.reviewPreview(id, item.id, signal),
    enabled: !isPdf, gcTime: 0, retry: false,
  });
  const pdf = useQuery({
    queryKey: ['review-pdf', id, item.id, page],
    queryFn: ({ signal }) => kycApi.reviewPdfPage(id, item.id, page, signal),
    enabled: isPdf, gcTime: 0, retry: false,
  });
  const supportsAnalysis = item.category !== 'video' && item.document_type !== 'kk_optional';
  const stored = useQuery({
    queryKey: ['review-analysis', id, item.id],
    queryFn: async ({ signal }) => {
      try { return await kycApi.analysis(id, item.id, signal); }
      catch (error) { if (error instanceof ApiError && error.code === 'ANALYSIS_NOT_FOUND') return null; throw error; }
    },
    enabled: supportsAnalysis, gcTime: 0, retry: false,
  });
  useEffect(() => {
    if (!preview.data) return;
    if (preview.data.type.startsWith('text/plain')) {
      let active = true;
      void preview.data.text().then(value => { if (active) setText(value); });
      return () => { active = false; };
    }
    const source = URL.createObjectURL(preview.data);
    setUrl(source);
    return () => URL.revokeObjectURL(source);
  }, [preview.data]);
  const result = analysis ?? stored.data;
  async function analyze() {
    setAnalysisError(null);
    setRunning(true);
    try { setAnalysis(await kycApi.analyze(id, item.id)); }
    catch (error) { if (error instanceof Error) setAnalysisError(error); }
    finally { setRunning(false); }
  }
  return <Modal open description="Bukti sintetis dari pengajuan yang ditugaskan kepadamu." onOpenChange={open => { if (!open) close(); }} title={item.document_type === 'kk_optional' ? 'KK opsional' : documentLabel(item)}>
    {(isPdf ? pdf.isPending : preview.isPending) && <p role="status">Memuat pratinjau…</p>}
    {(preview.error ?? pdf.error) && <ErrorState error={preview.error ?? pdf.error} />}
    <div className="evidence-preview">
      {preview.data?.type.startsWith('text/plain') && <pre className="document-review-text">{text || 'Teks tidak tersedia.'}</pre>}
      {pdf.data && <>
        <img src={`data:image/png;base64,${pdf.data.image_base64}`} alt={`Halaman PDF ${pdf.data.page}`} />
        <div className="modal-actions">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Sebelumnya</Button>
          <span>{pdf.data.page}/{pdf.data.pages}</span>
          <Button variant="secondary" disabled={page >= pdf.data.pages} onClick={() => setPage(page + 1)}>Berikutnya</Button>
        </div>
      </>}
      {url && (item.mime_type === 'video/mp4' ? <video src={url} controls playsInline aria-label="Video verifikasi dummy" />
        : <img src={url} alt="Dokumen identitas dummy" />)}
    </div>
    {supportsAnalysis && <>
      <Button variant="secondary" busy={running} onClick={() => void analyze()}>Jalankan analisis</Button>
      {(analysisError ?? stored.error) && <ErrorState error={analysisError ?? stored.error} />}
      {result && <section className="document-check" aria-label="Hasil analisis">
        <p>{result.error ?? `${result.engine} · ${result.model_version} · ${new Date(result.processed_at).toLocaleString('id-ID')}`}</p>
        {result.checks.map(check => <dl key={check.field}>
          <dt>{profileLabels[check.field as keyof typeof profileLabels] ?? check.field} · {check.result}</dt>
          <dd>Profil: {check.submitted_value ?? '—'}</dd>
          <dd>Dokumen: {check.extracted_value ?? '—'}</dd>
        </dl>)}
      </section>}
    </>}
    <div className="modal-actions"><Button onClick={close}>Tutup pratinjau</Button></div>
  </Modal>;
}
