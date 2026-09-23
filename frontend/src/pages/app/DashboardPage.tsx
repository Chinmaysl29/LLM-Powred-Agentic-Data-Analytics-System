/**
 * DashboardPage — AI Data Analyst launchpad.
 *
 * Sections (in order):
 *   1. Hero / Ask AI composer
 *   2. Quick Actions
 *   3. Recent Datasets      | Recent Analyses
 *   4. Key Insights         | Visualizations
 *   5. Recommendations      | Reports
 *
 * DATA NOTE:
 * All data in this file is development-only presentation data.
 * It is clearly isolated from future backend contracts.
 * Reuses DEV_DATASETS from datasetUtils.ts — no duplicate data model.
 *
 * BACKEND INTEGRATION POINTS:
 *   Dashboard summary service      - replaces DEV_ANALYSES, DEV_INSIGHTS,
 *                                    DEV_RECOMMENDATIONS, DEV_REPORTS
 *   Dataset service                - replaces DEV_DATASETS slice
 *   Analysis request service       - replaces the composer navigation handoff
 */

import { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Send,
  Database,
  MessageSquare,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Users,
  ShoppingCart,
  Lightbulb,
  FileText,
  ArrowUpRight,
} from 'lucide-react';

import { DEV_DATASETS } from '../../datasetUtils';
import type { Dataset } from '../../types/datasets';

// ---------------------------------------------------------------------------
// Development data — isolated from future API contracts
// ---------------------------------------------------------------------------

/** Confirmed dataset shape reused from Phase 2. */
const RECENT_DATASETS: Dataset[] = DEV_DATASETS.slice(0, 3);

interface DevAnalysis {
  id: string;
  question: string;
  timestamp: string;
  status: 'complete' | 'pending';
}

/**
 * DEV-ONLY: Represents past analytical questions.
 * Will be replaced by the analysis history service.
 */
const DEV_ANALYSES: DevAnalysis[] = [
  { id: 'a1', question: 'Which products generated the highest revenue last quarter?', timestamp: '2 hours ago', status: 'complete' },
  { id: 'a2', question: 'Why did customer churn increase in Q2?', timestamp: '1 day ago', status: 'complete' },
  { id: 'a3', question: 'Which customer segment is growing fastest?', timestamp: '3 days ago', status: 'complete' },
];

interface DevInsight {
  id: string;
  label: string;
  metric: string;
  text: string;
  severity: 'high' | 'medium' | 'low';
  icon: React.ReactNode;
}

/**
 * DEV-ONLY: Key business findings.
 * Will be replaced by the insights service.
 */
const DEV_INSIGHTS: DevInsight[] = [
  {
    id: 'i1',
    label: 'Revenue Growth',
    metric: '+18%',
    text: 'Revenue increased 18% this quarter vs previous quarter.',
    severity: 'low',
    icon: <TrendingUp size={14} />,
  },
  {
    id: 'i2',
    label: 'Customer Churn',
    metric: '14.2%',
    text: 'Churn is highest among the 18–25 age segment.',
    severity: 'high',
    icon: <TrendingDown size={14} />,
  },
  {
    id: 'i3',
    label: 'Top Product Share',
    metric: '38%',
    text: 'Product A contributes the largest share of total revenue.',
    severity: 'low',
    icon: <ShoppingCart size={14} />,
  },
  {
    id: 'i4',
    label: 'Active Customers',
    metric: '12,841',
    text: 'Monthly active customers up 9% compared to last month.',
    severity: 'medium',
    icon: <Users size={14} />,
  },
];

interface DevVis {
  id: string;
  title: string;
  desc: string;
  chart: React.ReactNode;
}

/**
 * DEV-ONLY: Visualization previews.
 * Architecture: Analysis Result → Visualization Specification → Renderer
 * Will be replaced by the visualizations service.
 */
