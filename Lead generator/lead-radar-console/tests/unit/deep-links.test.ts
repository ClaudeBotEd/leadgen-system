import { describe, it, expect } from 'vitest';
import { makeDeepLink } from '@/lib/telegram/deep-links';

describe('deep links', () => {
  it('decision with return_to', () => {
    expect(
      makeDeepLink({ type: 'decision', decisionId: 'abc', returnTo: 'triage' })
    ).toMatch(/d\/abc\?return_to=triage$/);
  });

  it('lead without return_to', () => {
    expect(makeDeepLink({ type: 'lead', leadId: 'lead-1' })).toMatch(
      /l\/lead-1$/
    );
  });

  it('triage link is just base/triage', () => {
    expect(makeDeepLink({ type: 'triage' })).toMatch(/\/triage$/);
  });
});
