import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Sparkles, 
  FileText, 
  Database, 
  Calendar, 
  Sliders, 
  CheckSquare, 
  Square, 
  FileSpreadsheet
} from 'lucide-react';
import type { ReportType, ReportSectionConfig } from '../../types/reports';
import { DEFAULT_REPORT_SECTIONS, createReport } from '../../services/reportsService';
import { ReportGenerationProgress, REPORT_GENERATION_STEPS } from '../../components/reports/ReportGenerationProgress';

export default function CreateReportPage() {
  const navigate = useNavigate();

  // Form Configuration State
  const [reportTitle, setReportTitle] = useState('Q3 2026 Executive Sales Performance Report');
  const [selectedDataset, setSelectedDataset] = useState('Global_Superstore_Sales_2026.csv');
  const [startDate, setStartDate] = useState('2026-01-01');
  const [endDate, setEndDate] = useState('2026-09-30');
  const [reportType, setReportType] = useState<ReportType>('business_performance');
  const [sections, setSections] = useState<ReportSectionConfig[]>([...DEFAULT_REPORT_SECTIONS]);
  const [outputFormat, setOutputFormat] = useState<'pdf' | 'excel' | 'csv'>('pdf');

  // Generation / Loading Stepper State
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Toggle individual section
  const handleToggleSection = (secId: string) => {
    setSections((prev) =>
      prev.map((s) => (s.id === secId ? { ...s, enabled: !s.enabled } : s))
    );
  };

  // Toggle all sections
  const handleSelectAllSections = (enableAll: boolean) => {
    setSections((prev) => prev.map((s) => ({ ...s, enabled: enableAll })));
  };

  // Trigger report generation flow
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportTitle.trim()) {
      setValidationError('Please enter a valid report name.');
      return;
    }
    const enabledSections = sections.filter((s) => s.enabled);
    if (enabledSections.length === 0) {
      setValidationError('Please enable at least one section to include in the report.');
      return;
    }

    setValidationError(null);
    setIsGenerating(true);
    setActiveStep(0);

    // Step-by-step progress simulation through all steps
    for (let step = 0; step < REPORT_GENERATION_STEPS.length; step++) {
      setActiveStep(step);
      // Wait for each step
      await new Promise((resolve) => setTimeout(resolve, 360));
    }

    // Call service creation
    try {
      const newReport = await createReport({
        title: reportTitle,
        dataset: selectedDataset,
        dateRange: { start: startDate, end: endDate, label: `${startDate} – ${endDate}` },
        reportType,
        sections,
        outputFormat,
      });

      // Brief completion delay then transition to generated report
      setTimeout(() => {
        navigate(`/reports/${newReport.id}`);
      }, 400);
    } catch (err) {
      console.error('Failed to create report:', err);
      setIsGenerating(false);
      setValidationError('Generation failed. Please retry.');
    }
  };

  if (isGenerating) {
    return (
      <div className="ws-page reports-page-root">
        <ReportGenerationProgress activeStep={activeStep} />
      </div>
    );
  }

  return (
    <div className="ws-page reports-page-root">
      {/* Back to Reports navigation */}
      <div className="reports-top-nav-bar">
        <Link to="/reports" className="reports-back-link">
          <ArrowLeft size={16} />
          <span>Back to Reports</span>
        </Link>
      </div>

      {/* Page Header */}
      <header className="reports-header">
        <div className="reports-header-left">
          <div className="reports-header-badge">
            <Sparkles size={13} />
            <span>Report Wizard</span>
          </div>
          <h1 className="ws-page-heading">Create Report</h1>
          <p className="ws-page-sub">
            Configure and generate a comprehensive executive business report backed by verified data.
          </p>
        </div>
      </header>

      {validationError && (
        <div className="reports-error-banner" role="alert">
          <span>{validationError}</span>
        </div>
      )}

      {/* Main Configuration Form */}
      <form onSubmit={handleGenerate} className="reports-create-form">
        {/* Section 1: Report Details */}
        <div className="reports-create-card">
          <div className="reports-create-card-header">
            <FileText size={18} className="reports-create-icon" />
            <div>
              <h3>1. Report Details</h3>
              <p>Set a descriptive document title and executive subject.</p>
            </div>
          </div>
          <div className="reports-form-field">
            <label htmlFor="report-title">Report Title</label>
            <input
              id="report-title"
              type="text"
              className="reports-input"
              value={reportTitle}
              onChange={(e) => setReportTitle(e.target.value)}
              placeholder="e.g. Q3 2026 Executive Sales Performance Report"
              required
            />
          </div>
        </div>

        {/* Section 2: Dataset Selection */}
        <div className="reports-create-card">
          <div className="reports-create-card-header">
            <Database size={18} className="reports-create-icon" />
            <div>
              <h3>2. Data Source</h3>
              <p>Select the analytical dataset providing empirical records.</p>
            </div>
          </div>
          <div className="reports-form-field">
            <label htmlFor="report-dataset">Verified Dataset</label>
            <select
              id="report-dataset"
              className="reports-select full"
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
            >
              <option value="Global_Superstore_Sales_2026.csv">
                Global_Superstore_Sales_2026.csv (Sales, Orders, Regions)
              </option>
              <option value="Marketing_Spend_2025.csv">
                Marketing_Spend_2025.csv (Ad Channels, CAC, ROAS)
              </option>
              <option value="Customer_Data.csv">
                Customer_Data.csv (Segments, Retention, Churn)
              </option>
            </select>
          </div>
        </div>

        {/* Section 3: Date Range */}
        <div className="reports-create-card">
          <div className="reports-create-card-header">
            <Calendar size={18} className="reports-create-icon" />
            <div>
              <h3>3. Evaluation Date Range</h3>
              <p>Define the chronological observation window.</p>
            </div>
          </div>
          <div className="reports-form-row">
            <div className="reports-form-field">
              <label htmlFor="start-date">Start Date</label>
              <input
                id="start-date"
                type="date"
                className="reports-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="reports-form-field">
              <label htmlFor="end-date">End Date</label>
              <input
                id="end-date"
                type="date"
                className="reports-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Section 4: Report Type */}
        <div className="reports-create-card">
          <div className="reports-create-card-header">
            <Sliders size={18} className="reports-create-icon" />
            <div>
              <h3>4. Report Category</h3>
              <p>Select the domain framing for executive presentation.</p>
            </div>
          </div>
          <div className="reports-form-field">
            <label htmlFor="report-type">Report Type</label>
            <select
              id="report-type"
              className="reports-select full"
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
            >
              <option value="business_performance">Business Performance Overview</option>
              <option value="sales_analysis">Sales & Regional Revenue Analysis</option>
              <option value="customer_analysis">Customer Cohort & Retention Analysis</option>
              <option value="marketing_analysis">Marketing Spend & Channel Efficiency</option>
              <option value="custom">Custom Executive Report</option>
            </select>
          </div>
        </div>

        {/* Section 5: Report Sections Selection */}
        <div className="reports-create-card">
          <div className="reports-create-card-header">
            <CheckSquare size={18} className="reports-create-icon" />
            <div>
              <h3>5. Included Sections</h3>
              <p>Select which narrative sections to compile into the document.</p>
            </div>
          </div>

          <div className="reports-sections-quick-actions">
            <button
              type="button"
              className="reports-text-link"
              onClick={() => handleSelectAllSections(true)}
            >
              Select All
            </button>
            <span>•</span>
            <button
              type="button"
              className="reports-text-link"
              onClick={() => handleSelectAllSections(false)}
            >
              Deselect All
            </button>
          </div>

          <div className="reports-sections-checkbox-grid">
            {sections.map((sec) => (
              <label
                key={sec.id}
                className={`reports-checkbox-card ${sec.enabled ? 'selected' : ''}`}
              >
                <input
                  type="checkbox"
                  className="reports-native-checkbox"
                  checked={sec.enabled}
                  onChange={() => handleToggleSection(sec.id)}
                />
                <span className="reports-custom-box">
                  {sec.enabled ? (
                    <CheckSquare size={18} className="reports-checkbox-checked" />
                  ) : (
                    <Square size={18} className="reports-checkbox-empty" />
                  )}
                </span>
                <div className="reports-checkbox-label-wrap">
                  <span className="reports-sec-title">{sec.title}</span>
                  {sec.description && (
                    <span className="reports-sec-desc">{sec.description}</span>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Section 6: Output Format */}
        <div className="reports-create-card">
          <div className="reports-create-card-header">
            <FileSpreadsheet size={18} className="reports-create-icon" />
            <div>
              <h3>6. Target Output Format</h3>
              <p>Primary document export target.</p>
            </div>
          </div>
          <div className="reports-format-options-row">
            <label className={`reports-format-pill ${outputFormat === 'pdf' ? 'active' : ''}`}>
              <input
                type="radio"
                name="format"
                value="pdf"
                checked={outputFormat === 'pdf'}
                onChange={() => setOutputFormat('pdf')}
              />
              <span>Executive PDF Document</span>
            </label>
            <label className={`reports-format-pill ${outputFormat === 'excel' ? 'active' : ''}`}>
              <input
                type="radio"
                name="format"
                value="excel"
                checked={outputFormat === 'excel'}
                onChange={() => setOutputFormat('excel')}
              />
              <span>Excel Spreadsheet (.xlsx)</span>
            </label>
            <label className={`reports-format-pill ${outputFormat === 'csv' ? 'active' : ''}`}>
              <input
                type="radio"
                name="format"
                value="csv"
                checked={outputFormat === 'csv'}
                onChange={() => setOutputFormat('csv')}
              />
              <span>CSV Data Files</span>
            </label>
          </div>
        </div>

        {/* Submit Actions */}
        <div className="reports-create-footer">
          <Link to="/reports" className="reports-btn-ghost">
            Cancel
          </Link>
          <button type="submit" className="reports-create-btn">
            <Sparkles size={16} />
            <span>Generate Report</span>
          </button>
        </div>
      </form>
    </div>
  );
}
