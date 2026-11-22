'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Check,
  Copy,
  Download,
  Eye,
  KeyRound,
  Lock,
  Mail,
  MessageCircle,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Unlock,
} from 'lucide-react';
import { api, saveBlob } from '@/lib/api';
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
  PENDING: { label: 'Menunggu persetujuan', tone: 'status-amber' },
  APPROVED: { label: 'Disetujui (Aktif)', tone: 'status-emerald' },
  REJECTED: { label: 'Ditolak', tone: 'status-rose' },
  CANCELLED: { label: 'Dibatalkan', tone: 'status-muted' },
  REVOKED: { label: 'Akses dicabut', tone: 'status-rose' },
  EXPIRED: { label: 'Kedaluwarsa', tone: 'status-muted' },
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

  if (myKeyQuery.isPending || incomingQuery.isPending || outgoingQuery.isPending) {
    return <LoadingState label="Memuat ruang manajemen kunci & berbagi data…" />;
  }

  return (
    <div className="stack">
      <PageHeading
        index="03"
        title="Manajemen Kunci & Berbagi Data"
        description="Berbagi data privat antar-pengguna dengan enkripsi hibrida (RSA-OAEP-256 + AES-256-GCM) dan distribusi kunci out-of-band (WhatsApp / Email)."
      />

      {/* Section 1: Client-Side RSA Key Management */}
      <section className="panel stack-sm">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <KeyRound size={20} aria-hidden="true" />
              <h2 style={{ margin: 0 }}>Pasangan Kunci Asimetris (RSA-2048)</h2>
            </div>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: '0.92rem' }}>
              Public key didaftarkan ke server agar pemilik data dapat mengenkripsi kunci simetris untuk Anda. Private key diunduh sebagai file .pem dan hanya Anda yang menyimpannya; tidak dikirim ke server dan tidak disimpan di browser.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Button onClick={handleGenerateKey} busy={keyBusy}>
              <RefreshCw size={16} aria-hidden="true" />
              {serverKey ? 'Rotasi Kunci RSA Baru' : 'Generate & Daftar Kunci RSA'}
            </Button>
          </div>
        </div>

        {keyError && <ErrorState error={new Error(keyError)} />}
        {keyNotice && (
          <div style={{ padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.35)', fontSize: '0.9rem' }}>
            {keyNotice}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem', marginTop: '0.5rem' }}>
          <div style={{ padding: '0.85rem 1rem', borderRadius: '0.5rem', border: '1px solid var(--border)', background: 'var(--surface-2, var(--surface))' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>Public Key di Server</div>
            {serverKey ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}>
                <ShieldCheck size={17} style={{ color: '#10b981' }} />
                <code>{serverKey.fingerprint}</code>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#f59e0b', fontWeight: 500 }}>
                <ShieldAlert size={17} />
                Belum terdaftar
              </div>
            )}
          </div>
          <div style={{ padding: '0.85rem 1rem', borderRadius: '0.5rem', border: '1px solid var(--border)', background: 'var(--surface-2, var(--surface))' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>Private Key</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--muted)' }}>
              <Lock size={17} />
              {serverKey
                ? `Hanya di file veltrix-private-key-${username}.pem milikmu. Pilih file itu saat membuka data.`
                : 'Akan diunduh sebagai file .pem saat kunci dibuat.'}
            </div>
          </div>
        </div>
      </section>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }} role="tablist" aria-label="Menu berbagi data">
        <Button variant={tab === 'incoming' ? 'primary' : 'secondary'} onClick={() => setTab('incoming')}>
          Permintaan Masuk ({incomingQuery.data?.items.length ?? 0})
        </Button>
        <Button variant={tab === 'outgoing' ? 'primary' : 'secondary'} onClick={() => setTab('outgoing')}>
          Permintaan Keluar ({outgoingQuery.data?.items.length ?? 0})
        </Button>
        <Button variant={tab === 'request' ? 'primary' : 'secondary'} onClick={() => setTab('request')}>
          <Send size={15} aria-hidden="true" />
          Ajukan Permintaan Akses
        </Button>
      </div>

      {/* TAB 1: Incoming Requests (Owner Side) */}
      {tab === 'incoming' && (
        <section className="panel stack-sm">
          <div>
            <h2 style={{ margin: 0 }}>Permintaan Masuk (Sebagai Pemilik Data)</h2>
            <p style={{ margin: '0.25rem 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>
              Saat Anda menyetujui permintaan, sistem membuat kunci simetris AES-256 baru, mengenkripsi salinan dokumen, lalu membungkus kunci tersebut dengan Public Key pemohon (RSA-OAEP-256) untuk Anda kirim via WhatsApp/Email.
            </p>
          </div>
          {incomingQuery.isError && <ErrorState error={incomingQuery.error} retry={() => incomingQuery.refetch()} />}
          {incomingQuery.data && incomingQuery.data.items.length === 0 ? (
            <EmptyState
              title="Belum ada permintaan masuk"
              description="Permintaan akses data dari pengguna lain akan muncul di sini."
            />
          ) : (
            <div className="stack-sm">
              {incomingQuery.data?.items.map(req => {
                const meta = SHARE_STATUS_META[req.status];
                return (
                  <article
                    key={req.id}
                    style={{
                      padding: '1rem',
                      borderRadius: '0.6rem',
                      border: '1px solid var(--border)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      gap: '1rem',
                      flexWrap: 'wrap',
                    }}
                  >
                    <div style={{ flex: '1 1 280px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.35rem' }}>
                        <strong>Pemohon: {req.requester_username}</strong>
                        <span className={`badge ${meta.tone}`}>{meta.label}</span>
                        {req.requester_key_fingerprint && (
                          <code style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
                            Key FP: {req.requester_key_fingerprint}
                          </code>
                        )}
                      </div>
                      <p style={{ margin: '0.25rem 0', fontSize: '0.92rem' }}>
                        <strong>Tujuan:</strong> {req.purpose}
                      </p>
                      <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
                        Dokumen diminta: {req.requested_items.map(i => ITEM_LABELS[i] ?? i).join(', ')}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {req.status === 'PENDING' && (
                        <>
                          <Button onClick={() => openApproveModal(req)} disabled={shareableApps.length === 0}>
                            <Check size={15} aria-hidden="true" />
                            Setujui & Buat Kunci
                          </Button>
                          <Button
                            variant="danger"
                            busy={rejectMutation.isPending}
                            onClick={() => rejectMutation.mutate(req.id)}
                          >
                            Tolak
                          </Button>
                        </>
                      )}
                      {req.status === 'APPROVED' && (
                        <>
                          <Button
                            variant="secondary"
                            busy={fetchPackageMutation.isPending}
                            onClick={() => fetchPackageMutation.mutate(req)}
                          >
                            <KeyRound size={15} aria-hidden="true" />
                            Lihat Paket Kunci (WA/Email)
                          </Button>
                          <Button
                            variant="danger"
                            busy={revokeMutation.isPending}
                            onClick={() => revokeMutation.mutate(req.id)}
                          >
                            <Trash2 size={15} aria-hidden="true" />
                            Cabut Akses
                          </Button>
                        </>
                      )}
                    </div>
                  </article>
                );
              })}
              {shareableApps.length === 0 && incomingQuery.data?.items.some(r => r.status === 'PENDING') && (
                <p style={{ color: '#f59e0b', fontSize: '0.88rem', margin: 0 }}>
                  Catatan: Anda memerlukan minimal satu pengajuan KYC (draf atau terkirim, bukan yang ditarik) agar dapat menyetujui permintaan berbagi data.
                </p>
              )}
            </div>
          )}
        </section>
      )}

      {/* TAB 2: Outgoing Requests (Requester Side) */}
      {tab === 'outgoing' && (
        <section className="panel stack-sm">
          <div>
            <h2 style={{ margin: 0 }}>Permintaan Keluar (Sebagai Pemohon)</h2>
            <p style={{ margin: '0.25rem 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>
              Setelah pemilik data menyetujui permintaan Anda dan mengirimkan paket <code>VELTRIX-SHARE-1...</code> via WhatsApp/Email, buka dokumennya di sini menggunakan Private Key Anda.
            </p>
          </div>
          {outgoingQuery.isError && <ErrorState error={outgoingQuery.error} retry={() => outgoingQuery.refetch()} />}
          {outgoingQuery.data && outgoingQuery.data.items.length === 0 ? (
            <EmptyState
              title="Belum ada permintaan keluar"
              description="Ajukan permintaan akses data ke pemohon lain pada tab Ajukan Permintaan."
              action={<Button onClick={() => setTab('request')}>Ajukan Permintaan</Button>}
            />
          ) : (
            <div className="stack-sm">
              {outgoingQuery.data?.items.map(req => {
                const meta = SHARE_STATUS_META[req.status];
                return (
                  <article
                    key={req.id}
                    style={{
                      padding: '1rem',
                      borderRadius: '0.6rem',
                      border: '1px solid var(--border)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      gap: '1rem',
                      flexWrap: 'wrap',
                    }}
                  >
                    <div style={{ flex: '1 1 280px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.35rem' }}>
                        <strong>Pemilik Data: {req.owner_username}</strong>
                        <span className={`badge ${meta.tone}`}>{meta.label}</span>
                      </div>
                      <p style={{ margin: '0.25rem 0', fontSize: '0.92rem' }}>
                        <strong>Tujuan:</strong> {req.purpose}
                      </p>
                      <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
                        Dokumen diminta: {req.requested_items.map(i => ITEM_LABELS[i] ?? i).join(', ')}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {req.status === 'PENDING' && (
                        <Button
                          variant="secondary"
                          busy={cancelMutation.isPending}
                          onClick={() => cancelMutation.mutate(req.id)}
                        >
                          Batalkan
                        </Button>
                      )}
                      {req.status === 'APPROVED' && (
                        <Button onClick={() => openUnlockModal(req)}>
                          <Unlock size={15} aria-hidden="true" />
                          Buka Paket Kunci & Lihat Data
                        </Button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* TAB 3: Create New Request */}
      {tab === 'request' && (
        <section className="panel stack-sm">
          <div>
            <h2 style={{ margin: 0 }}>Ajukan Permintaan Akses Data Pengguna Lain</h2>
            <p style={{ margin: '0.25rem 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>
              Masukkan username pemohon target dan pilih data sintetis yang ingin Anda minta aksesnya.
            </p>
          </div>
          {!serverKey && (
            <div style={{ padding: '0.85rem 1rem', borderRadius: '0.5rem', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.4)', fontSize: '0.9rem' }}>
              Anda harus men-generate dan mendaftarkan <strong>Kunci RSA</strong> terlebih dahulu di panel atas sebelum dapat mengajukan permintaan akses.
            </div>
          )}
          {createRequestMutation.isError && <ErrorState error={createRequestMutation.error} />}
          <form
            className="stack-sm"
            onSubmit={e => {
              e.preventDefault();
              createRequestMutation.mutate();
            }}
          >
            <div className="field">
              <label htmlFor="share-owner-username">Username Pemilik Data</label>
              <input
                id="share-owner-username"
                type="text"
                placeholder="Contoh: applicant_demo"
                value={targetOwner}
                onChange={e => setTargetOwner(e.target.value)}
                required
                disabled={!serverKey || createRequestMutation.isPending}
              />
            </div>
            <div className="field">
              <label htmlFor="share-purpose">Tujuan Permintaan Akses</label>
              <input
                id="share-purpose"
                type="text"
                placeholder="Contoh: Verifikasi berkas keanggotaan organisasi (minimal 10 karakter)"
                value={purpose}
                onChange={e => setPurpose(e.target.value)}
                minLength={10}
                maxLength={300}
                required
                disabled={!serverKey || createRequestMutation.isPending}
              />
            </div>
            <fieldset style={{ border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.85rem 1rem' }}>
              <legend style={{ padding: '0 0.4rem', fontWeight: 600, fontSize: '0.9rem' }}>Pilih Item Data yang Diminta</legend>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.6rem' }}>
                {SHAREABLE_ITEMS.map(item => (
                  <label key={item.id} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={selectedRequestItems.includes(item.id)}
                      onChange={() => toggleItem(selectedRequestItems, setSelectedRequestItems, item.id)}
                      disabled={!serverKey || createRequestMutation.isPending}
                    />
                    <span>
                      <strong style={{ display: 'block', fontSize: '0.9rem' }}>{item.label}</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{item.desc}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div>
              <Button
                type="submit"
                busy={createRequestMutation.isPending}
                disabled={!serverKey || !targetOwner.trim() || purpose.trim().length < 10 || selectedRequestItems.length === 0}
              >
                <Send size={16} aria-hidden="true" />
                Kirim Permintaan Akses
              </Button>
            </div>
          </form>
        </section>
      )}

      {/* MODAL 1: Approve Request */}
      <Modal
        open={Boolean(approveTarget)}
        onOpenChange={open => { if (!open) setApproveTarget(null); }}
        title="Setujui Permintaan & Generate Kunci Simetris"
        description={
          approveTarget
            ? `Pilih pengajuan dan dokumen yang ingin dibagikan kepada ${approveTarget.requester_username}.`
            : ''
        }
      >
        {approveTarget && (
          <div className="stack-sm">
            {approveMutation.isError && <ErrorState error={approveMutation.error} />}
            <div className="field">
              <label htmlFor="approve-app-select">Sumber Pengajuan KYC</label>
              <select
                id="approve-app-select"
                value={approveAppId}
                onChange={e => setApproveAppId(e.target.value)}
              >
                {shareableApps.map(app => (
                  <option key={app.id} value={app.id}>
                    {app.reference} — ({app.status})
                  </option>
                ))}
              </select>
            </div>
            <div className="stack-xs">
              <strong style={{ fontSize: '0.9rem' }}>Item yang Disetujui untuk Dibagikan:</strong>
              {approveTarget.requested_items.map(kind => (
                <label key={kind} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={approveItems.includes(kind)}
                    onChange={() => toggleItem(approveItems, setApproveItems, kind)}
                  />
                  <span>{ITEM_LABELS[kind] ?? kind}</span>
                </label>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
              <Button variant="secondary" onClick={() => setApproveTarget(null)}>Batal</Button>
              <Button
                busy={approveMutation.isPending}
                disabled={!approveAppId || approveItems.length === 0}
                onClick={() => approveMutation.mutate({ id: approveTarget.id, appId: approveAppId, items: approveItems })}
              >
                <KeyRound size={15} aria-hidden="true" />
                Generate Kunci & Enkripsi Paket
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* MODAL 2: Out-of-Band Encrypted Symmetric Key Package */}
      <Modal
        open={Boolean(packageModal)}
        onOpenChange={open => { if (!open) setPackageModal(null); }}
        title="Paket Kunci Terenkripsi (Out-of-Band)"
        description="Kunci simetris AES-256 telah dienkripsi menggunakan Public Key RSA-OAEP-256 milik pemohon. Salin dan kirimkan melalui WhatsApp atau Email."
      >
        {packageModal && (
          <div className="stack-sm">
            <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.35)', fontSize: '0.86rem' }}>
              <strong>Aman dikirim melalui jalur publik (WA/Email):</strong> Meskipun disadap pihak ketiga, hanya <strong>{packageModal.requester}</strong> yang dapat mendekripsi kunci ini menggunakan Private Key lokalnya.
            </div>
            <div className="field">
              <label htmlFor="oob-package-text">Paket VELTRIX-SHARE-1</label>
              <textarea
                id="oob-package-text"
                readOnly
                rows={5}
                value={packageModal.packageText}
                style={{ fontFamily: 'monospace', fontSize: '0.8rem', wordBreak: 'break-all' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <Button onClick={handleCopyPackage}>
                {copiedPackage ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
                {copiedPackage ? 'Tersalin!' : 'Salin Paket Kunci'}
              </Button>
              <a
                className="button button-secondary"
                href={`https://wa.me/?text=${encodeURIComponent(`Berikut paket kunci terenkripsi VELTRIX untuk permintaan akses data Anda:\n\n${packageModal.packageText}`)}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <MessageCircle size={15} aria-hidden="true" />
                Kirim via WhatsApp
              </a>
              <a
                className="button button-secondary"
                href={`mailto:?subject=${encodeURIComponent('VELTRIX Encrypted Share Key Package')}&body=${encodeURIComponent(`Berikut paket kunci terenkripsi VELTRIX (RSA-OAEP-256):\n\n${packageModal.packageText}`)}`}
              >
                <Mail size={15} aria-hidden="true" />
                Kirim via Email
              </a>
            </div>
          </div>
        )}
      </Modal>

      {/* MODAL 3: Unlock & Decrypt Shared Documents (Requester Side) */}
      <Modal
        open={Boolean(unlockTarget)}
        onOpenChange={open => {
          if (!open) {
            setUnlockTarget(null);
            setPreview(null);
          }
        }}
        title="Buka Paket Kunci & Dekripsi Data"
        description={
          unlockTarget
            ? `Tempel paket VELTRIX-SHARE-1 yang Anda terima dari ${unlockTarget.owner_username} (via WhatsApp/Email) untuk mendekripsi kunci simetris secara lokal di browser.`
            : ''
        }
      >
        {unlockTarget && (
          <div className="stack-sm">
            {unlockError && <ErrorState error={new Error(unlockError)} />}

            {!decryptedShareKey ? (
              <>
                <div className="field">
                  <label htmlFor="unlock-package-input">Paket Terenkripsi (dari WhatsApp / Email)</label>
                  <textarea
                    id="unlock-package-input"
                    rows={4}
                    placeholder="VELTRIX-SHARE-1.eyJhbGciOiJSU0EtT0FFUC0yNTYi..."
                    value={pastePackage}
                    onChange={e => setPastePackage(e.target.value)}
                    style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
                  />
                </div>
                <div className="field">
                  <label htmlFor="unlock-privkey-input">
                    Private Key RSA Anda (PKCS#8 PEM — diproses lokal di browser)
                  </label>
                  <input
                    type="file"
                    accept=".pem"
                    aria-label="Pilih file private key (.pem)"
                    onChange={async e => {
                      const file = e.target.files?.[0];
                      if (file) setUnlockPrivateKey(await file.text());
                      e.target.value = '';
                    }}
                  />
                  <textarea
                    id="unlock-privkey-input"
                    rows={4}
                    placeholder="-----BEGIN PRIVATE KEY-----..."
                    value={unlockPrivateKey}
                    onChange={e => setUnlockPrivateKey(e.target.value)}
                    style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                  <Button variant="secondary" onClick={() => setUnlockTarget(null)}>Tutup</Button>
                  <Button
                    busy={unlocking}
                    disabled={!pastePackage.trim() || !unlockPrivateKey.trim()}
                    onClick={handleDecryptPackage}
                  >
                    <Unlock size={15} aria-hidden="true" />
                    Dekripsi Paket Kunci
                  </Button>
                </div>
              </>
            ) : (
              <div className="stack-sm">
                <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.35)', fontSize: '0.88rem' }}>
                  <strong>Kunci simetris AES-256 (32-byte) berhasil didekripsi secara lokal!</strong> Pilih dokumen di bawah untuk membukanya dalam mode pratinjau in-memory.
                </div>

                <div className="stack-xs">
                  {sharedItems.map(item => (
                    <div
                      key={item.id}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0.65rem 0.85rem',
                        borderRadius: '0.5rem',
                        border: '1px solid var(--border)',
                      }}
                    >
                      <div>
                        <strong>{ITEM_LABELS[item.kind] ?? item.display_name}</strong>
                        <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                          {item.mime_type} · {(item.original_bytes / 1024).toFixed(1)} KiB
                        </div>
                      </div>
                      <Button
                        variant="secondary"
                        busy={openingItemId === item.id}
                        onClick={() => handleOpenSharedItem(item)}
                      >
                        <Eye size={15} aria-hidden="true" />
                        Buka Data
                      </Button>
                    </div>
                  ))}
                </div>

                {/* In-Memory Decrypted Preview Area */}
                {preview && (
                  <div
                    style={{
                      marginTop: '0.5rem',
                      padding: '0.85rem',
                      borderRadius: '0.5rem',
                      border: '1px solid var(--border)',
                      background: 'var(--surface-2, var(--surface))',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                      <strong>Pratinjau In-Memory: {preview.title}</strong>
                      {preview.blob && (
                        <Button
                          variant="secondary"
                          onClick={() => saveBlob(preview.blob!, preview.filename)}
                        >
                          <Download size={14} aria-hidden="true" />
                          Unduh
                        </Button>
                      )}
                    </div>

                    {preview.json && (
                      <dl style={{ display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '0.35rem 1rem', margin: 0, fontSize: '0.88rem' }}>
                        {Object.entries(preview.json).map(([k, v]) => (
                          <div key={k} style={{ display: 'contents' }}>
                            <dt style={{ color: 'var(--muted)', fontWeight: 600 }}>{k}</dt>
                            <dd style={{ margin: 0 }}>{String(v)}</dd>
                          </div>
                        ))}
                      </dl>
                    )}

                    {preview.blobUrl && preview.mime.startsWith('image/') && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={preview.blobUrl}
                        alt={preview.title}
                        style={{ maxWidth: '100%', maxHeight: '360px', borderRadius: '0.4rem', objectFit: 'contain' }}
                      />
                    )}

                    {preview.blobUrl && preview.mime === 'application/pdf' && (
                      <iframe
                        src={preview.blobUrl}
                        title={preview.title}
                        style={{ width: '100%', height: '380px', border: '1px solid var(--border)', borderRadius: '0.4rem' }}
                      />
                    )}

                    {preview.blobUrl && preview.mime.startsWith('video/') && (
                      <video
                        src={preview.blobUrl}
                        controls
                        style={{ width: '100%', maxHeight: '360px', borderRadius: '0.4rem' }}
                      />
                    )}

                    {preview.blobUrl &&
                      !preview.mime.startsWith('image/') &&
                      preview.mime !== 'application/pdf' &&
                      !preview.mime.startsWith('video/') && (
                        <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--muted)' }}>
                          Berkas ({preview.mime}) berhasil didekripsi. Gunakan tombol Unduh di atas untuk menyimpannya.
                        </p>
                      )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
