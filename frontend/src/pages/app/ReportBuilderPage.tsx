import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Save, 
  ExternalLink, 
  Download, 
  ShieldAlert, 
  Loader2,
  CheckCircle2
} from 'lucide-react';
import type { ReportSpecification, Report, ReportSectionConfig } from '../../types/reports';
import { 
  getReportById, 
  getReportSpecification, 
  updateReportSections 
} from '../../services/reportsService';
import { ReportStructurePanel } from '../../components/reports/ReportStructurePanel';
import { ReportDocumentPreview } from '../../components/reports/ReportDocumentPreview';
import { ExportModal } from '../../components/reports/ExportModal';

export default function ReportBuilderPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<Report | null>(null);
  const [spec, setSpec] = useState<ReportSpecification | null>(null);
  const [sections, setSections] = useState<ReportSectionConfig[]>([]);
  const [activeSectionId, setActiveSectionId] = useState<string>('sec-cover');

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);

  useEffect(() => {
    if (!reportId) return;

    let ignore = false;
    const loadBuilderData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [repData, specData] = await Promise.all([
          getReportById(reportId),
          getReportSpecification(reportId),
        ]);
        if (!ignore) {
          if (!repData || !specData) {
            setError('Report not found for editing.');
          } else {
            setReport(repData);
            setSpec(specData);
            setSections(repData.sections);
          }
          setIsLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          console.error('Failed to load builder data:', err);
          setError('Could not retrieve builder configuration.');
          setIsLoading(false);
        }
      }
    };

    loadBuilderData();

    return () => {
      ignore = true;
    };
  }, [reportId]);

  // Section toggle handler
  const handleToggleSection = (secId: string) => {
    setSections((prev) =>
      prev.map((s) => (s.id === secId ? { ...s, enabled: !s.enabled } : s))
    );
  };

  // Section selection & scroll handler
  const handleSelectSection = (secId: string) => {
    setActiveSectionId(secId);
    const element = document.getElementById(secId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Move up
  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    setSections((prev) => {
      const copy = [...prev];
      const temp = copy[index - 1];
      copy[index - 1] = copy[index];
      copy[index] = temp;
      return copy.map((s, i) => ({ ...s, order: i + 1 }));
    });
  };

  // Move down
  const handleMoveDown = (index: number) => {
    if (index === sections.length - 1) return;
    setSections((prev) => {
      const copy = [...prev];
      const temp = copy[index + 1];
      copy[index + 1] = copy[index];
      copy[index] = temp;
      return copy.map((s, i) => ({ ...s, order: i + 1 }));
    });
  };

  // Save changes
  const handleSave = async () => {
    if (!reportId) return;
    setIsSaving(true);
    try {
      const updated = await updateReportSections(reportId, sections);
      setReport(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2400);
    } catch (err) {
      console.error('Failed to save report sections:', err);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="ws-page reports-page-root">
        <div className="reports-detail-loader">
          <Loader2 size={32} className="reports-spinner" />
          <p>Initializing interactive Report Builder...</p>
        </div>
      </div>
    );
  }

  if (error || !report || !spec) {
    return (
      <div className="ws-page reports-page-root">
        <div className="reports-error-banner" role="alert">
          <ShieldAlert size={20} />
          <div>
            <strong>Builder Error:</strong> {error || 'Report not found.'}
          </div>
          <Link to="/reports" className="reports-btn-secondary">
            Return to Reports
          </Link>
        </div>
      </div>
    );
  }

  // Synchronized specification with current user section configs
  const liveSpec: ReportSpecification = {
    ...spec,
    sections,
  };

  return (
    <div className="ws-page reports-page-root report-builder-root">
      {/* Top Utility Nav Header */}
      <header className="reports-builder-header">
        <div className="reports-builder-header-left">
          <Link to={`/reports/${report.id}`} className="reports-back-link">
            <ArrowLeft size={16} />
            <span>View Report</span>
          </Link>
          <span className="reports-nav-divider">/</span>
          <span className="reports-nav-current">Builder: {report.title}</span>
        </div>

        <div className="reports-builder-header-actions">
          {saveSuccess && (
            <span className="reports-save-toast">
              <CheckCircle2 size={13} className="text-green" />
              <span>Changes Saved</span>
            </span>
          )}

          <button
            type="button"
            className="reports-btn-ghost"
            onClick={() => setIsExportModalOpen(true)}
            title="Export Report"
          >
            <Download size={14} />
            <span>Export</span>
          </button>

          <button
            type="button"
            className="reports-btn-secondary"
            onClick={() => navigate(`/reports/${report.id}`)}
            title="Preview generated document"
          >
            <ExternalLink size={14} />
            <span>Preview Document</span>
          </button>

          <button
            type="button"
            className="reports-btn-primary"
            onClick={handleSave}
            disabled={isSaving}
          >
            <Save size={14} />
            <span>{isSaving ? 'Saving...' : 'Save Structure'}</span>
          </button>
        </div>
      </header>

      {/* Main Split Layout: Left = Structure Panel, Right = Live Preview Canvas */}
      <div className="reports-builder-workspace">
        {/* Left Structure Column */}
        <aside className="reports-builder-sidebar">
          <ReportStructurePanel
            sections={sections}
            activeSectionId={activeSectionId}
            onSelectSection={handleSelectSection}
            onToggleSection={handleToggleSection}
            onMoveUp={handleMoveUp}
            onMoveDown={handleMoveDown}
          />
        </aside>

        {/* Right Live Document Preview Column */}
        <main className="reports-builder-preview-col">
          <div className="reports-builder-preview-canvas">
            <ReportDocumentPreview
              spec={liveSpec}
              highlightSectionId={activeSectionId}
            />
          </div>
        </main>
      </div>

      {/* Export Modal */}
      <ExportModal
        isOpen={isExportModalOpen}
        report={report}
        onClose={() => setIsExportModalOpen(false)}
      />
    </div>
  );
}
