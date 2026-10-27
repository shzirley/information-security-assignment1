export type Role = 'applicant' | 'reviewer' | 'admin' | 'evaluator';
export interface User { id: string; username: string; display_name: string; role: Role }
export interface ApiErrorShape {
  error: { code: string; message: string; field_errors?: Record<string, string[]>; request_id?: string };
}
export const isMock = process.env.NEXT_PUBLIC_API_MODE === 'mock';
export function bytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / 1024 ** 2).toFixed(2)} MiB`;
}
export function dateLabel(value: string) {
  return new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
}
