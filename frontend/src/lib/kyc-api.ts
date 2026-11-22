import { call } from './api';
import type { ApplicantProfile, Application, AssignmentList, CaseAction, CaseList, EvidenceCategory, LabRun, ProfileResponse, DocumentType, EvidenceCheck, ReviewChecksResponse, ReviewerProfile, DocumentAnalysis, PublicKeyInfo, ShareItem, ShareRequest } from './kyc';

const json = (value: unknown) => JSON.stringify(value);
const path = (id: string) => `/applications/${encodeURIComponent(id)}`;
const evidencePath = (id: string, evidenceId: string) => `${path(id)}/evidence/${encodeURIComponent(evidenceId)}`;
export const kycApi = {
  applications: () => call<CaseList>('/applications'),
  create: () => call<Application>('/applications', { method: 'POST', body: '{}' }),
  application: (id: string) => call<Application>(path(id)),
  profile: (id: string) => call<ProfileResponse>(`${path(id)}/personal-data`),
  saveProfile: (id: string, profile: ApplicantProfile, version: number) => call<Application>(`${path(id)}/personal-data`, { method: 'PUT', body: json({ profile, version }) }),
  upload: (id: string, category: EvidenceCategory, file: File, version: number, documentType?: DocumentType) => {
    const body = new FormData(); body.append('category', category); body.append('file', file); body.append('version', String(version));
    if (documentType) body.append('document_type', documentType);
    return call<Application>(`${path(id)}/evidence`, { method: 'POST', body });
  },
  reviewProfile: (id: string, signal?: AbortSignal) =>
    call<{ profile: ReviewerProfile }>(`${path(id)}/review/profile`, { signal }),
  reviewPreview: (id: string, evidenceId: string, signal?: AbortSignal) =>
    call<Blob>(`${evidencePath(id, evidenceId)}/review-preview`, { signal }),
  reviewPdfPage: (id: string, evidenceId: string, page: number, signal?: AbortSignal) =>
    call<{ page: number; pages: number; image_base64: string }>(`${evidencePath(id, evidenceId)}/review-preview?page=${page}`, { signal }),
  reviewChecks: (id: string, signal?: AbortSignal) =>
    call<ReviewChecksResponse>(`${path(id)}/review/checks`, { signal }),
  saveReviewChecks: (id: string, version: number, checks: EvidenceCheck[]) =>
    call<ReviewChecksResponse>(`${path(id)}/review/checks`, { method: 'POST', body: json({ version, checks }) }),
  analysis: (id: string, evidenceId: string, signal?: AbortSignal) =>
    call<DocumentAnalysis>(`${evidencePath(id, evidenceId)}/analysis`, { signal }),
  analyze: (id: string, evidenceId: string, signal?: AbortSignal) =>
    call<DocumentAnalysis>(`${evidencePath(id, evidenceId)}/analysis`, { method: 'POST', signal }),
  action: (id: string, action: CaseAction, version: number, note?: string, synthetic_acknowledged?: boolean) => call<Application>(`${path(id)}/actions`, { method: 'POST', body: json({ action, version, note, synthetic_acknowledged }) }),
  download: (id: string, evidenceId: string) => call<Blob>(`${path(id)}/evidence/${encodeURIComponent(evidenceId)}/download`),
  downloadProfile: (id: string) => call<Blob>(`${path(id)}/personal-data/download`),
  assignments: () => call<AssignmentList>('/admin/assignments'),
  assign: (id: string, reviewer_id: string, version: number) => call<Application>(`/admin/assignments/${encodeURIComponent(id)}`, { method: 'PUT', body: json({ reviewer_id, version }) }),
  labRuns: () => call<LabRun[]>('/lab/runs'),
  runLab: (kind: LabRun['kind'], fixture: string, repetitions: number) => call<LabRun>('/lab/runs', { method: 'POST', body: json({ kind, fixture, repetitions, warmups: 2 }) }),
  exportLab: (id: string) => call<Blob>(`/lab/runs/${encodeURIComponent(id)}/export`),
  // Assignment 2: Key Management & Out-of-Band Data Sharing
  myPublicKey: () => call<{ key: PublicKeyInfo | null }>('/keys/me'),
  registerPublicKey: (public_key_pem: string) =>
    call<{ public_key_pem: string; fingerprint: string }>('/keys/me', { method: 'PUT', body: json({ public_key_pem }) }),
  shareRequests: (box: 'incoming' | 'outgoing') =>
    call<{ items: ShareRequest[] }>(`/share-requests?box=${box}`),
  createShareRequest: (owner_username: string, purpose: string, items: string[]) =>
    call<ShareRequest>('/share-requests', { method: 'POST', body: json({ owner_username, purpose, items }) }),
  approveShareRequest: (id: string, application_id: string, items: string[]) =>
    call<{ status: string; expires_at: string; package: string }>(`/share-requests/${encodeURIComponent(id)}/approve`, {
      method: 'POST',
      body: json({ application_id, items }),
    }),
  rejectShareRequest: (id: string) =>
    call<{ status: string }>(`/share-requests/${encodeURIComponent(id)}/reject`, { method: 'POST' }),
  cancelShareRequest: (id: string) =>
    call<{ status: string }>(`/share-requests/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),
  revokeShareRequest: (id: string) =>
    call<{ status: string }>(`/share-requests/${encodeURIComponent(id)}/revoke`, { method: 'POST' }),
  sharePackage: (id: string) =>
    call<{ package: string; key_fp: string }>(`/share-requests/${encodeURIComponent(id)}/package`),
  shareItems: (id: string) =>
    call<{ items: ShareItem[]; expires_at: string }>(`/share-requests/${encodeURIComponent(id)}/items`),
  openShareItem: (requestId: string, itemId: string, share_key: string) =>
    call<Blob | Record<string, unknown>>(`/share-requests/${encodeURIComponent(requestId)}/items/${encodeURIComponent(itemId)}/open`, {
      method: 'POST',
      body: json({ share_key }),
    }),
};
