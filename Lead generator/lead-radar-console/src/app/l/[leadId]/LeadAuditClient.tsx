'use client';
import { useRouter } from 'next/navigation';
import { AuditChainView } from '@/components/audit/AuditChainView';

export function LeadAuditClient({ leadId }: { leadId: string }) {
  const router = useRouter();
  return <AuditChainView leadId={leadId} onClose={() => router.push('/triage')} />;
}