const DEV_VISUALIZATIONS: DevVis[] = [
  {
    id: 'v1',
    title: 'Revenue Trend',
    desc: 'Monthly revenue over the last 12 months.',
    chart: (
      <svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg" aria-label="Revenue trend sparkline">
        <defs>
          <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.15)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>
        <path d="M0 70 L20 60 L40 55 L60 48 L80 42 L100 35 L120 30 L140 25 L160 20 L180 14 L200 8" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M0 70 L20 60 L40 55 L60 48 L80 42 L100 35 L120 30 L140 25 L160 20 L180 14 L200 8 L200 80 L0 80 Z" fill="url(#grad1)" />
      </svg>
    ),
  },
  {
    id: 'v2',
    title: 'Product Performance',
    desc: 'Sales by product category.',
    chart: (
      <svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg" aria-label="Product performance bars">
        {[
          { x: 20, h: 55 }, { x: 50, h: 40 }, { x: 80, h: 65 },
          { x: 110, h: 30 }, { x: 140, h: 48 }, { x: 170, h: 58 },
        ].map(({ x, h }, i) => (
          <rect
            key={i}
            x={x}
            y={80 - h}
            width={20}
            height={h}
            rx={3}
            fill={i === 2 ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.15)'}
          />
        ))}
      </svg>
    ),
  },
  {
    id: 'v3',
    title: 'Customer Distribution',
    desc: 'Customers by age segment.',
    chart: (
      <svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg" aria-label="Customer distribution pie">
        <circle cx="100" cy="40" r="32" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="16" />
        <circle cx="100" cy="40" r="32" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="16"
          strokeDasharray="80 121" strokeDashoffset="40" strokeLinecap="round" />
        <circle cx="100" cy="40" r="32" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="16"
          strokeDasharray="40 161" strokeDashoffset="-40" strokeLinecap="round" />
        <text x="100" y="45" textAnchor="middle" fill="rgba(255,255,255,0.6)" fontSize="11" fontWeight="600">40%</text>
      </svg>
    ),
  },
];

interface DevRec {
  id: string;
  action: string;
  reason: string;
  impact: string;
  priority: 'high' | 'medium' | 'low';
}

/**
 * DEV-ONLY: Decision intelligence recommendations.
 * Will be replaced by the recommendations service.
 */
const DEV_RECOMMENDATIONS: DevRec[] = [
  {
    id: 'r1',
    action: 'Increase investment in Product A',
    reason: 'Product A accounts for 38% of revenue with a growing margin.',
    impact: 'Estimated +12% total revenue uplift over 2 quarters.',
    priority: 'high',
  },
  {
    id: 'r2',
    action: 'Investigate churn among 18–25 segment',
    reason: 'This segment has the highest churn rate at 14.2%, above company average.',
    impact: 'Retaining 10% of churning users could add ~$240K ARR.',
    priority: 'high',
  },
  {
    id: 'r3',
    action: 'Reduce spend on underperforming campaigns',
    reason: 'Three campaigns have negative ROI over the last 90 days.',
    impact: 'Reallocation could improve marketing efficiency by 18%.',
    priority: 'medium',
  },
];

interface DevReport {
  id: string;
  name: string;
  type: string;
  date: string;
  status: string;
}

/**
 * DEV-ONLY: Recent generated reports.
 * Will be replaced by the reports service.
 */
