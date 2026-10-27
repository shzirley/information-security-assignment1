'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { UsersRound } from 'lucide-react';
import { Button, EmptyState, ErrorState, LoadingState, Modal, PageHeading } from '@/components/ui';
import { useToast } from '@/components/providers';
import { kycApi } from '@/lib/kyc-api';
import type { Application } from '@/lib/kyc';
import { StatusPill } from './case-list';

export function Assignments() {
  const query = useQuery({ queryKey: ['assignments'], queryFn: kycApi.assignments });
  const [selected, setSelected] = useState<Application | null>(null); const [reviewerId, setReviewerId] = useState('');
  const client = useQueryClient(); const toast = useToast();
  const assign = useMutation({ mutationFn: () => kycApi.assign(selected!.id, reviewerId, selected!.version), onSuccess: () => { client.invalidateQueries({ queryKey: ['assignments'] }); setSelected(null); toast('Penugasan reviewer disimpan.'); } });
  return <><PageHeading index="Operasional" title="Penugasan reviewer" description="Hubungkan pengajuan dengan reviewer sebelum tinjauan dimulai." /><div className="scope-note"><UsersRound size={23} aria-hidden="true" /><p><strong>Administrasi tanpa membuka bukti</strong>Admin mengatur penugasan. Profil, nama file, dan isi bukti tidak tersedia pada halaman ini.</p></div>{query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} retry={() => query.refetch()} /> : <section className="panel"><div className="panel-heading"><h2>Pengajuan masuk</h2><span className="list-count">{query.data.items.length} pengajuan</span></div>{query.data.items.length ? query.data.items.map(application => <div key={application.id} className="assignment-row"><div><strong>{application.reference}</strong><p>{query.data.reviewers.find(r => r.id === application.assigned_reviewer_id)?.display_name ?? 'Belum ditugaskan'}</p></div><StatusPill status={application.status} /><Button variant="secondary" disabled={!['SUBMITTED', 'RESUBMITTED'].includes(application.status)} onClick={() => { setSelected(application); setReviewerId(application.assigned_reviewer_id ?? ''); assign.reset(); }}>{application.assigned_reviewer_id ? 'Ubah reviewer' : 'Tugaskan reviewer'}<span className="sr-only"> {application.reference}</span></Button></div>) : <EmptyState title="Belum ada pengajuan masuk" description="Draf pemohon akan muncul di sini setelah dikirim." />}<p className="assignment-note">Penugasan terkunci setelah tinjauan dimulai. Keputusan peninjauan ditentukan reviewer.</p></section>}<Modal open={!!selected} onOpenChange={open => { if (!open && !assign.isPending) setSelected(null); }} title="Tugaskan reviewer" description={selected?.reference ?? 'Pilih penanggung jawab tinjauan metadata.'}><div className="field"><label htmlFor="assignment-reviewer">Reviewer</label><select id="assignment-reviewer" value={reviewerId} onChange={e => setReviewerId(e.target.value)}><option value="">Pilih reviewer</option>{query.data?.reviewers.map(r => <option key={r.id} value={r.id}>{r.display_name}</option>)}</select></div>{assign.error && <ErrorState error={assign.error} retry={() => query.refetch()} />}<div className="modal-actions"><Button variant="secondary" disabled={assign.isPending} onClick={() => setSelected(null)}>Batal</Button><Button disabled={!reviewerId} busy={assign.isPending} onClick={() => assign.mutate()}>Simpan penugasan</Button></div></Modal></>;
}
