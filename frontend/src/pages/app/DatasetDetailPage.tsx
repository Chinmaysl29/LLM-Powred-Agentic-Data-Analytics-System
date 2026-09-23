/**
 * DatasetDetailPage
 *
 * Displays the metadata details and a bounded data preview for a single dataset.
 * Reached via the route: /datasets/:datasetId
 *
 * Phase 2D: Metadata details — dataset_id, filename, size, uploaded_at, status.
 * Phase 2E: Data Preview section added at the reserved placeholder. Shows a
 *   bounded sample of rows and columns from the development preview data.
 *   No browser-side file parsing occurs.
 *
 * Shared utilities (StatusBadge, formatFileSize, formatDate, formatDateTime,
 * getExtension, DEV_DATASETS, DEV_PREVIEWS) are imported from datasetUtils.ts
 * and components/StatusBadge.tsx to avoid duplication and to comply with
 * the ESLint react-refresh/only-export-components rule.
 *
 * Future integration path (metadata):
 *   1. Import { datasetService } from '../../services/datasetService'
 *   2. Replace the synchronous DEV_DATASETS lookup with a useEffect that calls
 *      datasetService.get(datasetId), sets isLoading, and catches ApiError.
 *   3. Remove the DEV_DATASETS import.
 *
 * Future integration path (preview):
 *   1. Replace the synchronous DEV_PREVIEWS lookup with a useEffect that calls
 *      datasetService.preview(datasetId), sets previewLoading/previewError.
 *   2. Remove the DEV_PREVIEWS import.
 *   No presentation code changes are required for either path.
 *
 * BACKEND DEPENDENCY:
 *   GET /api/datasets/:datasetId         — not yet implemented.
 *   GET /api/datasets/:datasetId/preview — not yet implemented.
 * SCOPE: Metadata + bounded preview. Row-level editing belongs to a future phase.
 */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { Dataset, DatasetPreview } from '../../types/datasets';
import {
  DEV_DATASETS,
  DEV_PREVIEWS,
  formatFileSize,
  formatDate,
  formatDateTime,
  getExtension,
} from '../../datasetUtils';
import { StatusBadge } from '../../components/StatusBadge';

// ---------------------------------------------------------------------------
// Utility: safe cell-value formatter
//
// Converts any CellValue to a display string.
// null/undefined → em-dash "—" (consistent, accessible representation)
// boolean        → "Yes" / "No"
// number         → toLocaleString (locale-aware, no forced currency)
// string         → as-is
// ---------------------------------------------------------------------------

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return value.toLocaleString();
  return String(value);
}

// ---------------------------------------------------------------------------
// Utility: convert a column key to a display header
//
// Converts snake_case / camelCase identifiers to Title Case words.
// e.g. "units_sold" -> "Units Sold", "npsScore" -> "Nps Score"
// ---------------------------------------------------------------------------

