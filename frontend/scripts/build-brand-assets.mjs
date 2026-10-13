import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = path.join(root, 'public', 'brand');
const font = (family, weight) => readFile(path.join(root, 'node_modules', '@fontsource', family, 'files', `${family}-latin-${weight}-normal.woff2`));
const [montserrat, inter] = await Promise.all([font('montserrat', 700), font('inter', 400)]);
await Promise.all([writeFile(path.join(target, 'montserrat-700.woff2'), montserrat), writeFile(path.join(target, 'inter-400.woff2'), inter)]);
const embeddedFonts = `<style>@font-face{font-family:Montserrat;src:url(data:font/woff2;base64,${montserrat.toString('base64')}) format('woff2');font-weight:700}@font-face{font-family:Inter;src:url(data:font/woff2;base64,${inter.toString('base64')}) format('woff2');font-weight:400}</style>`;

for (const variant of ['color', 'light', 'dark']) {
  const name = variant === 'color' ? 'veltrix-symbol.svg' : `veltrix-symbol-${variant}.svg`;
  const symbol = await readFile(path.join(target, name), 'utf8');
  const body = symbol.slice(symbol.indexOf('>', symbol.indexOf('<svg')) + 1, symbol.lastIndexOf('</svg>'));
  const foreground = variant === 'light' ? '#FFFFFF' : '#0B132B';
  const secondary = variant === 'light' ? '#CBD5E1' : '#475569';
  const common = `<title>VELTRIX logo (${variant}), reconstructed from the supplied brand board</title>${embeddedFonts}`;
  const primary = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 630 180">${common}<g transform="translate(10 9) scale(.8)">${body}</g><text x="195" y="92" font-family="Montserrat,sans-serif" font-weight="700" font-size="48" letter-spacing="9" fill="${foreground}">VELTRIX</text><text x="199" y="124" font-family="Inter,sans-serif" font-size="13" letter-spacing="3.2" fill="${secondary}">YOUR DATA. YOUR CONTROL.</text></svg>`;
  const stacked = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 390">${common}<g transform="translate(150 12)">${body}</g><text x="250" y="292" text-anchor="middle" font-family="Montserrat,sans-serif" font-weight="700" font-size="51" letter-spacing="10" fill="${foreground}">VELTRIX</text><text x="250" y="330" text-anchor="middle" font-family="Inter,sans-serif" font-size="13" letter-spacing="3.4" fill="${secondary}">YOUR DATA. YOUR CONTROL.</text></svg>`;
  await writeFile(path.join(target, `veltrix-primary-${variant}.svg`), primary);
  await writeFile(path.join(target, `veltrix-stacked-${variant}.svg`), stacked);
  const iconBackground = variant === 'dark' ? '#F1F5F9' : '#0B132B';
  const iconBody = variant === 'dark'
    ? (await readFile(path.join(target, 'veltrix-symbol.svg'), 'utf8')).split(/<svg[^>]*>/)[1].split('</svg>')[0]
    : body;
  const icon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><title>VELTRIX app icon (${variant})</title><rect width="256" height="256" rx="52" fill="${iconBackground}"/><g transform="translate(38 36) scale(.9)">${iconBody}</g></svg>`;
  await writeFile(path.join(target, `veltrix-app-${variant === 'color' ? 'color' : variant === 'light' ? 'monochrome' : 'cloud'}.svg`), icon);
}
console.log('Created six standalone logo lockups, three app icons, and self-hosted preview fonts.');
