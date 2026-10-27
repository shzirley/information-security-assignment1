import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';

const runtimeErrors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const errors: string[] = []; runtimeErrors.set(page, errors);
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/Failed to load resource: the server responded with a status of (401|403|404|409|422)/.test(message.text())) errors.push(message.text()); });
});
test.afterEach(({ page }) => { expect(runtimeErrors.get(page), 'Uncaught browser exceptions').toEqual([]); });
const pdf = Buffer.from('%PDF-1.4\nDUMMY ACCOUNT FORM\n%%EOF');
async function demoLogin(page: Page, role = 'applicant', fresh = true) {
  if (fresh) await page.goto(`/login?role=${role}`);
  else { await page.getByRole('button', { name: 'Keluar', exact: true }).click(); await expect(page).toHaveURL(/\/login/); }
  await page.getByLabel('Username', { exact: true }).fill(role === 'applicant' ? 'demo_user' : `${role}_demo`);
  await page.getByLabel('Password', { exact: true }).fill('veltrix123');
  await page.getByRole('button', { name: 'Masuk ke workspace', exact: true }).click();
  await expect(page.locator('.sidebar')).toBeAttached();
  await expect(page).toHaveURL(new RegExp(role === 'applicant' ? '/applicant/dashboard' : role === 'reviewer' ? '/reviewer/queue' : role === 'admin' ? '/admin/assignments' : '/lab/benchmark'));
  await expect(page.locator('#main-content .loading-state')).toHaveCount(0);
}
async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  await expect(page.locator('body')).not.toContainText(/\bFE\b|front[ -]?end|back[ -]?end|API (mock|live)|service worker|localhost|akun fixture|prototype|prototipe/i, { useInnerText: true });
}
async function accessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))).toEqual([]);
}
async function downloadBytes(page: Page, action: () => Promise<unknown>) {
  const waiting = page.waitForEvent('download'); await action(); const download = await waiting;
  return { download, data: await readFile((await download.path())!) };
}
async function openSeed(page: Page, reference: string) { await page.locator('.case-row').filter({ hasText: reference }).click(); await expect(page.getByRole('heading', { name: reference, exact: true })).toBeVisible(); }
async function apiRequest(page: Page, path: string, method = 'GET', body?: unknown) {
  return page.evaluate(async ({ path, method, body }) => {
    const response = await fetch(`/api/v1${path}`, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': 'veltrix-mock-csrf' }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    return { status: response.status, body: await response.json().catch(() => null) };
  }, { path, method, body });
}

test('landing: animated headline without controls, CTA, anchors, fonts, themes, reduced motion and responsive layout', async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 1000 }); await page.goto('/');
  await expect(page.getByRole('heading', { name: /Satu alur untuk/ })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Inter');
  expect(await page.locator('h1').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Montserrat');
  expect(await page.locator('.brand-symbol').first().evaluate(el => (el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await expect(page.locator('.hero-rotating')).toHaveText('identitasmu.');
  await expect(page.locator('.hero-rotating')).toHaveText('dokumenmu.', { timeout: 6500 });
  await expect(page.getByRole('heading', { level: 1 })).toHaveAccessibleName('Satu alur untuk identitas, dokumen, dan bukti KYC-mu.');
  await expect(page.getByRole('button', { name: /animasi headline/ })).toHaveCount(0);
  await expect(page.locator('.hero-footnote, .animation-toggle, .strip-academic')).toHaveCount(0);
  await expect(page.getByText('Data sintetis saja. Tidak membuka rekening bank.', { exact: true })).toHaveCount(0);
  await page.getByRole('link', { name: 'Lihat alurnya' }).click(); await expect(page).toHaveURL(/#alur/);
  await expect(page.locator('#flow-heading')).toBeInViewport();
  await page.getByRole('link', { name: 'Hak akses', exact: true }).click(); await expect(page).toHaveURL(/#akses/);
  await page.getByRole('link', { name: 'Kembali ke atas' }).click(); await expect(page.locator('h1')).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThan(2);
  await page.screenshot({ path: 'artifacts/bankkyc-landing-desktop.png', fullPage: true });
  await accessible(page);
  await page.getByRole('button', { name: 'Gunakan tema gelap' }).click(); await accessible(page);
  await page.screenshot({ path: 'artifacts/bankkyc-landing-dark.png', fullPage: true });
  await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(page.getByRole('button', { name: /animasi headline/ })).toHaveCount(0);
  await expect(page.locator('.hero-rotating')).toHaveText('bukti KYC-mu.');
  for (const width of [375, 768, 1024, 1440]) { await page.setViewportSize({ width, height: 900 }); await noOverflow(page); }
  await page.setViewportSize({ width: 375, height: 900 }); await page.screenshot({ path: 'artifacts/bankkyc-landing-mobile.png', fullPage: true });
  await accessible(page);
  await page.getByRole('link', { name: 'Mulai pengajuan', exact: true }).click(); await expect(page).toHaveURL(/\/register/);
});

test('auth: registration, validation, role from server, empty state, login failure and logout', async ({ page }) => {
  await page.goto('/register'); await page.getByRole('button', { name: 'Buat akun', exact: true }).click();
  await expect(page.getByText('Username minimal 3 karakter.')).toBeVisible();
  await page.getByLabel('Username', { exact: true }).fill('demo_user'); await page.getByLabel('Password', { exact: true }).fill('veltrix123'); await page.getByLabel('Konfirmasi password').fill('wrong');
  await page.getByRole('button', { name: 'Tampilkan password' }).click(); await expect(page.locator('#password')).toHaveAttribute('type', 'text');
  await page.getByRole('button', { name: 'Sembunyikan password' }).click();
  await page.getByRole('button', { name: 'Buat akun', exact: true }).click(); await expect(page.getByText('Konfirmasi password belum sesuai.')).toBeVisible();
  await page.getByLabel('Konfirmasi password').fill('veltrix123'); await page.getByRole('button', { name: 'Buat akun', exact: true }).click(); await expect(page.getByRole('alert').filter({ hasText: 'Username sudah digunakan.' })).toBeVisible();
  await page.getByLabel('Username', { exact: true }).fill('new_applicant'); await page.getByRole('button', { name: 'Buat akun', exact: true }).click(); await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('Username', { exact: true }).fill('new_applicant'); await page.getByLabel('Password', { exact: true }).fill('wrong'); await page.getByRole('button', { name: 'Masuk ke workspace' }).click(); await expect(page.getByRole('alert').filter({ hasText: 'Username atau password tidak sesuai.' })).toBeVisible();
  await page.getByLabel('Password', { exact: true }).fill('veltrix123'); await page.getByRole('button', { name: 'Masuk ke workspace' }).click(); await expect(page.getByRole('heading', { name: 'Belum ada pengajuan' })).toBeVisible();
  expect((await apiRequest(page, '/auth/me')).body.role).toBe('applicant');
  expect((await apiRequest(page, '/applications/case-1001')).status).toBe(404);
  await page.getByRole('button', { name: 'Keluar', exact: true }).click(); await expect(page).toHaveURL(/\/login/);
  await page.goto('/applicant/dashboard'); await expect(page).toHaveURL(/\/login\?expired=1/);
});

test('applicant: search/filter, profile privacy, previews, byte download and withdrawal', async ({ page }) => {
  await demoLogin(page); await page.screenshot({ path: 'artifacts/bankkyc-dashboard.png', fullPage: true });
  await page.getByLabel('Cari nomor pengajuan').fill('missing'); await expect(page.getByRole('heading', { name: 'Tidak ada yang cocok' })).toBeVisible();
  await page.getByLabel('Cari nomor pengajuan').fill(''); await page.getByLabel('Filter status').selectOption('DRAFT'); await expect(page.locator('.case-row')).toHaveCount(1); await page.getByLabel('Filter status').selectOption('all');
  await openSeed(page, 'VTX-2026-1001');
  await expect(page.getByText('Nara Contoh', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Lihat profil', exact: true }).click(); await expect(page.getByText('Nara Contoh', { exact: true })).toBeVisible(); await page.keyboard.press('Escape');
  await expect(page.getByText('Nara Contoh', { exact: true })).toHaveCount(0); await expect(page.getByRole('button', { name: 'Lihat profil', exact: true })).toBeFocused();
  const profile = await downloadBytes(page, () => page.getByRole('button', { name: 'Unduh JSON' }).click()); expect(JSON.parse(profile.data.toString()).identity_number).toMatch(/^DUMMY-/);
  await page.getByRole('button', { name: 'Preview identitas' }).click(); await expect(page.getByRole('dialog')).toBeVisible(); await expect(page.locator('iframe')).toHaveAttribute('title', 'Preview dokumen dummy'); await page.getByRole('button', { name: 'Tutup preview', exact: true }).click();
  await page.getByRole('button', { name: 'Preview video' }).click(); await expect(page.locator('video')).toHaveAttribute('controls', ''); await page.getByRole('button', { name: 'Tutup dialog', exact: true }).click();
  const video = await downloadBytes(page, () => page.locator('.evidence-group').filter({ hasText: 'Video verifikasi' }).getByRole('button', { name: 'Unduh versi 1', exact: true }).click()); expect(video.data.equals(await readFile('public/fixtures/verification-demo.mp4'))).toBe(true);
  await page.locator('summary').first().click(); await expect(page.getByRole('button', { name: 'Unduh v1 Scan identitas', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Tarik pengajuan', exact: true }).click(); await page.getByRole('button', { name: 'Batal', exact: true }).click();
  await page.getByRole('button', { name: 'Tarik pengajuan', exact: true }).click(); await page.getByRole('button', { name: 'Konfirmasi', exact: true }).click(); await expect(page.locator('.page-action')).toContainText('Ditarik'); await expect(page.getByRole('link', { name: 'Perbaiki pengajuan', exact: true })).toHaveCount(0);
});

test('wizard: required fields, invalid file signature, upload, submit, read-only and exact round trip', async ({ page }) => {
  test.setTimeout(100_000);
  await demoLogin(page); await page.getByRole('link', { name: 'Pengajuan baru', exact: true }).click(); await page.getByRole('button', { name: 'Buat draf & mulai' }).click();
  await expect(page).toHaveURL(/\/edit$/); const id = new URL(page.url()).pathname.split('/').at(-2)!;
  await page.getByRole('button', { name: 'Simpan & lanjutkan' }).click(); await expect(page.getByRole('alert').filter({ hasText: 'Periksa 8 kolom' })).toBeVisible();
  await page.getByRole('button', { name: 'Isi contoh dummy' }).click(); await page.getByLabel('Email contoh', { exact: true }).fill('real@gmail.com'); await page.getByRole('button', { name: 'Simpan & lanjutkan' }).click(); await expect(page.getByText('Gunakan alamat @example.com, @example.org, atau @example.net.')).toBeVisible();
  await page.getByLabel('Email contoh', { exact: true }).fill('dummy@example.com'); await page.getByRole('button', { name: 'Simpan & lanjutkan' }).click();
  await expect(page.getByRole('heading', { name: 'Scan identitas', exact: true })).toBeVisible();
  await noOverflow(page); await accessible(page);
  await page.getByLabel('Berkas Scan identitas', { exact: true }).setInputFiles({ name: 'bad.exe', mimeType: 'application/octet-stream', buffer: Buffer.from('bad') }); await expect(page.getByRole('alert').filter({ hasText: 'Format tidak didukung' })).toBeVisible();
  await page.getByLabel('Berkas Scan identitas', { exact: true }).setInputFiles({ name: 'bad.pdf', mimeType: 'application/pdf', buffer: Buffer.from('wrong signature') }); await page.getByRole('button', { name: 'Unggah berkas' }).click(); await expect(page.getByRole('alert').filter({ hasText: 'Isi file tidak sesuai format' })).toBeVisible();
  await page.getByLabel('Berkas Scan identitas', { exact: true }).setInputFiles({ name: 'dummy-identity.pdf', mimeType: 'application/pdf', buffer: pdf }); await page.getByRole('button', { name: 'Unggah berkas' }).click(); await expect(page.getByText('Versi 1 tersimpan dalam sesi', { exact: false })).toBeVisible(); await page.getByRole('button', { name: 'Lanjutkan', exact: true }).click();
  await page.getByLabel('Berkas Dokumen administrasi', { exact: true }).setInputFiles({ name: 'dummy-form.pdf', mimeType: 'application/pdf', buffer: pdf }); await page.getByRole('button', { name: 'Unggah berkas' }).click(); await expect(page.getByText('Versi 1 tersimpan dalam sesi', { exact: false })).toBeVisible(); await page.getByRole('button', { name: 'Lanjutkan', exact: true }).click();
  await page.getByLabel('Berkas Video verifikasi', { exact: true }).setInputFiles('public/fixtures/verification-demo.mp4'); await page.getByRole('button', { name: 'Unggah berkas' }).click(); await expect(page.getByText('Versi 1 tersimpan dalam sesi', { exact: false })).toBeVisible(); await page.getByRole('button', { name: 'Lanjutkan', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Kirim pengajuan', exact: true })).toBeDisabled(); await page.getByRole('checkbox').check(); await page.getByRole('button', { name: 'Kirim pengajuan', exact: true }).click(); await page.getByRole('button', { name: 'Ya, kirim pengajuan' }).click();
  await expect(page).toHaveURL(new RegExp(`/applications/${id}$`)); await expect(page.locator('.page-action')).toContainText('Terkirim'); await expect(page.getByRole('link', { name: 'Lanjutkan draf' })).toHaveCount(0);
  const downloaded = await downloadBytes(page, () => page.locator('.evidence-group').filter({ hasText: 'Dokumen administrasi' }).getByRole('button', { name: 'Unduh versi 1', exact: true }).click()); expect(downloaded.data.equals(pdf)).toBe(true);
  const application = (await apiRequest(page, `/applications/${id}`)).body;
  expect((await apiRequest(page, `/applications/${id}/personal-data`, 'PUT', { profile: {}, version: application.version })).body.error.code).toBe('CASE_READ_ONLY');
});

test('revision: new evidence version retained, resubmission, stale conflict and incomplete submit', async ({ page }) => {
  await demoLogin(page); const draft = (await apiRequest(page, '/applications/case-1002')).body;
  expect((await apiRequest(page, '/applications/case-1002/actions', 'POST', { action: 'submit', version: draft.version, synthetic_acknowledged: true })).body.error.code).toBe('CASE_INCOMPLETE');
  await openSeed(page, 'VTX-2026-1001'); await page.getByRole('link', { name: 'Perbaiki pengajuan', exact: true }).click(); await page.getByRole('button', { name: 'Simpan & lanjutkan' }).click();
  await page.getByRole('button', { name: 'Lanjutkan', exact: true }).click(); await page.getByLabel('Berkas Dokumen administrasi', { exact: true }).setInputFiles({ name: 'revision.pdf', mimeType: 'application/pdf', buffer: pdf }); await page.getByRole('button', { name: 'Unggah versi 2' }).click(); await expect(page.getByText('Versi 2 tersimpan dalam sesi', { exact: false })).toBeVisible(); await page.getByRole('button', { name: 'Lanjutkan', exact: true }).click(); await page.getByRole('button', { name: 'Lanjutkan', exact: true }).click(); await page.getByRole('checkbox').check(); await page.getByRole('button', { name: 'Kirim ulang pengajuan' }).click(); await page.getByRole('button', { name: 'Ya, kirim pengajuan' }).click();
  await expect(page.locator('.page-action')).toContainText('Dikirim ulang'); const evidence = (await apiRequest(page, '/applications/case-1001')).body.evidence;
  expect(evidence.filter((e: { category: string }) => e.category === 'document')).toHaveLength(2);
  const group = page.locator('.evidence-group').filter({ hasText: 'Dokumen administrasi' }); await group.locator('summary').click(); await expect(group.getByRole('button', { name: 'Unduh v1 Dokumen administrasi', exact: true })).toBeVisible();
  expect((await apiRequest(page, '/applications/case-1001/actions', 'POST', { action: 'resubmit', version: 1, synthetic_acknowledged: true })).body.error.code).toBe('VERSION_CONFLICT');
});

test('reviewer: assigned scope, no plaintext, metadata review, revision and terminal decisions', async ({ page }) => {
  await demoLogin(page, 'reviewer'); await expect(page.locator('.case-row')).toHaveCount(2);
  expect((await apiRequest(page, '/applications/case-2001')).status).toBe(404);
  const metadata = (await apiRequest(page, '/applications/case-1003')).body;
  expect(JSON.stringify(metadata)).not.toContain('display_name'); expect(JSON.stringify(metadata)).not.toContain('nara@example.com');
  expect((await apiRequest(page, '/applications/case-1003/personal-data')).status).toBe(404);
  expect((await apiRequest(page, '/applications/case-1003/evidence/case-1003-identity-v1/download')).status).toBe(404);
  await openSeed(page, 'VTX-2026-1003'); await expect(page.getByRole('button', { name: /Preview|Unduh|Lihat profil/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Mulai tinjauan', exact: true }).click(); await page.getByRole('button', { name: 'Konfirmasi', exact: true }).click(); await expect(page.locator('.page-action')).toContainText('Dalam tinjauan');
  await page.getByRole('button', { name: 'Minta revisi', exact: true }).click(); await expect(page.getByRole('button', { name: 'Konfirmasi', exact: true })).toBeDisabled(); await page.getByLabel('Catatan operasional').fill('Lengkapi halaman tujuan rekening pada dokumen dummy.'); await page.getByRole('button', { name: 'Konfirmasi', exact: true }).click(); await expect(page.locator('.page-action')).toContainText('Perlu revisi');
  await page.screenshot({ path: 'artifacts/bankkyc-reviewer.png', fullPage: true });
  // New case state from fixture permits the accept branch without manufacturing a UI success.
  await demoLogin(page, 'admin', false); await page.locator('.assignment-row').filter({ hasText: 'VTX-2026-2002' }).getByRole('button').click(); await page.getByLabel('Reviewer', { exact: true }).selectOption('reviewer-demo'); await page.getByRole('button', { name: 'Simpan penugasan' }).click();
  await demoLogin(page, 'reviewer', false); await openSeed(page, 'VTX-2026-2002'); await page.getByRole('button', { name: 'Mulai tinjauan', exact: true }).click(); await page.getByRole('button', { name: 'Konfirmasi', exact: true }).click(); await page.getByRole('button', { name: 'Terima', exact: true }).click(); await page.getByRole('button', { name: 'Konfirmasi', exact: true }).click(); await expect(page.locator('.page-action')).toContainText('Diterima'); await expect(page.getByRole('button', { name: 'Minta revisi', exact: true })).toHaveCount(0);
});

test('admin: assignment, metadata-only, reassignment, role guard and reviewer reject', async ({ page }) => {
  await demoLogin(page, 'admin'); await page.screenshot({ path: 'artifacts/bankkyc-admin.png', fullPage: true });
  const list = (await apiRequest(page, '/admin/assignments')).body; expect(JSON.stringify(list.items)).not.toContain('display_name'); expect((await apiRequest(page, '/applications/case-1003/personal-data')).status).toBe(404);
  await page.locator('.assignment-row').filter({ hasText: 'VTX-2026-2002' }).getByRole('button').click(); await page.getByRole('button', { name: 'Batal', exact: true }).click();
  await page.locator('.assignment-row').filter({ hasText: 'VTX-2026-2002' }).getByRole('button').click(); await page.getByLabel('Reviewer', { exact: true }).selectOption('reviewer-demo'); await page.getByRole('button', { name: 'Simpan penugasan' }).click(); await expect(page.locator('.assignment-row').filter({ hasText: 'VTX-2026-2002' })).toContainText('Reviewer Utama');
  await demoLogin(page, 'reviewer', false); await openSeed(page, 'VTX-2026-2002'); await page.getByRole('button', { name: 'Mulai tinjauan', exact: true }).click(); await page.getByRole('button', { name: 'Konfirmasi', exact: true }).click(); await page.getByRole('button', { name: 'Tolak', exact: true }).click(); await page.getByLabel('Catatan operasional').fill('Bukti belum lengkap untuk melanjutkan pengajuan.'); await page.getByRole('button', { name: 'Konfirmasi', exact: true }).click(); await expect(page.locator('.page-action')).toContainText('Ditolak');
  expect((await apiRequest(page, '/admin/assignments')).status).toBe(403);
  await page.goto('/applicant/dashboard'); await expect(page.getByRole('heading', { name: 'Akses dibatasi' })).toBeVisible();
});

test('lab: isolated fixtures, min trials, result, CSV simulation label, history and verification', async ({ page }) => {
  await demoLogin(page, 'evaluator'); await expect(page.getByRole('heading', { name: 'Belum ada hasil perbandingan' })).toBeVisible();
  expect((await apiRequest(page, '/applications')).status).toBe(403);
  await page.getByLabel('Pengulangan', { exact: true }).fill('10'); await expect(page.getByRole('button', { name: 'Jalankan simulasi' })).toBeDisabled(); await page.getByLabel('Pengulangan', { exact: true }).fill('30'); await page.getByLabel('Data uji', { exact: true }).selectOption('video-mp4'); await page.getByRole('button', { name: 'Jalankan simulasi' }).click(); await expect(page.getByRole('heading', { name: 'Perbandingan median waktu' })).toBeVisible();
  const csv = await downloadBytes(page, () => page.getByRole('button', { name: 'Ekspor CSV simulasi' }).click()); expect(csv.download.suggestedFilename()).toContain('SIMULATED'); expect(csv.data.toString()).toContain('SIMULATED DATA - NOT VALID EXPERIMENTAL EVIDENCE');
  await page.locator('.lab-history-row').click();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: 'artifacts/bankkyc-lab.png', fullPage: true });
  await page.getByRole('link', { name: 'Verifikasi integritas', exact: true }).click(); await page.getByRole('button', { name: 'Jalankan simulasi' }).click(); await expect(page.getByRole('heading', { name: 'Kecocokan hasil pemulihan' })).toBeVisible(); await expect(page.getByText('Belum dijalankan', { exact: true })).toBeVisible(); await accessible(page);
});

test('mobile, keyboard dialog, both themes, session expiry and error state', async ({ page }) => {
  test.setTimeout(120_000); await page.setViewportSize({ width: 375, height: 812 }); await demoLogin(page);
  await noOverflow(page); await page.getByRole('button', { name: 'Buka menu', exact: true }).click(); await expect(page.getByRole('link', { name: 'VELTRIX', exact: true })).toBeFocused(); await page.keyboard.press('Escape'); await expect(page.getByRole('button', { name: 'Buka menu', exact: true })).toBeFocused();
  await page.getByRole('button', { name: 'Buka menu', exact: true }).click(); await page.getByRole('link', { name: 'Pengajuan saya', exact: true }).click(); await expect(page).toHaveURL(/\/applicant\/applications$/); await openSeed(page, 'VTX-2026-1001');
  await page.getByRole('button', { name: 'Tarik pengajuan', exact: true }).click(); await page.keyboard.press('Tab'); await expect(page.getByRole('button', { name: 'Batal', exact: true })).toBeFocused(); await page.keyboard.press('Escape'); await expect(page.getByRole('button', { name: 'Tarik pengajuan', exact: true })).toBeFocused();
  await accessible(page); await page.getByRole('button', { name: 'Gunakan tema gelap' }).click(); await accessible(page); await noOverflow(page); await page.screenshot({ path: 'artifacts/bankkyc-detail-mobile-dark.png', fullPage: true });
  for (const width of [768, 1024, 1440]) { await page.setViewportSize({ width, height: 900 }); await noOverflow(page); }
  await page.getByRole('link', { name: 'Perbaiki pengajuan', exact: true }).click(); await accessible(page); await page.screenshot({ path: 'artifacts/bankkyc-wizard-dark.png', fullPage: true });
  await page.context().clearCookies(); await page.getByRole('button', { name: 'Isi contoh dummy' }).click(); await page.getByRole('button', { name: 'Simpan & lanjutkan' }).click(); await expect(page).toHaveURL(/\/login\?expired=1/);
  await demoLogin(page); await page.goto('/applicant/applications/not-owned'); await expect(page.getByRole('alert').filter({ hasText: 'Pengajuan tidak ditemukan' })).toBeVisible(); await page.getByRole('button', { name: 'Coba lagi', exact: true }).click(); await expect(page.getByRole('alert').filter({ hasText: 'Pengajuan tidak ditemukan' })).toBeVisible();
});

test('role layouts: both themes and four breakpoints, navigation and accessibility', async ({ page }) => {
  test.setTimeout(180_000);
  for (const role of ['applicant', 'reviewer', 'admin', 'evaluator']) {
    await page.setViewportSize({ width: 1440, height: 950 });
    await demoLogin(page, role);
    for (const theme of ['light', 'dark']) {
      const current = await page.locator('html').getAttribute('data-theme');
      if (current !== theme) await page.getByRole('button', { name: theme === 'dark' ? 'Gunakan tema gelap' : 'Gunakan tema terang' }).click();
      for (const width of [375, 768, 1024, 1440]) { await page.setViewportSize({ width, height: 900 }); await noOverflow(page); }
      await accessible(page);
      await page.setViewportSize({ width: 375, height: 900 }); await accessible(page);
    }
  }
});

test('landing destinations, empty filters, full keyboard trap and unsaved form warning', async ({ page }) => {
  await page.goto('/');
  for (const role of ['applicant', 'reviewer', 'admin', 'evaluator']) {
    await page.locator(`.permission-row[href='/login?role=${role}']`).click();
    await expect(page).toHaveURL(new RegExp(`role=${role}`)); await expect(page.getByLabel('Username', { exact: true })).toHaveValue('');
    await expect(page.locator('.demo-login')).toHaveCount(0);
    await noOverflow(page);
    await expect(page.getByText('Gunakan data sintetis. Data belum dienkripsi, tersimpan sementara di browser, dan hilang saat halaman dimuat ulang.')).toBeVisible();
    await page.getByRole('link', { name: 'Kembali ke beranda', exact: true }).click();
  }
  await page.getByRole('link', { name: 'Masuk', exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill('demo_user'); await page.getByLabel('Password', { exact: true }).fill('veltrix123'); await page.getByRole('button', { name: 'Masuk ke workspace', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Pengajuanmu, terpantau.' })).toBeVisible(); await openSeed(page, 'VTX-2026-1001');
  await page.getByRole('button', { name: 'Tarik pengajuan', exact: true }).click();
  await page.getByRole('button', { name: 'Konfirmasi', exact: true }).focus(); await page.keyboard.press('Tab'); await expect(page.getByRole('button', { name: 'Tutup dialog', exact: true })).toBeFocused();
  await page.keyboard.press('Shift+Tab'); await expect(page.getByRole('button', { name: 'Konfirmasi', exact: true })).toBeFocused(); await page.keyboard.press('Escape');
  await page.getByRole('link', { name: 'Perbaiki pengajuan', exact: true }).click(); await page.getByLabel('Nama lengkap fiktif', { exact: true }).fill('Nama Dummy Berubah');
  page.once('dialog', dialog => dialog.dismiss()); await page.getByRole('link', { name: 'Detail pengajuan', exact: true }).click(); await expect(page).toHaveURL(/\/edit$/);
  await page.getByRole('button', { name: 'Simpan & lanjutkan', exact: true }).click(); await page.getByRole('button', { name: 'Kembali', exact: true }).click(); await expect(page.getByLabel('Nama lengkap fiktif', { exact: true })).toHaveValue('Nama Dummy Berubah');
});

test('mock worker: full reload preserves fixture login without registration races', async ({ page }) => {
  await demoLogin(page);
  for (let i = 0; i < 5; i++) {
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Pengajuanmu, terpantau.' })).toBeVisible();
    await expect(page.locator('.case-row')).toHaveCount(3);
  }
  await page.getByRole('button', { name: 'Keluar', exact: true }).click();
  await expect(page).toHaveURL(/\/login/);
});
