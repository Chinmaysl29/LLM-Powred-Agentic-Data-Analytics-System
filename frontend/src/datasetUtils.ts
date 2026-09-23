/**
 * datasetUtils.ts
 *
 * Non-component shared utilities for the Dataset Management feature.
 * Contains ONLY data and pure functions (no React components).
 *
 * Extracted to a plain .ts file to comply with the ESLint
 * react-refresh/only-export-components rule. The StatusBadge component
 * lives in StatusBadge.tsx.
 *
 * BACKEND DEPENDENCY: DEV_DATASETS and DEV_PREVIEWS are removed when
 * the corresponding backend endpoints are live.
 */

import type { Dataset, DatasetStatus, DatasetPreview } from './types/datasets';

// ---------------------------------------------------------------------------
// DEVELOPMENT DATA - Phase 2B only.
//
// This constant provides UI-rendering data while the backend endpoint
// GET /api/datasets does not exist. It is:
//   - NOT a mock API
//   - NOT a fake HTTP endpoint
//   - NOT production data
//
// Fields mirror the confirmed DatasetResponse schema from the Phase 2A
// audit (backend/schemas/datasets.py). The `path` field is intentionally
// absent - server filesystem paths must never appear in the UI.
//
// Status values other than 'uploaded' are ANTICIPATED from the pipeline
// architecture (raw -> validated -> processed). They are not yet confirmed
// backend contract values. Treat them as development-only placeholders.
//
// BACKEND DEPENDENCY: Remove this constant when GET /api/datasets is live.
// ---------------------------------------------------------------------------

export const DEV_DATASETS: Dataset[] = [
  {
    dataset_id: 'dev-001',
    filename: 'sales_q1_2026.csv',
    size_bytes: 2_457_600,
    uploaded_at: '2026-03-15T09:22:00Z',
    status: 'processed',
  },
  {
    dataset_id: 'dev-002',
    filename: 'customer_survey_results.xlsx',
    size_bytes: 854_230,
    uploaded_at: '2026-04-02T14:05:00Z',
    status: 'validated',
  },
  {
    dataset_id: 'dev-003',
    filename: 'inventory_snapshot.json',
    size_bytes: 128_000,
    uploaded_at: '2026-05-10T08:30:00Z',
    status: 'processing',
  },
  {
    dataset_id: 'dev-004',
    filename: 'marketing_spend_2025.csv',
    size_bytes: 67_200,
    uploaded_at: '2026-06-12T16:48:00Z',
    status: 'uploaded',
  },
  {
    dataset_id: 'dev-005',
    filename: 'user_events_raw.parquet',
    size_bytes: 18_900_000,
    uploaded_at: '2026-07-14T11:00:00Z',
    status: 'validating',
  },
  {
    dataset_id: 'dev-006',
    filename: 'product_catalog_v3.xlsx',
    size_bytes: 432_000,
    uploaded_at: '2026-08-01T09:10:00Z',
    status: 'failed',
  },
];

// ---------------------------------------------------------------------------
// Status display labels
// ---------------------------------------------------------------------------

export const STATUS_LABELS: Record<DatasetStatus, string> = {
  uploaded:   'Uploaded',
  validating: 'Validating',
  validated:  'Validated',
  processing: 'Processing',
  processed:  'Processed',
  failed:     'Failed',
};

// ---------------------------------------------------------------------------
// Formatting utilities - pure, no side effects
// ---------------------------------------------------------------------------

/**
 * Formats a byte count into a human-readable size string.
 * e.g. 2_457_600 -> "2.3 MB"
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1_024) return `${bytes} B`;
  if (bytes < 1_024 * 1_024) return `${(bytes / 1_024).toFixed(1)} KB`;
  if (bytes < 1_024 * 1_024 * 1_024)
    return `${(bytes / (1_024 * 1_024)).toFixed(1)} MB`;
  return `${(bytes / (1_024 * 1_024 * 1_024)).toFixed(2)} GB`;
}

/**
 * Formats an ISO 8601 date string into a locale-aware short date.
 * e.g. "2026-03-15T09:22:00Z" -> "Mar 15, 2026"
 */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Formats an ISO 8601 date string into a locale-aware date + time string.
 * e.g. "2026-03-15T09:22:00Z" -> "Mar 15, 2026, 9:22 AM"
 */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Extracts the uppercase file extension from a filename.
 * e.g. "sales_q1.csv" -> "CSV"
 */
export function getExtension(filename: string): string {
  const ext = filename.split('.').pop()?.toUpperCase() ?? '';
  return ext || '-';
}

