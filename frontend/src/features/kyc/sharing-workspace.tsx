'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Check,
  Copy,
  Download,
  Eye,
  FileText,
  Inbox,
  KeyRound,
  Mail,
  RefreshCw,
  Send,
  ShieldCheck,
  Trash2,
  Unlock,
} from 'lucide-react';
import { api, saveBlob } from '@/lib/api';
import { bytes } from '@/lib/contracts';
import { kycApi } from '@/lib/kyc-api';
import type { ShareItem, ShareRequest } from '@/lib/kyc';
import { decryptSharePackage, generateRsaKeyPair } from '@/lib/sharing-crypto';
import { Button, EmptyState, ErrorState, LoadingState, Modal, PageHeading } from '@/components/ui';

const SHAREABLE_ITEMS: Array<{ id: ShareItem['kind']; label: string; desc: string }> = [
  { id: 'profile', label: 'Profil Pribadi (JSON)', desc: 'Nama, NIK dummy, tanggal lahir, alamat' },
  { id: 'identity', label: 'Scan Identitas (KTP)', desc: 'Gambar/PDF kartu identitas sintetis' },
  { id: 'document', label: 'Formulir Pembukaan Rekening', desc: 'Dokumen PDF/DOCX administrasi' },
  { id: 'kk', label: 'Kartu Keluarga (Opsional)', desc: 'Dokumen tambahan KK sintetis' },
  { id: 'video', label: 'Video Verifikasi (MP4)', desc: 'Rekaman video simulasi' },
];

const SHARE_STATUS_META: Record<ShareRequest['status'], { label: string; tone: string }> = {
  PENDING: { label: 'Menunggu', tone: 'status-NEEDS_REVISION' },
  APPROVED: { label: 'Aktif', tone: 'status-ACCEPTED_DEMO' },
  REJECTED: { label: 'Ditolak', tone: 'status-REJECTED_DEMO' },
  CANCELLED: { label: 'Dibatalkan', tone: '' },
  REVOKED: { label: 'Akses dicabut', tone: 'status-REJECTED_DEMO' },
  EXPIRED: { label: 'Kedaluwarsa', tone: '' },
};

const ITEM_LABELS: Record<string, string> = {
  profile: 'Profil Pribadi',
  identity: 'KTP Dummy',
  document: 'Formulir Rekening',
  kk: 'Kartu Keluarga',
  video: 'Video Verifikasi',
};

type TabKey = 'incoming' | 'outgoing' | 'request';

interface PreviewState {
  title: string;
  mime: string;
  json?: Record<string, unknown>;
  blobUrl?: string;
  blob?: Blob;
  filename: string;
}