const DEV_REPORTS: DevReport[] = [
  { id: 'rp1', name: 'Monthly Sales Analysis', type: 'Sales', date: 'Aug 2026', status: 'Complete' },
  { id: 'rp2', name: 'Customer Performance Report', type: 'Customer', date: 'Jul 2026', status: 'Complete' },
  { id: 'rp3', name: 'Marketing Performance Report', type: 'Marketing', date: 'Jun 2026', status: 'Complete' },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function statusClass(status: string): string {
  return `ws-badge ws-badge--${status}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** AI Query Composer: question input plus send action only. */
function AskAIComposer() {
  const [query, setQuery] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const navigate = useNavigate();

  function handleSend() {
    const trimmed = query.trim();
    if (!trimmed) return;
    // BACKEND INTEGRATION POINT:
    // Send { question: trimmed } to the future analysis request service.
    // For now navigate to the analysis page with the question as state.
    navigate('/analysis', { state: { question: trimmed } });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
  }

  // Auto-grow textarea
  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setQuery(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }
  }

  return (
    <div className="ws-composer" role="search" aria-label="Ask AI about your data">
      <div className="ws-composer-inner">
        <span className="ws-composer-icon" aria-hidden="true">
          <Sparkles size={18} />
        </span>
        <textarea
          ref={textareaRef}
          className="ws-composer-textarea"
          placeholder="Ask anything about your data…  (⌘ Enter to send)"
          value={query}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          rows={2}
          aria-label="Enter your analytical question"
          aria-multiline="true"
        />
      </div>
      <div className="ws-composer-footer">
        <button
          type="button"
          className="ws-composer-send"
          onClick={handleSend}
          disabled={!query.trim()}
          aria-label="Send question"
        >
          <Send size={13} />
          Send
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  return (
    <div className="ws-page">

      {/* ================================================================== */}
      {/* 1. Hero / Ask AI                                                    */}
      {/* ================================================================== */}
      <section className="ws-hero" aria-labelledby="dashboard-heading">
        <div className="ws-hero-mark" aria-hidden="true">
          <Sparkles size={30} />
        </div>
        <p className="ws-hero-eyebrow">WELCOME BACK</p>
        <h1 id="dashboard-heading" className="ws-hero-heading">
          What would you like to discover?
        </h1>
        <p className="ws-hero-sub">
          Ask questions about your data in plain language and turn analysis
          into actionable decisions.
        </p>
        <AskAIComposer />
      </section>

      {/* ================================================================== */}
      {/* 2. Quick Actions                                                     */}
      {/* ================================================================== */}
      <section aria-label="Quick actions">
        <div className="ws-quick-grid">
          <Link to="/datasets/upload" className="ws-quick-card">
            <div className="ws-quick-card-icon" aria-hidden="true">
              <Database size={18} />
            </div>
            <p className="ws-quick-card-title">Upload Dataset</p>
            <p className="ws-quick-card-desc">Add a dataset and start exploring your data.</p>
          </Link>

          <Link to="/analysis" className="ws-quick-card">
            <div className="ws-quick-card-icon" aria-hidden="true">
              <MessageSquare size={18} />
            </div>
            <p className="ws-quick-card-title">Ask AI</p>
            <p className="ws-quick-card-desc">Analyze data from a natural-language question.</p>
          </Link>

          <Link to="/datasets" className="ws-quick-card">
            <div className="ws-quick-card-icon" aria-hidden="true">
              <BarChart3 size={18} />
            </div>
            <p className="ws-quick-card-title">Explore Data</p>
            <p className="ws-quick-card-desc">Explore datasets, trends and generated insights.</p>
          </Link>
        </div>
      </section>

      {/* ================================================================== */}
      {/* 3. Recent Datasets + Recent Analyses                                */}
      {/* ================================================================== */}
      <div className="ws-bento-row">

        {/* Recent Datasets */}
        <section aria-labelledby="datasets-heading" className="ws-section-card">
          <div className="ws-section-card-header">
            <h2 id="datasets-heading" className="ws-section-card-title">Recent Datasets</h2>
            <Link to="/datasets" className="ws-section-card-link">View all →</Link>
          </div>
          <div className="ws-dataset-list">
            {RECENT_DATASETS.length === 0 ? (
              <div className="ws-empty">
                <span className="ws-empty-icon" aria-hidden="true"><Database size={28} /></span>
                <p className="ws-empty-text">
                  Upload your first dataset to start analyzing.
                </p>
              </div>
            ) : (
              RECENT_DATASETS.map((ds) => (
                <Link
                  key={ds.dataset_id}
                  to={`/datasets/${ds.dataset_id}`}
                  className="ws-dataset-item"
                  aria-label={`Dataset: ${ds.filename}`}
                >
                  <div className="ws-dataset-icon" aria-hidden="true">
                    <Database size={14} />
                  </div>
                  <div className="ws-dataset-info">
                    <p className="ws-dataset-name">{ds.filename}</p>
                    <p className="ws-dataset-meta">
                      {formatBytes(ds.size_bytes)} · {formatDate(ds.uploaded_at)}
                    </p>
                  </div>
                  <span className={statusClass(ds.status)}>
                    {ds.status}
                  </span>
                </Link>
              ))
            )}
          </div>
        </section>

        {/* Recent Analyses */}
        <section aria-labelledby="analyses-heading" className="ws-section-card">
          <div className="ws-section-card-header">
            <h2 id="analyses-heading" className="ws-section-card-title">Recent Analyses</h2>
            <Link to="/analysis" className="ws-section-card-link">View history →</Link>
          </div>
          <div className="ws-analysis-list">
            {DEV_ANALYSES.length === 0 ? (
              <div className="ws-empty">
                <span className="ws-empty-icon" aria-hidden="true"><MessageSquare size={28} /></span>
                <p className="ws-empty-text">
                  Ask your first question about your data.
                </p>
              </div>
            ) : (
              DEV_ANALYSES.map((a) => (
                <div key={a.id} className="ws-analysis-item">
                  <p className="ws-analysis-question">&ldquo;{a.question}&rdquo;</p>
                  <div className="ws-analysis-meta">
                    <span>{a.timestamp}</span>
                    <span aria-hidden="true">·</span>
                    <span style={{ color: a.status === 'complete' ? '#4ade80' : 'rgba(255,255,255,0.4)' }}>
                      {a.status === 'complete' ? 'Complete' : 'Pending'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {/* ================================================================== */}
      {/* 4. Key Insights + Visualizations                                    */}
      {/* ================================================================== */}
      <div className="ws-bento-row">

        {/* Key Insights */}
        <section aria-labelledby="insights-heading" className="ws-section-card">
          <div className="ws-section-card-header">
            <h2 id="insights-heading" className="ws-section-card-title">Key Insights</h2>
            <Link to="/insights" className="ws-section-card-link">View all →</Link>
          </div>
          {DEV_INSIGHTS.length === 0 ? (
            <div className="ws-empty">
              <span className="ws-empty-icon" aria-hidden="true"><Lightbulb size={28} /></span>
              <p className="ws-empty-text">
                Insights will appear after your data is analyzed.
              </p>
            </div>
          ) : (
            <div className="ws-insights-grid">
              {DEV_INSIGHTS.map((ins) => (
                <div key={ins.id} className="ws-insight-card">
                  <div className="ws-insight-icon-row">
                    <div className="ws-insight-icon" aria-hidden="true">{ins.icon}</div>
                    <div
                      className={`ws-insight-severity ws-insight-severity--${ins.severity}`}
                      aria-label={`Severity: ${ins.severity}`}
                    />
                  </div>
                  <p className="ws-insight-metric" aria-label={`Metric: ${ins.metric}`}>
                    {ins.metric}
                  </p>
                  <p className="ws-insight-label">{ins.label}</p>
                  <p className="ws-insight-text">{ins.text}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Visualizations */}
        <section aria-labelledby="vis-heading" className="ws-section-card">
          <div className="ws-section-card-header">
            <h2 id="vis-heading" className="ws-section-card-title">Visualizations</h2>
            <Link to="/visualizations" className="ws-section-card-link">View all →</Link>
          </div>
          <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {DEV_VISUALIZATIONS.length === 0 ? (
              <div className="ws-empty">
                <span className="ws-empty-icon" aria-hidden="true"><BarChart3 size={28} /></span>
                <p className="ws-empty-text">
                  Visualizations will appear after analysis is complete.
                </p>
              </div>
            ) : (
              DEV_VISUALIZATIONS.map((vis) => (
                <div key={vis.id} className="ws-vis-card">
                  <div className="ws-vis-preview" aria-hidden="true">
                    {vis.chart}
                  </div>
                  <div className="ws-vis-info">
                    <div>
                      <p className="ws-vis-title">{vis.title}</p>
                      <p className="ws-vis-desc">{vis.desc}</p>
                    </div>
                    <Link to="/visualizations" className="ws-vis-open-btn" aria-label={`Open ${vis.title} visualization`}>
                      Open <ArrowUpRight size={10} style={{ display: 'inline', verticalAlign: 'middle' }} />
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {/* ================================================================== */}
      {/* 5. Recommendations + Reports                                        */}
      {/* ================================================================== */}
      <div className="ws-bento-row">

        {/* Recommendations */}
        <section aria-labelledby="recs-heading" className="ws-section-card">
          <div className="ws-section-card-header">
            <h2 id="recs-heading" className="ws-section-card-title">Recommendations</h2>
            <Link to="/insights" className="ws-section-card-link">View all →</Link>
          </div>
          {DEV_RECOMMENDATIONS.length === 0 ? (
            <div className="ws-empty">
              <span className="ws-empty-icon" aria-hidden="true"><Lightbulb size={28} /></span>
              <p className="ws-empty-text">
                Recommendations will appear after your data is analyzed.
              </p>
            </div>
          ) : (
            <div className="ws-rec-list">
              {DEV_RECOMMENDATIONS.map((rec) => (
                <div key={rec.id} className="ws-rec-card">
                  <div className="ws-rec-header">
                    <p className="ws-rec-action">{rec.action}</p>
                    <span className={`ws-rec-priority ws-rec-priority--${rec.priority}`}>
                      {rec.priority.charAt(0).toUpperCase() + rec.priority.slice(1)}
                    </span>
                  </div>
                  <p className="ws-rec-reason">{rec.reason}</p>
                  <p className="ws-rec-impact">{rec.impact}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Recent Reports */}
        <section aria-labelledby="reports-heading" className="ws-section-card">
          <div className="ws-section-card-header">
            <h2 id="reports-heading" className="ws-section-card-title">Recent Reports</h2>
            <Link to="/reports" className="ws-section-card-link">View all →</Link>
          </div>
          {DEV_REPORTS.length === 0 ? (
            <div className="ws-empty">
              <span className="ws-empty-icon" aria-hidden="true"><FileText size={28} /></span>
              <p className="ws-empty-text">Generated reports will appear here.</p>
            </div>
          ) : (
            <div className="ws-report-list">
              {DEV_REPORTS.map((rep) => (
                <div key={rep.id} className="ws-report-item">
                  <div className="ws-report-icon" aria-hidden="true">
                    <FileText size={14} />
                  </div>
                  <div className="ws-report-info">
                    <p className="ws-report-name">{rep.name}</p>
                    <p className="ws-report-meta">{rep.type} · {rep.date}</p>
                  </div>
                  <span className="ws-badge ws-badge--processed" style={{ fontSize: 10 }}>
                    {rep.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

    </div>
  );
}