// ---------------------------------------------------------------------------
// DEV_PREVIEWS - Phase 2E development preview data.
//
// A map from dataset_id to a bounded DatasetPreview snapshot.
// Provides realistic sample rows for each development dataset so the
// preview UI can be built and validated before the backend endpoint exists.
//
// Rules:
//   - No browser-side file parsing (no PapaParse, SheetJS, etc.)
//   - Columns and rows are hand-authored to match each dataset's domain
//   - null values are intentionally included to exercise null handling
//   - Datasets in non-previewable states (processing, validating, failed,
//     uploaded) have no preview data by design — the UI handles this case
//     as an empty preview state
//   - totalRows reflects a realistic full-dataset size so "Showing X of Y"
//     text is meaningful
//
// BACKEND DEPENDENCY: Remove this constant when
//   GET /api/datasets/:id/preview is implemented.
// ---------------------------------------------------------------------------

export const DEV_PREVIEWS: Record<string, DatasetPreview> = {
  // dev-001: sales_q1_2026.csv — status: processed (preview available)
  'dev-001': {
    columns: ['date', 'region', 'product', 'units_sold', 'revenue', 'cost'],
    rows: [
      { date: '2026-01-03', region: 'North', product: 'Widget A', units_sold: 142, revenue: 7100.00, cost: 4260.00 },
      { date: '2026-01-05', region: 'South', product: 'Widget B', units_sold: 89,  revenue: 5340.00, cost: 2670.00 },
      { date: '2026-01-07', region: 'East',  product: 'Gadget X', units_sold: 203, revenue: 20300.00, cost: 10150.00 },
      { date: '2026-01-10', region: 'West',  product: 'Widget A', units_sold: 57,  revenue: 2850.00, cost: 1710.00 },
      { date: '2026-01-14', region: 'North', product: 'Gadget Y', units_sold: null, revenue: null, cost: null },
      { date: '2026-01-17', region: 'South', product: 'Widget B', units_sold: 310, revenue: 18600.00, cost: 9300.00 },
      { date: '2026-01-21', region: 'East',  product: 'Widget A', units_sold: 77,  revenue: 3850.00, cost: 2310.00 },
      { date: '2026-01-25', region: 'West',  product: 'Gadget X', units_sold: 195, revenue: 19500.00, cost: 9750.00 },
      { date: '2026-02-01', region: 'North', product: 'Gadget Y', units_sold: 88,  revenue: 8800.00, cost: 4400.00 },
      { date: '2026-02-06', region: 'South', product: 'Widget A', units_sold: 231, revenue: 11550.00, cost: 6930.00 },
    ],
    totalRows: 1_250,
  },

  // dev-002: customer_survey_results.xlsx — status: validated (preview available)
  'dev-002': {
    columns: ['respondent_id', 'age_group', 'satisfaction', 'nps_score', 'would_recommend', 'comment'],
    rows: [
      { respondent_id: 'R-0001', age_group: '25-34', satisfaction: 'Very Satisfied', nps_score: 9,  would_recommend: true,  comment: 'Great product overall.' },
      { respondent_id: 'R-0002', age_group: '35-44', satisfaction: 'Satisfied',      nps_score: 7,  would_recommend: true,  comment: null },
      { respondent_id: 'R-0003', age_group: '18-24', satisfaction: 'Neutral',        nps_score: 5,  would_recommend: false, comment: 'Could improve onboarding.' },
      { respondent_id: 'R-0004', age_group: '45-54', satisfaction: 'Dissatisfied',   nps_score: 2,  would_recommend: false, comment: 'Frequent bugs in the dashboard.' },
      { respondent_id: 'R-0005', age_group: '55+',   satisfaction: 'Very Satisfied', nps_score: 10, would_recommend: true,  comment: 'Excellent customer support.' },
      { respondent_id: 'R-0006', age_group: '25-34', satisfaction: 'Satisfied',      nps_score: 8,  would_recommend: true,  comment: null },
      { respondent_id: 'R-0007', age_group: '35-44', satisfaction: 'Neutral',        nps_score: 6,  would_recommend: null,  comment: 'Needs better mobile support.' },
      { respondent_id: 'R-0008', age_group: '18-24', satisfaction: 'Very Satisfied', nps_score: 9,  would_recommend: true,  comment: 'Love the new features.' },
      { respondent_id: 'R-0009', age_group: '45-54', satisfaction: 'Satisfied',      nps_score: 7,  would_recommend: true,  comment: null },
      { respondent_id: 'R-0010', age_group: '25-34', satisfaction: 'Dissatisfied',   nps_score: 3,  would_recommend: false, comment: 'Pricing is too high for the value.' },
    ],
    totalRows: 4_830,
  },

  // dev-003: inventory_snapshot.json — status: processing
  // No preview available while processing is in progress.

  // dev-004: marketing_spend_2025.csv — status: uploaded
  // No preview available until validation completes.

  // dev-005: user_events_raw.parquet — status: validating
  // No preview available while validation is in progress.

  // dev-006: product_catalog_v3.xlsx — status: failed
  // No preview available due to processing failure.
};
