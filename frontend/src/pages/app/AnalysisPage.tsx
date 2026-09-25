import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowUpRight,
  BarChart3,
  ChevronDown,
  FileText,
  Lightbulb,
  Plus,
  RotateCcw,
  Send,
  Sparkles,
  X,
} from 'lucide-react';
import { TextShimmer } from '../../components/ui/shimmer-text';
import { datasetService } from '../../services/datasetService';
import { analysisService } from '../../services/analysisService';
import type { Dataset } from '../../types/datasets';
import type { ChatResponse } from '../../types/analysis';

type WorkspaceView = 'new' | 'history';
type AnalysisState = 'idle' | 'simple' | 'result';

/** Represents a file attached to the composer for AI context. */
interface AttachedFile {
  /** Unique key to track the file in the list. */
  id: string;
  name: string;
  sizeLabel: string;
  /** Broad category for the badge label. */
  kind: 'dataset' | 'document' | 'image';
}

const SUGGESTIONS = [
  'What is the average cost?',
  'Show total revenue by item',
  'Which product has the highest growth?',
  'Summarize the dataset health and performance',
];

const HISTORY = [
  { question: 'What is the average cost?', dataset: 'test_products.csv', when: 'Today' },
  { question: 'Show total revenue by item', dataset: 'test_products.csv', when: 'Yesterday' },
];

function ResultPreview({ result }: { result: ChatResponse }) {
  const hasData = result.data && result.data.length > 0;

  return (
    <motion.section
      className="analysis-results"
      aria-labelledby="analysis-summary-heading"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="analysis-result-summary">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
          <p className="analysis-overline" style={{ margin: 0 }}>AI Summary</p>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '12px',
              background: 'rgba(107, 220, 255, 0.12)',
              color: '#6bdcff',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {result.intent}
          </span>
          <span style={{ fontSize: '12px', color: 'rgba(218, 228, 240, 0.65)' }}>
            {Math.round(result.confidence * 100)}% confidence
          </span>
          <span style={{ fontSize: '12px', color: 'rgba(218, 228, 240, 0.45)' }}>
            • {result.execution_time.toFixed(2)}s execution
          </span>
        </div>
        <h2 id="analysis-summary-heading">{result.answer}</h2>
        {result.explanation && (
          <p>{result.explanation}</p>
        )}
      </div>

      <div className="analysis-result-grid">
        {/* Key Findings / Returned Data */}
        <section className="analysis-result-card" aria-labelledby="key-findings-heading">
          <div className="analysis-card-heading">
            <BarChart3 size={15} aria-hidden="true" />
            <h3 id="key-findings-heading">Key Findings & Data</h3>
          </div>
          {hasData ? (
            <dl className="analysis-metrics">
              {result.data.slice(0, 8).map((row, rIdx) =>
                Object.entries(row).map(([key, val]) => (
                  <div key={`${rIdx}-${key}`}>
                    <dt title={key}>{key.replace(/_/g, ' ')}</dt>
                    <dd style={{ color: '#6bdcff' }}>
                      {val !== null && val !== undefined ? String(val) : '—'}
                    </dd>
                  </div>
                ))
              )}
            </dl>
          ) : (
            <p style={{ color: 'rgba(218, 228, 240, 0.48)', fontSize: '13px', margin: '16px 0 0' }}>
              No structured data records returned for this query.
            </p>
          )}
        </section>

        {/* Visualization Card */}
        <section className="analysis-result-card analysis-chart-card" aria-labelledby="visual-preview-heading">
          <div className="analysis-card-heading">
            <BarChart3 size={15} aria-hidden="true" />
            <h3 id="visual-preview-heading">Visualization</h3>
          </div>
          <div style={{ margin: '14px 0', fontSize: '13px', color: 'rgba(218, 228, 240, 0.65)', lineHeight: 1.5 }}>
            {hasData
              ? `${result.data.length} structured data record${result.data.length === 1 ? '' : 's'} available.`
              : 'Analytical narrative generated from dataset context.'}
            <div style={{ marginTop: '6px', fontSize: '12px', color: 'rgba(218, 228, 240, 0.45)' }}>
              Interactive visualization generation is scheduled for Phase 11.
            </div>
          </div>
          <Link to="/visualizations" className="analysis-open-visualization">
            Open in Visualizations <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
        </section>

        {/* Insights Card */}
        <section className="analysis-result-card" aria-labelledby="insights-result-heading">
          <div className="analysis-card-heading">
            <Lightbulb size={15} aria-hidden="true" />
            <h3 id="insights-result-heading">Insights</h3>
          </div>
          <ul className="analysis-bullet-list">
            <li>Intent classification: <strong>{result.intent}</strong> ({Math.round(result.confidence * 100)}% match)</li>
            {result.explanation ? (
              <li>{result.explanation}</li>
            ) : (
              <li>Execution completed in {result.execution_time.toFixed(2)}s</li>
            )}
            {hasData && (
              <li>Processed {result.data.length} analytical data observation{result.data.length === 1 ? '' : 's'}.</li>
            )}
          </ul>
          <Link to="/insights" className="analysis-inline-link">
            View insights <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
        </section>

        {/* Recommendations Card */}
        <section className="analysis-result-card" aria-labelledby="recommendations-heading">
          <div className="analysis-card-heading">
            <FileText size={15} aria-hidden="true" />
            <h3 id="recommendations-heading">Recommendations</h3>
          </div>
          <ul className="analysis-bullet-list">
            {result.actionable && result.actionable.length > 0 ? (
              result.actionable.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))
            ) : (
              <>
                <li>Review the calculated metrics against operational benchmarks.</li>
                <li>Drill down into related dimensions or time periods for deeper analysis.</li>
              </>
            )}
          </ul>
          <Link to="/reports" className="analysis-inline-link">
            View reports <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
        </section>
      </div>
    </motion.section>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ACCEPTED_TYPES = '.csv,.xlsx,.json,.pdf,.png,.jpg,.jpeg';

