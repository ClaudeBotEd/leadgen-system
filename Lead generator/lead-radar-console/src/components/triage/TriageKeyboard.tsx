'use client';
import { useRouter } from 'next/navigation';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

export function TriageKeyboard() {
  const router = useRouter();
  useKeyboardShortcuts({
    '1': () => router.push('/q/lead_delivery_routing'),
    '2': () => router.push('/q/signal_classification_ambiguous_band'),
    '3': () => router.push('/q/conversion_registration'),
  });
  return null;
}
