'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { roleHome } from '@/lib/kyc';
import { LoadingState } from './ui';

export function WorkspaceRedirect() {
  const router = useRouter(); const session = useQuery({ queryKey: ['session'], queryFn: api.me });
  useEffect(() => { if (session.data) router.replace(roleHome[session.data.role]); }, [session.data, router]);
  return <LoadingState label="Membuka workspace…" />;
}
