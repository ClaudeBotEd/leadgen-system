import { WHY_RULES, FALLBACK } from './rules';

export function whyString(decision: { tierAtDecision: string; inputsPayload: any }, profile: { profile: any }): string {
  for (const r of WHY_RULES) if (r.matches(decision, profile)) return r.text;
  return FALLBACK;
}
