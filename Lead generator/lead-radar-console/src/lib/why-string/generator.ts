import { WHY_RULES, FALLBACK, type DecisionLike, type ProfileLike } from './rules';

export function whyString(decision: DecisionLike, profile: ProfileLike): string {
  for (const r of WHY_RULES) if (r.matches(decision, profile)) return r.text;
  return FALLBACK;
}
