/**
 * reportsService.ts
 *
 * Centralized service boundary and development data for Phase 7: Reports.
 * Provides report management, section updating, specification retrieval,
 * and export triggers.
 *
 * FUTURE BACKEND INTEGRATION POINTS:
 *   GET    /api/reports                 -> getReports(filters)
 *   GET    /api/reports/:id             -> getReportById(reportId)
 *   GET    /api/reports/:id/spec        -> getReportSpecification(reportId)
 *   POST   /api/reports                 -> createReport(params)
 *   PUT    /api/reports/:id/sections    -> updateReportSections(reportId, sections)
 *   POST   /api/reports/:id/duplicate   -> duplicateReport(reportId)
 *   POST   /api/reports/:id/archive     -> archiveReport(reportId)
 *   DELETE /api/reports/:id             -> deleteReport(reportId)
 *   POST   /api/reports/:id/export      -> exportReport(reportId, format)
 */

import type {
  Report,
  ReportSpecification,
  ReportSectionConfig,
  ReportFilters,
  CreateReportParams,
  ReportVisualizationItem,
} from '../types/reports';

import {
  getBusinessHealth,
  getInsights,
  getRisks,
  getOpportunities,
  getRecommendations,
  calculateScenarioProjection,
} from './insightsService';

// ---------------------------------------------------------------------------
// Default Sections Template
// ---------------------------------------------------------------------------

export const DEFAULT_REPORT_SECTIONS: ReportSectionConfig[] = [
  {
    id: 'sec-cover',
    type: 'cover',
    title: 'Cover Page',
    description: 'Executive document title, metadata, and data provenance.',
    enabled: true,
    order: 1,
  },
  {
    id: 'sec-summary',
    type: 'summary',
    title: 'Executive Summary',
    description: 'High-level narrative synthesis of key analytical findings.',
    enabled: true,
    order: 2,
  },
  {
    id: 'sec-kpis',
    type: 'kpis',
    title: 'Business Health KPIs',
    description: 'Core quantitative performance metrics and growth deltas.',
    enabled: true,
    order: 3,
  },
  {
    id: 'sec-viz',
    type: 'visualizations',
    title: 'Visualizations',
    description: 'High-signal revenue trends and regional distribution charts.',
    enabled: true,
    order: 4,
  },
  {
    id: 'sec-insights',
    type: 'insights',
    title: 'Key Insights',
    description: 'Observed evidence paired with derived model interpretations.',
    enabled: true,
    order: 5,
  },
  {
    id: 'sec-risks',
    type: 'risks',
    title: 'Detected Risks',
    description: 'Structural vulnerabilities and contributing risk factors.',
    enabled: true,
    order: 6,
  },
  {
    id: 'sec-opps',
    type: 'opportunities',
    title: 'Strategic Opportunities',
    description: 'High-leverage expansion vectors and addressable markets.',
    enabled: true,
    order: 7,
  },
  {
    id: 'sec-recs',
    type: 'recommendations',
    title: 'Action Recommendations',
    description: 'Evidence-backed strategic next steps and assumptions.',
    enabled: true,
    order: 8,
  },
  {
    id: 'sec-what-if',
    type: 'what_if',
    title: 'What-If Scenario Simulation',
    description: 'Forward-looking price and marketing elasticity simulation.',
    enabled: true,
    order: 9,
  },
];

// ---------------------------------------------------------------------------
// Sample Visualization Datasets for Reports
// ---------------------------------------------------------------------------

const REVENUE_TREND_DATA: ReportVisualizationItem = {
  id: 'viz-rev-trend',
  title: 'Quarterly Revenue & Order Trajectory',
  chartType: 'Line',
  description: '12-month revenue curve indicating steady acceleration through Q3 with seasonal stabilization.',
  xAxisLabel: 'Month',
  yAxisLabel: 'Revenue ($)',
  dataPoints: [
    { label: 'Jan', value: 164000 },
    { label: 'Feb', value: 178000 },
    { label: 'Mar', value: 195000 },
    { label: 'Apr', value: 188000 },
    { label: 'May', value: 212000 },
    { label: 'Jun', value: 234000 },
    { label: 'Jul', value: 228000 },
    { label: 'Aug', value: 254000 },
    { label: 'Sep', value: 268000 },
  ],
};

const REGIONAL_PERFORMANCE_DATA: ReportVisualizationItem = {
  id: 'viz-reg-bar',
  title: 'Revenue Distribution by Geographic Region',
  chartType: 'Bar',
  description: 'North America leads total volume at $1.18M, while European growth accelerates by +22.4% year-over-year.',
  xAxisLabel: 'Region',
  yAxisLabel: 'Revenue ($)',
  dataPoints: [
    { label: 'North America', value: 1180000 },
    { label: 'Europe', value: 680000 },
    { label: 'Asia Pacific', value: 430000 },
    { label: 'Latin America', value: 190000 },
  ],
};

// ---------------------------------------------------------------------------
// Initial In-Memory Reports Collection
// ---------------------------------------------------------------------------

