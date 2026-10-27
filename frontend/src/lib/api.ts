import type { ApiErrorShape, User } from './contracts';

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public fields: Record<string, string[]> = {}) {
    super(message);
  }
}
let csrfToken: string | undefined;
export function clearApiSession() { csrfToken = undefined; }

export async function call<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const method = options.method ?? 'GET';
  if (!['GET', 'HEAD'].includes(method)) {
    if (!csrfToken) {
      const tokenResponse = await fetch('/api/v1/auth/csrf', { credentials: 'include', cache: 'no-store' });
      if (!tokenResponse.ok) throw new ApiError(tokenResponse.status, 'CSRF_UNAVAILABLE', 'Tidak bisa menyiapkan sesi. Coba lagi.');
      csrfToken = ((await tokenResponse.json()) as { token: string }).token;
    }
    headers.set('X-CSRF-Token', csrfToken!);
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'include', cache: 'no-store' });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'NETWORK_ERROR', 'Koneksi terputus. Periksa koneksi lalu coba lagi.');
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as ApiErrorShape | null;
    const failure = new ApiError(response.status, payload?.error.code ?? 'REQUEST_FAILED', payload?.error.message ?? 'Permintaan gagal. Coba lagi.', payload?.error.field_errors);
    if (response.status === 401 && path !== '/auth/login' && path !== '/auth/me') {
      window.dispatchEvent(new Event('veltrix:session-expired'));
    }
    if (response.status === 403) csrfToken = undefined;
    throw failure;
  }
  if (response.status === 204) return undefined as T;
  if (!response.headers.get('content-type')?.includes('application/json')) return await response.blob() as T;
  return await response.json() as T;
}
const json = (data: unknown) => JSON.stringify(data);
async function session(path: string, options?: RequestInit) {
  const user = await call<User>(path, options);
  if (!user || !['applicant', 'reviewer', 'admin', 'evaluator'].includes(user.role) || typeof user.display_name !== 'string') {
    throw new ApiError(426, 'KYC_CONTRACT_REQUIRED', 'Layanan pengajuan belum tersedia. Coba lagi setelah layanan diperbarui.');
  }
  if (path === '/auth/login' || path === '/auth/register') clearApiSession();
  return user;
}
export const api = {
  me: () => session('/auth/me'),
  login: (username: string, password: string) => session('/auth/login', { method: 'POST', body: json({ username, password }) }),
  register: (username: string, password: string) => session('/auth/register', { method: 'POST', body: json({ username, password }) }),
  logout: () => call<void>('/auth/logout', { method: 'POST' }),
};
export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
