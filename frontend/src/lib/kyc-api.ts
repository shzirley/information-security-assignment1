import { call } from './api';
import type { ApplicantProfile, Application, AssignmentList, CaseAction, CaseList, EvidenceCategory, LabRun, ProfileResponse } from './kyc';

const json = (value: unknown) => JSON.stringify(value);
const path = (id: string) => `/applications/${encodeURIComponent(id)}`;
export const kycApi = {
  applications: () => call<CaseList>('/applications'),
  create: () => call<Application>('/applications', { method: 'POST', body: '{}' }),
  application: (id: string) => call<Application>(path(id)),
  profile: (id: string) => call<ProfileResponse>(`${path(id)}/personal-data`),
  saveProfile: (id: string, profile: ApplicantProfile, version: number) => call<Application>(`${path(id)}/personal-data`, { method: 'PUT', body: json({ profile, version }) }),
  upload: (id: string, category: EvidenceCategory, file: File, version: number) => {
    const body = new FormData(); body.append('category', category); body.append('file', file); body.append('version', String(version));
    return call<Application>(`${path(id)}/evidence`, { method: 'POST', body });
  },
  action: (id: string, action: CaseAction, version: number, note?: string, synthetic_acknowledged?: boolean) => call<Application>(`${path(id)}/actions`, { method: 'POST', body: json({ action, version, note, synthetic_acknowledged }) }),
  download: (id: string, evidenceId: string) => call<Blob>(`${path(id)}/evidence/${encodeURIComponent(evidenceId)}/download`),
  downloadProfile: (id: string) => call<Blob>(`${path(id)}/personal-data/download`),
  assignments: () => call<AssignmentList>('/admin/assignments'),
  assign: (id: string, reviewer_id: string, version: number) => call<Application>(`/admin/assignments/${encodeURIComponent(id)}`, { method: 'PUT', body: json({ reviewer_id, version }) }),
  labRuns: () => call<LabRun[]>('/lab/runs'),
  runLab: (kind: LabRun['kind'], fixture: string, repetitions: number) => call<LabRun>('/lab/runs', { method: 'POST', body: json({ kind, fixture, repetitions, warmups: 2 }) }),
  exportLab: (id: string) => call<Blob>(`/lab/runs/${encodeURIComponent(id)}/export`),
};