let REPORTS_STORE: Report[] = [
  {
    id: 'rep-1',
    title: 'Q3 2026 Executive Sales Performance Report',
    description: 'Comprehensive evaluation of global sales revenue, regional distribution, and key driver insights.',
    dataset: 'Global_Superstore_Sales_2026.csv',
    dateRange: { start: '2026-01-01', end: '2026-09-30', label: 'Jan 2026 – Sep 2026' },
    reportType: 'business_performance',
    status: 'generated',
    sections: [...DEFAULT_REPORT_SECTIONS],
    outputFormat: 'pdf',
    createdAt: '2026-09-21T14:30:00Z',
    updatedAt: '2026-09-23T18:45:00Z',
    generatedAt: '2026-09-23T18:45:00Z',
    author: 'AI Data Analyst',
  },
  {
    id: 'rep-2',
    title: 'Global Regional Expansion & Opportunity Analysis',
    description: 'Detailed analysis of European and APAC account expansion potential with margin simulations.',
    dataset: 'Global_Superstore_Sales_2026.csv',
    dateRange: { start: '2026-06-01', end: '2026-09-23', label: 'Last 90 Days' },
    reportType: 'sales_analysis',
    status: 'generated',
    sections: DEFAULT_REPORT_SECTIONS.filter((s) => s.id !== 'sec-what-if'),
    outputFormat: 'pdf',
    createdAt: '2026-09-18T10:15:00Z',
    updatedAt: '2026-09-22T11:20:00Z',
    generatedAt: '2026-09-22T11:20:00Z',
    author: 'AI Data Analyst',
  },
  {
    id: 'rep-3',
    title: 'Marketing Campaign ROI & Acquisition Efficiency Report',
    description: 'Evaluation of paid search, social, and display channel CAC response curves.',
    dataset: 'Marketing_Spend_2025.csv',
    dateRange: { start: '2025-04-01', end: '2025-06-30', label: 'Q2 2025' },
    reportType: 'marketing_analysis',
    status: 'draft',
    sections: [...DEFAULT_REPORT_SECTIONS],
    outputFormat: 'excel',
    createdAt: '2026-09-22T16:00:00Z',
    updatedAt: '2026-09-22T16:00:00Z',
    author: 'AI Data Analyst',
  },
  {
    id: 'rep-4',
    title: 'Enterprise Customer Churn Risk & Retention Brief',
    description: 'Vulnerability assessment identifying high-risk customer segments and retention recommendations.',
    dataset: 'Customer_Data.csv',
    dateRange: { start: '2026-01-01', end: '2026-09-20', label: 'YTD 2026' },
    reportType: 'customer_analysis',
    status: 'generated',
    sections: DEFAULT_REPORT_SECTIONS.filter((s) => s.id !== 'sec-viz'),
    outputFormat: 'pdf',
    createdAt: '2026-09-15T09:30:00Z',
    updatedAt: '2026-09-20T14:10:00Z',
    generatedAt: '2026-09-20T14:10:00Z',
    author: 'AI Data Analyst',
  },
];

// ---------------------------------------------------------------------------
// Service Methods
// ---------------------------------------------------------------------------

export async function getReports(filters?: ReportFilters): Promise<Report[]> {
  await new Promise((r) => setTimeout(r, 60));
  let result = [...REPORTS_STORE];

  if (filters?.searchQuery) {
    const q = filters.searchQuery.toLowerCase().trim();
    result = result.filter(
      (r) =>
        r.title.toLowerCase().includes(q) ||
        r.dataset.toLowerCase().includes(q) ||
        (r.description && r.description.toLowerCase().includes(q))
    );
  }

  if (filters?.dataset && filters.dataset !== 'all') {
    result = result.filter((r) => r.dataset === filters.dataset);
  }

  if (filters?.reportType && filters.reportType !== 'all') {
    result = result.filter((r) => r.reportType === filters.reportType);
  }

  if (filters?.status && filters.status !== 'all') {
    result = result.filter((r) => r.status === filters.status);
  }

  return result;
}

export async function getReportById(reportId: string): Promise<Report | null> {
  await new Promise((r) => setTimeout(r, 40));
  const found = REPORTS_STORE.find((r) => r.id === reportId);
  return found ? { ...found } : null;
}

