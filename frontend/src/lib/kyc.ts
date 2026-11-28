import type { Role, User } from './contracts';

export const statusLabels = {
  DRAFT: 'Draf', SUBMITTED: 'Terkirim', UNDER_REVIEW: 'Dalam tinjauan',
  NEEDS_REVISION: 'Perlu revisi', RESUBMITTED: 'Dikirim ulang',
  ACCEPTED_DEMO: 'Diterima', REJECTED_DEMO: 'Ditolak', WITHDRAWN: 'Ditarik',
} as const;
export type CaseStatus = keyof typeof statusLabels;
export type EvidenceCategory = 'identity' | 'document' | 'video';
export const evidenceRules = {
  identity: { label: 'KTP dummy', description: 'Wajib. KTP sintetis yang terbaca; nama dan tanggal lahir harus sama dengan data pribadi.', extensions: ['png', 'jpg', 'jpeg', 'pdf'], accept: '.png,.jpg,.jpeg,.pdf', max: 5 * 1024 ** 2, size: '5 MiB' },
  document: { label: 'Formulir pembukaan rekening', description: 'Wajib. Formulir pembukaan rekening sintetis (PDF/DOCX). KK dummy dapat ditambahkan bila relevan.', extensions: ['pdf', 'docx'], accept: '.pdf,.docx', max: 10 * 1024 ** 2, size: '10 MiB' },
  video: { label: 'Video verifikasi', description: 'Wajib untuk simulasi ini. MP4 sintetis 10–30 detik; diperiksa manual, bukan verifikasi liveness otomatis.', extensions: ['mp4'], accept: '.mp4', max: 30 * 1024 ** 2, size: '30 MiB' },
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
export type DocumentType = 'ktp' | 'account_opening_form' | 'kk_optional' | 'verification_video';
export interface Evidence {
  id: string; category: EvidenceCategory; version: number; original_bytes: number;
  document_type?: DocumentType | 'legacy_supporting_document'; required?: boolean;
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
export const evidenceFor = (application: Application, category: EvidenceCategory) => application.evidence.filter(e => e.category === category && e.required !== false).sort((a, b) => b.version - a.version)[0];
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

export interface EvidenceCheck {
  evidence_id: string;
  evidence_version: number;
  readable: boolean;
  correct_document_type: boolean;
  matches_applicant_form: boolean;
  needs_clarification: boolean;
  reason_code: 'VERIFIED' | 'UNREADABLE' | 'WRONG_DOCUMENT_TYPE' | 'MISMATCH' | 'CLARIFICATION';
  note?: string | null;
}
export interface ReviewChecksResponse { version: number; review: { checks: EvidenceCheck[] } | null }
export type ReviewerProfile = Pick<ApplicantProfile, 'full_name' | 'identity_number' | 'date_of_birth' | 'address'>;
export interface DocumentAnalysis {
  status: 'COMPLETED' | 'FAILED';
  engine: string;
  model_version: string;
  processed_at: string;
  manual_review_required: boolean;
  error?: string;
  checks: Array<{ field: string; submitted_value: string | null; extracted_value: string | null; result: string }>;
}

export interface ShareRequest {
  id: string;
  requester_username: string;
  owner_username: string;
  purpose: string;
  requested_items: string[];
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'REVOKED' | 'EXPIRED';
  application_id: string | null;
  requester_key_fingerprint: string | null;
  created_at: string;
  decided_at: string | null;
  expires_at: string | null;
}

export interface ShareItem {
  id: string;
  kind: 'profile' | 'identity' | 'document' | 'video' | 'kk';
  mime_type: string;
  display_name: string;
  original_bytes: number;
}

export interface PublicKeyInfo {
  public_key_pem: string;
  fingerprint: string;
  created_at: string;
}

// Assignment 3: digital signatures on the account-opening form PDF.
export interface SigningKeyInfo {
  id: string; fingerprint: string; cert_serial: string; expires_at: string; created_at: string;
  revoked_at: string | null; revoke_reason: string | null; certificate_pem?: string;
}
export interface SigningKeyState { active: SigningKeyInfo | null; history: SigningKeyInfo[] }
export interface SigningChallenge { challenge_id: string; challenge: string; user_id: string; expires_at: string }
export interface SignaturePrepare {
  session_id: string; signed_attrs_der: string; digest: string;
  byte_range: [number, number, number, number]; key_fingerprint: string; expires_at: string;
}
export type SignatureStatus = 'VALID' | 'VALID_UNTRUSTED' | 'INVALID' | 'MODIFIED_AFTER_SIGNING' | 'KEY_REVOKED' | 'SIGNER_MISMATCH' | 'NOT_SIGNED' | 'MALFORMED';
export interface DocumentSignature {
  id: string; evidence_id: string; signer: string; fingerprint: string;
  signed_at: string; status: SignatureStatus; last_verified_at: string | null;
}
export interface SignatureVerification {
  status: SignatureStatus; reasons: string[]; signer: string | null; fingerprint: string | null; signed_at: string | null;
}
export const signatureStatus: Record<SignatureStatus, { label: string; tone: string; meaning: string }> = {
  VALID: { label: 'Valid', tone: 'status-ACCEPTED_DEMO', meaning: 'Dokumen tidak berubah sejak ditandatangani dengan kunci yang terdaftar.' },
  VALID_UNTRUSTED: { label: 'Valid, tidak dikenal', tone: 'status-NEEDS_REVISION', meaning: 'Tanda tangan cocok secara matematis, tetapi sertifikatnya bukan dari VELTRIX atau tidak dikenal.' },
  INVALID: { label: 'Tidak valid', tone: 'status-REJECTED_DEMO', meaning: 'Isi dokumen atau tanda tangannya telah berubah.' },
  MODIFIED_AFTER_SIGNING: { label: 'Diubah setelah ditandatangani', tone: 'status-REJECTED_DEMO', meaning: 'Bagian yang ditandatangani utuh, tetapi ada tambahan setelah penandatanganan.' },
  KEY_REVOKED: { label: 'Kunci dicabut', tone: 'status-REJECTED_DEMO', meaning: 'Kunci sudah dicabut saat dokumen ditandatangani.' },
  SIGNER_MISMATCH: { label: 'Penandatangan tidak cocok', tone: 'status-REJECTED_DEMO', meaning: 'Kunci penandatangan bukan milik pemohon pemilik dokumen.' },
  NOT_SIGNED: { label: 'Belum ditandatangani', tone: '', meaning: 'PDF ini tidak memiliki tanda tangan digital.' },
  MALFORMED: { label: 'Rusak', tone: 'status-REJECTED_DEMO', meaning: 'Struktur PDF atau tanda tangan tidak dapat dibaca dengan aman.' },
};

