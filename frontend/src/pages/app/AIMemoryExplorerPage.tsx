/**
 * AIMemoryExplorerPage � Phase 23.10
 *
 * Visualizes the AI Memory Layer:
 *  - Conversation history with context chain
 *  - Memory graph (topics, entities, relationships)
 *  - Session timeline
 *  - Export and clear memory actions
 */

import { useState } from "react";
import {
  Brain,
  MessageSquare,
  Database,
  BarChart3,
  Clock,
  Trash2,
  Download,
  Search,
  ChevronRight,
  Zap,
  Tag,
  Link,
  RefreshCw,
} from "lucide-react";
import { useToast } from "../../components/ui/Toast";

// ---------------------------------------------------------------------------
// Types & mock data
// ---------------------------------------------------------------------------

interface MemoryEntry {
  id: string;
  sessionId: string;
  timestamp: string;
  question: string;
  answer: string;
  dataset?: string;
  entities: string[];
  intent: "analysis" | "forecast" | "visualization" | "insight" | "report";
  relatedIds: string[];
}

const INTENT_CONFIG = {
  analysis:      { label: "Analysis",     color: "#3b82f6", icon: MessageSquare },
  forecast:      { label: "Forecast",     color: "#8b5cf6", icon: BarChart3 },
  visualization: { label: "Chart",        color: "#10b981", icon: BarChart3 },
  insight:       { label: "Insight",      color: "#f59e0b", icon: Zap },
  report:        { label: "Report",       color: "#ef4444", icon: Database },
};

const DEV_MEMORY: MemoryEntry[] = [
  {
    id: "m1",
    sessionId: "s1",
    timestamp: "2024-01-15T09:23:00Z",
    question: "What is the total revenue for Q4 2023?",
    answer: "Q4 2023 total revenue was $2.4M, representing an 18% increase over Q3 2023.",
    dataset: "sales_data_2024.csv",
    entities: ["revenue", "Q4 2023", "Q3 2023"],
    intent: "analysis",
    relatedIds: ["m2", "m3"],
  },
  {
    id: "m2",
    sessionId: "s1",
    timestamp: "2024-01-15T09:31:00Z",
    question: "Which products drove that revenue growth?",
    answer: "Product A (SaaS subscription) accounted for 62% of Q4 revenue. Product B grew 45% YoY.",
    dataset: "sales_data_2024.csv",
    entities: ["Product A", "Product B", "SaaS subscription"],
    intent: "analysis",
    relatedIds: ["m1", "m4"],
  },
  {
    id: "m3",
    sessionId: "s1",
    timestamp: "2024-01-15T09:45:00Z",
    question: "Forecast revenue for the next 6 months",
    answer: "Based on current trends, projected revenue is $14.2M for H1 2024, with 85% confidence interval [12.8M, 15.7M].",
    dataset: "sales_data_2024.csv",
    entities: ["revenue", "H1 2024", "forecast", "confidence interval"],
    intent: "forecast",
    relatedIds: ["m1"],
  },
  {
    id: "m4",
    sessionId: "s2",
    timestamp: "2024-01-16T14:05:00Z",
    question: "Show me a breakdown chart of revenue by product category",
    answer: "Generated a donut chart showing: SaaS (52%), Professional Services (31%), Licensing (17%).",
    dataset: "sales_data_2024.csv",
    entities: ["SaaS", "Professional Services", "Licensing", "donut chart"],
    intent: "visualization",
    relatedIds: ["m2"],
  },
  {
    id: "m5",
    sessionId: "s2",
    timestamp: "2024-01-16T14:22:00Z",
    question: "What anomalies do you see in the data?",
    answer: "Detected 3 anomalies: Unusual spike in refunds week of Dec 12, 40% drop in new signups Dec 25-27, abnormal return rate for SKU-B44.",
    dataset: "sales_data_2024.csv",
    entities: ["anomaly", "refunds", "signups", "SKU-B44"],
    intent: "insight",
    relatedIds: [],
  },
  {
    id: "m6",
    sessionId: "s3",
    timestamp: "2024-01-17T10:00:00Z",
    question: "Generate an executive report for Q4 performance",
    answer: "Generated Q4 Executive Report (PDF, 12 pages) including KPI dashboard, revenue analysis, and 6-month forecast.",
    dataset: "sales_data_2024.csv",
    entities: ["Q4", "executive report", "KPI", "PDF"],
    intent: "report",
    relatedIds: ["m1", "m3"],
  },
];

