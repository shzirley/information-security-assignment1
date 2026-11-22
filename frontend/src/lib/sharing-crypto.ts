/**
 * Client-side Web Crypto helpers for Assignment 2 (Key Management & Data Sharing).
 *
 * - RSA-OAEP-256 (2048-bit) key pair generation in the browser.
 * - SPKI Public Key PEM export (sent to server via PUT /api/v1/keys/me).
 * - PKCS#8 Private Key PEM export, downloaded once as a file the user keeps. It is never sent
 *   to the server and never stored in browser storage, where an XSS bug could read it.
 * - Unpacking & decrypting VELTRIX-SHARE-1.<base64url> out-of-band key packages.
 */

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToUint8Array(base64: string): Uint8Array {
  const cleaned = base64.replace(/\s+/g, '');
  const binary = atob(cleaned);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function base64UrlToUint8Array(base64url: string): Uint8Array {
  let base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const pad = base64.length % 4;
  if (pad) base64 += '='.repeat(4 - pad);
  return base64ToUint8Array(base64);
}

function formatPem(base64: string, label: 'PUBLIC KEY' | 'PRIVATE KEY'): string {
  const lines = base64.match(/.{1,64}/g) ?? [base64];
  return `-----BEGIN ${label}-----\n${lines.join('\n')}\n-----END ${label}-----`;
}

function parsePemToDer(pem: string, label: 'PUBLIC KEY' | 'PRIVATE KEY'): ArrayBuffer {
  const normalized = pem.trim().replace(/\r\n/g, '\n');
  const header = `-----BEGIN ${label}-----`;
  const footer = `-----END ${label}-----`;
  if (!normalized.includes(header) || !normalized.includes(footer)) {
    throw new Error(`Format PEM tidak valid. Pastikan memuat ${header}.`);
  }
  const body = normalized
    .replace(header, '')
    .replace(footer, '')
    .replace(/\s+/g, '');
  const bytes = base64ToUint8Array(body);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

export interface GeneratedKeyPair {
  publicKeyPem: string;
  privateKeyPem: string;
  fingerprint: string;
}

export async function generateRsaKeyPair(): Promise<GeneratedKeyPair> {
  if (typeof window === 'undefined' || !window.crypto?.subtle) {
    throw new Error('Web Crypto API tidak tersedia pada browser ini (gunakan localhost atau HTTPS).');
  }

  const keyPair = await window.crypto.subtle.generateKey(
    {
      name: 'RSA-OAEP',
      modulusLength: 2048,
      publicExponent: new Uint8Array([0x01, 0x00, 0x01]), // 65537
      hash: 'SHA-256',
    },
    true,
    ['encrypt', 'decrypt'],
  );

  const spki = await window.crypto.subtle.exportKey('spki', keyPair.publicKey);
  const pkcs8 = await window.crypto.subtle.exportKey('pkcs8', keyPair.privateKey);

  const digest = await window.crypto.subtle.digest('SHA-256', spki);
  const fingerprint = Array.from(new Uint8Array(digest))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 16);

  return {
    publicKeyPem: formatPem(arrayBufferToBase64(spki), 'PUBLIC KEY'),
    privateKeyPem: formatPem(arrayBufferToBase64(pkcs8), 'PRIVATE KEY'),
    fingerprint,
  };
}

export interface UnpackedShareKey {
  requestId: string;
  keyFingerprint: string;
  algorithm: string;
  shareKeyBase64: string;
}

export interface ParsedSharePackage {
  v: number;
  request_id: string;
  alg: string;
  key_fp: string;
  ek: string;
}

export function parseSharePackage(packageText: string): ParsedSharePackage {
  const trimmed = packageText.trim();
  const prefix = 'VELTRIX-SHARE-1.';
  if (!trimmed.startsWith(prefix)) {
    throw new Error('Format paket tidak dikenali. Paket harus diawali dengan "VELTRIX-SHARE-1."');
  }
  const encoded = trimmed.slice(prefix.length);
  try {
    const raw = base64UrlToUint8Array(encoded);
    const parsed = JSON.parse(new TextDecoder().decode(raw)) as ParsedSharePackage;
    if (!parsed || parsed.v !== 1 || !parsed.request_id || !parsed.ek) {
      throw new Error('Struktur isi paket tidak lengkap.');
    }
    return parsed;
  } catch (err) {
    throw new Error(err instanceof Error ? err.message : 'Paket tidak dapat dibaca (format rusak).');
  }
}

export async function decryptSharePackage(packageText: string, privateKeyPem: string): Promise<UnpackedShareKey> {
  if (typeof window === 'undefined' || !window.crypto?.subtle) {
    throw new Error('Web Crypto API tidak tersedia pada browser ini.');
  }

  const parsed = parseSharePackage(packageText);
  const pkcs8Der = parsePemToDer(privateKeyPem, 'PRIVATE KEY');

  let privateKey: CryptoKey;
  try {
    privateKey = await window.crypto.subtle.importKey(
      'pkcs8',
      pkcs8Der,
      { name: 'RSA-OAEP', hash: 'SHA-256' },
      false,
      ['decrypt'],
    );
  } catch {
    throw new Error('Kunci privat RSA tidak valid atau rusak. Pastikan menggunakan format PKCS#8 PEM.');
  }

  const encryptedKeyBytes = base64ToUint8Array(parsed.ek);
  const encryptedBuffer = encryptedKeyBytes.buffer.slice(
    encryptedKeyBytes.byteOffset,
    encryptedKeyBytes.byteOffset + encryptedKeyBytes.byteLength,
  ) as ArrayBuffer;

  let decryptedBuffer: ArrayBuffer;
  try {
    decryptedBuffer = await window.crypto.subtle.decrypt(
      { name: 'RSA-OAEP' },
      privateKey,
      encryptedBuffer,
    );
  } catch {
    throw new Error(
      'Gagal mendekripsi kunci simetris. Kunci privat tidak cocok dengan kunci publik pemohon atau paket telah dimodifikasi.',
    );
  }

  if (decryptedBuffer.byteLength !== 32) {
    throw new Error('Panjang kunci simetris hasil dekripsi tidak valid (harus 32 byte / AES-256).');
  }

  return {
    requestId: parsed.request_id,
    keyFingerprint: parsed.key_fp,
    algorithm: parsed.alg,
    shareKeyBase64: arrayBufferToBase64(decryptedBuffer),
  };
}
