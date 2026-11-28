'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, FileCheck2, FileSignature, KeyRound, RefreshCw, ShieldCheck, Upload } from 'lucide-react';
import { api, saveBlob } from '@/lib/api';
import { dateLabel, isMock } from '@/lib/contracts';
import { kycApi } from '@/lib/kyc-api';
import { editable, evidenceFor, signatureStatus, type Application, type SignaturePrepare, type SignatureVerification } from '@/lib/kyc';
import { base64ToBytes, digestByteRange, generateSigningKeyPair, messageDigestOf, sameBytes, signPopChallenge, signSignedAttrs, toHex } from '@/lib/signing-crypto';
import { Button, ErrorState, LoadingState, Modal, PageHeading } from '@/components/ui';

const MOCK_NOTE = 'Fitur tanda tangan hanya tersedia di mode live.';
const VALID_MEANING = 'Valid berarti dokumen tidak berubah sejak ditandatangani dengan kunci terdaftar, bukan berarti isinya benar.';
const short = (fingerprint: string | null | undefined) => fingerprint ? fingerprint.slice(0, 16) : '—';

function StatusPill({ status }: { status: keyof typeof signatureStatus }) {
  return <span className={`status-pill ${signatureStatus[status].tone}`}>{signatureStatus[status].label}</span>;
}

function VerificationResult({ result }: { result: SignatureVerification }) {
  return (
    <div className="signature-result" role="status">
      <StatusPill status={result.status} />
      <p>{signatureStatus[result.status].meaning}</p>
      <dl className="profile-reveal">
        <div><dt>Penandatangan</dt><dd>{result.signer ?? '—'}</dd></div>
        <div><dt>Fingerprint kunci</dt><dd><code>{short(result.fingerprint)}</code></dd></div>
        <div><dt>Waktu tanda tangan</dt><dd>{result.signed_at ? dateLabel(result.signed_at) : '—'}</dd></div>
      </dl>
      {result.reasons.length > 0 && <ul className="signature-reasons">{result.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>}
      <p className="small-note">{VALID_MEANING}</p>
    </div>
  );
}

/** A3-FE-02: signing key, separate from the Assignment 2 sharing key. */
export function SigningKeyPanel() {
  const client = useQueryClient();
  const session = useQuery({ queryKey: ['session'], queryFn: api.me });
  const keyQuery = useQuery({ queryKey: ['signing-key'], queryFn: kycApi.signingKey, enabled: !isMock });
  const [confirmRotate, setConfirmRotate] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: async () => {
      const username = session.data?.username ?? 'pemohon';
      const pair = await generateSigningKeyPair();
      const challenge = await kycApi.signingChallenge();
      const pop = await signPopChallenge({ userId: challenge.user_id, challenge: challenge.challenge, fingerprint: pair.fingerprint }, pair.privateKeyPem);
      const registered = await kycApi.registerSigningKey(pair.publicKeyPem, challenge.challenge_id, pop);
      // Download only after the server accepted the key; the file is the only copy.
      saveBlob(new Blob([pair.privateKeyPem], { type: 'application/x-pem-file' }), `veltrix-signing-key-${username}.pem`);
      return registered;
    },
    onSuccess: registered => {
      setConfirmRotate(false);
      setNotice(`Kunci tanda tangan terdaftar (fingerprint ${short(registered.fingerprint)}). File private key sudah diunduh; simpan baik-baik.`);
      void client.invalidateQueries({ queryKey: ['signing-key'] });
    },
  });
  const active = keyQuery.data?.active ?? null;
  const revoked = keyQuery.data?.history.length ?? 0;

  return (
    <section className="panel case-next share-key">
      <span className="section-index">Kunci tanda tangan</span>
      <h2>Kunci RSA-3072</h2>
      {isMock ? <p>{MOCK_NOTE}</p> : keyQuery.isPending ? <p>Memuat…</p> : keyQuery.isError ? <ErrorState error={keyQuery.error} retry={() => keyQuery.refetch()} /> : active ? (
        <p>
          <span className="status-pill status-ACCEPTED_DEMO">Aktif</span><br />
          Fingerprint <code>{short(active.fingerprint)}</code>, sertifikat <code>{active.cert_serial}</code>, berlaku sampai {dateLabel(active.expires_at)}.
          {revoked > 0 && <> {revoked} kunci lama dicabut; tanda tangan lamanya tetap bisa diverifikasi.</>}
        </p>
      ) : (
        <p>
          <span className="status-pill status-NEEDS_REVISION">Belum ada kunci</span><br />
          Dipakai untuk menandatangani formulir PDF. Terpisah dari kunci berbagi data.
        </p>
      )}
      {notice && <p className="inline-note" role="status">{notice}</p>}
      {create.isError && <ErrorState error={create.error} />}
      {!isMock && !keyQuery.isPending && !keyQuery.isError && (
        <Button className="full-width" variant={active ? 'secondary' : 'primary'} busy={create.isPending && !confirmRotate}
          onClick={() => (active ? setConfirmRotate(true) : create.mutate())}>
          {active ? <RefreshCw size={16} aria-hidden="true" /> : <KeyRound size={16} aria-hidden="true" />}
          {active ? 'Ganti kunci tanda tangan' : 'Buat kunci tanda tangan'}
        </Button>
      )}
      <p className="small-note">Siapa pun yang memegang file private key bisa menandatangani atas namamu.</p>
      <Modal open={confirmRotate} onOpenChange={open => { if (!create.isPending) setConfirmRotate(open); }} title="Ganti kunci tanda tangan?"
        description="Tanda tangan lama tetap valid, tetapi kunci lama tidak bisa dipakai menandatangani lagi. File private key baru akan diunduh.">
        {create.isError && <ErrorState error={create.error} />}
        <div className="modal-actions">
          <Button variant="secondary" disabled={create.isPending} onClick={() => setConfirmRotate(false)}>Batal</Button>
          <Button busy={create.isPending} onClick={() => create.mutate()}>Ganti kunci</Button>
        </div>
      </Modal>
    </section>
  );
}

