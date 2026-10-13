import { delay, http, HttpResponse } from 'msw';
import { ALGORITHMS, type Algorithm, type BenchmarkResult, type Category, type CipherVersion, type CryptoSample, type DownloadAttempt, type PersonalFields, type PersonalRecord, type User, type VaultFile } from '@/lib/contracts';

const limits = { max_file_bytes: 25_000_000, supported_extensions: ['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'mp4'], min_repetitions: 10, max_repetitions: 30 };
const demoUser: User = { id: '00000000-0000-4000-8000-000000000001', username: 'demo_user' };
const accounts = new Map<string, { user: User; password: string }>([['demo_user', { user: demoUser, password: 'veltrix123' }]]);
type StoredFile = { owner: string; metadata: VaultFile; blob: Blob };
type StoredProfile = { owner: string; metadata: PersonalRecord; fields: PersonalFields };
const files = new Map<string, StoredFile>();
const profiles = new Map<string, StoredProfile>();
const benchmarks = new Map<string, { owner: string; result: BenchmarkResult }>();
const downloadTests = new Map<string, { owner: string; file_id: string; repetitions: number; attempts: DownloadAttempt[] }>();
const syntheticFields: PersonalFields = { full_name: 'Pengguna Demo', email: 'demo@example.com', phone: '080000000000', address: 'Alamat contoh untuk demonstrasi', date_of_birth: '2000-01-01', identity_number: 'DUMMY-000001' };

function versions(length: number): CipherVersion[] {
  return ALGORITHMS.map(algorithm => {
    const block = algorithm === 'AES' ? 16 : 8;
    const size = algorithm === 'RC4' ? length : (Math.floor(length / block) + 1) * block;
    return { algorithm, mode: algorithm === 'RC4' ? null : 'CBC', ciphertext_bytes: size, stored_bytes: size + 64, ciphertext_sample_hex: Array.from(crypto.getRandomValues(new Uint8Array(32))).map(n => n.toString(16).padStart(2, '0')).join('') };
  });
}
function simplePdf(text: string) {
  const stream = `BT /F1 16 Tf 50 740 Td (${text}) Tj ET`;
  const objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`];
  let content = '%PDF-1.4\n'; const offsets = [0];
  objects.forEach((obj, i) => { offsets.push(content.length); content += `${i + 1} 0 obj\n${obj}\nendobj\n`; });
  const xref = content.length;
  content += `xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(n => `${String(n).padStart(10, '0')} 00000 n \n`).join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return new Blob([content], { type: 'application/pdf' });
}
function addFile(id: string, owner: string, name: string, category: Category, blob: Blob) {
  const cipherVersions = versions(blob.size);
  const metadata: VaultFile = { id, display_name: name, category, mime_type: blob.type || 'application/octet-stream', original_bytes: blob.size, total_stored_bytes: cipherVersions.reduce((sum, v) => sum + v.stored_bytes, 0), status: 'ready', created_at: new Date().toISOString(), versions: cipherVersions };
  files.set(id, { owner, metadata, blob }); return metadata;
}
addFile('11111111-1111-4111-8111-111111111111', demoUser.id, 'dokumen-contoh.pdf', 'document', simplePdf('VELTRIX: sample document, fictional data only.'));
addFile('22222222-2222-4222-8222-222222222222', demoUser.id, 'catatan-eksperimen.pdf', 'document', simplePdf('Academic cipher comparison: AES, RC4, DES.'));
const png = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII='), c => c.charCodeAt(0));
addFile('33333333-3333-4333-8333-333333333333', demoUser.id, 'gambar-dummy.png', 'identity', new Blob([png], { type: 'image/png' }));
const profileId = '44444444-4444-4444-8444-444444444444';
profiles.set(demoUser.id, { owner: demoUser.id, metadata: { id: profileId, updated_at: new Date().toISOString(), versions: versions(new TextEncoder().encode(JSON.stringify(syntheticFields)).length), status: 'ready' }, fields: syntheticFields });

function currentUser(): User | undefined {
  const username = document.cookie.split('; ').find(v => v.startsWith('veltrix_demo_user='))?.split('=')[1];
  return username ? accounts.get(decodeURIComponent(username))?.user : undefined;
}
function fail(status: number, code: string, message: string, field_errors?: Record<string, string[]>) {
  return HttpResponse.json({ error: { code, message, field_errors, request_id: crypto.randomUUID() } }, { status, headers: { 'Cache-Control': 'no-store' } });
}
function sessionFailure() { return fail(401, 'SESSION_EXPIRED', 'Sesi berakhir. Silakan masuk kembali.'); }
function notFound() { return fail(404, 'RESOURCE_NOT_FOUND', 'Data tidak ditemukan atau tidak dapat diakses.'); }
function json(data: unknown, status = 200) { return new HttpResponse(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } }); }
function validRepetitions(n: unknown) { return Number.isInteger(n) && Number(n) >= 10 && Number(n) <= 30; }
function stats(values: number[]) {
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const ordered = [...values].sort((a, b) => a - b);
  const middle = Math.floor(ordered.length / 2);
  return { mean, median: ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2, sd: Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, values.length - 1)) };
}
function csv(rows: (string | number | boolean)[][], name: string) {
  const body = rows.map(row => row.map(cell => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\r\n');
  return new HttpResponse(body, { headers: { 'Content-Type': 'text/csv;charset=utf-8', 'Content-Disposition': `attachment; filename="${name}"`, 'Cache-Control': 'no-store' } });
}

export const handlers = [
  http.all('/api/v1/*', async ({ request }) => {
    if (!['GET', 'HEAD'].includes(request.method) && request.headers.get('X-CSRF-Token') !== 'veltrix-mock-csrf') return fail(403, 'CSRF_INVALID', 'Sesi form tidak valid. Coba lagi.');
  }),
  http.get('/api/v1/capabilities', () => json(limits)),
  http.get('/api/v1/auth/csrf', () => json({ token: 'veltrix-mock-csrf' })),
  http.get('/api/v1/auth/me', async () => { await delay(120); return currentUser() ? json(currentUser()) : sessionFailure(); }),
  http.post('/api/v1/auth/register', async ({ request }) => {
    await delay(400);
    const { username, password } = await request.json() as { username: string; password: string };
    if (!/^[a-zA-Z0-9_]{3,24}$/.test(username) || password.length < 8) return fail(422, 'VALIDATION_ERROR', 'Periksa username dan password.', { username: ['Gunakan 3–24 huruf, angka, atau underscore.'] });
    if (accounts.has(username)) return fail(409, 'USERNAME_TAKEN', 'Username sudah digunakan.', { username: ['Pilih username lain.'] });
    const user = { id: crypto.randomUUID(), username }; accounts.set(username, { user, password }); return json(user, 201);
  }),
  http.post('/api/v1/auth/login', async ({ request }) => {
    await delay(350);
    const { username, password } = await request.json() as { username: string; password: string };
    const account = accounts.get(username);
    if (!account || account.password !== password) return fail(401, 'INVALID_CREDENTIALS', 'Username atau password tidak sesuai.');
    document.cookie = `veltrix_demo_user=${encodeURIComponent(username)}; Path=/; SameSite=Lax`;
    return json(account.user);
  }),
  http.post('/api/v1/auth/logout', () => { document.cookie = 'veltrix_demo_user=; Max-Age=0; Path=/'; return new HttpResponse(null, { status: 204 }); }),
  http.get('/api/v1/vault/summary', async () => {
    await delay(180); const user = currentUser(); if (!user) return sessionFailure();
    const owned = [...files.values()].filter(f => f.owner === user.id);
    return json({ file_count: owned.length, original_bytes: owned.reduce((s, f) => s + f.metadata.original_bytes, 0), stored_bytes: owned.reduce((s, f) => s + f.metadata.total_stored_bytes, 0), personal_data_exists: profiles.has(user.id) });
  }),
  http.get('/api/v1/vault/files', async ({ request }) => {
    await delay(220); const user = currentUser(); if (!user) return sessionFailure();
    const query = new URL(request.url).searchParams;
    const owned = [...files.values()].filter(f => f.owner === user.id && (!query.get('category') || f.metadata.category === query.get('category')) && f.metadata.display_name.toLowerCase().includes((query.get('search') ?? '').toLowerCase())).map(f => f.metadata).reverse();
    return json({ items: owned, page: 1, page_size: 50, total: owned.length });
  }),
  http.post('/api/v1/vault/files', async ({ request }) => {
    const user = currentUser(); if (!user) return sessionFailure();
    const form = await request.formData(); const file = form.get('file'); const category = form.get('category') as Category;
    if (!(file instanceof File) || !['identity', 'document', 'video'].includes(category)) return fail(422, 'VALIDATION_ERROR', 'Pilih kategori dan file.');
    if (file.size > limits.max_file_bytes) return fail(413, 'FILE_TOO_LARGE', 'Ukuran file melebihi batas 25 MB.', { file: ['Pilih file maksimal 25 MB.'] });
    const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
    const allowed = category === 'identity' ? ['jpg', 'jpeg', 'png'] : category === 'video' ? ['mp4'] : ['pdf', 'doc', 'docx', 'xls', 'xlsx'];
    if (!allowed.includes(extension)) return fail(415, 'UNSUPPORTED_FILE_TYPE', 'Format file tidak sesuai kategori.');
    await delay(650); return json(addFile(crypto.randomUUID(), user.id, file.name, category, file), 201);
  }),
  http.get('/api/v1/vault/files/:id/download', async ({ params, request }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const file = files.get(String(params.id));
    if (!file || file.owner !== user.id) return notFound();
    if (!ALGORITHMS.includes(new URL(request.url).searchParams.get('algorithm') as Algorithm)) return fail(422, 'VALIDATION_ERROR', 'Pilih algoritma yang valid.');
    await delay(35);
    return new HttpResponse(await file.blob.arrayBuffer(), { headers: { 'Content-Type': file.blob.type, 'Content-Disposition': 'attachment', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
  }),
  http.get('/api/v1/vault/files/:id', async ({ params }) => {
    await delay(150); const user = currentUser(); if (!user) return sessionFailure(); const file = files.get(String(params.id));
    return file?.owner === user.id ? json(file.metadata) : notFound();
  }),
  http.delete('/api/v1/vault/files/:id', async ({ params }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const file = files.get(String(params.id));
    if (file?.owner !== user.id) return notFound(); await delay(180); files.delete(String(params.id)); return new HttpResponse(null, { status: 204 });
  }),
  http.get('/api/v1/vault/personal-data', async () => { await delay(180); const user = currentUser(); return user ? json(profiles.get(user.id)?.metadata ?? null) : sessionFailure(); }),
  http.post('/api/v1/vault/personal-data/:id/decrypt', async ({ params, request }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const profile = profiles.get(user.id);
    if (!profile || profile.metadata.id !== params.id) return notFound();
    const { algorithm } = await request.json() as { algorithm: Algorithm };
    if (!ALGORITHMS.includes(algorithm)) return fail(422, 'VALIDATION_ERROR', 'Pilih algoritma yang valid.');
    await delay(200); return json(profile.fields);
  }),
  ...(['post', 'put'] as const).map(method => http[method](method === 'post' ? '/api/v1/vault/personal-data' : '/api/v1/vault/personal-data/:id', async ({ request, params }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const old = profiles.get(user.id);
    if (method === 'post' && old) return fail(409, 'PROFILE_EXISTS', 'Profil sudah ada. Gunakan aksi edit.');
    if (method === 'put' && old?.metadata.id !== params.id) return notFound();
    const fields = await request.json() as PersonalFields;
    if (!fields.full_name?.trim()) return fail(422, 'VALIDATION_ERROR', 'Nama lengkap wajib diisi.', { full_name: ['Masukkan nama lengkap.'] });
    await delay(450);
    const metadata: PersonalRecord = { id: old?.metadata.id ?? crypto.randomUUID(), updated_at: new Date().toISOString(), versions: versions(new TextEncoder().encode(JSON.stringify(fields)).length), status: 'ready' };
    profiles.set(user.id, { owner: user.id, fields, metadata }); return json(metadata, method === 'post' ? 201 : 200);
  })),
  http.delete('/api/v1/vault/personal-data/:id', async ({ params }) => {
    const user = currentUser(); if (!user) return sessionFailure(); if (profiles.get(user.id)?.metadata.id !== params.id) return notFound();
    profiles.delete(user.id); return new HttpResponse(null, { status: 204 });
  }),
  http.post('/api/v1/benchmarks', async ({ request }) => {
    const user = currentUser(); if (!user) return sessionFailure();
    const { source, repetitions, warmups } = await request.json() as Pick<BenchmarkResult, 'source' | 'repetitions' | 'warmups'>;
    if (!validRepetitions(repetitions) || warmups !== 2) return fail(422, 'VALIDATION_ERROR', 'Gunakan 10–30 pengulangan dan 2 warm-up.');
    const file = files.get(source.id); const profile = profiles.get(user.id);
    const length = source.type === 'file' && file?.owner === user.id ? file.blob.size : source.type === 'personal_data' && profile?.metadata.id === source.id ? new TextEncoder().encode(JSON.stringify(profile.fields)).length : null;
    if (length === null) return notFound();
    await delay(900);
    const cipherVersions = versions(length);
    const samples: CryptoSample[] = ALGORITHMS.flatMap((algorithm, ai) => Array.from({ length: repetitions }, (_, index) => ({ algorithm, repetition: index + 1, encrypt_ns: Math.round((150000 + length * (2 + ai * 0.8)) * (1 + ((index % 5) - 2) / 25)), decrypt_ns: Math.round((120000 + length * (1.8 + ai * 0.7)) * (1 + ((index % 3) - 1) / 20)), integrity_ns: 50000 + length, correctness_ns: 15000 + length, ciphertext_bytes: cipherVersions[ai].ciphertext_bytes, stored_bytes: cipherVersions[ai].stored_bytes, round_trip_ok: true })));
    const result: BenchmarkResult = { id: crypto.randomUUID(), source, input_bytes: length, repetitions, warmups, created_at: new Date().toISOString(), environment: { mode: 'SIMULASI, bukan pengukuran kriptografi', timer: 'Generated fixture', storage: 'Browser memory' }, methodology_version: 'mock-v1', samples, summary: ALGORITHMS.map(algorithm => {
      const rows = samples.filter(s => s.algorithm === algorithm); const enc = stats(rows.map(r => r.encrypt_ns)); const dec = stats(rows.map(r => r.decrypt_ns));
      return { algorithm, mean_encrypt_ns: enc.mean, median_encrypt_ns: enc.median, stddev_encrypt_ns: enc.sd, mean_decrypt_ns: dec.mean, median_decrypt_ns: dec.median, stddev_decrypt_ns: dec.sd, round_trip_successes: repetitions, measured_runs: repetitions };
    }) };
    benchmarks.set(result.id, { owner: user.id, result }); return json(result, 201);
  }),
  http.get('/api/v1/benchmarks', async () => { await delay(100); const user = currentUser(); return user ? json([...benchmarks.values()].filter(b => b.owner === user.id).map(b => b.result).reverse()) : sessionFailure(); }),
  http.get('/api/v1/benchmarks/:id/export', ({ params }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const run = benchmarks.get(String(params.id)); if (run?.owner !== user.id) return notFound();
    return csv([['mode', 'method', 'input_bytes', 'algorithm', 'repetition', 'encrypt_ns', 'decrypt_ns', 'integrity_ns', 'correctness_ns', 'ciphertext_bytes', 'stored_bytes', 'round_trip_ok'], ...run.result.samples.map(s => ['SIMULATED', run.result.methodology_version, run.result.input_bytes, s.algorithm, s.repetition, s.encrypt_ns, s.decrypt_ns, s.integrity_ns, s.correctness_ns, s.ciphertext_bytes, s.stored_bytes, s.round_trip_ok])], 'veltrix-simulated-crypto.csv');
  }),
  http.get('/api/v1/benchmarks/:id', async ({ params }) => { await delay(100); const user = currentUser(); if (!user) return sessionFailure(); const run = benchmarks.get(String(params.id)); return run?.owner === user.id ? json(run.result) : notFound(); }),
  http.post('/api/v1/download-tests', async ({ request }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const { file_id, repetitions } = await request.json() as { file_id: string; repetitions: number };
    if (files.get(file_id)?.owner !== user.id) return notFound(); if (!validRepetitions(repetitions)) return fail(422, 'VALIDATION_ERROR', 'Gunakan 10–30 pengulangan.');
    const id = crypto.randomUUID(); downloadTests.set(id, { owner: user.id, file_id, repetitions, attempts: [] }); return json({ id }, 201);
  }),
  http.post('/api/v1/download-tests/:id/results', async ({ params, request }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const run = downloadTests.get(String(params.id)); if (run?.owner !== user.id) return notFound();
    const { attempts } = await request.json() as { attempts: DownloadAttempt[] };
    if (!Array.isArray(attempts) || attempts.length > run.repetitions * 3 || attempts.some(a => !ALGORITHMS.includes(a.algorithm) || !Number.isFinite(a.elapsed_ms) || a.elapsed_ms < 0)) return fail(422, 'VALIDATION_ERROR', 'Sample download tidak valid.');
    run.attempts = attempts; return json({ id: params.id });
  }),
  http.get('/api/v1/download-tests/:id/export', ({ params }) => {
    const user = currentUser(); if (!user) return sessionFailure(); const run = downloadTests.get(String(params.id)); if (run?.owner !== user.id) return notFound();
    return csv([['mode', 'algorithm', 'repetition', 'elapsed_ms', 'received_bytes', 'success', 'error_code'], ...run.attempts.map(a => ['CLIENT-MEASURED-MOCK', a.algorithm, a.repetition, a.elapsed_ms, a.received_bytes, a.success, a.error_code ?? ''])], 'veltrix-mock-download.csv');
  }),
];
