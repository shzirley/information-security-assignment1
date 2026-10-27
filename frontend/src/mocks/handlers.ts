import { delay, http, HttpResponse } from 'msw';
import type { Role, User } from '@/lib/contracts';
import { blankProfile, categories, completeness, editable, evidenceRules, fileError, profileErrors, syntheticProfile, type ApplicantProfile, type Application, type CaseAction, type Evidence, type EvidenceCategory, type LabRun } from '@/lib/kyc';

// Interaction fixtures only: no encryption, durable storage, or real sessions.
const demoAccounts: User[] = [
  { id: 'applicant-demo', username: 'demo_user', display_name: 'Nara', role: 'applicant' },
  { id: 'applicant-other', username: 'other_applicant', display_name: 'Pemohon Lain', role: 'applicant' },
  { id: 'reviewer-demo', username: 'reviewer_demo', display_name: 'Reviewer Utama', role: 'reviewer' },
  { id: 'reviewer-other', username: 'reviewer_other', display_name: 'Reviewer Kedua', role: 'reviewer' },
  { id: 'admin-demo', username: 'admin_demo', display_name: 'Admin Operasional', role: 'admin' },
  { id: 'evaluator-demo', username: 'evaluator_demo', display_name: 'Evaluator Lab', role: 'evaluator' },
];
const accounts = new Map(demoAccounts.map(user => [user.username, { user, password: 'veltrix123' }]));
type StoredCase = { owner: string; application: Application; profile: ApplicantProfile | null; blobs: Map<string, Blob> };
const cases = new Map<string, StoredCase>();
const labRuns = new Map<string, { owner: string; run: LabRun }>();
const now = () => new Date().toISOString();
function event(action: string, actor_role: Role, note?: string) { return { id: crypto.randomUUID(), at: now(), action, actor_role, ...(note ? { note } : {}) }; }
function pdf(text: string) {
  const stream = `BT /F1 16 Tf 45 740 Td (${text}) Tj ET`;
  const objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`];
  let value = '%PDF-1.4\n'; const offsets: number[] = [];
  objects.forEach((object, i) => { offsets.push(value.length); value += `${i + 1} 0 obj\n${object}\nendobj\n`; });
  const start = value.length;
  value += `xref\n0 6\n0000000000 65535 f \n${offsets.map(n => `${String(n).padStart(10, '0')} 00000 n \n`).join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${start}\n%%EOF`;
  return new Blob([value], { type: 'application/pdf' });
}
function seedCase(id: string, owner: string, status: Application['status'], assigned?: string) {
  const application: Application = {
    id, reference: `VTX-2026-${id.split('-').pop()}`, status, version: 1, created_at: '2026-10-24T08:00:00.000Z', updated_at: '2026-10-26T09:00:00.000Z',
    personal_data_complete: status !== 'DRAFT', evidence: [], events: [{ ...event('Pengajuan dibuat', 'applicant'), at: '2026-10-24T08:00:00.000Z' }],
    synthetic_acknowledged: status !== 'DRAFT', assigned_reviewer_id: assigned,
  };
  const stored: StoredCase = { owner, application, profile: status === 'DRAFT' ? null : { ...syntheticProfile }, blobs: new Map() };
  cases.set(id, stored);
  if (status !== 'DRAFT') {
    for (const category of categories) {
      const isVideo = category === 'video';
      const blob = isVideo ? null : pdf(category === 'identity' ? 'DUMMY IDENTITY: fictional person. No real identity.' : 'DUMMY ACCOUNT FORM: academic sample. Not a bank document.');
      const metadata: Evidence = { id: `${id}-${category}-v1`, category, version: 1, original_bytes: blob?.size ?? 0, mime_type: isVideo ? 'video/mp4' : 'application/pdf', display_name: isVideo ? 'verification-demo.mp4' : `${category}-dummy.pdf`, created_at: application.created_at, validation: 'format_checked' };
      application.evidence.push(metadata); if (blob) stored.blobs.set(metadata.id, blob);
    }
    application.events.push({ ...event('Bukti sintetis lengkap dan dikirim', 'applicant'), at: '2026-10-25T08:00:00.000Z' });
  }
  if (status === 'NEEDS_REVISION') {
    application.revision_note = 'Lengkapi dokumen administrasi dummy dengan halaman tujuan rekening simulasi.';
    application.events.push({ ...event('Tinjauan metadata dimulai', 'reviewer'), at: '2026-10-26T08:00:00.000Z' });
    application.events.push({ ...event('Revisi diminta', 'reviewer', application.revision_note), at: application.updated_at });
  }
}
seedCase('case-1001', 'applicant-demo', 'NEEDS_REVISION', 'reviewer-demo');
seedCase('case-1002', 'applicant-demo', 'DRAFT');
seedCase('case-1003', 'applicant-demo', 'SUBMITTED', 'reviewer-demo');
seedCase('case-2001', 'applicant-other', 'SUBMITTED', 'reviewer-other');
seedCase('case-2002', 'applicant-other', 'SUBMITTED');
let fixturesReady: Promise<void> | undefined;
function initFixtures() {
  return fixturesReady ??= fetch('/fixtures/verification-demo.mp4').then(async response => {
    if (!response.ok) throw new Error('Fixture video tidak tersedia.');
    const blob = await response.blob();
    for (const stored of cases.values()) for (const evidence of stored.application.evidence) if (evidence.category === 'video') { evidence.original_bytes = blob.size; stored.blobs.set(evidence.id, blob); }
  });
}
function currentUser() {
  const value = document.cookie.split('; ').find(c => c.startsWith('veltrix_demo_user='))?.split('=')[1];
  return value ? accounts.get(decodeURIComponent(value))?.user : undefined;
}
function json(data: unknown, status = 200) { return new HttpResponse(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } }); }
function fail(status: number, code: string, message: string, fields?: Record<string, string[]>) { return json({ error: { code, message, field_errors: fields, request_id: crypto.randomUUID() } }, status); }
const unauthenticated = () => fail(401, 'SESSION_EXPIRED', 'Sesi berakhir. Silakan masuk kembali.');
const denied = () => fail(403, 'ROLE_FORBIDDEN', 'Peran ini tidak memiliki akses ke tindakan tersebut.');
const missing = () => fail(404, 'RESOURCE_NOT_FOUND', 'Pengajuan tidak ditemukan atau tidak dapat diakses.');
function visible(stored: StoredCase, user: User) {
  return user.role === 'applicant' ? stored.owner === user.id : user.role === 'reviewer' ? stored.application.assigned_reviewer_id === user.id && stored.application.status !== 'DRAFT' && stored.application.status !== 'WITHDRAWN' : false;
}
function view(stored: StoredCase, role: Role): Application {
  const result = structuredClone(stored.application);
  if (role !== 'applicant') result.evidence = result.evidence.map(({ display_name: _privateName, ...metadata }) => metadata);
  return result;
}
function writable(stored: StoredCase, version: number) {
  if (!editable(stored.application.status)) return fail(409, 'CASE_READ_ONLY', 'Pengajuan terkunci. Perubahan hanya diizinkan pada draf atau permintaan revisi.');
  if (stored.application.version !== version) return fail(409, 'VERSION_CONFLICT', 'Pengajuan berubah di sesi lain. Muat ulang sebelum melanjutkan.');
}
function changed(stored: StoredCase, action: string, user: User, note?: string) { stored.application.version++; stored.application.updated_at = now(); stored.application.events.push(event(action, user.role, note)); }
async function signatureValid(file: File) {
  const bytes = new Uint8Array(await file.slice(0, 16).arrayBuffer());
  const text = new TextDecoder().decode(bytes); const ext = file.name.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return text.startsWith('%PDF-');
  if (ext === 'png') return bytes[0] === 137 && text.slice(1, 4) === 'PNG';
  if (ext === 'jpg' || ext === 'jpeg') return bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
  if (ext === 'docx') return bytes[0] === 80 && bytes[1] === 75; // Backend must inspect the OOXML container.
  if (ext === 'mp4') return text.slice(4, 8) === 'ftyp';
  return false;
}

export const handlers = [
  http.all('/api/v1/*', ({ request }) => {
    if (!['GET', 'HEAD'].includes(request.method) && request.headers.get('X-CSRF-Token') !== 'veltrix-mock-csrf') return fail(403, 'CSRF_INVALID', 'Sesi form tidak valid. Coba lagi.');
  }),
  http.get('/api/v1/auth/csrf', () => json({ token: 'veltrix-mock-csrf' })),
  http.get('/api/v1/auth/me', async () => { await delay(100); return currentUser() ? json(currentUser()) : unauthenticated(); }),
  http.post('/api/v1/auth/register', async ({ request }) => {
    const { username, password } = await request.json() as { username: string; password: string };
    if (typeof username !== 'string' || !/^[a-zA-Z0-9_]{3,24}$/.test(username) || typeof password !== 'string' || password.length < 8) return fail(422, 'VALIDATION_ERROR', 'Periksa username dan password.');
    if (accounts.has(username)) return fail(409, 'USERNAME_TAKEN', 'Username sudah digunakan.', { username: ['Pilih username lain.'] });
    const user: User = { id: crypto.randomUUID(), username, display_name: username, role: 'applicant' };
    accounts.set(username, { user, password }); return json(user, 201);
  }),
  http.post('/api/v1/auth/login', async ({ request }) => {
    await delay(180); const { username, password } = await request.json() as { username: string; password: string }; const account = accounts.get(username);
    if (!account || account.password !== password) return fail(401, 'INVALID_CREDENTIALS', 'Username atau password tidak sesuai.');
    document.cookie = `veltrix_demo_user=${encodeURIComponent(username)}; Path=/; SameSite=Lax`; return json(account.user);
  }),
  http.post('/api/v1/auth/logout', () => { document.cookie = 'veltrix_demo_user=; Max-Age=0; Path=/; SameSite=Lax'; return new HttpResponse(null, { status: 204 }); }),
  http.get('/api/v1/applications', async () => {
    const user = currentUser(); if (!user) return unauthenticated(); if (!['applicant', 'reviewer'].includes(user.role)) return denied();
    await initFixtures(); await delay(120);
    const items = [...cases.values()].filter(c => visible(c, user)).map(c => view(c, user.role)).sort((a, b) => b.updated_at.localeCompare(a.updated_at)); return json({ items, total: items.length });
  }),
  http.post('/api/v1/applications', () => {
    const user = currentUser(); if (!user) return unauthenticated(); if (user.role !== 'applicant') return denied();
    const id = crypto.randomUUID(); const stamp = now();
    const application: Application = { id, reference: `VTX-2026-${id.slice(0, 8).toUpperCase()}`, status: 'DRAFT', version: 1, created_at: stamp, updated_at: stamp, personal_data_complete: false, evidence: [], events: [event('Pengajuan dibuat', 'applicant')], synthetic_acknowledged: false };
    cases.set(id, { owner: user.id, application, profile: null, blobs: new Map() }); return json(application, 201);
  }),
  http.get('/api/v1/applications/:id', async ({ params }) => {
    const user = currentUser(); if (!user) return unauthenticated(); const stored = cases.get(String(params.id));
    if (!stored || !visible(stored, user)) return missing(); await initFixtures(); return json(view(stored, user.role));
  }),
  http.get('/api/v1/applications/:id/personal-data', ({ params }) => {
    const user = currentUser(); if (!user) return unauthenticated(); const stored = cases.get(String(params.id));
    if (!stored || stored.owner !== user.id || user.role !== 'applicant') return missing(); return json({ profile: stored.profile });
  }),
  http.put('/api/v1/applications/:id/personal-data', async ({ params, request }) => {
    const user = currentUser(); if (!user) return unauthenticated(); const stored = cases.get(String(params.id));
    if (!stored || stored.owner !== user.id || user.role !== 'applicant') return missing();
    const { profile, version } = await request.json() as { profile: ApplicantProfile; version: number }; const error = writable(stored, version); if (error) return error;
    const normalized = { ...blankProfile, ...profile }; if (Object.values(normalized).some(v => typeof v !== 'string')) return fail(422, 'VALIDATION_ERROR', 'Format data pribadi tidak valid.');
    const errors = profileErrors(normalized);
    if (Object.keys(errors).length) return fail(422, 'VALIDATION_ERROR', 'Periksa data pribadi dummy.', Object.fromEntries(Object.entries(errors).map(([k, v]) => [k, [v]])));
    stored.profile = Object.fromEntries(Object.keys(blankProfile).map(key => [key, normalized[key as keyof ApplicantProfile]])) as unknown as ApplicantProfile;
    stored.application.personal_data_complete = true; changed(stored, 'Data pribadi diperbarui', user); return json(view(stored, user.role));
  }),
  http.post('/api/v1/applications/:id/evidence', async ({ params, request }) => {
    const user = currentUser(); if (!user) return unauthenticated(); const stored = cases.get(String(params.id));
    if (!stored || stored.owner !== user.id || user.role !== 'applicant') return missing();
    const form = await request.formData(); const category = form.get('category') as EvidenceCategory; const file = form.get('file');
    const error = writable(stored, Number(form.get('version'))); if (error) return error;
    if (!(category in evidenceRules) || !(file instanceof File)) return fail(422, 'INVALID_UPLOAD', 'Pilih kategori dan file yang valid.');
    const invalid = fileError(file, category); if (invalid) return fail(422, 'INVALID_UPLOAD', invalid);
    if (!(await signatureValid(file))) return fail(422, 'SIGNATURE_MISMATCH', 'Isi file tidak sesuai format. Gunakan berkas dummy yang valid.');
    await delay(250);
    const evidence: Evidence = { id: crypto.randomUUID(), category, version: 1 + stored.application.evidence.filter(e => e.category === category).length, display_name: file.name, original_bytes: file.size, mime_type: file.type || 'application/octet-stream', created_at: now(), validation: 'format_checked' };
    stored.blobs.set(evidence.id, file); stored.application.evidence.push(evidence); changed(stored, `${evidenceRules[category].label} versi ${evidence.version} ditambahkan`, user); return json(view(stored, user.role), 201);
  }),
  http.post('/api/v1/applications/:id/actions', async ({ params, request }) => {
    const user = currentUser(); if (!user) return unauthenticated(); const stored = cases.get(String(params.id)); if (!stored || !visible(stored, user)) return missing();
    const { action, version, note, synthetic_acknowledged } = await request.json() as { action: CaseAction; version: number; note?: string; synthetic_acknowledged?: boolean };
    const application = stored.application; if (application.version !== version) return fail(409, 'VERSION_CONFLICT', 'Pengajuan berubah. Muat ulang sebelum melanjutkan.');
    const allowed: Partial<Record<CaseAction, Application['status']>> = {};
    if (user.role === 'applicant') {
      if (application.status === 'DRAFT') { allowed.submit = 'SUBMITTED'; allowed.withdraw = 'WITHDRAWN'; }
      if (application.status === 'NEEDS_REVISION') { allowed.resubmit = 'RESUBMITTED'; allowed.withdraw = 'WITHDRAWN'; }
    }
    if (user.role === 'reviewer') {
      if (application.status === 'SUBMITTED' || application.status === 'RESUBMITTED') allowed['start-review'] = 'UNDER_REVIEW';
      if (application.status === 'UNDER_REVIEW') { allowed['request-revision'] = 'NEEDS_REVISION'; allowed.accept = 'ACCEPTED_DEMO'; allowed.reject = 'REJECTED_DEMO'; }
    }
    const target = allowed[action]; if (!target) return fail(409, 'INVALID_TRANSITION', 'Tindakan tidak tersedia pada status pengajuan saat ini.');
    if (action === 'submit' || action === 'resubmit') { if (completeness(application) !== 4 || !synthetic_acknowledged) return fail(422, 'CASE_INCOMPLETE', 'Lengkapi empat kategori dan konfirmasi penggunaan data sintetis.'); application.synthetic_acknowledged = true; }
    if (action === 'request-revision' || action === 'reject') {
      if (typeof note !== 'string' || note.trim().length < 10 || note.length > 500) return fail(422, 'NOTE_REQUIRED', 'Tulis catatan operasional 10–500 karakter tanpa data pribadi.'); application.revision_note = note.trim();
    }
    application.status = target;
    changed(stored, ({ submit: 'Pengajuan dikirim', resubmit: 'Pengajuan dikirim ulang', withdraw: 'Pengajuan ditarik', 'start-review': 'Tinjauan metadata dimulai', 'request-revision': 'Revisi diminta', accept: 'Pengajuan diterima', reject: 'Pengajuan ditolak' })[action], user, action === 'request-revision' || action === 'reject' ? note?.trim() : undefined);
    return json(view(stored, user.role));
  }),
  http.get('/api/v1/applications/:id/evidence/:evidenceId/download', async ({ params }) => {
    const user = currentUser(); if (!user) return unauthenticated(); const stored = cases.get(String(params.id));
    if (!stored || stored.owner !== user.id || user.role !== 'applicant') return missing(); await initFixtures(); const blob = stored.blobs.get(String(params.evidenceId)); if (!blob) return missing();
    return new HttpResponse(await blob.arrayBuffer(), { headers: { 'Content-Type': blob.type || 'application/octet-stream', 'Content-Disposition': 'attachment', 'Cache-Control': 'no-store', 'X-Veltrix-Simulated': 'true' } });
  }),
  http.get('/api/v1/applications/:id/personal-data/download', ({ params }) => {
    const user = currentUser(); if (!user) return unauthenticated(); const stored = cases.get(String(params.id)); if (!stored || stored.owner !== user.id || user.role !== 'applicant' || !stored.profile) return missing();
    return new HttpResponse(JSON.stringify(stored.profile, null, 2), { headers: { 'Content-Type': 'application/octet-stream', 'Cache-Control': 'no-store' } });
  }),
  http.get('/api/v1/admin/assignments', async () => {
    const user = currentUser(); if (!user) return unauthenticated(); if (user.role !== 'admin') return denied(); await initFixtures();
    return json({ items: [...cases.values()].filter(c => c.application.status !== 'DRAFT' && c.application.status !== 'WITHDRAWN').map(c => view(c, 'admin')), reviewers: demoAccounts.filter(u => u.role === 'reviewer').map(({ id, display_name }) => ({ id, display_name })) });
  }),
  http.put('/api/v1/admin/assignments/:id', async ({ params, request }) => {
    const user = currentUser(); if (!user) return unauthenticated(); if (user.role !== 'admin') return denied(); const stored = cases.get(String(params.id)); if (!stored) return missing();
    const { reviewer_id, version } = await request.json() as { reviewer_id: string; version: number };
    if (version !== stored.application.version) return fail(409, 'VERSION_CONFLICT', 'Penugasan berubah. Muat ulang.');
    if (!['SUBMITTED', 'RESUBMITTED'].includes(stored.application.status)) return fail(409, 'ASSIGNMENT_LOCKED', 'Penugasan hanya dapat diubah sebelum tinjauan dimulai.');
    if (!demoAccounts.some(u => u.role === 'reviewer' && u.id === reviewer_id)) return fail(422, 'INVALID_REVIEWER', 'Pilih reviewer yang tersedia.');
    stored.application.assigned_reviewer_id = reviewer_id; changed(stored, 'Reviewer ditugaskan', user); return json(view(stored, 'admin'));
  }),
  http.get('/api/v1/lab/runs', () => {
    const user = currentUser(); if (!user) return unauthenticated(); if (user.role !== 'evaluator') return denied(); return json([...labRuns.values()].filter(v => v.owner === user.id).map(v => v.run));
  }),
  http.post('/api/v1/lab/runs', async ({ request }) => {
    const user = currentUser(); if (!user) return unauthenticated(); if (user.role !== 'evaluator') return denied();
    const { kind, fixture, repetitions, warmups } = await request.json() as { kind: LabRun['kind']; fixture: string; repetitions: number; warmups: number };
    if (!['benchmark', 'verification'].includes(kind) || !['personal-json', 'identity-png', 'document-pdf', 'video-mp4'].includes(fixture) || !Number.isInteger(repetitions) || repetitions < 30 || repetitions > 100 || warmups !== 2) return fail(422, 'INVALID_EXPERIMENT', 'Gunakan fixture lab dan 30–100 pengulangan dengan 2 warm-up.');
    await delay(700);
    const run: LabRun = { id: crypto.randomUUID(), kind, fixture, repetitions, warmups, status: 'completed', simulated: true, created_at: now(), rows: ['AES-256-GCM', 'DES-CBC', 'RC4', 'Pipeline berlapis'].map((algorithm, i) => ({ algorithm, encrypt_ms: [1.2, 4.8, 0.9, 6.9][i], decrypt_ms: [1.1, 4.6, 0.9, 6.6][i], iqr_ms: [0.2, 0.5, 0.1, 0.7][i], overhead_bytes: [28, 16, 0, 52][i], round_trip_ok: true })) };
    labRuns.set(run.id, { owner: user.id, run }); return json(run, 201);
  }),
  http.get('/api/v1/lab/runs/:id/export', ({ params }) => {
    const user = currentUser(); if (!user) return unauthenticated(); if (user.role !== 'evaluator') return denied(); const entry = labRuns.get(String(params.id)); if (!entry || entry.owner !== user.id) return missing();
    const body = ['SIMULATED DATA - NOT VALID EXPERIMENTAL EVIDENCE', 'algorithm,encrypt_median_ms,decrypt_median_ms,encrypt_iqr_ms,overhead_bytes,round_trip_simulated,fixture,repetitions,warmups', ...entry.run.rows.map(row => [row.algorithm, row.encrypt_ms, row.decrypt_ms, row.iqr_ms, row.overhead_bytes, row.round_trip_ok, entry.run.fixture, entry.run.repetitions, entry.run.warmups].join(','))].join('\r\n');
    return new HttpResponse(body, { headers: { 'Content-Type': 'text/csv;charset=utf-8', 'Cache-Control': 'no-store' } });
  }),
];
