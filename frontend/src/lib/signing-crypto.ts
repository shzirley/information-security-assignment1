/**
 * Assignment 3 browser signing (A3-FE-01).
 *
 * Library use is limited to key generation, SHA-256, and PEM/JWK import. The signature itself is
 * the team's own RSASSA-PKCS1-v1_5 (RFC 8017): EMSA-PKCS1-v1_5 encoding, RSASP1 with CRT and
 * blinding, and RSAVP1. Every signature is checked against the public key before it leaves the browser.
 *
 * Self-contained on purpose (no imports) so `node --experimental-strip-types` can unit-test it.
 */

const MIN_BITS = 3072;
// DER prefix of DigestInfo for SHA-256 (RFC 8017 §9.2, note 1).
const DIGEST_INFO_SHA256 = Uint8Array.from([0x30, 0x31, 0x30, 0x0d, 0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01, 0x05, 0x00, 0x04, 0x20]);
// OID 1.2.840.113549.1.9.4 (messageDigest) followed by SET { OCTET STRING (32) }.
const MESSAGE_DIGEST_ATTR = Uint8Array.from([0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x09, 0x04, 0x31, 0x22, 0x04, 0x20]);
const ALGORITHM = { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' } as const;

function subtle(): SubtleCrypto {
  const value = globalThis.crypto?.subtle;
  if (!value) throw new Error('Web Crypto API tidak tersedia. Buka aplikasi lewat localhost atau HTTPS.');
  return value;
}

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

export function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value.replace(/\s+/g, ''));
  return Uint8Array.from(binary, c => c.charCodeAt(0));
}

function base64UrlToBigInt(value: string): bigint {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4);
  return os2ip(base64ToBytes(base64));
}

const toHex = (bytes: Uint8Array) => Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');

function toPem(der: ArrayBuffer, label: 'PUBLIC KEY' | 'PRIVATE KEY'): string {
  const lines = bytesToBase64(new Uint8Array(der)).match(/.{1,64}/g) ?? [];
  return `-----BEGIN ${label}-----\n${lines.join('\n')}\n-----END ${label}-----`;
}

