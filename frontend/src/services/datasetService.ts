/**
 * Dataset service boundary connected to the real backend datasets API.
 *
 * Implements:
 * - list: GET /api/v1/datasets -> maps backend DatasetResponse to frontend Dataset
 * - getById: GET /api/v1/datasets/:id -> maps to frontend Dataset
 * - upload: POST /api/v1/datasets/upload (multipart/form-data) -> maps to frontend Dataset
 * - delete: DELETE /api/v1/datasets/:id
 */

import { apiClient } from '../api/client';
import type { Dataset, DatasetStatus } from '../types/datasets';

export interface BackendDatasetResponse {
  dataset_id: string;
  dataset_name: string;
  file_name: string;
  file_type: string;
  file_path: string;
  original_path?: string | null;
  json_path?: string | null;
  canonical_path?: string | null;
  canonical_format?: string | null;
  content_hash?: string | null;
  size_bytes?: number | null;
  row_count?: number | null;
  column_count?: number | null;
  version: number;
  last_active_version_id?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export function mapBackendDatasetToFrontend(backend: BackendDatasetResponse): Dataset {
  return {
    dataset_id: backend.dataset_id,
    filename: backend.file_name || backend.dataset_name || 'untitled',
    size_bytes: backend.size_bytes ?? 0,
    uploaded_at: backend.created_at
      ? new Date(backend.created_at).toISOString()
      : new Date().toISOString(),
    status: (backend.status as DatasetStatus) || 'uploaded',
  };
}

export const datasetService = {
  async list(skip = 0, limit = 50): Promise<Dataset[]> {
    const data = await apiClient.get<BackendDatasetResponse[]>('/api/v1/datasets', {
      params: {
        skip: String(skip),
        limit: String(limit),
      },
    });
    return data.map(mapBackendDatasetToFrontend);
  },

  async getById(datasetId: string): Promise<Dataset> {
    const data = await apiClient.get<BackendDatasetResponse>(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}`,
    );
    return mapBackendDatasetToFrontend(data);
  },

  async upload(file: File, datasetName?: string): Promise<Dataset> {
    const formData = new FormData();
    formData.append('file', file);
    if (datasetName) {
      formData.append('dataset_name', datasetName);
    }
    const data = await apiClient.post<BackendDatasetResponse>(
      '/api/v1/datasets/upload',
      formData,
    );
    return mapBackendDatasetToFrontend(data);
  },

  async delete(datasetId: string): Promise<void> {
    await apiClient.delete(`/api/v1/datasets/${encodeURIComponent(datasetId)}`);
  },
};