export function SharingWorkspace() {
  const queryClient = useQueryClient();
  const session = useQuery({ queryKey: ['session'], queryFn: api.me });
  const username = session.data?.username ?? '';

  const [tab, setTab] = useState<TabKey>('incoming');
  const [keyBusy, setKeyBusy] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);
  const [keyNotice, setKeyNotice] = useState<string | null>(null);

  // Request creation form state
  const [targetOwner, setTargetOwner] = useState('');
  const [purpose, setPurpose] = useState('');
  const [selectedRequestItems, setSelectedRequestItems] = useState<string[]>(['profile', 'identity']);

  // Approve modal state
  const [approveTarget, setApproveTarget] = useState<ShareRequest | null>(null);
  const [approveAppId, setApproveAppId] = useState('');
  const [approveItems, setApproveItems] = useState<string[]>([]);

  // Out-of-band package display modal state
  const [packageModal, setPackageModal] = useState<{ requestId: string; requester: string; packageText: string } | null>(null);
  const [copiedPackage, setCopiedPackage] = useState(false);

  // Outgoing unlock & decrypt modal state
  const [unlockTarget, setUnlockTarget] = useState<ShareRequest | null>(null);
  const [pastePackage, setPastePackage] = useState('');
  const [unlockPrivateKey, setUnlockPrivateKey] = useState('');
  const [decryptedShareKey, setDecryptedShareKey] = useState<string | null>(null);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [sharedItems, setSharedItems] = useState<ShareItem[]>([]);
  const [openingItemId, setOpeningItemId] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);

  // Cleanup blob URL when preview closes or changes
  useEffect(() => {
    const url = preview?.blobUrl;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [preview]);

  const myKeyQuery = useQuery({ queryKey: ['sharing', 'my-key'], queryFn: kycApi.myPublicKey });
  const incomingQuery = useQuery({ queryKey: ['sharing', 'incoming'], queryFn: () => kycApi.shareRequests('incoming') });
  const outgoingQuery = useQuery({ queryKey: ['sharing', 'outgoing'], queryFn: () => kycApi.shareRequests('outgoing') });
  const appsQuery = useQuery({ queryKey: ['applications'], queryFn: kycApi.applications });

  const shareableApps = useMemo(
    () => (appsQuery.data?.items ?? []).filter(a => a.status !== 'WITHDRAWN'),
    [appsQuery.data],
  );

  const refreshSharing = () => {
    queryClient.invalidateQueries({ queryKey: ['sharing'] });
  };

  const handleGenerateKey = async () => {
    if (!username) return;
    setKeyBusy(true);
    setKeyError(null);
    setKeyNotice(null);
    try {
      const pair = await generateRsaKeyPair();
      const registered = await kycApi.registerPublicKey(pair.publicKeyPem);
      // The download is the only copy: the key is not kept in memory or browser storage.
      saveBlob(new Blob([pair.privateKeyPem], { type: 'application/x-pem-file' }), `veltrix-private-key-${username}.pem`);
      setKeyNotice(
        `Pasangan kunci RSA-2048 berhasil dibuat. Public key terdaftar (fingerprint: ${registered.fingerprint}). File private key sudah diunduh: simpan baik-baik, karena tidak disimpan di browser maupun server. Tanpa file ini kamu tidak bisa membuka dokumen yang dibagikan kepadamu.`,
      );
      queryClient.invalidateQueries({ queryKey: ['sharing', 'my-key'] });
    } catch (err) {
      setKeyError(err instanceof Error ? err.message : 'Gagal membuat kunci RSA.');
    } finally {
      setKeyBusy(false);
    }
  };

  const createRequestMutation = useMutation({
    mutationFn: () => kycApi.createShareRequest(targetOwner.trim(), purpose.trim(), selectedRequestItems),
    onSuccess: () => {
      setTargetOwner('');
      setPurpose('');
      setSelectedRequestItems(['profile', 'identity']);
      refreshSharing();
      setTab('outgoing');
    },
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, appId, items }: { id: string; appId: string; items: string[] }) =>
      kycApi.approveShareRequest(id, appId, items),
    onSuccess: (res, vars) => {
      const requester = approveTarget?.requester_username ?? '';
      setApproveTarget(null);
      setPackageModal({ requestId: vars.id, requester, packageText: res.package });
      setCopiedPackage(false);
      refreshSharing();
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => kycApi.rejectShareRequest(id),
    onSuccess: refreshSharing,
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => kycApi.cancelShareRequest(id),
    onSuccess: refreshSharing,
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => kycApi.revokeShareRequest(id),
    onSuccess: refreshSharing,
  });

  const fetchPackageMutation = useMutation({
    mutationFn: async (req: ShareRequest) => {
      const res = await kycApi.sharePackage(req.id);
      return { req, packageText: res.package };
    },
    onSuccess: ({ req, packageText }) => {
      setPackageModal({ requestId: req.id, requester: req.requester_username, packageText });
      setCopiedPackage(false);
    },
  });

  const openApproveModal = (req: ShareRequest) => {
    setApproveTarget(req);
    setApproveItems([...req.requested_items]);
    setApproveAppId(shareableApps[0]?.id ?? '');
  };

  const openUnlockModal = (req: ShareRequest) => {
    setUnlockTarget(req);
    setPastePackage('');
    setUnlockPrivateKey('');
    setDecryptedShareKey(null);
    setUnlockError(null);
    setSharedItems([]);
    setPreview(null);
  };

  const handleDecryptPackage = async () => {
    if (!unlockTarget) return;
    setUnlocking(true);
    setUnlockError(null);
    try {
      const unpacked = await decryptSharePackage(pastePackage, unlockPrivateKey);
      if (unpacked.requestId !== unlockTarget.id) {
        throw new Error(
          `Paket ini ditujukan untuk ID permintaan lain (${unpacked.requestId.slice(0, 8)}…), bukan permintaan ini.`,
        );
      }
      const itemsRes = await kycApi.shareItems(unlockTarget.id);
      setDecryptedShareKey(unpacked.shareKeyBase64);
      setSharedItems(itemsRes.items);
    } catch (err) {
      setUnlockError(err instanceof Error ? err.message : 'Gagal mendekripsi paket kunci.');
    } finally {
      setUnlocking(false);
    }
  };

  const handleOpenSharedItem = async (item: ShareItem) => {
    if (!unlockTarget || !decryptedShareKey) return;
    setOpeningItemId(item.id);
    setUnlockError(null);
    try {
      const result = await kycApi.openShareItem(unlockTarget.id, item.id, decryptedShareKey);
      if (item.mime_type === 'application/json' && !(result instanceof Blob)) {
        setPreview({
          title: ITEM_LABELS[item.kind] ?? item.display_name,
          mime: item.mime_type,
          json: result,
          filename: `${item.kind}.json`,
        });
      } else if (result instanceof Blob) {
        const blobUrl = URL.createObjectURL(result);
        const ext = item.mime_type.split('/')[1]?.replace('jpeg', 'jpg') ?? 'bin';
        setPreview({
          title: ITEM_LABELS[item.kind] ?? item.display_name,
          mime: item.mime_type,
          blobUrl,
          blob: result,
          filename: `shared-${item.kind}.${ext}`,
        });
      }
    } catch (err) {
      setUnlockError(err instanceof Error ? err.message : 'Gagal membuka dokumen terenkripsi.');
    } finally {
      setOpeningItemId(null);
    }
  };

  const handleCopyPackage = async () => {
    if (!packageModal) return;
    try {
      await navigator.clipboard.writeText(packageModal.packageText);
      setCopiedPackage(true);
      setTimeout(() => setCopiedPackage(false), 2500);
    } catch {
      setCopiedPackage(false);
    }
  };

  const toggleItem = (list: string[], setList: (next: string[]) => void, id: string) => {
    setList(list.includes(id) ? list.filter(x => x !== id) : [...list, id]);
  };


  const serverKey = myKeyQuery.data?.key ?? null;
  const incoming = incomingQuery.data?.items ?? [];
  const outgoing = outgoingQuery.data?.items ?? [];
  const itemList = (items: string[]) => items.map(i => ITEM_LABELS[i] ?? i).join(', ');

  if (myKeyQuery.isPending || incomingQuery.isPending || outgoingQuery.isPending) {
    return <LoadingState label="Memuat berbagi data…" />;
  }

  const tabs: Array<{ id: TabKey; label: string }> = [
    { id: 'incoming', label: `Permintaan masuk (${incoming.length})` },
    { id: 'outgoing', label: `Permintaan keluar (${outgoing.length})` },
    { id: 'request', label: 'Ajukan permintaan' },
  ];

  return (
    <>
      <PageHeading
        index="03"
        title="Berbagi data"
        description="Minta atau bagikan dokumen KYC dengan pemohon lain. Kunci akses dikirim terenkripsi lewat email, di luar aplikasi."
      />

      <div className="case-detail-grid">
        <div className="case-detail-main">
          <div className="lab-tabs" role="tablist" aria-label="Menu berbagi data">
            {tabs.map(t => (
              <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'active' : ''} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'incoming' && (
            <section className="panel share-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-index">Sebagai pemilik data</span>
                  <h2>Permintaan masuk</h2>
                  <p>Saat kamu menyetujui, sistem membuat kunci AES-256 baru, mengenkripsi salinan dokumen, lalu mengunci kunci itu dengan public key peminta. Kirim paket kuncinya lewat email.</p>
                </div>
              </div>
              {incomingQuery.isError && <ErrorState error={incomingQuery.error} retry={() => incomingQuery.refetch()} />}
              {shareableApps.length === 0 && incoming.some(r => r.status === 'PENDING') && (
                <div className="share-body"><div className="revision-banner"><strong>Belum ada pengajuan untuk dibagikan</strong><p>Buat minimal satu pengajuan KYC (draf atau terkirim) sebelum menyetujui permintaan.</p></div></div>
              )}
              {incoming.length === 0 ? (
                <EmptyState title="Belum ada permintaan masuk" description="Permintaan akses dari pemohon lain akan muncul di sini." />
              ) : incoming.map(req => {
                const meta = SHARE_STATUS_META[req.status];
                return (
                  <div className="evidence-group" key={req.id}>
                    <div className="evidence-record">
                      <span className="record-icon"><Inbox size={21} aria-hidden="true" /></span>
                      <div>
                        <h3>{req.requester_username}</h3>
                        <p>{req.purpose}</p>
                        <p>Diminta: {itemList(req.requested_items)}{req.requester_key_fingerprint && <> · Kunci <code>{req.requester_key_fingerprint}</code></>}</p>
                      </div>
                      <span className={`status-pill ${meta.tone}`}>{meta.label}</span>
                    </div>
                    {req.status === 'PENDING' && (
                      <div className="record-actions">
                        <Button onClick={() => openApproveModal(req)} disabled={shareableApps.length === 0}><Check size={16} aria-hidden="true" />Setujui</Button>
                        <Button variant="ghost" busy={rejectMutation.isPending} onClick={() => rejectMutation.mutate(req.id)}>Tolak</Button>
                      </div>
                    )}
                    {req.status === 'APPROVED' && (
                      <div className="record-actions">
                        <Button variant="secondary" busy={fetchPackageMutation.isPending} onClick={() => fetchPackageMutation.mutate(req)}><KeyRound size={16} aria-hidden="true" />Lihat paket kunci</Button>
                        <Button variant="ghost" busy={revokeMutation.isPending} onClick={() => revokeMutation.mutate(req.id)}><Trash2 size={16} aria-hidden="true" />Cabut akses</Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </section>
          )}

          {tab === 'outgoing' && (
            <section className="panel share-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-index">Sebagai peminta</span>
                  <h2>Permintaan keluar</h2>
                  <p>Setelah pemilik menyetujui dan mengirim paket <code>VELTRIX-SHARE-1…</code> lewat email, buka dokumennya di sini dengan file private key milikmu.</p>
                </div>
              </div>
              {outgoingQuery.isError && <ErrorState error={outgoingQuery.error} retry={() => outgoingQuery.refetch()} />}
              {outgoing.length === 0 ? (
                <EmptyState
                  title="Belum ada permintaan keluar"
                  description="Ajukan permintaan akses ke dokumen pemohon lain."
                  action={<Button onClick={() => setTab('request')}>Ajukan permintaan</Button>}
                />
              ) : outgoing.map(req => {
                const meta = SHARE_STATUS_META[req.status];
                return (
                  <div className="evidence-group" key={req.id}>
                    <div className="evidence-record">
                      <span className="record-icon"><Send size={21} aria-hidden="true" /></span>
                      <div>
                        <h3>{req.owner_username}</h3>
                        <p>{req.purpose}</p>
                        <p>Diminta: {itemList(req.requested_items)}</p>
                      </div>
                      <span className={`status-pill ${meta.tone}`}>{meta.label}</span>
                    </div>
                    {req.status === 'PENDING' && (
                      <div className="record-actions">
                        <Button variant="ghost" busy={cancelMutation.isPending} onClick={() => cancelMutation.mutate(req.id)}>Batalkan permintaan</Button>
                      </div>
                    )}
                    {req.status === 'APPROVED' && (
                      <div className="record-actions">
                        <Button onClick={() => openUnlockModal(req)}><Unlock size={16} aria-hidden="true" />Buka dokumen</Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </section>
          )}

          {tab === 'request' && (
            <section className="panel share-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-index">Permintaan baru</span>
                  <h2>Ajukan permintaan akses</h2>
                  <p>Masukkan username pemilik data dan pilih dokumen yang ingin kamu lihat. Pemilik bisa menyetujui sebagian atau menolak.</p>
                </div>
              </div>
              <form
                className="share-body form-stack"
                onSubmit={e => {
                  e.preventDefault();
                  createRequestMutation.mutate();
                }}
              >
                {!serverKey && (
                  <div className="revision-banner"><strong>Buat kunci berbagi dulu</strong><p>Permintaan hanya bisa dikirim setelah kamu membuat pasangan kunci RSA di panel kanan.</p></div>
                )}
                {createRequestMutation.isError && <ErrorState error={createRequestMutation.error} />}
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="share-owner-username">Username pemilik data</label>
                    <input id="share-owner-username" type="text" placeholder="Contoh: demo_user" value={targetOwner} onChange={e => setTargetOwner(e.target.value)} required disabled={!serverKey || createRequestMutation.isPending} />
                  </div>
                  <div className="field">
                    <label htmlFor="share-purpose">Tujuan permintaan</label>
                    <input id="share-purpose" type="text" placeholder="Minimal 10 karakter" value={purpose} onChange={e => setPurpose(e.target.value)} minLength={10} maxLength={300} required disabled={!serverKey || createRequestMutation.isPending} />
                  </div>
                </div>
                <fieldset className="share-fieldset">
                  <legend className="standalone-label">Dokumen yang diminta</legend>
                  <div className="share-options">
                    {SHAREABLE_ITEMS.map(item => (
                      <label key={item.id} className="checkbox-field">
                        <input type="checkbox" checked={selectedRequestItems.includes(item.id)} onChange={() => toggleItem(selectedRequestItems, setSelectedRequestItems, item.id)} disabled={!serverKey || createRequestMutation.isPending} />
                        <span>{item.label}<small>{item.desc}</small></span>
                      </label>
                    ))}
                  </div>
                </fieldset>
                <div className="form-actions">
                  <Button type="submit" busy={createRequestMutation.isPending} disabled={!serverKey || !targetOwner.trim() || purpose.trim().length < 10 || selectedRequestItems.length === 0}>
                    <Send size={16} aria-hidden="true" />Kirim permintaan
                  </Button>
                </div>
              </form>
            </section>
          )}
        </div>

        <aside className="case-detail-aside">
          <section className="panel case-next share-key">
            <span className="section-index">Kunci berbagi</span>
            <h2>Kunci RSA-2048</h2>
            {serverKey ? (
              <p><span className="status-pill status-ACCEPTED_DEMO">Terdaftar</span><br />Fingerprint <code>{serverKey.fingerprint}</code>. Private key hanya ada di file <code>veltrix-private-key-{username}.pem</code> milikmu.</p>
            ) : (
              <p><span className="status-pill status-NEEDS_REVISION">Belum ada kunci</span><br />Buat kunci sebelum meminta dokumen. Private key akan diunduh sebagai file .pem dan tidak disimpan di server maupun browser.</p>
            )}
            {keyNotice && <p className="inline-note" role="status">{keyNotice}</p>}
            {keyError && <ErrorState error={new Error(keyError)} />}
            <Button className="full-width" variant={serverKey ? 'secondary' : 'primary'} onClick={handleGenerateKey} busy={keyBusy}>
              <RefreshCw size={16} aria-hidden="true" />{serverKey ? 'Ganti kunci' : 'Buat kunci'}
            </Button>
          </section>
          <section className="scope-card">
            <ShieldCheck size={24} aria-hidden="true" />
            <h3>Cara kerjanya</h3>
            <p>Pemilik menyetujui, sistem membuat kunci AES-256 khusus untuk permintaan itu, lalu menguncinya dengan public key peminta. Paket kunci dikirim lewat email dan hanya bisa dibuka dengan private key peminta.</p>
            <p className="small-note">Akses berlaku 7 hari dan bisa dicabut pemilik kapan saja.</p>
          </section>
        </aside>
      </div>

      {/* Approve request */}
      <Modal
        open={Boolean(approveTarget)}
        onOpenChange={open => { if (!open) setApproveTarget(null); }}
        title="Setujui permintaan"
        description={approveTarget ? `Pilih pengajuan dan dokumen yang dibagikan kepada ${approveTarget.requester_username}.` : ''}
      >
        {approveTarget && (
          <>
            {approveMutation.isError && <ErrorState error={approveMutation.error} />}
            <div className="field">
              <label htmlFor="approve-app-select">Sumber pengajuan</label>
              <select id="approve-app-select" value={approveAppId} onChange={e => setApproveAppId(e.target.value)}>
                {shareableApps.map(app => <option key={app.id} value={app.id}>{app.reference} ({app.status})</option>)}
              </select>
            </div>
            <fieldset className="share-fieldset">
              <legend className="standalone-label">Dokumen yang dibagikan</legend>
              {approveTarget.requested_items.map(kind => (
                <label key={kind} className="checkbox-field">
                  <input type="checkbox" checked={approveItems.includes(kind)} onChange={() => toggleItem(approveItems, setApproveItems, kind)} />
                  <span>{ITEM_LABELS[kind] ?? kind}</span>
                </label>
              ))}
            </fieldset>
            {approveTarget.requester_key_fingerprint && <p className="small-note">Cocokkan fingerprint kunci peminta dengan orangnya: <code>{approveTarget.requester_key_fingerprint}</code></p>}
            <div className="modal-actions">
              <Button variant="secondary" onClick={() => setApproveTarget(null)}>Batal</Button>
              <Button busy={approveMutation.isPending} disabled={!approveAppId || approveItems.length === 0} onClick={() => approveMutation.mutate({ id: approveTarget.id, appId: approveAppId, items: approveItems })}>
                <KeyRound size={16} aria-hidden="true" />Setujui &amp; buat paket kunci
              </Button>
            </div>
          </>
        )}
      </Modal>

      {/* Encrypted key package to send out of band */}
      <Modal
        open={Boolean(packageModal)}
        onOpenChange={open => { if (!open) setPackageModal(null); }}
        title="Paket kunci terenkripsi"
        description={packageModal ? `Kirim paket ini ke ${packageModal.requester} lewat email. Hanya private key miliknya yang bisa membukanya.` : ''}
      >
        {packageModal && (
          <>
            <div className="hex-sample share-package">
              <span>VELTRIX-SHARE-1 · RSA-OAEP-256</span>
              <code>{packageModal.packageText}</code>
            </div>
            <p className="small-note">Aman walaupun email dibaca pihak lain: tanpa private key {packageModal.requester}, paket ini tidak bisa dibuka.</p>
            <div className="modal-actions">
              <Button variant="secondary" onClick={handleCopyPackage}>
                {copiedPackage ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
                {copiedPackage ? 'Tersalin' : 'Salin paket'}
              </Button>
              <a
                className="button button-primary"
                href={`mailto:?subject=${encodeURIComponent('VELTRIX Encrypted Share Key Package')}&body=${encodeURIComponent(`Berikut paket kunci terenkripsi VELTRIX (RSA-OAEP-256):\n\n${packageModal.packageText}`)}`}
              >
                <Mail size={16} aria-hidden="true" />Kirim via Email
              </a>
            </div>
          </>
        )}
      </Modal>

      {/* Unlock and preview shared documents */}
      <Modal
        open={Boolean(unlockTarget)}
        onOpenChange={open => {
          if (!open) {
            setUnlockTarget(null);
            setPreview(null);
          }
        }}
        title={decryptedShareKey ? 'Dokumen yang dibagikan' : 'Buka paket kunci'}
        description={unlockTarget ? (decryptedShareKey
          ? `Dokumen dari ${unlockTarget.owner_username} didekripsi di memori. Tutup setelah selesai.`
          : `Tempel paket dari email ${unlockTarget.owner_username} dan pilih file private key milikmu. Kunci dibuka di browser, private key tidak dikirim ke server.`) : ''}
      >
        {unlockTarget && (
          <>
            {unlockError && <ErrorState error={new Error(unlockError)} />}
            {!decryptedShareKey ? (
              <>
                <div className="field">
                  <label htmlFor="unlock-package-input">Paket kunci dari email</label>
                  <textarea id="unlock-package-input" className="mono" rows={4} placeholder="VELTRIX-SHARE-1.eyJ…" value={pastePackage} onChange={e => setPastePackage(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="unlock-privkey-file">File private key (.pem)</label>
                  <input
                    id="unlock-privkey-file"
                    type="file"
                    accept=".pem"
                    onChange={async e => {
                      const file = e.target.files?.[0];
                      if (file) setUnlockPrivateKey(await file.text());
                      e.target.value = '';
                    }}
                  />
                  <p className="small-note">{unlockPrivateKey ? 'Private key sudah dimuat.' : 'Belum ada file dipilih.'}</p>
                </div>
                <div className="modal-actions">
                  <Button variant="secondary" onClick={() => setUnlockTarget(null)}>Tutup</Button>
                  <Button busy={unlocking} disabled={!pastePackage.trim() || !unlockPrivateKey.trim()} onClick={handleDecryptPackage}>
                    <Unlock size={16} aria-hidden="true" />Buka paket
                  </Button>
                </div>
              </>
            ) : (
              <>
                {sharedItems.map(item => (
                  <div className="selected-file" key={item.id}>
                    <FileText size={20} aria-hidden="true" />
                    <div>
                      <strong>{ITEM_LABELS[item.kind] ?? item.display_name}</strong>
                      <span>{item.mime_type} · {bytes(item.original_bytes)}</span>
                    </div>
                    <Button variant="secondary" busy={openingItemId === item.id} onClick={() => handleOpenSharedItem(item)}>
                      <Eye size={16} aria-hidden="true" />Lihat
                    </Button>
                  </div>
                ))}

                {preview && (
                  <div className="share-preview">
                    <div className="share-preview-heading">
                      <strong>{preview.title}</strong>
                      {preview.blob && (
                        <Button variant="ghost" onClick={() => saveBlob(preview.blob!, preview.filename)}>
                          <Download size={16} aria-hidden="true" />Unduh
                        </Button>
                      )}
                    </div>
                    {preview.json && (
                      <dl className="profile-reveal">
                        {Object.entries(preview.json).map(([k, v]) => (
                          <div key={k}><dt>{k}</dt><dd>{String(v)}</dd></div>
                        ))}
                      </dl>
                    )}
                    {preview.blobUrl && (
                      <div className="evidence-preview">
                        {preview.mime.startsWith('image/') ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={preview.blobUrl} alt={preview.title} />
                        ) : preview.mime === 'application/pdf' ? (
                          <iframe src={preview.blobUrl} title={preview.title} />
                        ) : preview.mime.startsWith('video/') ? (
                          <video src={preview.blobUrl} controls playsInline aria-label={preview.title} />
                        ) : (
                          <p>Format ini tidak dapat dipratinjau. Gunakan Unduh untuk membukanya.</p>
                        )}
                      </div>
                    )}
                  </div>
                )}
                <div className="modal-actions">
                  <Button variant="secondary" onClick={() => { setUnlockTarget(null); setPreview(null); }}>Tutup</Button>
                </div>
              </>
            )}
          </>
        )}
      </Modal>
    </>
  );
}
