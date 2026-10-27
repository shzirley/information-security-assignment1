'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, ArrowUpRight, Check, CircleAlert, ClipboardList, Plus, Search } from 'lucide-react';
import { useState } from 'react';
import { ErrorState, EmptyState, LoadingState, PageHeading } from '@/components/ui';
import { kycApi } from '@/lib/kyc-api';
import { categories, completeness, evidenceRules, statusLabels, type Application, type CaseStatus } from '@/lib/kyc';
import { dateLabel } from '@/lib/contracts';

export function StatusPill({ status }: { status: CaseStatus }) { return <span className={`status-pill status-${status}`}>{statusLabels[status]}</span>; }
export function CaseList({ reviewer = false, dashboard = false }: { reviewer?: boolean; dashboard?: boolean }) {
  const query = useQuery({ queryKey: ['applications'], queryFn: kycApi.applications });
  const [search, setSearch] = useState(''); const [status, setStatus] = useState('all');
  const title = reviewer ? 'Antrean tinjauan' : dashboard ? 'Pengajuanmu, terpantau.' : 'Pengajuan saya';
  const description = reviewer ? 'Tinjau kelengkapan metadata pengajuan yang ditugaskan kepadamu.' : dashboard ? 'Lanjutkan langkah berikutnya dari satu tempat.' : 'Kelola draf, lengkapi revisi, dan ikuti hasil peninjauan.';
  const items = query.data?.items ?? [];
  const filtered = items.filter(c => (status === 'all' || c.status === status) && c.reference.toLowerCase().includes(search.toLowerCase()));
  const attention = items.find(c => c.status === 'NEEDS_REVISION') ?? items.find(c => c.status === 'DRAFT');
  return <><PageHeading index={reviewer ? 'Tinjauan metadata' : 'BankKYC'} title={title} description={description} action={!reviewer && <Link href="/applicant/applications/new" className="button"><Plus size={17} aria-hidden="true" />Pengajuan baru</Link>} />
    {reviewer && <div className="scope-note"><ShieldScope /><p><strong>Akses metadata saja</strong>Isi profil, nama berkas, preview, dan unduhan pemohon tidak tersedia. Tinjau kelengkapan kategori pada pengajuan yang ditugaskan kepadamu.</p></div>}
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} retry={() => query.refetch()} /> : <>
      {dashboard && <>
        <div className="case-summary"><div><span>Total pengajuan</span><strong>{items.length.toString().padStart(2, '0')}</strong></div><div><span>Butuh tindakanmu</span><strong>{items.filter(c => c.status === 'DRAFT' || c.status === 'NEEDS_REVISION').length.toString().padStart(2, '0')}</strong></div><div><span>Dalam proses</span><strong>{items.filter(c => ['SUBMITTED', 'RESUBMITTED', 'UNDER_REVIEW'].includes(c.status)).length.toString().padStart(2, '0')}</strong></div><div><span>Selesai</span><strong>{items.filter(c => ['ACCEPTED_DEMO', 'REJECTED_DEMO', 'WITHDRAWN'].includes(c.status)).length.toString().padStart(2, '0')}</strong></div></div>
        {attention && <div className="next-action"><div className="next-action-icon"><CircleAlert size={24} aria-hidden="true" /></div><div><span className="section-index">Langkah berikutnya / {attention.reference}</span><h2>{attention.status === 'NEEDS_REVISION' ? 'Ada bukti yang perlu kamu perbarui.' : 'Drafmu menunggu dilengkapi.'}</h2><p>{attention.status === 'NEEDS_REVISION' ? attention.revision_note : 'Lengkapi profil dan tiga jenis berkas dummy sebelum dikirim.'}</p></div><Link href={`/applicant/applications/${attention.id}/edit`} className="button button-secondary">{attention.status === 'NEEDS_REVISION' ? 'Perbaiki pengajuan' : 'Lanjutkan draf'}<ArrowRight size={17} aria-hidden="true" /></Link></div>}
      </>}
      <div className={dashboard ? 'case-dashboard-grid' : ''}><section className="panel case-list-panel" aria-label={reviewer ? 'Pengajuan ditugaskan' : 'Daftar pengajuan'}>
        <div className="panel-heading"><div><span className="section-index">{reviewer ? 'Ditugaskan kepadamu' : 'Berkas pengajuan'}</span><h2>{dashboard ? 'Aktivitas pengajuan' : reviewer ? 'Daftar tinjauan' : 'Semua pengajuan'}</h2></div><span className="list-count">{items.length} pengajuan</span></div>
        <div className="case-filters"><div className="search-control"><Search size={18} aria-hidden="true" /><label htmlFor="case-search" className="sr-only">Cari nomor pengajuan</label><input id="case-search" placeholder="Cari nomor pengajuan…" value={search} onChange={e => setSearch(e.target.value)} /></div><label className="sr-only" htmlFor="case-status">Filter status</label><select id="case-status" value={status} onChange={e => setStatus(e.target.value)}><option value="all">Semua status</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
        {filtered.length ? <div className="case-rows">{filtered.map(application => <CaseRow key={application.id} application={application} reviewer={reviewer} />)}</div> : <EmptyState title={items.length ? 'Tidak ada yang cocok' : reviewer ? 'Antrean masih kosong' : 'Belum ada pengajuan'} description={items.length ? 'Coba kata pencarian atau status yang berbeda.' : reviewer ? 'Pengajuan muncul setelah admin menugaskannya kepadamu.' : 'Siapkan bukti dummy dan buat pengajuan pertamamu.'} action={!items.length && !reviewer ? <Link href="/applicant/applications/new" className="button">Buat pengajuan</Link> : undefined} />}
        <div className="case-list-foot">{filtered.length} dari {items.length} pengajuan · Nomor pengajuan tidak memuat identitas pribadi</div>
      </section>{dashboard && <aside className="case-preparation"><span className="section-index">Sebelum mulai</span><h2>Siapkan empat kategori bukti.</h2><ul><li><Check size={16} aria-hidden="true" /><span>Profil dan kontak fiktif</span></li>{categories.map(c => <li key={c}><Check size={16} aria-hidden="true" /><span>{evidenceRules[c].label}<small>{evidenceRules[c].size} maks.</small></span></li>)}</ul><p>Semua data harus sintetis. Hindari KTP, video wajah, atau dokumen asli.</p><Link href="/applicant/applications/new" className="text-link">Mulai pengajuan <ArrowUpRight size={17} aria-hidden="true" /></Link></aside>}</div>
    </>}
  </>;
}
function ShieldScope() { return <ClipboardList size={23} aria-hidden="true" />; }
function CaseRow({ application, reviewer }: { application: Application; reviewer: boolean }) {
  return <Link className="case-row" href={`/${reviewer ? 'reviewer' : 'applicant'}/applications/${application.id}`}>
    <div className="case-row-mark"><ClipboardList size={21} aria-hidden="true" /></div><div className="case-row-title"><strong>{application.reference}</strong><span>Diperbarui {dateLabel(application.updated_at)} · Versi {application.version}</span></div><div className="case-row-completeness"><span>{completeness(application)}/4 kategori</span><div><span style={{ width: `${completeness(application) * 25}%` }} /></div></div><StatusPill status={application.status} /><ArrowUpRight size={19} aria-label="Buka detail" />
  </Link>;
}