function fileSizeLabel(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

function fileKind(name: string): AttachedFile['kind'] {
  const ext = name.split('.').pop()?.toLowerCase() ?? '';
  if (['csv', 'xlsx', 'json'].includes(ext)) return 'dataset';
  if (ext === 'pdf') return 'document';
  return 'image';
}

// ---------------------------------------------------------------------------
// AnalysisPage
// ---------------------------------------------------------------------------

export default function AnalysisPage() {
  const location = useLocation();
  const reducedMotion = useReducedMotion();
  const pendingQuestion = (location.state as { question?: string } | null)?.question ?? '';
  const [view, setView] = useState<WorkspaceView>('new');
  
  // Real datasets loaded from backend
  const [availableDatasets, setAvailableDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [isLoadingDatasets, setIsLoadingDatasets] = useState<boolean>(true);

  // Analysis query & execution state
  const [question, setQuestion] = useState(pendingQuestion);
  const [analysisState, setAnalysisState] = useState<AnalysisState>('idle');
  const [analysisResult, setAnalysisResult] = useState<ChatResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Attachment state
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let isMounted = true;
    datasetService
      .list()
      .then((list) => {
        if (isMounted) {
          setAvailableDatasets(list);
          if (list.length > 0) {
            setSelectedDatasetId(list[0].dataset_id);
          }
        }
      })
      .catch(() => {
        // Fallback gracefully; general queries remain available
      })
      .finally(() => {
        if (isMounted) setIsLoadingDatasets(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  function handleAttachClick() {
    fileInputRef.current?.click();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const incoming = Array.from(e.target.files ?? []);
    if (!incoming.length) return;
    const next: AttachedFile[] = incoming.map((f) => ({
      id: `${f.name}-${f.lastModified}-${f.size}`,
      name: f.name,
      sizeLabel: fileSizeLabel(f.size),
      kind: fileKind(f.name),
    }));
    setAttachedFiles((prev) => {
      const existingIds = new Set(prev.map((a) => a.id));
      return [...prev, ...next.filter((a) => !existingIds.has(a.id))];
    });
    e.target.value = '';
  }

  function removeAttachment(id: string) {
    setAttachedFiles((prev) => prev.filter((a) => a.id !== id));
  }

  async function startAnalysis() {
    const trimmed = question.trim();
    if (!trimmed || analysisState === 'simple') return;

    setAnalysisError(null);
    setAnalysisState('simple');

    try {
      const res = await analysisService.ask(trimmed, selectedDatasetId || null);
      setAnalysisResult(res);
      setAnalysisState('result');
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to process analysis request. Please try again.';
      setAnalysisError(message);
      setAnalysisState('idle');
    }
  }

  function resetAnalysis() {
    setAnalysisState('idle');
    setAnalysisResult(null);
    setAnalysisError(null);
    setQuestion('');
    setView('new');
  }

  const selectedDatasetObj = availableDatasets.find((d) => d.dataset_id === selectedDatasetId);

  return (
    <div className="ws-page analysis-workspace">
      <div className="analysis-workspace-inner">
        <div className="analysis-tabs" role="tablist" aria-label="AI Analysis views">
          <button
            type="button"
            role="tab"
            aria-selected={view === 'new'}
            className={`analysis-tab${view === 'new' ? ' analysis-tab--active' : ''}`}
            onClick={() => setView('new')}
          >
            New Analysis
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === 'history'}
            className={`analysis-tab${view === 'history' ? ' analysis-tab--active' : ''}`}
            onClick={() => setView('history')}
          >
            History
          </button>
        </div>

        {view === 'history' ? (
          <section className="analysis-history" aria-labelledby="analysis-history-heading">
            <div className="analysis-history-heading">
              <p className="analysis-overline">Analysis History</p>
              <h1 id="analysis-history-heading">Continue an earlier question</h1>
            </div>
            <div className="analysis-history-list">
              {HISTORY.map((item) => (
                <button
                  key={item.question}
                  type="button"
                  className="analysis-history-item"
                  onClick={() => {
                    setQuestion(item.question);
                    setView('new');
                    setAnalysisState('idle');
                    setAnalysisResult(null);
                    setAnalysisError(null);
                  }}
                >
                  <span>{item.question}</span>
                  <small>{item.dataset} <span aria-hidden="true">&#8226;</span> {item.when}</small>
                </button>
              ))}
            </div>
          </section>
        ) : (
          <>
            {analysisState !== 'result' && (
              <motion.header
                className="analysis-hero"
                initial={reducedMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              >
                <p className="analysis-overline">AI Analysis</p>
                <h1>What would you like to discover?</h1>
                <p>Ask questions about your data and let AI uncover meaningful insights.</p>
              </motion.header>
            )}

            {analysisState !== 'result' && (
              <section className="analysis-composer-area" aria-label="Ask AI to analyze your data">
                {/* Error Banner */}
                {analysisError && (
                  <div
                    role="alert"
                    style={{
                      marginBottom: '16px',
                      padding: '12px 16px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      color: '#f87171',
                      fontSize: '13px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '12px',
                    }}
                  >
                    <span>{analysisError}</span>
                    <button
                      type="button"
                      onClick={() => setAnalysisError(null)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#f87171',
                        cursor: 'pointer',
                        padding: '2px 4px',
                        display: 'flex',
                        alignItems: 'center',
                      }}
                      aria-label="Dismiss error"
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}

                <label className="analysis-dataset-select" htmlFor="analysis-dataset">
                  <span>Dataset</span>
                  <span className="analysis-select-wrap">
                    <select
                      id="analysis-dataset"
                      value={selectedDatasetId}
                      onChange={(event) => setSelectedDatasetId(event.target.value)}
                      disabled={isLoadingDatasets}
                    >
                      {availableDatasets.length === 0 ? (
                        <option value="">No datasets uploaded (General Query)</option>
                      ) : (
                        availableDatasets.map((item) => (
                          <option key={item.dataset_id} value={item.dataset_id}>
                            {item.filename}
                          </option>
                        ))
                      )}
                    </select>
                    <ChevronDown size={14} aria-hidden="true" />
                  </span>
                </label>

                <div className="analysis-composer">
                  {/* Hidden file input */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ACCEPTED_TYPES}
                    multiple
                    aria-hidden="true"
                    tabIndex={-1}
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                  />

                  <div className="analysis-composer-content">
                    {/* Attachment chips */}
                    {attachedFiles.length > 0 && (
                      <ul className="analysis-attachments" aria-label="Attached files">
                        {attachedFiles.map((af) => (
                          <li key={af.id} className="analysis-attachment-chip">
                            <span className={`analysis-attachment-badge analysis-attachment-badge--${af.kind}`}>
                              {af.kind === 'dataset' ? 'CSV' : af.kind === 'document' ? 'PDF' : 'IMG'}
                            </span>
                            <span className="analysis-attachment-name" title={af.name}>{af.name}</span>
                            <span className="analysis-attachment-size">{af.sizeLabel}</span>
                            <button
                              type="button"
                              className="analysis-attachment-remove"
                              onClick={() => removeAttachment(af.id)}
                              aria-label={`Remove ${af.name}`}
                            >
                              <X size={11} aria-hidden="true" />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}

                    <Sparkles className="analysis-composer-icon" size={18} aria-hidden="true" />
                    <textarea
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      onKeyDown={(event) => {
                        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                          event.preventDefault();
                          startAnalysis();
                        }
                      }}
                      placeholder="Ask anything about your data..."
                      aria-label="Ask an analytical question"
                      rows={4}
                      disabled={analysisState === 'simple'}
                    />

                    {/* Attach button */}
                    <button
                      type="button"
                      className="analysis-attach-button"
                      onClick={handleAttachClick}
                      aria-label="Attach files"
                      disabled={analysisState === 'simple'}
                    >
                      <Plus size={16} aria-hidden="true" />
                    </button>

                    <button
                      type="button"
                      className="analysis-send-button"
                      onClick={startAnalysis}
                      disabled={!question.trim() || analysisState === 'simple'}
                      aria-label="Send analysis question"
                    >
                      <Send size={16} aria-hidden="true" />
                    </button>
                  </div>
                </div>

                {analysisState === 'simple' && (
                  <section className="analysis-status" aria-live="polite" aria-label="Analysis progress">
                    <TextShimmer className="analysis-thinking">Agent is analyzing your dataset...</TextShimmer>
                  </section>
                )}

                {analysisState === 'idle' && (
                  <div className="analysis-suggestions" aria-label="Suggested questions">
                    {SUGGESTIONS.map((suggestion) => (
                      <button key={suggestion} type="button" onClick={() => setQuestion(suggestion)}>
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}

            {analysisState === 'result' && analysisResult && (
              <>
                <div className="analysis-result-toolbar">
                  <div>
                    <p className="analysis-overline">{selectedDatasetObj?.filename || 'General Analysis'}</p>
                    <p className="analysis-result-question">{question}</p>
                  </div>
                  <button type="button" className="analysis-new-button" onClick={resetAnalysis}>
                    <RotateCcw size={14} aria-hidden="true" />
                    New analysis
                  </button>
                </div>
                <ResultPreview result={analysisResult} />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
