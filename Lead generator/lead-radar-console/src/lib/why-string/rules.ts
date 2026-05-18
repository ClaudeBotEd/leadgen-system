type Rule = { matches: (d: any, p: any) => boolean; text: string };

export const WHY_RULES: Rule[] = [
  { matches: (d) => Boolean(d.inputsPayload?.cof_circuit_breaker_tripped), text: 'CoF circuit breaker tripped — forced T1' },
  { matches: (_, p) => p.profile?.risk_class === 'dataset_defining', text: 'Dataset-defining workflow — terminal T1' },
  { matches: (_, p) => p.profile?.risk_class === 'trust_load_bearing' && p.profile?.terminal_tier === 'T1', text: 'T1 always-review, trust-load-bearing' },
  { matches: (_, p) => p.profile?.risk_class === 'trust_load_bearing', text: 'Trust-load-bearing — sample review' },
  { matches: (d) => Boolean(d.inputsPayload?.in_ambiguous_band), text: 'Within ambigue band 40-75' },
  { matches: (d) => Boolean(d.inputsPayload?.source_novelty_flag), text: 'Source novelty alert — vocabulary shift' },
  { matches: (d) => Boolean(d.inputsPayload?.outcome_confirmation_pending), text: 'Outcome confirmation pending' },
];

export const FALLBACK = 'Review required';
