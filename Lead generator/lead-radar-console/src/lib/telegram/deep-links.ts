type Target =
  | { type: 'decision'; decisionId: string; returnTo?: string }
  | { type: 'lead'; leadId: string; returnTo?: string }
  | { type: 'triage' };

export function makeDeepLink(target: Target): string {
  const base = process.env.CONSOLE_BASE_URL ?? 'http://localhost:3000';
  switch (target.type) {
    case 'decision':
      return `${base}/d/${target.decisionId}${target.returnTo ? `?return_to=${target.returnTo}` : ''}`;
    case 'lead':
      return `${base}/l/${target.leadId}${target.returnTo ? `?return_to=${target.returnTo}` : ''}`;
    case 'triage':
      return `${base}/triage`;
  }
}