function columnHeader(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// DatasetDetailLoadingSkeleton
//
// Shown while datasetService.get() is in flight.
// Phase 2D/2E: never shown because the lookup is synchronous, but the
// structure is ready for future API integration.
// ---------------------------------------------------------------------------

function DatasetDetailLoadingSkeleton() {
  return (
    <div className="detail-skeleton" aria-label="Loading dataset details" aria-busy="true" role="status">
      <div className="detail-skeleton-header">
        <div className="skeleton-block" style={{ width: '55%', height: '22px' }} />
        <div className="skeleton-block" style={{ width: '90px', height: '24px' }} />
      </div>
      <div className="detail-skeleton-body">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="detail-skeleton-row">
            <div className="skeleton-block" style={{ width: '18%', height: '13px' }} />
            <div className="skeleton-block" style={{ width: '38%', height: '13px' }} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// DatasetDetailError
//
// Shown when datasetService.get() rejects with an ApiError.
// Phase 2D/2E: never triggered because no API call is made.
// ---------------------------------------------------------------------------

function DatasetDetailError({ message }: { message: string }) {
  return (
    <div className="dataset-error" role="alert">
      <strong>Failed to load dataset details.</strong>{' '}
      {message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DatasetNotFound
//
// Shown when the dataset_id from the route does not match any known dataset.
// ---------------------------------------------------------------------------

function DatasetNotFound({ datasetId }: { datasetId: string }) {
  return (
    <div className="detail-not-found">
      <svg
        className="detail-not-found-icon"
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="12" />
        <line x1="11" y1="16" x2="11.01" y2="16" />
      </svg>
      <h2 className="detail-not-found-title">Dataset not found</h2>
      <p className="detail-not-found-body">
        No dataset with the identifier{' '}
        <code className="detail-not-found-id">{datasetId}</code> could be found.
        It may have been removed or the link may be incorrect.
      </p>
      <Link to="/datasets" className="detail-back-link detail-back-link--prominent">
        Back to Datasets
      </Link>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MetadataRow - a single labelled field in the metadata section
// ---------------------------------------------------------------------------

function MetadataRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="detail-meta-row">
      <dt className="detail-meta-label">{label}</dt>
      <dd className="detail-meta-value">{children}</dd>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PreviewLoadingSkeleton
//
// Shown while datasetService.preview() is in flight.
// Phase 2E: never shown (synchronous lookup), but structure is ready for
// future API integration.
// ---------------------------------------------------------------------------

function PreviewLoadingSkeleton() {
  return (
    <div
      className="preview-skeleton"
      aria-label="Loading data preview"
      aria-busy="true"
      role="status"
    >
      {/* Simulate a table header + 5 data rows */}
      <div className="preview-skeleton-header">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="skeleton-block preview-skeleton-col" />
        ))}
      </div>
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="preview-skeleton-row">
          {Array.from({ length: 4 }, (_, j) => (
            <div key={j} className="skeleton-block preview-skeleton-cell" />
          ))}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PreviewError
//
// Shown when datasetService.preview() rejects with an ApiError.
// Phase 2E: never triggered (no API call is made).
// ---------------------------------------------------------------------------

function PreviewError({ message }: { message: string }) {
  return (
    <div className="dataset-error preview-error" role="alert">
      <strong>Failed to load data preview.</strong>{' '}
      {message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PreviewEmpty
//
// Shown when the dataset exists but has no preview rows available.
// This is distinct from DatasetNotFound — the dataset is valid, but
// preview data is unavailable (e.g. still processing, failed, or empty).
// ---------------------------------------------------------------------------

function PreviewEmpty() {
  return (
    <div className="preview-empty">
      <svg
        className="preview-empty-icon"
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
      <p className="preview-empty-title">No preview available</p>
      <p className="preview-empty-body">
        Preview data is not available for this dataset. This may be because the
        dataset is still processing, failed validation, or has not yet been
        ingested.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PreviewTable
//
// Read-only data table. Renders dynamically from preview.columns and
// preview.rows — no hard-coded columns or rows.
//
// Accepts:
//   preview - the resolved DatasetPreview object
//
// The table is wrapped in a scrollable container so wide datasets do not
// cause page-level horizontal overflow.
// ---------------------------------------------------------------------------

function PreviewTable({ preview }: { preview: DatasetPreview }) {
  const { columns, rows, totalRows } = preview;
  const shownRows = rows.length;

  return (
    <section className="preview-section" aria-label="Data preview">
      {/* Preview header */}
      <div className="preview-header">
        <h3 className="detail-section-title preview-section-title">Data Preview</h3>
        <p className="preview-row-info">
          Showing{' '}
          <strong>{shownRows.toLocaleString()}</strong>
          {' '}of{' '}
          <strong>{totalRows.toLocaleString()}</strong>
          {' '}row{totalRows === 1 ? '' : 's'} — sample only
        </p>
      </div>

      {/* Scrollable table container — horizontal scroll stays inside this box */}
      <div className="preview-table-wrapper" tabIndex={0} aria-label="Dataset preview table, scroll horizontally to see all columns">
        <table className="preview-table" aria-label={`Preview: ${shownRows} of ${totalRows} rows`}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col} scope="col" className="preview-th">
                  {columnHeader(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              // rowIdx is stable for static dev data; future API should provide a stable key
              <tr key={rowIdx} className="preview-tr">
                {columns.map((col) => (
                  <td key={col} className="preview-td" title={formatCellValue(row[col])}>
                    {row[col] === null || row[col] === undefined ? (
                      <span className="preview-null" aria-label="No value">—</span>
                    ) : (
                      formatCellValue(row[col])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer row-count note */}
      <p className="preview-footer-note">
        This preview shows a sample of the dataset. Full data is available
        for analysis once the dataset has been processed.
      </p>
    </section>
  );
}

// ---------------------------------------------------------------------------
// DatasetDetail
//
// Renders confirmed dataset metadata + data preview section.
// Accepts a resolved Dataset object and its preview data.
// Presentation is data-source agnostic.
// ---------------------------------------------------------------------------

function DatasetDetail({
  dataset,
  preview,
  previewLoading,
  previewError,
}: {
  dataset: Dataset;
  preview: DatasetPreview | null;
  previewLoading: boolean;
  previewError: string | null;
}) {
  const ext = getExtension(dataset.filename);

  return (
    <article aria-label={`Dataset details for ${dataset.filename}`}>
      {/* Dataset Header */}
      <div className="detail-header">
        <div className="detail-header-info">
          <h2 className="detail-filename">{dataset.filename}</h2>
          <span className="detail-filetype-badge">{ext}</span>
        </div>
        <div className="detail-header-status">
          <StatusBadge status={dataset.status} />
        </div>
      </div>

      {/* Dataset Metadata */}
      <section aria-label="Dataset metadata">
        <h3 className="detail-section-title">File Information</h3>
        <dl className="detail-meta-list">
          <MetadataRow label="Dataset ID">
            <code className="detail-id-value">{dataset.dataset_id}</code>
          </MetadataRow>
          <MetadataRow label="Filename">
            {dataset.filename}
          </MetadataRow>
          <MetadataRow label="File type">
            {ext}
          </MetadataRow>
          <MetadataRow label="File size">
            {formatFileSize(dataset.size_bytes)}
            <span className="detail-meta-secondary">
              {' '}({dataset.size_bytes.toLocaleString()} bytes)
            </span>
          </MetadataRow>
          <MetadataRow label="Uploaded">
            <time dateTime={dataset.uploaded_at}>
              {formatDateTime(dataset.uploaded_at)}
            </time>
            <span className="detail-meta-secondary">
              {' '}({formatDate(dataset.uploaded_at)})
            </span>
          </MetadataRow>
          <MetadataRow label="Status">
            <StatusBadge status={dataset.status} />
          </MetadataRow>
        </dl>
      </section>

      {/* ----------------------------------------------------------------
          Data Preview — Phase 2E
          Future integration: replace previewLoading/previewError/preview
          state with results from datasetService.preview(datasetId).
          No presentation changes required.
          ---------------------------------------------------------------- */}
      <div className="preview-divider" />

      {previewLoading && <PreviewLoadingSkeleton />}
      {!previewLoading && previewError !== null && <PreviewError message={previewError} />}
      {!previewLoading && previewError === null && (!preview || preview.rows.length === 0) && (
        <PreviewEmpty />
      )}
      {!previewLoading && previewError === null && preview && preview.rows.length > 0 && (
        <PreviewTable preview={preview} />
      )}
    </article>
  );
}

// ---------------------------------------------------------------------------
// DatasetDetailPage - page component for route /datasets/:datasetId
//
// State:
//   isLoading      - always false in Phase 2D/2E (synchronous lookup)
//   error          - always null in Phase 2D/2E (no API call)
//   previewLoading - always false in Phase 2E (synchronous lookup)
//   previewError   - always null in Phase 2E (no API call)
//
// The dataset and its preview are resolved from DEV_DATASETS / DEV_PREVIEWS
// using the route parameter. An unknown dataset_id produces DatasetNotFound.
//
// Future integration (metadata — no presentation changes needed):
//   const [dataset, setDataset] = useState<Dataset | null>(null);
//   const [isLoading, setIsLoading] = useState(true);
//   const [error, setError] = useState<string | null>(null);
//   useEffect(() => {
//     datasetService.get(datasetId)
//       .then(setDataset)
//       .catch((err: ApiError) => setError(err.message))
//       .finally(() => setIsLoading(false));
//   }, [datasetId]);
//
// Future integration (preview — no presentation changes needed):
//   const [preview, setPreview] = useState<DatasetPreview | null>(null);
//   const [previewLoading, setPreviewLoading] = useState(true);
//   const [previewError, setPreviewError] = useState<string | null>(null);
//   useEffect(() => {
//     datasetService.preview(datasetId)
//       .then(setPreview)
//       .catch((err: ApiError) => setPreviewError(err.message))
//       .finally(() => setPreviewLoading(false));
//   }, [datasetId]);
// ---------------------------------------------------------------------------

export default function DatasetDetailPage() {
  const { datasetId } = useParams<{ datasetId: string }>();

  // Phase 2D/2E: synchronous lookup against development data.
  // BACKEND DEPENDENCY: Replace with datasetService.get(datasetId) when live.
  const [isLoading] = useState<boolean>(false);
  const [error] = useState<string | null>(null);

  // Phase 2E: synchronous preview lookup against development data.
  // BACKEND DEPENDENCY: Replace with datasetService.preview(datasetId) when live.
  const [previewLoading] = useState<boolean>(false);
  const [previewError] = useState<string | null>(null);

  // Resolve dataset by ID from the shared development source.
  const dataset: Dataset | undefined = datasetId
    ? DEV_DATASETS.find((ds) => ds.dataset_id === datasetId)
    : undefined;

  // Resolve preview data. Returns undefined if no preview exists for this ID.
  // DEV_PREVIEWS only contains entries for datasets in previewable states.
  const preview: DatasetPreview | null = datasetId
    ? (DEV_PREVIEWS[datasetId] ?? null)
    : null;

  return (
    <div>
      {/* Back navigation */}
      <nav aria-label="Breadcrumb" className="detail-breadcrumb">
        <Link to="/datasets" className="detail-back-link" aria-label="Back to Datasets">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Datasets
        </Link>
      </nav>

      {/* Page Header */}
      <header className="page-header">
        <h1 className="page-title">Dataset Details</h1>
        <p className="page-description">
          View metadata and a data preview for this dataset.
        </p>
      </header>

      {/* Content - conditional on state */}
      {isLoading && <DatasetDetailLoadingSkeleton />}
      {!isLoading && error !== null && <DatasetDetailError message={error} />}
      {!isLoading && error === null && !dataset && datasetId && (
        <DatasetNotFound datasetId={datasetId} />
      )}
      {!isLoading && error === null && dataset && (
        <div className="detail-card">
          <DatasetDetail
            dataset={dataset}
            preview={preview}
            previewLoading={previewLoading}
            previewError={previewError}
          />
        </div>
      )}
    </div>
  );
}
