import type { Role, User } from './contracts';

export const statusLabels = {
  DRAFT: 'Draf', SUBMITTED: 'Terkirim', UNDER_REVIEW: 'Dalam tinjauan',
  NEEDS_REVISION: 'Perlu revisi', RESUBMITTED: 'Dikirim ulang',
  ACCEPTED_DEMO: 'Diterima', REJECTED_DEMO: 'Ditolak', WITHDRAWN: 'Ditarik',
} as const;
export type CaseStatus = keyof typeof statusLabels;
export type EvidenceCategory = 'identity' | 'document' | 'video';
export const evidenceRules = {
  identity: { label: 'Scan identitas', description: 'Kartu identitas sintetis bertanda DUMMY.', extensions: ['png', 'jpg', 'jpeg', 'pdf'], accept: '.png,.jpg,.jpeg,.pdf', max: 5 * 1024 ** 2, size: '5 MiB' },
  document: { label: 'Dokumen administrasi', description: 'Formulir pembukaan rekening atau surat pekerjaan fiktif.', extensions: ['pdf', 'docx'], accept: '.pdf,.docx', max: 10 * 1024 ** 2, size: '10 MiB' },
  video: { label: 'Video verifikasi', description: 'Video simulasi 10–30 detik tanpa identitas asli. Tidak ada pemeriksaan biometrik.', extensions: ['mp4'], accept: '.mp4', max: 30 * 1024 ** 2, size: '30 MiB' },
} satisfies Record<EvidenceCategory, { label: string; description: string; extensions: string[]; accept: string; max: number; size: string }>;
export const categories = Object.keys(evidenceRules) as EvidenceCategory[];
export const roleLabels: Record<Role, string> = { applicant: 'Pemohon', reviewer: 'Reviewer', admin: 'Admin operasional', evaluator: 'Evaluator' };
export const roleHome: Record<Role, string> = { applicant: '/applicant/dashboard', reviewer: '/reviewer/queue', admin: '/admin/assignments', evaluator: '/lab/benchmark' };
export interface ApplicantProfile {
  full_name: string; identity_number: string; date_of_birth: string;
  email: string; phone: string; address: string; occupation: string; account_purpose: string;
}
export const blankProfile: ApplicantProfile = { full_name: '', identity_number: '', date_of_birth: '', email: '', phone: '', address: '', occupation: '', account_purpose: '' };
export const profileLabels: Record<keyof ApplicantProfile, string> = {
  full_name: 'Nama lengkap fiktif', identity_number: 'Nomor identitas dummy', date_of_birth: 'Tanggal lahir fiktif',
  email: 'Email contoh', phone: 'Nomor telepon dummy', address: 'Alamat fiktif', occupation: 'Pekerjaan fiktif', account_purpose: 'Tujuan pembukaan rekening',
};
export const syntheticProfile: ApplicantProfile = {
  full_name: 'Nara Contoh', identity_number: 'DUMMY-2026-001', date_of_birth: '2000-01-15',
  email: 'nara@example.com', phone: '080000000001', address: 'Jalan Simulasi 12, Kota Contoh',
  occupation: 'Desainer fiktif', account_purpose: 'Tabungan pribadi (simulasi)',
};
export interface Evidence {
  id: string; category: EvidenceCategory; version: number; original_bytes: number;
  mime_type: string; created_at: string; validation: 'format_checked'; display_name?: string;
}
export interface CaseEvent { id: string; at: string; action: string; actor_role: Role; note?: string }
export interface Application {
  id: string; reference: string; status: CaseStatus; version: number; created_at: string; updated_at: string;
  personal_data_complete: boolean; evidence: Evidence[]; events: CaseEvent[];
  revision_note?: string; assigned_reviewer_id?: string; synthetic_acknowledged: boolean;
}
export interface ProfileResponse { profile: ApplicantProfile | null }
export interface CaseList { items: Application[]; total: number }
export interface AssignmentList { items: Application[]; reviewers: Pick<User, 'id' | 'display_name'>[] }
export type CaseAction = 'submit' | 'resubmit' | 'withdraw' | 'start-review' | 'request-revision' | 'accept' | 'reject';
export interface LabRun {
  id: string; kind: 'benchmark' | 'verification'; fixture: string; repetitions: number; warmups: number;
  status: 'completed'; simulated: boolean; created_at: string;
  rows: Array<{ algorithm: string; encrypt_ms: number; decrypt_ms: number; iqr_ms: number; overhead_bytes: number; round_trip_ok: boolean }>;
}
export const editable = (status: CaseStatus) => status === 'DRAFT' || status === 'NEEDS_REVISION';
export const evidenceFor = (application: Application, category: EvidenceCategory) => application.evidence.filter(e => e.category === category).sort((a, b) => b.version - a.version)[0];
export const completeness = (application: Application) => Number(application.personal_data_complete) + categories.filter(c => evidenceFor(application, c)).length;
export function profileErrors(profile: ApplicantProfile): Partial<Record<keyof ApplicantProfile, string>> {
  const errors: Partial<Record<keyof ApplicantProfile, string>> = {};
  for (const key of Object.keys(profileLabels) as (keyof ApplicantProfile)[]) if (!profile[key].trim()) errors[key] = 'Wajib diisi menggunakan data fiktif.';
  if (profile.identity_number && !/^DUMMY-[A-Z0-9-]{3,40}$/i.test(profile.identity_number)) errors.identity_number = 'Gunakan awalan DUMMY-, misalnya DUMMY-2026-001.';
  if (profile.email && !/^[^@\s]+@example\.(com|org|net)$/.test(profile.email)) errors.email = 'Gunakan alamat @example.com, @example.org, atau @example.net.';
  if (profile.phone && !/^0800\d{6,10}$/.test(profile.phone)) errors.phone = 'Gunakan nomor dummy berawalan 0800 dengan 10–14 digit.';
  if (profile.date_of_birth && (!/^\d{4}-\d{2}-\d{2}$/.test(profile.date_of_birth) || !Number.isFinite(Date.parse(profile.date_of_birth)) || profile.date_of_birth >= new Date().toISOString().slice(0, 10))) errors.date_of_birth = 'Masukkan tanggal lahir fiktif yang valid di masa lalu.';
  for (const key of Object.keys(profileLabels) as (keyof ApplicantProfile)[]) if (profile[key].length > 500) errors[key] = 'Maksimal 500 karakter.';
  return errors;
}
export function fileError(file: File, category: EvidenceCategory) {
  const rule = evidenceRules[category];
  if (!(rule.extensions as readonly string[]).includes(file.name.split('.').pop()?.toLowerCase() ?? '')) return `Format tidak didukung. Gunakan ${rule.extensions.join(', ').toUpperCase()}.`;
  if (!file.size) return 'File kosong tidak dapat diunggah.';
  if (file.size > rule.max) return `Ukuran file melebihi batas ${rule.size}.`;
  return '';
}
