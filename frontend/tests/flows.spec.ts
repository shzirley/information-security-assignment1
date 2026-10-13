import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';

const sampleId = '11111111-1111-4111-8111-111111111111';
async function demoLogin(page: Page) {
  await page.goto('/login');
  await page.getByRole('button', { name: 'Gunakan akun demo' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible();
}
async function noOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.width);
}
async function downloadBytes(page: Page, action: () => Promise<unknown>) {
  const download = page.waitForEvent('download'); await action();
  const file = await download; const path = await file.path();
  expect(path).not.toBeNull(); return { file, data: await readFile(path!) };
}

test('beranda, register, validasi, login gagal, akun baru, logout', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Your data/ })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Inter');
  expect(await page.locator('h1').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Montserrat');
  expect(await page.locator('.brand-symbol').first().evaluate(el => (el as HTMLImageElement).complete && (el as HTMLImageElement).naturalWidth > 0)).toBe(true);
  await page.screenshot({ path: 'artifacts/landing-branded.png', fullPage: true });
  await page.getByRole('button', { name: 'Gunakan tema gelap' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
  await page.getByRole('link', { name: 'Buat akun', exact: true }).click();
  await page.getByRole('button', { name: 'Buat akun', exact: true }).click();
  await expect(page.getByText('Username minimal 3 karakter.')).toBeVisible();
  await page.getByLabel('Username', { exact: true }).fill('demo_user');
  await page.getByLabel('Password', { exact: true }).fill('veltrix123');
  await page.getByLabel('Konfirmasi password').fill('notmatching');
  await page.getByRole('button', { name: 'Tampilkan password' }).click();
  await expect(page.locator('#password')).toHaveAttribute('type', 'text');
  await page.getByRole('button', { name: 'Sembunyikan password' }).click();
  await page.getByRole('button', { name: 'Buat akun', exact: true }).click();
  await expect(page.getByText('Konfirmasi password belum sesuai.')).toBeVisible();
  await page.getByLabel('Konfirmasi password').fill('veltrix123');
  await page.getByRole('button', { name: 'Buat akun', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Username sudah digunakan.' })).toBeVisible();
  await page.getByLabel('Username', { exact: true }).fill('new_user');
  await page.getByRole('button', { name: 'Buat akun', exact: true }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('Username', { exact: true }).fill('new_user');
  await page.getByLabel('Password', { exact: true }).fill('wrong');
  await page.getByRole('button', { name: 'Masuk ke workspace' }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Username atau password tidak sesuai.' })).toBeVisible();
  await page.getByLabel('Password', { exact: true }).fill('veltrix123');
  await page.getByRole('button', { name: 'Masuk ke workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Vault kamu masih kosong' })).toBeVisible();
  const status = await page.evaluate(async id => (await fetch(`/api/v1/vault/files/${id}`)).status, sampleId);
  expect(status).toBe(404);
  await page.getByRole('button', { name: 'Keluar', exact: true }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto('/vault');
  await expect(page).toHaveURL(/\/login/);
});

test('kontrol pendukung dan kontras halaman pada dua tema', async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto('/');
  await page.getByRole('link', { name: 'Masuk', exact: true }).click();
  await page.getByRole('link', { name: 'Kembali ke beranda' }).click();
  await page.getByRole('link', { name: 'Masuk ke workspace', exact: true }).click();
  await page.getByRole('link', { name: 'Buat akun', exact: true }).click();
  await page.getByRole('link', { name: 'Masuk', exact: true }).click();
  await page.getByRole('button', { name: 'Gunakan akun demo' }).click();
  await page.getByRole('link', { name: 'VELTRIX', exact: true }).click();
  await page.getByRole('link', { name: 'Semua file', exact: true }).click();
  await page.getByRole('button', { name: 'Upload file', exact: true }).click();
  await page.getByRole('button', { name: 'Tutup dialog', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Upload file', exact: true })).toBeFocused();
  await page.setViewportSize({ width: 375, height: 900 });
  await page.getByRole('button', { name: 'Buka menu', exact: true }).click();
  await page.getByRole('button', { name: 'Tutup menu', exact: true }).click();
  await page.getByRole('button', { name: 'Buka menu', exact: true }).click();
  await page.getByRole('button', { name: 'Tutup menu navigasi', exact: true }).click({ position: { x: 340, y: 300 } });
  await expect(page.getByRole('button', { name: 'Buka menu', exact: true })).toHaveAttribute('aria-expanded', 'false');
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => { localStorage.setItem('veltrix-theme', value); }, theme);
    for (const path of ['/', '/login', '/register', '/personal-data', `/vault/${sampleId}`]) {
      await page.goto(path);
      await expect(page.locator('h1').first()).toBeVisible();
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
      expect(audit.violations, `${theme} ${path}: ${JSON.stringify(audit.violations)}`).toEqual([]);
    }
  }
  await page.goto(`/lab?file=${sampleId}`);
  await page.getByRole('button', { name: 'Jalankan benchmark' }).click();
  await expect(page.getByRole('heading', { name: 'Hasil simulasi crypto' })).toBeVisible();
  await page.getByRole('button', { name: 'Tutup pesan' }).click();
  await page.locator('.recharts-bar-rectangle').last().hover();
  const chartAudit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  expect(chartAudit.violations, JSON.stringify(chartAudit.violations)).toEqual([]);
  await page.goto('/brand/preview.html');
  await page.evaluate(() => document.fonts.ready);
  const images = await page.locator('img').evaluateAll(nodes => nodes.every(node => (node as HTMLImageElement).complete && (node as HTMLImageElement).naturalWidth > 0));
  expect(images).toBe(true);
  await page.screenshot({ path: 'artifacts/brand-assets.png', fullPage: true });
});

test('vault: filter, search, upload, validasi, tiga jalur download identik, delete', async ({ page }) => {
  await demoLogin(page);
  await page.getByRole('link', { name: 'File Vault', exact: true }).click();
  await page.getByRole('button', { name: 'Video', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Belum ada file yang cocok' })).toBeVisible();
  await page.getByRole('button', { name: 'Reset filter' }).click();
  await page.getByRole('button', { name: 'Kartu identitas', exact: true }).click();
  await expect(page.getByText('gambar-dummy.png').first()).toBeVisible();
  await page.getByRole('button', { name: 'Dokumen', exact: true }).click();
  await page.getByLabel('Cari nama file').fill('not-present');
  await expect(page.getByRole('heading', { name: 'Belum ada file yang cocok' })).toBeVisible();
  await page.getByRole('button', { name: 'Reset filter' }).click();
  await page.getByRole('button', { name: 'Upload file', exact: true }).click();
  const input = page.getByLabel('Pilih file untuk upload');
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Pilih file', exact: true }).click();
  await (await chooser).setFiles([]);
  await input.setInputFiles({ name: 'bad.exe', mimeType: 'application/octet-stream', buffer: Buffer.from('dummy') });
  await expect(page.getByRole('alert').filter({ hasText: 'Format tidak sesuai.' })).toBeVisible();
  await input.setInputFiles({ name: 'oversized.pdf', mimeType: 'application/pdf', buffer: Buffer.alloc(25_000_001) });
  await expect(page.getByRole('alert').filter({ hasText: 'Ukuran file melebihi batas 25 MB.' })).toBeVisible();
  await input.setInputFiles({ name: 'empty.pdf', mimeType: 'application/pdf', buffer: Buffer.alloc(0) });
  await expect(page.getByRole('alert').filter({ hasText: 'File kosong.' })).toBeVisible();
  const content = Buffer.from('%PDF-1.4\nDummy round-trip file for frontend testing\n%%EOF');
  const filename = 'dokumen-dummy-dengan-nama-panjang-untuk-pengujian-layout.pdf';
  await input.setInputFiles({ name: filename, mimeType: 'application/pdf', buffer: content });
  await page.getByRole('button', { name: 'Hapus pilihan file' }).click();
  await input.setInputFiles({ name: filename, mimeType: 'application/pdf', buffer: content });
  await page.getByRole('button', { name: 'Simulasikan enkripsi & simpan' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('link', { name: new RegExp(filename.replaceAll('.', '\\.')) }).first().click();
  await expect(page.getByRole('heading', { name: filename })).toBeVisible();
  for (const algorithm of ['AES', 'RC4', 'DES']) {
    await page.getByRole('button', { name: new RegExp(`^${algorithm}`) }).click();
    const saved = await downloadBytes(page, () => page.getByRole('button', { name: 'Download file demo' }).click());
    expect(saved.file.suggestedFilename()).toBe(filename); expect(saved.data).toEqual(content);
  }
  await page.getByRole('button', { name: 'Hapus file', exact: true }).click();
  await page.getByRole('button', { name: 'Batal', exact: true }).click();
  await page.getByRole('button', { name: 'Hapus file', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Hapus file', exact: true }).click();
  await expect(page).toHaveURL(/\/vault$/);
  await expect(page.getByText(filename)).toHaveCount(0);
  await page.getByRole('button', { name: 'Upload file', exact: true }).click();
  await page.getByLabel('Kategori file').selectOption('identity');
  await input.setInputFiles({ name: 'dummy.png', mimeType: 'image/png', buffer: Buffer.from('dummy image fixture') });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('button', { name: 'Upload file', exact: true }).click();
  await page.getByLabel('Kategori file').selectOption('video');
  await input.setInputFiles({ name: 'dummy.mp4', mimeType: 'video/mp4', buffer: Buffer.from('dummy video fixture') });
  await page.getByRole('button', { name: 'Batal', exact: true }).click();
  await page.goto('/vault/unknown-id');
  await expect(page.getByRole('alert').filter({ hasText: 'Data tidak ditemukan' })).toBeVisible();
  await page.getByRole('button', { name: 'Coba lagi' }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Data tidak ditemukan' })).toBeVisible();
  await page.getByRole('link', { name: 'Kembali ke Vault' }).click();
});

test('profil: reveal tiga cipher, hide, edit, validasi, dummy, cancel dan delete', async ({ page }) => {
  await demoLogin(page);
  await page.getByRole('link', { name: 'Buka data pribadi' }).click();
  await expect(page.getByText('Pengguna Demo', { exact: true })).toHaveCount(0);
  for (const algorithm of ['AES', 'RC4', 'DES']) {
    await page.getByRole('button', { name: new RegExp(`^${algorithm}`) }).click();
    await page.getByRole('button', { name: 'Tampilkan data', exact: true }).click();
    await expect(page.getByText('Pengguna Demo', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Sembunyikan data', exact: true }).click();
    await expect(page.getByText('Pengguna Demo', { exact: true })).toHaveCount(0);
  }
  await page.getByRole('button', { name: 'Edit profil' }).click();
  await page.getByLabel('Email', { exact: true }).fill('invalid');
  await page.getByRole('button', { name: 'Simpan profil demo' }).click();
  await expect(page.getByText('Format email belum sesuai.')).toBeVisible();
  await page.getByRole('button', { name: 'Batal' }).click();
  await page.getByRole('button', { name: 'Edit profil' }).click();
  await page.getByRole('button', { name: 'Isi contoh dummy' }).click();
  await page.getByLabel('Nama lengkap').fill('Profil Uji Dummy');
  await page.getByRole('button', { name: 'Simpan profil demo' }).click();
  await page.getByRole('button', { name: 'Tampilkan data', exact: true }).click();
  await expect(page.getByText('Profil Uji Dummy', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Hapus profil', exact: true }).click();
  await page.getByRole('button', { name: 'Batal' }).click();
  await page.getByRole('button', { name: 'Hapus profil', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Hapus profil', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Belum ada data pribadi' })).toBeVisible();
  await page.getByRole('button', { name: 'Tambah data dummy' }).click();
  await page.getByRole('button', { name: 'Simpan profil demo' }).click();
  await expect(page.getByText('Nama lengkap wajib diisi.')).toBeVisible();
  await page.getByRole('button', { name: 'Isi contoh dummy' }).click();
  await page.getByRole('button', { name: 'Simpan profil demo' }).click();
  await expect(page.getByRole('button', { name: 'Tampilkan data', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click();
  await page.getByRole('link', { name: 'Data Pribadi', exact: true }).click();
  await expect(page.getByText('Pengguna Contoh', { exact: true })).toHaveCount(0);
});

test('lab: crypto charts, raw CSV, histori, download repeat, stop dan CSV', async ({ page }) => {
  await demoLogin(page);
  await page.goto(`/vault/${sampleId}`);
  await page.getByRole('link', { name: /Uji file ini di Lab/ }).click();
  await expect(page.getByLabel('Sumber data')).toHaveValue(`file:${sampleId}`);
  await page.getByLabel('Pengulangan').selectOption('20');
  await page.getByRole('button', { name: 'Jalankan benchmark' }).click();
  await expect(page.getByRole('heading', { name: 'Hasil simulasi crypto' })).toBeVisible();
  await page.screenshot({ path: 'artifacts/lab-desktop.png', fullPage: true });
  const cryptoCsv = await downloadBytes(page, () => page.getByRole('button', { name: 'Ekspor CSV', exact: true }).click());
  const csvText = cryptoCsv.data.toString();
  expect(csvText).toContain('SIMULATED'); expect(csvText.split('\r\n')).toHaveLength(61);
  await page.locator('.history-row').last().click();
  await expect(page.getByRole('heading', { name: 'Catatan eksperimen' })).toBeVisible();
  await page.getByRole('link', { name: 'Kembali ke Cryptography Lab' }).click();
  await page.getByRole('button', { name: 'Uji Download', exact: true }).click();
  await page.getByLabel('Sumber data').selectOption(`file:${sampleId}`);
  await page.getByRole('button', { name: 'Mulai uji download' }).click();
  await expect(page.getByRole('button', { name: 'Ekspor CSV', exact: true })).toBeEnabled({ timeout: 20_000 });
  const downloadCsv = await downloadBytes(page, () => page.getByRole('button', { name: 'Ekspor CSV', exact: true }).click());
  const downloadText = downloadCsv.data.toString();
  expect(downloadText).toContain('CLIENT-MEASURED-MOCK'); expect(downloadText.split('\r\n')).toHaveLength(31);
  await page.getByLabel('Pengulangan').selectOption('30');
  await page.getByRole('button', { name: 'Mulai uji download' }).click();
  await page.getByRole('button', { name: 'Hentikan uji' }).click();
  await expect(page.getByRole('button', { name: 'Mulai uji download' })).toBeEnabled();
  await page.getByRole('button', { name: 'Benchmark Crypto', exact: true }).click();
  await page.getByLabel('Sumber data').selectOption('personal_data:44444444-4444-4444-8444-444444444444');
  await page.getByRole('button', { name: 'Jalankan benchmark' }).click();
  await expect(page.getByRole('heading', { name: 'Hasil simulasi crypto' })).toBeVisible();
});

test('session berakhir membersihkan reveal dan membatasi API', async ({ page }) => {
  await demoLogin(page);
  await page.getByRole('link', { name: 'Data Pribadi', exact: true }).click();
  await page.getByRole('button', { name: 'Tampilkan data', exact: true }).click();
  await expect(page.getByText('Pengguna Demo', { exact: true })).toBeVisible();
  await page.context().clearCookies();
  await page.getByRole('button', { name: 'Edit profil' }).click();
  await expect(page).toHaveURL(/\/login\?expired=1/);
  await expect(page.getByText('Pengguna Demo', { exact: true })).toHaveCount(0);
});

test('mobile/tablet, keyboard, dialog focus, tema, aksesibilitas dan screenshot', async ({ page }, testInfo) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await demoLogin(page);
  await page.screenshot({ path: 'artifacts/dashboard-desktop.png', fullPage: true });
  for (const theme of ['light', 'dark']) {
    if (theme === 'dark') await page.getByRole('button', { name: 'Gunakan tema gelap' }).click();
    const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(accessibility.violations, JSON.stringify(accessibility.violations, null, 2)).toEqual([]);
    await noOverflow(page);
  }
  await page.screenshot({ path: 'artifacts/dashboard-dark.png', fullPage: true });
  await page.getByRole('button', { name: 'Gunakan tema terang' }).click();
  for (const width of [375, 768]) {
    await page.setViewportSize({ width, height: 900 }); await noOverflow(page);
    for (const path of ['/personal-data', '/vault', `/vault/${sampleId}`, '/lab', '/']) {
      await page.goto(path); await expect(page.locator('h1').first()).toBeVisible(); await noOverflow(page);
    }
  }
  await page.setViewportSize({ width: 375, height: 900 }); await page.goto('/dashboard');
  await page.getByRole('button', { name: 'Buka menu', exact: true }).click();
  await page.getByRole('link', { name: 'File Vault', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'File Vault', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Buka menu', exact: true }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Buka menu', exact: true })).toHaveAttribute('aria-expanded', 'false');
  await page.getByRole('button', { name: 'Upload file', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Tab'); await page.keyboard.press('Shift+Tab');
  expect(await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]'))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Upload file', exact: true })).toBeFocused();
  await page.screenshot({ path: 'artifacts/vault-mobile.png', fullPage: true });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.getByRole('button', { name: 'Gunakan tema gelap' }).click();
  const mobileA11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  expect(mobileA11y.violations, JSON.stringify(mobileA11y.violations, null, 2)).toEqual([]);
  await noOverflow(page); expect(errors).toEqual([]);
  await page.goto('/lab');
  await page.getByLabel('Sumber data').selectOption(`file:${sampleId}`);
  await page.getByRole('button', { name: 'Jalankan benchmark' }).click();
  await expect(page.getByRole('heading', { name: 'Hasil simulasi crypto' })).toBeVisible();
  await noOverflow(page);
  await page.screenshot({ path: 'artifacts/lab-mobile-dark.png', fullPage: true });
  const labA11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  expect(labA11y.violations, JSON.stringify(labA11y.violations, null, 2)).toEqual([]);
  await testInfo.attach('browser-errors', { body: JSON.stringify(errors), contentType: 'application/json' });
});
