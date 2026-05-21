import { describe, it, expect } from 'vitest';
import { whyString } from '@/lib/why-string/generator';

describe('why-string', () => {
  it('T1 trust-load-bearing routing', () => {
    expect(whyString({ tierAtDecision: 'T1', inputsPayload: {} } as any, { profile: { risk_class: 'trust_load_bearing', terminal_tier: 'T1' } } as any))
      .toMatch(/T1 always-review/i);
  });
  it('dataset-defining', () => {
    expect(whyString({ tierAtDecision: 'T1', inputsPayload: {} } as any, { profile: { risk_class: 'dataset_defining' } } as any))
      .toMatch(/dataset-defining/i);
  });
  it('respects 12-word limit', () => {
    const r = whyString({ tierAtDecision: 'T1', inputsPayload: {} } as any, { profile: { risk_class: 'trust_load_bearing', terminal_tier: 'T1' } } as any);
    expect(r.split(/\s+/).length).toBeLessThanOrEqual(12);
  });
});
