export const ALGORITHMS = ['AES', 'RC4', 'DES'] as const;
export type Algorithm = typeof ALGORITHMS[number];
export type Category = 'identity' | 'document' | 'video';
export const categoryLabels: Record<Category, string> = {
  identity: 'Kartu identitas', document: 'Dokumen', video: 'Video',
};
export interface User { id: string; username: string }
export interface CipherVersion {
  algorithm: Algorithm;
  mode: 'CBC' | null;
  ciphertext_bytes: number;
  stored_bytes: number;
  ciphertext_sample_hex?: string;
}
export interface VaultFile {
  id: string;
  display_name: string;
  category: Category;
  mime_type: string;
  original_bytes: number;
  total_stored_bytes: number;
  status: 'ready';
  created_at: string;
  versions: CipherVersion[];
}
export interface FileList { items: VaultFile[]; page: number; page_size: number; total: number }
export interface PersonalFields {
  full_name: string; email: string; phone: string; address: string;
  date_of_birth: string; identity_number: string;
}
export interface PersonalRecord {
  id: string; updated_at: string; versions: CipherVersion[]; status: 'ready';
}
export interface Summary {
  file_count: number; original_bytes: number; stored_bytes: number; personal_data_exists: boolean;
}
export interface Capabilities {
  max_file_bytes: number; supported_extensions: string[];
  min_repetitions: number; max_repetitions: number;
}
export interface ApiErrorShape {
  error: { code: string; message: string; field_errors?: Record<string, string[]>; request_id?: string };
}
export interface CryptoSample {
  algorithm: Algorithm; repetition: number; encrypt_ns: number; decrypt_ns: number;
  integrity_ns: number; correctness_ns: number; ciphertext_bytes: number; stored_bytes: number;
  round_trip_ok: boolean;
}
export interface BenchmarkResult {
  id: string; source: { type: 'file' | 'personal_data'; id: string }; input_bytes: number;
  repetitions: number; warmups: number; created_at: string;
  environment: Record<string, string>; methodology_version: string; samples: CryptoSample[];
  summary: Array<{
    algorithm: Algorithm; mean_encrypt_ns: number; median_encrypt_ns: number;
    stddev_encrypt_ns: number; mean_decrypt_ns: number; median_decrypt_ns: number;
    stddev_decrypt_ns: number; round_trip_successes: number; measured_runs: number;
  }>;
}
export interface DownloadAttempt {
  algorithm: Algorithm; repetition: number; elapsed_ms: number; received_bytes: number;
  success: boolean; error_code?: string;
}
export const isMock = process.env.NEXT_PUBLIC_API_MODE !== 'live';

export function bytes(value: number) {
  if (value < 1000) return `${value} B`;
  if (value < 1_000_000) return `${(value / 1000).toFixed(1)} KB`;
  return `${(value / 1_000_000).toFixed(2)} MB`;
}
export function dateLabel(value: string) {
  return new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
}
