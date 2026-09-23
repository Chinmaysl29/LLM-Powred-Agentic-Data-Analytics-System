import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Edit3, 
  Download, 
  Share2, 
  Check, 
  ShieldAlert, 
  Loader2
} from 'lucide-react';
import type { ReportSpecification, Report } from '../../types/reports';
import type { Insight } from '../../types/insights';
import { getReportSpecification, getReportById } from '../../services/reportsService';
import { ReportDocumentPreview } from '../../components/reports/ReportDocumentPreview';
import { ExportModal } from '../../components/reports/ExportModal';
import { ReportStatusBadge } from '../../components/reports/ReportStatusBadge';

export default function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();

  const [spec, setSpec] = useState<ReportSpecification | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Export & Share state
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (!reportId) return;

    let ignore = false;
    const fetchDoc = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [repData, specData] = await Promise.all([
          getReportById(reportId),
          getReportSpecification(reportId),
        ]);
        if (!ignore) {
          if (!specData || !repData) {
            setError('Report not found or unavailable.');
          } else {
            setReport(repData);
            setSpec(specData);
          }
          setIsLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          console.error('Failed to load report document:', err);
          setError('Could not retrieve report specification.');
          setIsLoading(false);
        }
      }
    };

    fetchDoc();

    return () => {
      ignore = true;
    };
  }, [reportId]);

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2400);
  };

  const handleOpenVisualization = (insight: Insight) => {
    const ref = insight.visualizationReference;
    if (!ref) return;
    navigate('/visualizations', {
      state: {
        dataset: report?.dataset,
        chartType: ref.chartType,
        xAxis: ref.xAxis,
        yAxis: ref.yAxis,
        highlightTitle: ref.title,
      },
    });
  };

  const handleAskAI = (item: { title: string; summary?: string }) => {
    navigate('/analysis', {
      state: {
        question: `Based on the report "${spec?.title}", analyze the following finding: "${item.title}". Context: ${item.summary || ''}`,
        dataset: report?.dataset,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="ws-page reports-page-root">
        <div className="reports-detail-loader">
          <Loader2 size={32} className="reports-spinner" />
          <p>Loading generated executive report...</p>
        </div>
      </div>
    );
  }

  if (error || !spec || !report) {
    return (
      <div className="ws-page reports-page-root">
        <div className="reports-error-banner" role="alert">
          <ShieldAlert size={20} />
          <div>
            <strong>Report Unavailable:</strong> {error || 'The requested document does not exist.'}
          </div>
          <Link to="/reports" className="reports-btn-secondary">
            Return to Reports
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="ws-page reports-page-root">
      {/* Top Utility Nav Header */}
      <div className="reports-detail-top-bar">
        <div className="reports-detail-top-left">
          <Link to="/reports" className="reports-back-link">
            <ArrowLeft size={16} />
            <span>Reports</span>
          </Link>
          <span className="reports-nav-divider">/</span>
          <span className="reports-nav-current" title={report.title}>{report.title}</span>
          <ReportStatusBadge status={report.status} />
        </div>

        <div className="reports-detail-actions">
          <button
            type="button"
            className="reports-btn-ghost"
            onClick={handleShare}
            title="Copy report share link"
          >
            {copiedLink ? <Check size={14} className="text-green" /> : <Share2 size={14} />}
            <span>{copiedLink ? 'Link Copied' : 'Share'}</span>
          </button>

          <button
            type="button"
            className="reports-btn-secondary"
            onClick={() => setIsExportModalOpen(true)}
            title="Export as PDF, Excel, or CSV"
          >
            <Download size={14} />
            <span>Export</span>
          </button>

          <button
            type="button"
            className="reports-btn-primary"
            onClick={() => navigate(`/reports/${report.id}/edit`)}
            title="Open interactive report builder"
          >
            <Edit3 size={14} />
            <span>Edit in Builder</span>
          </button>
        </div>
      </div>

      {/* Embedded Document Presentation Surface */}
      <main className="reports-document-view-container">
        <ReportDocumentPreview
          spec={spec}
          onOpenVisualization={handleOpenVisualization}
          onAskAI={handleAskAI}
        />
      </main>

      {/* Export Dialog */}
      <ExportModal
        isOpen={isExportModalOpen}
        report={report}
        onClose={() => setIsExportModalOpen(false)}
      />
    </div>
  );
}
