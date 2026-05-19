import { textMode } from './text-mode';
import { exactMode } from './exact-mode';

export type RetrievalMode = 'text' | 'exact';
export type Match = {
  leadId: string;
  preview: string;
  source?: string;
  status?: string;
  matchedAt: string;
};

export async function retrieve(query: string, mode: RetrievalMode = 'text'): Promise<Match[]> {
  switch (mode) {
    case 'text': return textMode(query);
    case 'exact': return exactMode(query);
    default: throw new Error(`Unknown mode: ${mode}`);
  }
}