const SESSIONS = [
  { id: "s1", label: "Session 1 � Jan 15 AM", count: 3 },
  { id: "s2", label: "Session 2 � Jan 16 PM", count: 2 },
  { id: "s3", label: "Session 3 � Jan 17 AM", count: 1 },
];

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3600000);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AIMemoryExplorerPage() {
  const { success, warning } = useToast();
  const [search, setSearch] = useState("");
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>("m1");

  const filtered = DEV_MEMORY.filter(m => {
    const matchesSession = !selectedSession || m.sessionId === selectedSession;
    const q = search.toLowerCase();
    const matchesSearch = !q || m.question.toLowerCase().includes(q) || m.answer.toLowerCase().includes(q) || m.entities.some(e => e.toLowerCase().includes(q));
    return matchesSession && matchesSearch;
  });

  const allEntities = [...new Set(DEV_MEMORY.flatMap(m => m.entities))];
  const intentCounts = Object.fromEntries(
    Object.keys(INTENT_CONFIG).map(k => [k, DEV_MEMORY.filter(m => m.intent === k).length])
  );

  function handleClearMemory() {
    warning("Memory cleared", "All AI context has been reset for this workspace.");
  }

  function handleExport() {
    success("Memory exported", "memory_export.json downloaded successfully.");
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-left">
          <div className="page-header-icon page-header-icon--indigo">
            <Brain size={20} />
          </div>
          <div>
            <h1 className="page-title">AI Memory Explorer</h1>
            <p className="page-subtitle">Visualize what the AI remembers from your conversations</p>
          </div>
        </div>
        <div className="page-header-actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={handleExport}>
            <Download size={15} /> Export Memory
          </button>
          <button type="button" className="btn btn--ghost btn--sm btn--danger" onClick={handleClearMemory}>
            <Trash2 size={15} /> Clear Memory
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="mem-stats">
        <div className="mem-stat-card">
          <div className="mem-stat-value">{DEV_MEMORY.length}</div>
          <div className="mem-stat-label">Total Memories</div>
        </div>
        <div className="mem-stat-card">
          <div className="mem-stat-value">{SESSIONS.length}</div>
          <div className="mem-stat-label">Sessions</div>
        </div>
        <div className="mem-stat-card">
          <div className="mem-stat-value">{allEntities.length}</div>
          <div className="mem-stat-label">Known Entities</div>
        </div>
        <div className="mem-stat-card">
          <div className="mem-stat-value">{DEV_MEMORY.filter(m => m.relatedIds.length > 0).length}</div>
          <div className="mem-stat-label">Context Chains</div>
        </div>
      </div>

      <div className="mem-layout">
        {/* Left panel: filters */}
        <div className="mem-sidebar">
          <div className="mem-panel">
            <div className="mem-panel-title">Sessions</div>
            <div className="mem-session-list">
              <button
                type="button"
                className={`mem-session-item${!selectedSession ? " mem-session-item--active" : ""}`}
                onClick={() => setSelectedSession(null)}
              >
                <RefreshCw size={13} />
                All Sessions
                <span className="mem-session-count">{DEV_MEMORY.length}</span>
              </button>
              {SESSIONS.map(s => (
                <button
                  key={s.id}
                  type="button"
                  className={`mem-session-item${selectedSession === s.id ? " mem-session-item--active" : ""}`}
                  onClick={() => setSelectedSession(s.id)}
                >
                  <Clock size={13} />
                  {s.label}
                  <span className="mem-session-count">{s.count}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="mem-panel">
            <div className="mem-panel-title">Intent Breakdown</div>
            <div className="mem-intent-list">
              {(Object.entries(INTENT_CONFIG) as [keyof typeof INTENT_CONFIG, typeof INTENT_CONFIG.analysis][]).map(([key, info]) => (
                <div key={key} className="mem-intent-item">
                  <div className="mem-intent-dot" style={{ background: info.color }} />
                  <span className="mem-intent-label">{info.label}</span>
                  <span className="mem-intent-count">{intentCounts[key] || 0}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mem-panel">
            <div className="mem-panel-title">Known Entities</div>
            <div className="mem-entity-cloud">
              {allEntities.slice(0, 20).map(e => (
                <span key={e} className="mem-entity-tag" onClick={() => setSearch(e)}>
                  <Tag size={10} /> {e}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Main: memory timeline */}
        <div className="mem-main">
          {/* Search */}
          <div className="mem-search-wrapper">
            <Search size={15} className="mem-search-icon" />
            <input
              type="text"
              className="mem-search"
              placeholder="Search memories, entities, answers..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <div className="mem-timeline">
            {filtered.length === 0 && (
              <div className="mem-empty">
                <Brain size={32} />
                <p>No memories found matching your filters.</p>
              </div>
            )}
            {filtered.map((m, i) => {
              const cfg = INTENT_CONFIG[m.intent];
              const Icon = cfg.icon;
              const isExpanded = expandedId === m.id;
              const related = DEV_MEMORY.filter(x => m.relatedIds.includes(x.id));
              return (
                <div key={m.id} className={`mem-entry${isExpanded ? " mem-entry--expanded" : ""}`}>
                  {/* Timeline connector */}
                  {i < filtered.length - 1 && <div className="mem-connector" />}

                  <div className="mem-entry-header" onClick={() => setExpandedId(isExpanded ? null : m.id)}>
                    <div className="mem-entry-dot" style={{ background: cfg.color }}>
                      <Icon size={11} />
                    </div>
                    <div className="mem-entry-meta">
                      <span className="mem-intent-badge" style={{ background: cfg.color + "22", color: cfg.color }}>{cfg.label}</span>
                      {m.dataset && <span className="mem-dataset-tag"><Database size={10} /> {m.dataset}</span>}
                      <span className="mem-time"><Clock size={10} /> {timeAgo(m.timestamp)}</span>
                    </div>
                    <ChevronRight size={14} className={`mem-chevron${isExpanded ? " mem-chevron--open" : ""}`} />
                  </div>

                  <div className="mem-question">{m.question}</div>

                  {isExpanded && (
                    <div className="mem-entry-body">
                      <div className="mem-answer">
                        <p>{m.answer}</p>
                      </div>
                      {m.entities.length > 0 && (
                        <div className="mem-entities">
                          <span className="mem-entities-label"><Tag size={11} /> Entities:</span>
                          {m.entities.map(e => (
                            <span key={e} className="mem-entity-chip">{e}</span>
                          ))}
                        </div>
                      )}
                      {related.length > 0 && (
                        <div className="mem-related">
                          <span className="mem-related-label"><Link size={11} /> Context chain:</span>
                          <div className="mem-related-list">
                            {related.map(r => (
                              <button
                                key={r.id}
                                type="button"
                                className="mem-related-item"
                                onClick={() => setExpandedId(r.id)}
                              >
                                <ChevronRight size={11} />
                                {r.question.slice(0, 60)}...
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