/** A3-FE-03 (applicant) and A3-FE-04 (reviewer): signature state of the latest account-opening form. */
export function SignaturePanel({ application, reviewer }: { application: Application; reviewer: boolean }) {
  const client = useQueryClient();
  const form = evidenceFor(application, 'document');
  const signatures = useQuery({ queryKey: ['signatures', application.id], queryFn: () => kycApi.signatures(application.id), enabled: !isMock });
  const signingKey = useQuery({ queryKey: ['signing-key'], queryFn: kycApi.signingKey, enabled: !isMock && !reviewer });
  const [signing, setSigning] = useState(false);
  const signature = form && signatures.data?.items.find(item => item.evidence_id === form.id);
  const verify = useMutation({
    mutationFn: () => kycApi.verifySignature(application.id, signature!.id),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['signatures', application.id] }),
  });
  const download = useMutation({ mutationFn: async () => saveBlob(await kycApi.downloadSigned(application.id, signature!.id), `${application.reference}-formulir-bertanda-tangan.pdf`) });
  const isPdf = form?.mime_type === 'application/pdf';

  let body: React.ReactNode;
  let padded = true;
  if (isMock) body = <p>{MOCK_NOTE}</p>;
  else if (!form) body = <p>Belum ada formulir pembukaan rekening.</p>;
  else if (signatures.isPending) body = <p>Memuat status tanda tangan…</p>;
  else if (signatures.isError) body = <ErrorState error={signatures.error} retry={() => signatures.refetch()} />;
  else if (signature) { padded = false; body = (
    <>
      <div className="evidence-record signature-record">
        <span className="record-icon"><FileCheck2 size={21} aria-hidden="true" /></span>
        <div>
          <h3>Ditandatangani oleh {signature.signer}</h3>
          <p>{dateLabel(signature.signed_at)} · kunci <code>{short(signature.fingerprint)}</code>{signature.last_verified_at && ` · diperiksa ${dateLabel(signature.last_verified_at)}`}</p>
        </div>
        <StatusPill status={signature.status} />
      </div>
      {reviewer && signature.status !== 'VALID' && (
        <div className="share-body"><div className="revision-banner"><strong>Jangan putuskan sebelum diperiksa</strong><p>{signatureStatus[signature.status].meaning}</p></div></div>
      )}
      <div className="record-actions">
        <Button variant="secondary" busy={verify.isPending} onClick={() => verify.mutate()}><ShieldCheck size={16} aria-hidden="true" />Verifikasi ulang</Button>
        {!reviewer && <Button variant="ghost" busy={download.isPending} onClick={() => download.mutate()}><Download size={16} aria-hidden="true" />Unduh PDF bertanda tangan</Button>}
      </div>
      {verify.data && <div className="share-body"><VerificationResult result={verify.data} /></div>}
    </>
  ); }
  else if (reviewer) body = <p>Formulir versi terbaru belum ditandatangani pemohon.</p>;
  else if (!isPdf) body = <p>Unggah formulir dalam format PDF untuk ditandatangani. Formulir DOCX tidak bisa ditandatangani.</p>;
  else if (!editable(application.status)) body = <p>Pengajuan terkunci dan formulir belum ditandatangani.</p>;
  else if (signingKey.data && !signingKey.data.active) body = (
    <>
      <p>Buat kunci tanda tangan dulu, lalu kembali ke sini.</p>
      <Link href="/applicant/sharing" className="button button-primary"><KeyRound size={16} aria-hidden="true" />Buat kunci tanda tangan</Link>
    </>
  );
  else body = (
    <>
      <p>Tanda tangani formulir <strong>{form.display_name ?? 'PDF'}</strong> (versi {form.version}) dengan private key milikmu. Tanda tangan dibuat di browser dan tertanam di PDF.</p>
      <Button onClick={() => setSigning(true)}><FileSignature size={16} aria-hidden="true" />Tanda tangani</Button>
    </>
  );

  return (
    <section className="panel share-panel signature-panel">
      <div className="panel-heading">
        <div>
          <span className="section-index">Formulir pembukaan rekening</span>
          <h2>Tanda tangan digital</h2>
        </div>
      </div>
      {padded ? <div className="share-body">{body}</div> : body}
      {(verify.error || download.error) && <div className="share-body"><ErrorState error={verify.error ?? download.error} /></div>}
      {signing && form && <SignModal application={application} evidenceId={form.id} onClose={() => setSigning(false)} />}
    </section>
  );
}

