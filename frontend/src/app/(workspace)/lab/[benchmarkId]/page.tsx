'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ErrorState, LoadingState, MockNote, PageHeading } from '@/components/ui';
import { BenchmarkView } from '@/features/lab/benchmark-view';
export default function BenchmarkDetail() {
  const { benchmarkId } = useParams<{ benchmarkId: string }>();
  const result = useQuery({ queryKey: ['benchmark', benchmarkId], queryFn: () => api.result(benchmarkId) });
  return <><Link href="/lab" className="back-link">Kembali ke Cryptography Lab</Link><PageHeading index="04 / Hasil" title="Catatan eksperimen" description="Konfigurasi, hasil per algoritma, dan data yang bisa diekspor." /><MockNote />{result.isPending ? <LoadingState /> : result.isError ? <ErrorState error={result.error} retry={() => result.refetch()} /> : <BenchmarkView result={result.data} />}</>;
}
