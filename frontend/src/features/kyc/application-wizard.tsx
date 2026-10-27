'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, FileUp, LockKeyhole } from 'lucide-react';
import { Button, ErrorState, LoadingState, Modal, PageHeading } from '@/components/ui';
import { useToast } from '@/components/providers';
import { kycApi } from '@/lib/kyc-api';
import { isMock } from '@/lib/contracts';
import { blankProfile, categories, completeness, editable, evidenceFor, evidenceRules, fileError, profileErrors, profileLabels, syntheticProfile, type ApplicantProfile, type Application, type EvidenceCategory } from '@/lib/kyc';
import { StatusPill } from './case-list';

const steps = ['Data pribadi', 'Scan identitas', 'Dokumen', 'Video', 'Tinjau & kirim'];
export function NewApplication() {
  const router = useRouter(); const client = useQueryClient();
  const create = useMutation({ mutationFn: kycApi.create, onSuccess: application => { client.setQueryData(['application', application.id], application); client.invalidateQueries({ queryKey: ['applications'] }); router.push(`/applicant/applications/${application.id}/edit`); } });
  return <><PageHeading index="Pengajuan baru" title="Mulai dari bukti yang tepat." description="Siapkan profil dan dokumen untuk peninjauan pengajuanmu." /><section className="panel new-application"><div className="new-application-intro"><LockKeyhole size={32} aria-hidden="true" /><h2>Siapkan empat kategori bukti.</h2><p>Profil pribadi, scan identitas, dokumen administrasi, dan video verifikasi. Periksa setiap langkah sebelum pengiriman.</p></div><ol className="new-checklist">{steps.map((step, i) => <li key={step}><span>0{i + 1}</span><div><strong>{step}</strong><p>{i === 0 ? 'Profil, pekerjaan, dan tujuan pengajuan.' : i === 4 ? 'Periksa kelengkapan dan konfirmasi data sintetis.' : evidenceRules[categories[i - 1]].description}</p></div></li>)}</ol><div className="inline-note">Gunakan data uji dan simpan tiap langkah sebelum berpindah.{isMock && ' Data belum dienkripsi, tersimpan sementara di browser, dan hilang saat halaman dimuat ulang.'}</div>{create.error && <ErrorState error={create.error} />}<div className="wizard-actions"><Link href="/applicant/applications" className="text-link">Kembali ke pengajuan</Link><Button busy={create.isPending} onClick={() => create.mutate()}>Buat draf & mulai <ArrowRight size={17} aria-hidden="true" /></Button></div></section></>;
}
export function ApplicationWizard({ id }: { id: string }) {
  const query = useQuery({ queryKey: ['application', id], queryFn: () => kycApi.application(id) });
  if (query.isPending) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} retry={() => query.refetch()} />;
  if (!editable(query.data.status)) return <section className="panel access-denied"><h1>Pengajuan terkunci</h1><p>Perubahan hanya tersedia saat draf atau perlu revisi.</p><Link href={`/applicant/applications/${id}`} className="button">Lihat pengajuan</Link></section>;
  return <WizardForm application={query.data} />;
}
function WizardForm({ application }: { application: Application }) {
  const id = application.id; const router = useRouter(); const client = useQueryClient(); const toast = useToast();
  const [step, setStep] = useState(0); const [ack, setAck] = useState(false); const [confirm, setConfirm] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const onStep = (index: number) => { setStep(index); window.setTimeout(() => heading.current?.focus(), 0); };
  const commit = (updated: Application) => { client.setQueryData(['application', id], updated); client.invalidateQueries({ queryKey: ['applications'] }); };
  const submit = useMutation({ mutationFn: () => kycApi.action(id, application.status === 'NEEDS_REVISION' ? 'resubmit' : 'submit', application.version, undefined, ack), onSuccess: updated => { commit(updated); toast('Pengajuan berhasil dikirim.'); router.push(`/applicant/applications/${id}`); } });
  return <><Link href={`/applicant/applications/${id}`} className="text-link back-link"><ArrowLeft size={16} aria-hidden="true" />Detail pengajuan</Link><PageHeading index={application.reference} title={application.status === 'NEEDS_REVISION' ? 'Perbarui bukti pengajuan.' : 'Lengkapi pengajuanmu.'} description="Lima langkah, empat kategori bukti. Simpan setiap langkah sebelum melanjutkan." action={<StatusPill status={application.status} />} />
    {application.status === 'NEEDS_REVISION' && <div className="revision-banner"><strong>Catatan revisi</strong><p>{application.revision_note}</p><small>Unggah ulang sebagai versi baru. Versi sebelumnya tetap tersimpan dalam sesi.</small></div>}
    <ol className="wizard-stepper" aria-label="Langkah pengajuan">{steps.map((label, i) => <li key={label} className={i === step ? 'current' : i < step ? 'done' : ''} aria-current={i === step ? 'step' : undefined}><span>{i < step ? <Check size={16} aria-hidden="true" /> : i + 1}</span><strong>{label}</strong></li>)}</ol>
    <section className="panel wizard-panel"><div className="wizard-panel-heading"><span className="section-index">Langkah {step + 1} dari 5</span><h2 ref={heading} tabIndex={-1}>{steps[step]}</h2></div>
      {step === 0 ? <ProfileStep key="profile" application={application} onSaved={updated => { commit(updated); onStep(1); }} /> : step < 4 ? <UploadStep key={categories[step - 1]} category={categories[step - 1]} application={application} onSaved={commit} onNext={() => onStep(step + 1)} onBack={() => onStep(step - 1)} /> : <div className="wizard-body"><p>Pastikan semua bukti milik tokoh fiktif dan sudah sesuai catatan revisi, bila ada.</p><div className="review-checklist"><div><span>Data pribadi</span><strong>{application.personal_data_complete ? 'Lengkap' : 'Belum lengkap'}</strong></div>{categories.map(category => { const item = evidenceFor(application, category); return <div key={category}><span>{evidenceRules[category].label}</span><strong>{item ? `Versi ${item.version} tersedia` : 'Belum diunggah'}</strong></div>; })}</div><p className="small-note">{completeness(application)} dari 4 kategori lengkap. Setelah dikirim, data terkunci sampai reviewer meminta revisi.</p><label className="checkbox-field"><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} /><span>Saya memastikan semua data dan bukti sintetis, serta memahami ini bukan pembukaan rekening bank.</span></label>{completeness(application) !== 4 && <p className="form-error" role="status">Lengkapi semua kategori pada langkah sebelumnya agar dapat mengirim.</p>}<div className="wizard-actions"><Button variant="secondary" onClick={() => onStep(3)}><ArrowLeft size={16} aria-hidden="true" />Kembali</Button><Button disabled={completeness(application) !== 4 || !ack} onClick={() => setConfirm(true)}>{application.status === 'NEEDS_REVISION' ? 'Kirim ulang pengajuan' : 'Kirim pengajuan'}<ArrowRight size={17} aria-hidden="true" /></Button></div></div>}
    </section><Modal open={confirm} onOpenChange={open => { if (!submit.isPending) setConfirm(open); }} title="Kirim pengajuan ini?" description="Bukti akan dikunci untuk tinjauan metadata. Kamu tetap dapat mengambil berkas milikmu."><p className="small-note">{application.reference} · {completeness(application)}/4 kategori lengkap</p>{submit.error && <ErrorState error={submit.error} retry={() => queryRefresh(client, id)} />}<div className="modal-actions"><Button variant="secondary" disabled={submit.isPending} onClick={() => setConfirm(false)}>Periksa lagi</Button><Button busy={submit.isPending} onClick={() => submit.mutate()}>Ya, kirim pengajuan</Button></div></Modal>
  </>;
}
function queryRefresh(client: ReturnType<typeof useQueryClient>, id: string) { client.invalidateQueries({ queryKey: ['application', id] }); }
function useUnsavedChanges(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    const unload = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    const navigate = (e: MouseEvent) => {
      if (!(e.target instanceof Element) || !e.target.closest('a[href]')) return;
      if (!window.confirm('Perubahan belum disimpan. Tinggalkan langkah ini?')) { e.preventDefault(); e.stopPropagation(); }
    };
    window.addEventListener('beforeunload', unload); document.addEventListener('click', navigate, true);
    return () => { window.removeEventListener('beforeunload', unload); document.removeEventListener('click', navigate, true); };
  }, [dirty]);
}
function ProfileStep({ application, onSaved }: { application: Application; onSaved: (updated: Application) => void }) {
  const profile = useQuery({ queryKey: ['profile', application.id], queryFn: () => kycApi.profile(application.id), gcTime: 0, staleTime: 0 });
  const [fields, setFields] = useState<ApplicantProfile | null>(null); const [errors, setErrors] = useState<Partial<Record<keyof ApplicantProfile, string>>>({});
  const values = fields ?? profile.data?.profile ?? blankProfile;
  const save = useMutation({ mutationFn: () => kycApi.saveProfile(application.id, values, application.version), onSuccess: updated => { setFields(null); onSaved(updated); } });
  const errorSummary = useRef<HTMLDivElement>(null);
  useUnsavedChanges(fields !== null);
  if (profile.isPending) return <LoadingState />;
  if (profile.isError) return <ErrorState error={profile.error} retry={() => profile.refetch()} />;
  return <form noValidate className="wizard-body" onSubmit={e => { e.preventDefault(); const invalid = profileErrors(values); setErrors(invalid); if (Object.keys(invalid).length) { window.setTimeout(() => errorSummary.current?.focus(), 0); return; } save.mutate(); }}>
    <div className="form-top-note"><p>Gunakan informasi fiktif. Email wajib memakai domain example.</p>{isMock && <Button variant="ghost" onClick={() => { setFields({ ...syntheticProfile }); setErrors({}); }}>Isi contoh dummy</Button>}</div>
    {Object.keys(errors).length > 0 && <div ref={errorSummary} tabIndex={-1} className="form-error" role="alert">Periksa {Object.keys(errors).length} kolom yang ditandai sebelum melanjutkan.</div>}
    <div className="form-grid">{(Object.keys(profileLabels) as (keyof ApplicantProfile)[]).map(key => <div className={`field ${key === 'address' ? 'field-wide' : ''}`} key={key}><label htmlFor={`profile-${key}`}>{profileLabels[key]}</label><input id={`profile-${key}`} type={key === 'date_of_birth' ? 'date' : key === 'email' ? 'email' : key === 'phone' ? 'tel' : 'text'} maxLength={500} value={values[key]} autoComplete="off" required aria-invalid={!!errors[key]} aria-describedby={errors[key] ? `${key}-error` : undefined} onChange={e => setFields({ ...values, [key]: e.target.value })} /><p id={`${key}-error`} className="field-error">{errors[key]}</p></div>)}</div>{save.error && <ErrorState error={save.error} />}<div className="wizard-actions"><span className="small-note">Tersimpan setelah menekan tombol di samping.</span><Button type="submit" busy={save.isPending}>Simpan & lanjutkan <ArrowRight size={17} aria-hidden="true" /></Button></div>
  </form>;
}
function UploadStep({ category, application, onSaved, onNext, onBack }: { category: EvidenceCategory; application: Application; onSaved: (updated: Application) => void; onNext: () => void; onBack: () => void }) {
  const [file, setFile] = useState<File | null>(null); const [error, setError] = useState('');
  const current = evidenceFor(application, category); const rule = evidenceRules[category]; const input = useRef<HTMLInputElement>(null);
  const upload = useMutation({ mutationFn: () => kycApi.upload(application.id, category, file!, application.version), onSuccess: updated => { setFile(null); if (input.current) input.current.value = ''; onSaved(updated); } });
  useUnsavedChanges(file !== null);
  return <div className="wizard-body"><p>{rule.description}</p><div className="upload-zone"><FileUp size={35} strokeWidth={1.5} aria-hidden="true" /><strong>{current ? 'Unggah versi baru' : 'Pilih berkas dummy'}</strong><p>{rule.extensions.join(' / ').toUpperCase()} · Maks. {rule.size}</p><label htmlFor={`upload-${category}`} className="sr-only">Berkas {rule.label}</label><input ref={input} id={`upload-${category}`} type="file" accept={rule.accept} aria-describedby="upload-help upload-error" aria-invalid={!!error} disabled={upload.isPending} onChange={e => { const selected = e.target.files?.[0]; const invalid = selected ? fileError(selected, category) : ''; setError(invalid); setFile(selected && !invalid ? selected : null); }} /><span id="upload-help" className="small-note">Pemilihan file belum menyimpan. Tekan unggah untuk menyimpan langkah ini.</span></div>{error && <p id="upload-error" className="form-error" role="alert">{error}</p>}{file && <div className="upload-pending"><span>{file.name}</span><Button busy={upload.isPending} onClick={() => upload.mutate()}>Unggah {current ? `versi ${current.version + 1}` : 'berkas'}</Button></div>}{upload.error && <ErrorState error={upload.error} />}{current && <div className="upload-current"><Check size={20} aria-hidden="true" /><div><strong>{current.display_name}</strong><p>Versi {current.version} tersimpan dalam sesi · Validasi format awal{isMock ? ', bukan bukti enkripsi' : ''}</p></div></div>}<div className="wizard-actions"><Button variant="secondary" disabled={upload.isPending || !!file} onClick={onBack}><ArrowLeft size={16} aria-hidden="true" />Kembali</Button><Button disabled={!current || upload.isPending || !!file} onClick={onNext}>Lanjutkan <ArrowRight size={16} aria-hidden="true" /></Button></div><p className="small-note">Berkas baru menjadi versi tambahan. Versi lama tetap tersedia pada detail pengajuan.</p></div>;
}