function SignModal({ application, evidenceId, onClose }: { application: Application; evidenceId: string; onClose: () => void }) {
  const client = useQueryClient();
  const [session, setSession] = useState<SignaturePrepare | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [privateKey, setPrivateKey] = useState('');
  const prepare = useMutation({
    mutationFn: async () => {
      const prepared = await kycApi.prepareSignature(application.id, evidenceId);
      const preview = new Uint8Array(await (await kycApi.signaturePreview(prepared.session_id)).arrayBuffer());
      // What you see is what you sign: the hash in signedAttrs must match the PDF shown here.
      const shown = await digestByteRange(preview, prepared.byte_range);
      if (toHex(shown) !== prepared.digest.toLowerCase() || !sameBytes(shown, messageDigestOf(base64ToBytes(prepared.signed_attrs_der)))) {
        throw new Error('Hash dokumen dari server tidak cocok dengan PDF yang ditampilkan. Penandatanganan dibatalkan.');
      }
      return { prepared, url: URL.createObjectURL(new Blob([preview], { type: 'application/pdf' })) };
    },
    onSuccess: ({ prepared, url }) => { setSession(prepared); setPreviewUrl(url); },
  });
  const complete = useMutation({
    mutationFn: async () => {
      const signature = await signSignedAttrs(base64ToBytes(session!.signed_attrs_der), privateKey, session!.key_fingerprint);
      return kycApi.completeSignature(session!.session_id, signature);
    },
    onSuccess: () => void client.invalidateQueries({ queryKey: ['signatures', application.id] }),
  });
  const { mutate: start } = prepare;
  useEffect(() => { start(); }, [start]);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  const close = () => { if (!complete.isPending) { setPrivateKey(''); onClose(); } };

  return (
    <Modal open onOpenChange={open => { if (!open) close(); }} title={complete.isSuccess ? 'Formulir ditandatangani' : 'Tanda tangani formulir'}
      description={complete.isSuccess ? 'Tanda tangan tertanam di PDF dan sudah diverifikasi server.' : 'Periksa dokumen, lalu pilih file private key tanda tanganmu. Private key tidak dikirim ke server.'}>
      {prepare.isPending && <LoadingState label="Menyiapkan dokumen…" />}
      {prepare.isError && <ErrorState error={prepare.error} retry={() => start()} />}
      {session && previewUrl && !complete.isSuccess && (
        <>
          <div className="evidence-preview"><iframe src={previewUrl} title="Dokumen yang akan ditandatangani" /></div>
          <div className="hex-sample">
            <span>SHA-256 dokumen · kunci {short(session.key_fingerprint)}</span>
            <code>{session.digest}</code>
          </div>
          <div className="field signature-key-field">
            <label htmlFor="signing-key-file">File private key tanda tangan (.pem)</label>
            <input id="signing-key-file" type="file" accept=".pem" onChange={async e => { const picked = e.target.files?.[0]; if (picked) setPrivateKey(await picked.text()); e.target.value = ''; }} />
            <p className="small-note">{privateKey ? 'Private key sudah dimuat.' : 'Pilih veltrix-signing-key-<username>.pem.'} Sesi berlaku sampai {dateLabel(session.expires_at)}.</p>
          </div>
          {complete.isError && <ErrorState error={complete.error} />}
        </>
      )}
      {complete.isSuccess && <p className="inline-note" role="status">Status: {signatureStatus[complete.data.status].label}. {VALID_MEANING}</p>}
      <div className="modal-actions">
        <Button variant="secondary" disabled={complete.isPending} onClick={close}>{complete.isSuccess ? 'Tutup' : 'Batal'}</Button>
        {!complete.isSuccess && <Button busy={complete.isPending} disabled={!session || !privateKey} onClick={() => complete.mutate()}><FileSignature size={16} aria-hidden="true" />Tanda tangani</Button>}
      </div>
    </Modal>
  );
}

