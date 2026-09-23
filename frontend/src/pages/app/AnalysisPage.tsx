import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  Circle,
  FileText,
  Lightbulb,
  Plus,
  RotateCcw,
  Send,
  Sparkles,
  X,
} from 'lucide-react';
import { TextShimmer } from '../../components/ui/shimmer-text';

type WorkspaceView = 'new' | 'history';
type AnalysisState = 'idle' | 'simple' | 'visualizing' | 'result';
type PromptIntent = 'simple' | 'visualization';

/** Represents a file attached to the composer for AI context. */
interface AttachedFile {
  /** Unique key to track the file in the list. */
  id: string;
  name: string;
  sizeLabel: string;
  /** Broad category for the badge label. */
  kind: 'dataset' | 'document' | 'image';
}

const DATASETS = [
  'Sales_Data_2026.xlsx',
  'Customer_Data.csv',
  'Marketing_Data.xlsx',
  'Product_Performance.csv',
];

const SUGGESTIONS = [
  'Why did revenue decrease last month?',
  'Which product has the highest growth?',
  'Which customer segment has the highest churn?',
  'Show me the relationship between marketing spend and revenue.',
];

const HISTORY = [
  { question: 'Why did revenue decrease last month?', dataset: 'Sales Data', when: 'Today' },
  { question: 'Which customers are most likely to churn?', dataset: 'Customer Data', when: 'Yesterday' },
  { question: 'Which campaign generated the highest ROI?', dataset: 'Marketing Data', when: '2 days ago' },
];

const VISUALIZATION_STEPS = [
  'Understanding your request',
  'Preparing your dataset',
  'Analyzing patterns',
  'Generating visualizations',
  'Finalizing your workspace',
];

function classifyPromptIntent(question: string): PromptIntent {
  const normalized = question.toLowerCase();
  const visualizationSignals = [
    'chart',
    'visual',
    'visualize',
    'visualization',
    'graph',
    'plot',
    'line',
    'bar',
    'pie',
    'donut',
    'trend',
    'compare',
    'distribution',
    'dashboard',
    'region',
    'revenue',
    'sales',
    'performance',
  ];
  return visualizationSignals.some((signal) => normalized.includes(signal)) ? 'visualization' : 'simple';
}

function VisualizationGenerationLoader({ activeStep }: { activeStep: number }) {
  return (
    <section className="analysis-viz-loader" aria-live="polite" aria-label="Visualization generation progress">
      <div className="analysis-viz-animation" aria-hidden="true">
        <svg viewBox="0 0 420 210">
          <defs>
            <linearGradient id="loaderLine" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="#ffb86b" />
              <stop offset="52%" stopColor="#6bdcff" />
              <stop offset="100%" stopColor="#8f7cff" />
            </linearGradient>
            <radialGradient id="loaderGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#6bdcff" stopOpacity="0.42" />
              <stop offset="100%" stopColor="#6bdcff" stopOpacity="0" />
            </radialGradient>
          </defs>
          <circle className="analysis-loader-radial" cx="210" cy="104" r="78" fill="url(#loaderGlow)" />
          <path className="analysis-loader-grid" d="M40 50H380M40 95H380M40 140H380M95 26V168M155 26V168M215 26V168M275 26V168M335 26V168" />
          <path className="analysis-loader-flow" d="M42 132 C92 54 136 54 184 111 S278 169 378 62" />
          <g className="analysis-loader-points">
            {[72, 116, 160, 204, 248, 292, 336].map((x, index) => (
              <circle key={x} cx={x} cy={index % 2 ? 82 : 122} r={index === activeStep + 1 ? 7 : 4} />
            ))}
          </g>
          <g className="analysis-loader-bubbles">
            <circle cx="118" cy="58" r="13" />
            <circle cx="286" cy="74" r="18" />
            <circle cx="334" cy="136" r="10" />
          </g>
        </svg>
      </div>
      <div className="analysis-viz-copy">
        <h2>Creating your visualizations</h2>
        <p>Analyzing your data and generating insights...</p>
      </div>
      <ol className="analysis-workflow-list analysis-workflow-list--viz">
        {VISUALIZATION_STEPS.map((step, index) => {
          const state = index < activeStep ? 'complete' : index === activeStep ? 'active' : 'upcoming';
          return (
            <li key={step} className={`analysis-workflow-step analysis-workflow-step--${state}`}>
              {state === 'complete' ? <Check size={13} aria-hidden="true" /> : <Circle size={11} aria-hidden="true" />}
              <span>{step}</span>
            </li>
          );
        })}
      </ol>
      <div className="analysis-viz-status">
        <strong>Turning your data into meaningful visual stories</strong>
        <span>Almost there...</span>
      </div>
    </section>
  );
}