export async function getReportSpecification(reportId: string): Promise<ReportSpecification | null> {
  const report = await getReportById(reportId);
  if (!report) return null;

  const datasetId = report.dataset.toLowerCase().includes('marketing') ? 'marketing' : 'sales';

  const [kpis, insights, risks, opportunities, recommendations] = await Promise.all([
    getBusinessHealth(datasetId),
    getInsights(datasetId),
    getRisks(datasetId),
    getOpportunities(datasetId),
    getRecommendations(datasetId),
  ]);

  const defaultScenarioInputs = {
    marketingSpendDelta: 15,
    priceDelta: 5,
    churnDelta: -5,
  };

  const scenarioProjection = calculateScenarioProjection(datasetId, defaultScenarioInputs);

  const spec: ReportSpecification = {
    reportId: report.id,
    title: report.title,
    dataset: report.dataset,
    dateRange: report.dateRange,
    reportType: report.reportType,
    generatedAt: report.generatedAt || new Date().toISOString(),
    author: report.author || 'AI Data Analyst',
    sections: report.sections,
    cover: {
      title: report.title,
      subtitle: report.description || 'Executive Business Intelligence & Decision Analysis Document',
      organization: 'Enterprise Analytics Group',
      datasetName: report.dataset,
      periodLabel: report.dateRange.label || `${report.dateRange.start} – ${report.dateRange.end}`,
      generatedDate: new Date(report.generatedAt || Date.now()).toLocaleDateString('en-US', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      }),
      confidentialityNotice: 'Confidential & Proprietary — For Internal Executive Review Only',
    },
    summary: {
      narrative:
        'During the evaluated operational window, global revenue expanded across core enterprise segments, driven primarily by strong performance in technology hardware and accelerated order volume across North America. Although overall customer acquisition exhibited positive momentum, margin compression was detected in discount-heavy small business cohorts, presenting an immediate optimization opportunity.',
      keyHighlights: [
        'Total revenue reached $2.48M, representing an 18.4% acceleration over baseline periods.',
        'North American accounts delivered 52% of total net sales with high customer retention.',
        'Promotional discount rates exceeding 12% in Small Business exhibited poor unit volume elasticity.',
        'High-probability growth vectors identified in European accessory attachment bundling (+$160K upside).',
      ],
    },
    kpis,
    visualizations: [REVENUE_TREND_DATA, REGIONAL_PERFORMANCE_DATA],
    insights,
    risks,
    opportunities,
    recommendations,
    scenario: {
      scenarioName: 'Balanced Growth & Margin Expansion Scenario',
      narrative:
        'Simulated forward-looking impact of increasing marketing spend by 15% paired with a 5% price adjustment and 5% churn reduction across enterprise tiers.',
      inputs: defaultScenarioInputs,
      projection: scenarioProjection,
    },
  };

  return spec;
}

export async function createReport(params: CreateReportParams): Promise<Report> {
  await new Promise((r) => setTimeout(r, 120));

  const newReport: Report = {
    id: `rep-${Date.now()}`,
    title: params.title.trim() || 'Untitled Business Report',
    description: `Automated ${params.reportType.replace('_', ' ')} generated from ${params.dataset}.`,
    dataset: params.dataset,
    dateRange: params.dateRange,
    reportType: params.reportType,
    status: 'generated',
    sections: params.sections && params.sections.length > 0 ? params.sections : [...DEFAULT_REPORT_SECTIONS],
    outputFormat: params.outputFormat || 'pdf',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    generatedAt: new Date().toISOString(),
    author: 'AI Data Analyst',
  };

  REPORTS_STORE = [newReport, ...REPORTS_STORE];
  return { ...newReport };
}

export async function updateReportSections(
  reportId: string,
  sections: ReportSectionConfig[]
): Promise<Report> {
  await new Promise((r) => setTimeout(r, 60));
  const idx = REPORTS_STORE.findIndex((r) => r.id === reportId);
  if (idx === -1) {
    throw new Error(`Report with id ${reportId} not found.`);
  }

  const updated: Report = {
    ...REPORTS_STORE[idx],
    sections,
    updatedAt: new Date().toISOString(),
  };

  REPORTS_STORE[idx] = updated;
  return { ...updated };
}

export async function duplicateReport(reportId: string): Promise<Report> {
  const original = await getReportById(reportId);
  if (!original) throw new Error('Report not found');

  const duplicated: Report = {
    ...original,
    id: `rep-${Date.now()}`,
    title: `${original.title} (Copy)`,
    status: 'draft',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    generatedAt: undefined,
  };

  REPORTS_STORE = [duplicated, ...REPORTS_STORE];
  return { ...duplicated };
}

export async function archiveReport(reportId: string): Promise<boolean> {
  await new Promise((r) => setTimeout(r, 50));
  const idx = REPORTS_STORE.findIndex((r) => r.id === reportId);
  if (idx === -1) return false;

  REPORTS_STORE[idx] = {
    ...REPORTS_STORE[idx],
    status: 'archived',
    updatedAt: new Date().toISOString(),
  };
  return true;
}

export async function deleteReport(reportId: string): Promise<boolean> {
  await new Promise((r) => setTimeout(r, 50));
  const initialLen = REPORTS_STORE.length;
  REPORTS_STORE = REPORTS_STORE.filter((r) => r.id !== reportId);
  return REPORTS_STORE.length < initialLen;
}

export async function exportReport(
  reportId: string,
  format: 'pdf' | 'excel' | 'csv'
): Promise<{ success: boolean; filename: string }> {
  await new Promise((r) => setTimeout(r, 300));
  const report = await getReportById(reportId);
  const baseName = report ? report.title.toLowerCase().replace(/[^a-z0-9]/g, '_') : 'report';
  const filename = `${baseName}_export.${format === 'excel' ? 'xlsx' : format}`;
  return { success: true, filename };
}
