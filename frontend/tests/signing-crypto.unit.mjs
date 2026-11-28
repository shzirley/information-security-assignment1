// Unit tests for src/lib/signing-crypto.ts (A3-FE-01). Not a Playwright spec. Run from frontend/:
//   npm run test:signing
// The reference is Node's OpenSSL RSASSA-PKCS1-v1_5; PKCS#1 v1.5 is deterministic, so our own
// implementation must match it byte for byte (plan §3.1 T02, browser side).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { constants, createHash, generateKeyPairSync, randomBytes, sign, verify } from 'node:crypto';
import {
  digestByteRange, emsaPkcs1v15Encode, loadPrivateKeyParams, messageDigestOf, rsavp1,
  signHash, signPopChallenge, signSignedAttrs,
} from '../src/lib/signing-crypto.ts';

const keyPair = (bits) => generateKeyPairSync('rsa', { modulusLength: bits, publicExponent: 65537 });
const { privateKey, publicKey } = keyPair(3072);
const pem = privateKey.export({ type: 'pkcs8', format: 'pem' });
const fingerprint = createHash('sha256').update(publicKey.export({ type: 'spki', format: 'der' })).digest('hex');
const pkcs1 = { key: privateKey, padding: constants.RSA_PKCS1_PADDING };

test('own RSASSA-PKCS1-v1_5 equals OpenSSL for 30 random messages', async () => {
  const { params, fingerprint: fp } = await loadPrivateKeyParams(pem);
  assert.equal(fp, fingerprint);
  assert.equal(params.k, 384);
  for (let i = 0; i < 30; i++) {
    const message = randomBytes(1 + (i * 37) % 200);
    const ours = signHash(createHash('sha256').update(message).digest(), params);
    assert.deepEqual(Buffer.from(ours), sign('sha256', message, pkcs1));
  }
});

test('EMSA-PKCS1-v1_5 layout', () => {
  const hash = new Uint8Array(32).fill(7);
  const em = emsaPkcs1v15Encode(hash, 384);
  assert.equal(em.length, 384);
  assert.deepEqual([...em.subarray(0, 3)], [0x00, 0x01, 0xff]);
  assert.equal(em[384 - 32 - 19 - 1], 0x00);
  assert.deepEqual([...em.subarray(384 - 32)], [...hash]);
  assert.throws(() => emsaPkcs1v15Encode(new Uint8Array(20), 384));
});

test('signSignedAttrs signs SHA-256 of the DER and refuses a different key file', async () => {
  const attrs = randomBytes(120);
  const signature = Buffer.from(await signSignedAttrs(attrs, pem, fingerprint), 'base64');
  assert.ok(verify('sha256', attrs, { key: publicKey, padding: constants.RSA_PKCS1_PADDING }, signature));
  const other = keyPair(3072).privateKey.export({ type: 'pkcs8', format: 'pem' });
  await assert.rejects(signSignedAttrs(attrs, other, fingerprint), /bukan pasangan kunci/);
});

test('proof of possession signs the canonical JSON the backend expects', async () => {
  const input = { userId: 'user-1', challenge: 'Y2hhbGxlbmdl', fingerprint };
  const signature = Buffer.from(await signPopChallenge(input, pem), 'base64');
  // Python: json.dumps(value, sort_keys=True, separators=(',', ':'))
  const canonical = `{"challenge":"Y2hhbGxlbmdl","spki_sha256":"${fingerprint}","user_id":"user-1"}`;
  assert.ok(verify('sha256', Buffer.from(canonical), { key: publicKey, padding: constants.RSA_PKCS1_PADDING }, signature));
});

test('keys below RSA-3072 and non-PKCS#8 files are rejected', async () => {
  const small = keyPair(2048).privateKey.export({ type: 'pkcs8', format: 'pem' });
  await assert.rejects(loadPrivateKeyParams(small), /RSA-3072/);
  await assert.rejects(loadPrivateKeyParams('-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----'), /PKCS#8/);
});

test('RSAVP1 rejects s >= n', async () => {
  const { params } = await loadPrivateKeyParams(pem);
  assert.throws(() => rsavp1(params.n, params.n, params.e));
});

test('ByteRange digest and messageDigest extraction', async () => {
  const pdf = Buffer.from('%PDF-1.7 head <0000> tail');
  const range = [0, 14, 20, pdf.length - 20];
  const expected = createHash('sha256').update(Buffer.concat([pdf.subarray(0, 14), pdf.subarray(20)])).digest();
  assert.deepEqual(Buffer.from(await digestByteRange(pdf, range)), expected);
  await assert.rejects(digestByteRange(pdf, [0, 14, 20, 1]), /ByteRange/);
  const attr = Buffer.concat([Buffer.from('310b', 'hex'), Buffer.from('06092a864886f70d01090431220420', 'hex'), expected]);
  assert.deepEqual(Buffer.from(messageDigestOf(attr)), expected);
});
