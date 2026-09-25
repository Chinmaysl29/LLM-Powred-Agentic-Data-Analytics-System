/**
 * Analysis service for natural-language analytics and orchestration chat.
 * Connects directly to backend POST /api/v1/chat.
 */

import { apiClient } from '../api/client';
import type { ChatRequest, ChatResponse } from '../types/analysis';

export const analysisService = {
  /**
   * Submit an analytical question or query to the backend agent orchestrator.
   *
   * @param message - User's question or analytical request.
   * @param datasetId - Optional dataset UUID to scope analysis to.
   * @returns Structured ChatResponse with answer, data, explanation, and actionable recommendations.
   */
  async ask(message: string, datasetId?: string | null): Promise<ChatResponse> {
    const payload: ChatRequest = {
      message: message.trim(),
      dataset_id: datasetId ? datasetId : null,
    };
    return apiClient.post<ChatResponse>('/api/v1/chat', payload);
  },
};