/** A3-FE-04: upload any PDF and check its embedded signature. */
export function VerifyWorkspace() {
  const [file, setFile] = useState<File | null>(null);
  const verify = useMutation({ mutationFn: (pdf: File) => kycApi.verifyPdf(pdf) });
  const ca = useMutation({ mutationFn: async () => saveBlob(await kycApi.caCertificate(), 'veltrix-demo-ca.pem') });
  const tooBig = Boolean(file && file.size > 10_000_000);

  return (
    <>
      <PageHeading index="Verifikasi" title="Verifikasi PDF" description="Periksa tanda tangan digital yang tertanam di PDF. Berkas tidak disimpan." />
      <div className="case-detail-grid">
        <div className="case-detail-main">
          <section className="panel share-panel">
            <div className="panel-heading"><div><span className="section-index">Unggah PDF</span><h2>Periksa tanda tangan</h2></div></div>
            <div className="share-body">
              {isMock ? <p>{MOCK_NOTE}</p> : (
                <form onSubmit={e => { e.preventDefault(); if (file) verify.mutate(file); }}>
                  <div className="upload-zone">
                    <Upload size={26} aria-hidden="true" />
                    <strong>Pilih PDF bertanda tangan</strong>
                    <p>PDF maksimum 10 MB.</p>
                    <input type="file" accept=".pdf,application/pdf" aria-label="Pilih PDF" onChange={e => { setFile(e.target.files?.[0] ?? null); verify.reset(); }} />
                  </div>
                  {tooBig && <p className="field-error">PDF maksimum 10 MB.</p>}
                  <div className="form-actions">
                    <Button type="submit" busy={verify.isPending} disabled={!file || tooBig}><FileCheck2 size={16} aria-hidden="true" />Verifikasi</Button>
                  </div>
                </form>
              )}
              {verify.isError && <ErrorState error={verify.error} />}
              {verify.data && <VerificationResult result={verify.data} />}
            </div>
          </section>
        </div>
        <aside className="case-detail-aside">
          <section className="panel case-next">
            <span className="section-index">Pembaca PDF lain</span>
            <h2>Sertifikat VELTRIX Demo CA</h2>
            <p>Agar Adobe Reader mengenali penandatangan, impor sertifikat ini sebagai sertifikat tepercaya:</p>
            <ol className="signature-steps">
              <li>Unduh <code>veltrix-demo-ca.pem</code>.</li>
              <li>Adobe Reader: Menu → Preferences → Signatures → Identities &amp; Trusted Certificates → More.</li>
              <li>Trusted Certificates → Import, pilih berkasnya, centang &quot;Use this certificate as a trusted root&quot;.</li>
              <li>Buka ulang PDF bertanda tangan.</li>
            </ol>
            {ca.isError && <ErrorState error={ca.error} />}
            <Button className="full-width" variant="secondary" busy={ca.isPending} disabled={isMock} onClick={() => ca.mutate()}><Download size={16} aria-hidden="true" />Unduh sertifikat CA</Button>
          </section>
          <section className="scope-card">
            <ShieldCheck size={24} aria-hidden="true" />
            <h3>Arti hasil</h3>
            <p>{VALID_MEANING} CA ini hanya untuk demo, jadi bukan sertifikat yang diakui pemerintah atau bank.</p>
          </section>
        </aside>
      </div>
    </>
  );
}
