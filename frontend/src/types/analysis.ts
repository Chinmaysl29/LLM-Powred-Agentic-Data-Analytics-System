/**
 * Frontend types for AI Analysis & Chat.
 * Matches backend POST /api/v1/chat contract.
 */

export interface ChatRequest {
  message: string;
  dataset_id?: string | null;
}

export interface ChatResponse {
  answer: string;
  intent: string;
  confidence: number;
  execution_time: number;
  data: Array<Record<string, unknown>>;
  explanation?: string | null;
  actionable: string[];
}