function ResultPreview() {
  return (
    <motion.section
      className="analysis-results"
      aria-labelledby="analysis-summary-heading"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="analysis-result-summary">
        <p className="analysis-overline">AI Summary</p>
        <h2 id="analysis-summary-heading">Revenue is down 12.4% from the previous month.</h2>
        <p>
          The decline is primarily driven by lower Product B performance and a weaker return from Campaign Y.
        </p>
      </div>

      <div className="analysis-result-grid">
        <section className="analysis-result-card" aria-labelledby="key-findings-heading">
          <div className="analysis-card-heading">
            <BarChart3 size={15} aria-hidden="true" />
            <h3 id="key-findings-heading">Key Findings</h3>
          </div>
          <dl className="analysis-metrics">
            <div><dt>Revenue</dt><dd>-12.4%</dd></div>
            <div><dt>Orders</dt><dd>-8.2%</dd></div>
            <div><dt>Conversion</dt><dd>-4.1%</dd></div>
          </dl>
        </section>

        <section className="analysis-result-card analysis-chart-card" aria-labelledby="visual-preview-heading">
          <div className="analysis-card-heading">
            <BarChart3 size={15} aria-hidden="true" />
            <h3 id="visual-preview-heading">Visualization Preview</h3>
          </div>
          <svg viewBox="0 0 280 100" role="img" aria-label="Revenue trend declining over the last six months">
            <defs>
              <linearGradient id="analysis-chart-gradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#8be8dd" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#8be8dd" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path className="analysis-chart-grid" d="M0 25H280M0 50H280M0 75H280" />
            <path className="analysis-chart-area" d="M0 18 L45 24 L90 32 L135 42 L180 48 L225 62 L280 80 L280 100 L0 100 Z" />
            <path className="analysis-chart-line" d="M0 18 L45 24 L90 32 L135 42 L180 48 L225 62 L280 80" />
          </svg>
          <Link to="/visualizations" className="analysis-open-visualization">
            Open in Visualizations <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
        </section>

        <section className="analysis-result-card" aria-labelledby="insights-result-heading">
          <div className="analysis-card-heading">
            <Lightbulb size={15} aria-hidden="true" />
            <h3 id="insights-result-heading">Insights</h3>
          </div>
          <ul className="analysis-bullet-list">
            <li>Revenue decline is concentrated in Product B.</li>
            <li>Customer segment X showed the largest decrease.</li>
            <li>Campaign Y generated negative ROI.</li>
          </ul>
          <Link to="/insights" className="analysis-inline-link">View insights <ArrowUpRight size={13} aria-hidden="true" /></Link>
        </section>

        <section className="analysis-result-card" aria-labelledby="recommendations-heading">
          <div className="analysis-card-heading">
            <FileText size={15} aria-hidden="true" />
            <h3 id="recommendations-heading">Recommendations</h3>
          </div>
          <ul className="analysis-bullet-list">
            <li>Investigate Product B performance.</li>
            <li>Review campaign allocation.</li>
            <li>Focus retention efforts on affected customers.</li>
          </ul>
          <Link to="/reports" className="analysis-inline-link">View reports <ArrowUpRight size={13} aria-hidden="true" /></Link>
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
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();
  const pendingQuestion = (location.state as { question?: string } | null)?.question ?? '';
  const [view, setView] = useState<WorkspaceView>('new');
  const [dataset, setDataset] = useState(DATASETS[0]);
  const [question, setQuestion] = useState(pendingQuestion);
  const [analysisState, setAnalysisState] = useState<AnalysisState>('idle');
  const [workflowStep, setWorkflowStep] = useState(0);

  // Attachment state — local to this page; no backend call yet.
  // BACKEND INTEGRATION POINT: wire attachments to the future analysis context service.
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      // Deduplicate by id
      const existingIds = new Set(prev.map((a) => a.id));
      return [...prev, ...next.filter((a) => !existingIds.has(a.id))];
    });
    // Reset so the same file can be re-selected after removal
    e.target.value = '';
  }

  function removeAttachment(id: string) {
    setAttachedFiles((prev) => prev.filter((a) => a.id !== id));
  }

  useEffect(() => {
    if (analysisState === 'simple') {
      const timer = window.setTimeout(() => setAnalysisState('result'), 1150);
      return () => window.clearTimeout(timer);
    }

    if (analysisState === 'visualizing') {
      const timer = window.setInterval(() => {
        setWorkflowStep((current) => {
          if (current >= VISUALIZATION_STEPS.length - 1) {
            window.clearInterval(timer);
            navigate('/visualizations', {
              state: {
                dataset,
                question,
                chartType: 'Line',
              },
            });
            return current;
          }
          return current + 1;
        });
      }, 680);
      return () => window.clearInterval(timer);
    }

    return undefined;
  }, [analysisState, dataset, navigate, question]);

  function startAnalysis() {
    const trimmed = question.trim();
    if (!trimmed) return;
    setWorkflowStep(0);
    setAnalysisState(classifyPromptIntent(trimmed) === 'visualization' ? 'visualizing' : 'simple');
  }

  function resetAnalysis() {
    setAnalysisState('idle');
    setQuestion('');
    setWorkflowStep(0);
    setView('new');
  }

  const statusVisible = analysisState === 'simple' || analysisState === 'visualizing';

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
                <label className="analysis-dataset-select" htmlFor="analysis-dataset">
                  <span>Dataset</span>
                  <span className="analysis-select-wrap">
                    <select id="analysis-dataset" value={dataset} onChange={(event) => setDataset(event.target.value)}>
                      {DATASETS.map((item) => <option key={item}>{item}</option>)}
                    </select>
                    <ChevronDown size={14} aria-hidden="true" />
                  </span>
                </label>

                <div className="analysis-composer">
                  {/* Hidden file input — triggered by the + button */}
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
                    {/* Attachment chips — shown when files are attached */}
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
                        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') startAnalysis();
                      }}
                      placeholder="Ask anything about your data..."
                      aria-label="Ask an analytical question"
                      rows={4}
                    />

                    {/* Attach button — bottom-left */}
                    <button
                      type="button"
                      className="analysis-attach-button"
                      onClick={handleAttachClick}
                      aria-label="Attach files"
                    >
                      <Plus size={16} aria-hidden="true" />
                    </button>

                    <button type="button" className="analysis-send-button" onClick={startAnalysis} disabled={!question.trim()} aria-label="Send analysis question">
                      <Send size={16} aria-hidden="true" />
                    </button>
                  </div>
                </div>

                {analysisState === 'simple' && (
                  <section className="analysis-status" aria-live="polite" aria-label="Analysis progress">
                    <TextShimmer className="analysis-thinking">Agent is thinking ...</TextShimmer>
                  </section>
                )}

                {analysisState === 'visualizing' && (
                  <VisualizationGenerationLoader activeStep={workflowStep} />
                )}

                {!statusVisible && (
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

            {analysisState === 'result' && (
              <>
                <div className="analysis-result-toolbar">
                  <div>
                    <p className="analysis-overline">{dataset}</p>
                    <p className="analysis-result-question">{question}</p>
                  </div>
                  <button type="button" className="analysis-new-button" onClick={resetAnalysis}>
                    <RotateCcw size={14} aria-hidden="true" />
                    New analysis
                  </button>
                </div>
                <ResultPreview />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
