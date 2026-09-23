import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, 
  Plus, 
  Search, 
  RotateCw, 
  ShieldAlert, 
  Layers, 
  CheckCircle2, 
  Clock, 
  Archive,
  X
} from 'lucide-react';
import type { Report, ReportType, ReportStatus } from '../../types/reports';
import { 
  getReports, 
  duplicateReport, 
  archiveReport, 
  deleteReport 
} from '../../services/reportsService';
import { ReportCard } from '../../components/reports/ReportCard';
import { ExportModal } from '../../components/reports/ExportModal';

export default function ReportsPage() {
  const navigate = useNavigate();

  // Filters state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('all');
  const [selectedType, setSelectedType] = useState<ReportType | 'all'>('all');
  const [selectedStatus, setSelectedStatus] = useState<ReportStatus | 'all'>('all');
  const [dateFilter, setDateFilter] = useState('all');

  // Data state
  const [reports, setReports] = useState<Report[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Export modal state
  const [exportModalReport, setExportModalReport] = useState<Report | null>(null);

  // Load reports
  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getReports({
        searchQuery,
        dataset: selectedDataset,
        reportType: selectedType,
        status: selectedStatus,
        dateFilter,
      });
      setReports(data);
    } catch (err) {
      console.error('Failed to load reports:', err);
      setError('Unable to load reports. Please verify your connection or try again.');
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, selectedDataset, selectedType, selectedStatus, dateFilter]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Actions
  const handleOpenReport = (reportId: string) => {
    navigate(`/reports/${reportId}`);
  };

  const handleEditReport = (reportId: string) => {
    navigate(`/reports/${reportId}/edit`);
  };

  const handleExportReport = (report: Report) => {
    setExportModalReport(report);
  };

  const handleDuplicateReport = async (reportId: string) => {
    try {
      await duplicateReport(reportId);
      await fetchReports();
    } catch (err) {
      console.error('Failed to duplicate report:', err);
    }
  };

  const handleArchiveReport = async (reportId: string) => {
    try {
      await archiveReport(reportId);
      await fetchReports();
    } catch (err) {
      console.error('Failed to archive report:', err);
    }
  };

  const handleDeleteReport = async (reportId: string) => {
    try {
      await deleteReport(reportId);
      await fetchReports();
    } catch (err) {
      console.error('Failed to delete report:', err);
    }
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedDataset('all');
    setSelectedType('all');
    setSelectedStatus('all');
    setDateFilter('all');
  };

  const hasActiveFilters = Boolean(
    searchQuery ||
    selectedDataset !== 'all' ||
    selectedType !== 'all' ||
    selectedStatus !== 'all' ||
    dateFilter !== 'all'
  );

  // Compute stats
  const stats = useMemo(() => {
    return {
      total: reports.length,
      generated: reports.filter((r) => r.status === 'generated').length,
      draft: reports.filter((r) => r.status === 'draft').length,
      archived: reports.filter((r) => r.status === 'archived').length,
    };
  }, [reports]);

  return (
    <div className="ws-page reports-page-root">
      {/* 1. Header with Title & [+ Create Report] */}
      <header className="reports-header">
        <div className="reports-header-left">
          <div className="reports-header-badge">
            <FileText size={13} />
            <span>Document Management</span>
          </div>
          <h1 className="ws-page-heading">Reports</h1>
          <p className="ws-page-sub">
            Create, manage and export AI-powered executive business reports.
          </p>
        </div>

        <div className="reports-header-right">
          <button
            type="button"
            className="reports-create-btn"
            onClick={() => navigate('/reports/create')}
          >
            <Plus size={16} />
            <span>Create Report</span>
          </button>
        </div>
      </header>

      {/* 2. Summary Statistics Strip */}
      <div className="reports-stats-strip">
        <div className="reports-stat-card">
          <div className="reports-stat-label">Total Reports</div>
          <div className="reports-stat-value">
            <Layers size={16} className="reports-stat-icon" />
            <span>{stats.total}</span>
          </div>
        </div>

        <div className="reports-stat-card">
          <div className="reports-stat-label">Generated & Ready</div>
          <div className="reports-stat-value text-green">
            <CheckCircle2 size={16} className="reports-stat-icon text-green" />
            <span>{stats.generated}</span>
          </div>
        </div>

        <div className="reports-stat-card">
          <div className="reports-stat-label">Draft Workspaces</div>
          <div className="reports-stat-value text-blue">
            <Clock size={16} className="reports-stat-icon text-blue" />
            <span>{stats.draft}</span>
          </div>
        </div>

        <div className="reports-stat-card">
          <div className="reports-stat-label">Archived</div>
          <div className="reports-stat-value text-muted">
            <Archive size={16} className="reports-stat-icon text-muted" />
            <span>{stats.archived}</span>
          </div>
        </div>
      </div>

      {/* 3. Search Bar & Filter Controls Strip */}
      <div className="reports-filter-bar">
        {/* Search Input */}
        <div className="reports-search-box">
          <Search size={15} className="reports-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="reports-search-input"
            placeholder="Search reports by title or dataset..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search reports"
          />
          {searchQuery && (
            <button
              type="button"
              className="reports-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search query"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Dropdown Filters */}
        <div className="reports-filter-dropdowns">
          {/* Dataset Filter */}
          <div className="reports-select-wrap">
            <select
              aria-label="Filter by Dataset"
              className="reports-select"
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
            >
              <option value="all">All Datasets</option>
              <option value="Global_Superstore_Sales_2026.csv">Global Superstore Sales</option>
              <option value="Marketing_Spend_2025.csv">Marketing Campaign Spend</option>
              <option value="Customer_Data.csv">Customer Retention Dataset</option>
            </select>
          </div>

          {/* Report Type Filter */}
          <div className="reports-select-wrap">
            <select
              aria-label="Filter by Report Type"
              className="reports-select"
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as ReportType | 'all')}
            >
              <option value="all">All Report Types</option>
              <option value="business_performance">Business Performance</option>
              <option value="sales_analysis">Sales Analysis</option>
              <option value="customer_analysis">Customer Analysis</option>
              <option value="marketing_analysis">Marketing Analysis</option>
              <option value="custom">Custom Report</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="reports-select-wrap">
            <select
              aria-label="Filter by Status"
              className="reports-select"
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as ReportStatus | 'all')}
            >
              <option value="all">All Statuses</option>
              <option value="generated">Generated</option>
              <option value="draft">Draft</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          {/* Clear Filters CTA */}
          {hasActiveFilters && (
            <button
              type="button"
              className="reports-clear-filters-btn"
              onClick={handleClearFilters}
              title="Reset all search and filter fields"
            >
              <RotateCw size={12} />
              <span>Clear filters</span>
            </button>
          )}
        </div>
      </div>

      {/* 4. Error State */}
      {error && (
        <div className="reports-error-banner" role="alert">
          <ShieldAlert size={18} />
          <div>
            <strong>Unable to load reports:</strong> {error}
          </div>
          <button type="button" onClick={fetchReports} className="reports-btn-retry">
            Try Again
          </button>
        </div>
      )}

      {/* 5. Loading Skeleton */}
      {isLoading && (
        <div className="reports-loading-grid" aria-busy="true">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="reports-skeleton-card" />
          ))}
        </div>
      )}

      {/* 6. Recent Reports Grid */}
      {!isLoading && !error && (
        <section className="reports-list-section">
          <div className="reports-section-header-row">
            <h2 className="reports-section-title">
              Recent Reports {reports.length > 0 && `(${reports.length})`}
            </h2>
            <button
              type="button"
              className="reports-refresh-icon-btn"
              onClick={fetchReports}
              title="Refresh reports library"
            >
              <RotateCw size={13} />
            </button>
          </div>

          {reports.length === 0 ? (
            <div className="reports-empty-state">
              <div className="reports-empty-icon-wrap" aria-hidden="true">
                <FileText size={32} />
              </div>
              <h3>No reports found</h3>
              <p>
                {hasActiveFilters
                  ? 'No reports matched your current filter criteria. Try clearing filters or search terms.'
                  : 'Create your first AI-powered business report from your datasets and analysis.'}
              </p>
              {hasActiveFilters ? (
                <button
                  type="button"
                  className="reports-btn-secondary"
                  onClick={handleClearFilters}
                >
                  Clear all filters
                </button>
              ) : (
                <button
                  type="button"
                  className="reports-create-btn"
                  onClick={() => navigate('/reports/create')}
                >
                  <Plus size={16} />
                  <span>Create Report</span>
                </button>
              )}
            </div>
          ) : (
            <div className="reports-grid">
              {reports.map((report) => (
                <ReportCard
                  key={report.id}
                  report={report}
                  onOpen={handleOpenReport}
                  onEdit={handleEditReport}
                  onExport={handleExportReport}
                  onDuplicate={handleDuplicateReport}
                  onArchive={handleArchiveReport}
                  onDelete={handleDeleteReport}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {/* Export Modal */}
      <ExportModal
        isOpen={Boolean(exportModalReport)}
        report={exportModalReport}
        onClose={() => setExportModalReport(null)}
      />
    </div>
  );
}