function fromPem(pem: string, label: 'PRIVATE KEY'): ArrayBuffer {
  const match = pem.replace(/\r\n/g, '\n').match(new RegExp(`-----BEGIN ${label}-----([\\s\\S]+?)-----END ${label}-----`));
  if (!match) throw new Error('File bukan private key PKCS#8 (harus diawali -----BEGIN PRIVATE KEY-----).');
  const bytes = base64ToBytes(match[1]);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

export async function sha256(data: Uint8Array | string): Promise<Uint8Array> {
  const bytes = typeof data === 'string' ? new TextEncoder().encode(data) : data;
  return new Uint8Array(await subtle().digest('SHA-256', bytes as BufferSource));
}

/** I2OSP: big-endian, left-padded to `length` bytes. */
export function i2osp(value: bigint, length: number): Uint8Array {
  if (value < 0n || value >= 1n << BigInt(8 * length)) throw new Error('Integer terlalu besar untuk panjang yang diminta.');
  const out = new Uint8Array(length);
  for (let i = length - 1; i >= 0; i--) { out[i] = Number(value & 0xffn); value >>= 8n; }
  return out;
}

/** OS2IP: big-endian bytes to integer. */
export function os2ip(bytes: Uint8Array): bigint {
  let value = 0n;
  for (const byte of bytes) value = (value << 8n) | BigInt(byte);
  return value;
}

export function modPow(base: bigint, exponent: bigint, modulus: bigint): bigint {
  let result = 1n;
  base %= modulus;
  while (exponent > 0n) {
    if (exponent & 1n) result = (result * base) % modulus;
    base = (base * base) % modulus;
    exponent >>= 1n;
  }
  return result;
}

function modInverse(value: bigint, modulus: bigint): bigint {
  let [oldR, r] = [value % modulus, modulus];
  let [oldS, s] = [1n, 0n];
  while (r !== 0n) {
    const q = oldR / r;
    [oldR, r] = [r, oldR - q * r];
    [oldS, s] = [s, oldS - q * s];
  }
  if (oldR !== 1n) throw new Error('Tidak punya invers modulo.');
  return ((oldS % modulus) + modulus) % modulus;
}

/** EMSA-PKCS1-v1_5 for SHA-256: 0x00 || 0x01 || FF..FF || 0x00 || DigestInfo || H. */
export function emsaPkcs1v15Encode(hash: Uint8Array, k: number): Uint8Array {
  if (hash.length !== 32) throw new Error('Hash SHA-256 harus 32 byte.');
  const tLen = DIGEST_INFO_SHA256.length + hash.length;
  if (k < tLen + 11) throw new Error('Modulus terlalu pendek untuk SHA-256.');
  const em = new Uint8Array(k).fill(0xff);
  em[0] = 0x00;
  em[1] = 0x01;
  em[k - tLen - 1] = 0x00;
  em.set(DIGEST_INFO_SHA256, k - tLen);
  em.set(hash, k - hash.length);
  return em;
}

export interface RsaPrivateParams { n: bigint; e: bigint; d: bigint; p: bigint; q: bigint; dp: bigint; dq: bigint; qi: bigint; k: number }

/** RSASP1 with CRT and multiplicative blinding against timing leaks of BigInt arithmetic. */
export function rsasp1(m: bigint, key: RsaPrivateParams): bigint {
  if (m < 0n || m >= key.n) throw new Error('Representasi pesan di luar rentang modulus.');
  let r = 0n;
  while (r < 2n) r = os2ip(globalThis.crypto.getRandomValues(new Uint8Array(key.k))) % key.n;
  const blinded = (m * modPow(r, key.e, key.n)) % key.n;
  const s1 = modPow(blinded, key.dp, key.p);
  const s2 = modPow(blinded, key.dq, key.q);
  const h = (key.qi * (((s1 - s2) % key.p) + key.p)) % key.p;
  const sBlinded = s2 + h * key.q;
  return (sBlinded * modInverse(r, key.n)) % key.n;
}

/** RSAVP1: m = s^e mod n. */
export function rsavp1(s: bigint, n: bigint, e: bigint): bigint {
  if (s < 0n || s >= n) throw new Error('Signature di luar rentang modulus.');
  return modPow(s, e, n);
}

export interface SigningKeyPair { publicKeyPem: string; privateKeyPem: string; fingerprint: string }

export async function generateSigningKeyPair(): Promise<SigningKeyPair> {
  const pair = await subtle().generateKey(
    { ...ALGORITHM, modulusLength: MIN_BITS, publicExponent: new Uint8Array([0x01, 0x00, 0x01]) },
    true, ['sign', 'verify'],
  ) as CryptoKeyPair;
  const spki = await subtle().exportKey('spki', pair.publicKey);
  const pkcs8 = await subtle().exportKey('pkcs8', pair.privateKey);
  return {
    publicKeyPem: toPem(spki, 'PUBLIC KEY'),
    privateKeyPem: toPem(pkcs8, 'PRIVATE KEY'),
    fingerprint: toHex(await sha256(new Uint8Array(spki))),
  };
}

/** Imports a PKCS#8 PEM through Web Crypto and exposes the RSA parameters for our own RSASP1. */
export async function loadPrivateKeyParams(pem: string): Promise<{ params: RsaPrivateParams; fingerprint: string }> {
  let jwk: JsonWebKey;
  try {
    const key = await subtle().importKey('pkcs8', fromPem(pem, 'PRIVATE KEY'), ALGORITHM, true, ['sign']);
    jwk = await subtle().exportKey('jwk', key);
  } catch (err) {
    if (err instanceof Error && err.message.startsWith('File bukan')) throw err;
    throw new Error('Private key tidak dapat dibaca. Pilih file veltrix-signing-key-<username>.pem.');
  }
  const need = ['n', 'e', 'd', 'p', 'q', 'dp', 'dq', 'qi'] as const;
  if (jwk.kty !== 'RSA' || need.some(name => !jwk[name])) throw new Error('Private key bukan kunci RSA lengkap.');
  const [n, e, d, p, q, dp, dq, qi] = need.map(name => base64UrlToBigInt(jwk[name]!));
  const bits = n.toString(2).length;
  if (bits < MIN_BITS || e !== 65537n) throw new Error(`Kunci tanda tangan harus RSA-${MIN_BITS} dengan e = 65537 (file ini RSA-${bits}).`);
  // The public half gives the registered fingerprint, so a wrong file is caught before signing.
  const publicKey = await subtle().importKey('jwk', { kty: 'RSA', n: jwk.n, e: jwk.e, alg: 'RS256', ext: true }, ALGORITHM, true, ['verify']);
  const spki = new Uint8Array(await subtle().exportKey('spki', publicKey));
  return { params: { n, e, d, p, q, dp, dq, qi, k: Math.ceil(bits / 8) }, fingerprint: toHex(await sha256(spki)) };
}

/** RSASSA-PKCS1-v1_5 signature over a SHA-256 hash, verified with the public key before returning. */
export function signHash(hash: Uint8Array, key: RsaPrivateParams): Uint8Array {
  const em = emsaPkcs1v15Encode(hash, key.k);
  const m = os2ip(em);
  const s = rsasp1(m, key);
  // Encode-then-compare self-check; a CRT fault would otherwise leak a factor of n.
  if (rsavp1(s, key.n, key.e) !== m) throw new Error('Pemeriksaan tanda tangan gagal; tanda tangan tidak dikirim.');
  return i2osp(s, key.k);
}

/** Signs SHA-256(signedAttrs DER, tag 0x31) from `prepare`; returns base64 for `complete`. */
export async function signSignedAttrs(signedAttrsDer: Uint8Array, privateKeyPem: string, expectedFingerprint: string): Promise<string> {
  const { params, fingerprint } = await loadPrivateKeyParams(privateKeyPem);
  if (fingerprint !== expectedFingerprint.toLowerCase()) throw new Error('File private key ini bukan pasangan kunci tanda tangan yang terdaftar.');
  return bytesToBase64(signHash(await sha256(signedAttrsDer), params));
}

/** Proof of possession: sign SHA-256(canonical JSON {challenge, spki_sha256, user_id}). */
export async function signPopChallenge(input: { userId: string; challenge: string; fingerprint: string }, privateKeyPem: string): Promise<string> {
  const { params, fingerprint } = await loadPrivateKeyParams(privateKeyPem);
  if (fingerprint !== input.fingerprint) throw new Error('Private key tidak cocok dengan public key yang didaftarkan.');
  // Same bytes as Python kyc.crypto.canonical: sorted keys, no spaces.
  const message = JSON.stringify({ challenge: input.challenge, spki_sha256: input.fingerprint, user_id: input.userId });
  return bytesToBase64(signHash(await sha256(message), params));
}

/** SHA-256 over the two ByteRange segments: file[a0:a0+l0] || file[a1:a1+l1]. */
export async function digestByteRange(pdf: Uint8Array, range: [number, number, number, number]): Promise<Uint8Array> {
  const [a0, l0, a1, l1] = range;
  if (a0 !== 0 || l0 <= 0 || a1 <= l0 || a1 + l1 !== pdf.length) throw new Error('ByteRange tidak menutup seluruh berkas.');
  const joined = new Uint8Array(l0 + l1);
  joined.set(pdf.subarray(0, l0));
  joined.set(pdf.subarray(a1, a1 + l1), l0);
  return sha256(joined);
}

/** Extracts the messageDigest attribute value from DER signedAttrs. */
export function messageDigestOf(signedAttrsDer: Uint8Array): Uint8Array {
  outer: for (let i = 0; i + MESSAGE_DIGEST_ATTR.length + 32 <= signedAttrsDer.length; i++) {
    for (let j = 0; j < MESSAGE_DIGEST_ATTR.length; j++) if (signedAttrsDer[i + j] !== MESSAGE_DIGEST_ATTR[j]) continue outer;
    const start = i + MESSAGE_DIGEST_ATTR.length;
    return signedAttrsDer.slice(start, start + 32);
  }
  throw new Error('Atribut messageDigest tidak ditemukan.');
}

export const sameBytes = (a: Uint8Array, b: Uint8Array) => a.length === b.length && a.every((byte, i) => byte === b[i]);
export { toHex };
