// Ticket type stubs. Aligned to PRD §8 in Phase 1.
export interface Ticket {
  id: number;
  title: string;
  message: string;
  category?: string | null;
  sentiment: string;
  confidence: number;
  created_at: string;
}
