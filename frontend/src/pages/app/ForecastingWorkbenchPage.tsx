/**
 * ForecastingWorkbenchPage � Phase 23.8
 *
 * Visual forecasting workbench with:
 *  - Dataset + column selector
 *  - Model selection (Prophet, XGBoost, Ensemble)
 *  - Horizon / confidence interval controls
 *  - Model comparison accuracy table
 *  - Interactive forecast chart (Plotly-ready placeholders)
 *  - Real-time training progress
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp,
  Play,
  Settings2,
    AlertCircle,
  CheckCircle,
  Database,
  ArrowRight,
  Cpu,
  Target,
  Activity,
  ChevronDown,
} from "lucide-react";
import { useToast } from "../../components/ui/Toast";
import { SkeletonChart } from "../../components/ui/Skeleton";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ForecastModel = "prophet" | "xgboost" | "ensemble";
type ForecastStatus = "idle" | "training" | "complete" | "error";

interface ModelResult {
  model: string;
  mae: number;
  rmse: number;
  mape: number;
  r2: number;
  trainingTime: number;
}

interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
}

// ---------------------------------------------------------------------------
// Mock data � will be replaced by ForecastEngine API calls
// ---------------------------------------------------------------------------

const DEV_DATASETS = [
  { id: "ds-1", name: "sales_data_2024.csv",   rows: 12000, dateCol: "date",       valueCol: "revenue" },
  { id: "ds-2", name: "inventory_monthly.csv", rows: 3600,  dateCol: "month",      valueCol: "stock_level" },
  { id: "ds-3", name: "customer_churn.csv",    rows: 45000, dateCol: "created_at", valueCol: "churn_score" },
];

const MODEL_INFO: Record<ForecastModel, { label: string; description: string; color: string }> = {
  prophet:  { label: "Prophet",  description: "Facebook's time-series model. Great for seasonal patterns.", color: "#3b82f6" },
  xgboost:  { label: "XGBoost",  description: "Gradient boosting with feature engineering. High accuracy.",  color: "#10b981" },
  ensemble: { label: "Ensemble", description: "Weighted combination of Prophet + XGBoost. Best overall.",   color: "#8b5cf6" },
};

function generateMockForecast(horizon: number): ForecastPoint[] {
  const now = new Date();
  const pts: ForecastPoint[] = [];
  let val = 125000;
  for (let i = 0; i < horizon; i++) {
    const d = new Date(now);
    d.setDate(d.getDate() + i * 7);
    val = val * (1 + (Math.random() - 0.45) * 0.08);
    pts.push({
      date: d.toISOString().slice(0, 10),
      value: Math.round(val),
      lower: Math.round(val * 0.88),
      upper: Math.round(val * 1.12),
    });
  }
  return pts;
}

// ---------------------------------------------------------------------------
// Forecast Chart (simplified SVG � replace with Plotly in production)
// ---------------------------------------------------------------------------

function ForecastChart({ points, model }: { points: ForecastPoint[]; model: ForecastModel }) {
  if (!points.length) return null;
  const W = 800;
  const H = 280;
  const PAD = { top: 20, right: 20, bottom: 40, left: 70 };
  const w = W - PAD.left - PAD.right;
  const h = H - PAD.top - PAD.bottom;

  const allVals = points.flatMap(p => [p.lower, p.upper]);
  const minV = Math.min(...allVals);
  const maxV = Math.max(...allVals);
  const xScale = (i: number) => (i / (points.length - 1)) * w;
  const yScale = (v: number) => h - ((v - minV) / (maxV - minV)) * h;
  const color = MODEL_INFO[model].color;

  const lineD = points.map((p, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(p.value)}`).join(" ");
  const areaTop = points.map((p, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(p.upper)}`).join(" ");
  const areaBot = [...points].reverse().map((p, i) => `${i === 0 ? "L" : "L"}${xScale(points.length - 1 - i)},${yScale(p.lower)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="forecast-chart-svg" aria-label="Forecast chart">
      <defs>
        <linearGradient id="fg-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" />
          <stop offset="100%" stopColor={color} stopOpacity="0.03" />
        </linearGradient>
      </defs>
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map(f => (
          <line key={f} x1={0} y1={h * f} x2={w} y2={h * f}
            stroke="rgba(148,163,184,0.15)" strokeDasharray="4 4" />
        ))}
        {/* Confidence band */}
        <path d={`${areaTop} ${areaBot} Z`} fill="url(#fg-area)" />
        {/* Upper / lower bounds */}
        <path d={areaTop} fill="none" stroke={color} strokeWidth={1} strokeOpacity={0.35} strokeDasharray="4 4" />
        {/* Main line */}
        <path d={lineD} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
        {/* Dots at every 4th point */}
        {points.filter((_, i) => i % 4 === 0).map((p, i) => (
          <circle key={i} cx={xScale(i * 4)} cy={yScale(p.value)} r={3.5}
            fill={color} stroke="white" strokeWidth={1.5} />
        ))}
        {/* X axis labels */}
        {points.filter((_, i) => i % Math.floor(points.length / 5) === 0).map((p, i) => {
          const origIdx = points.findIndex(q => q.date === p.date);
          return (
            <text key={i} x={xScale(origIdx)} y={h + 18} textAnchor="middle"
              fontSize={10} fill="var(--text)" opacity={0.6}>
              {p.date.slice(5)}
            </text>
          );
        })}
        {/* Y axis labels */}
        {[0, 0.5, 1].map(f => {
          const v = minV + (maxV - minV) * (1 - f);
          return (
            <text key={f} x={-8} y={h * f + 4} textAnchor="end"
              fontSize={10} fill="var(--text)" opacity={0.6}>
              {v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toFixed(0)}
            </text>
          );
        })}
      </g>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function ForecastingWorkbenchPage() {
  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  const [selectedDataset, setSelectedDataset] = useState(DEV_DATASETS[0]);
  const [selectedModels, setSelectedModels] = useState<ForecastModel[]>(["prophet", "ensemble"]);
  const [horizon, setHorizon] = useState(12);
  const [confidenceInterval, setConfidenceInterval] = useState(90);
  const [status, setStatus] = useState<ForecastStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [activeModel, setActiveModel] = useState<ForecastModel>("ensemble");
  const [forecastPoints, setForecastPoints] = useState<ForecastPoint[]>([]);
  const [modelResults, setModelResults] = useState<ModelResult[]>([]);
  const [showConfig, setShowConfig] = useState(true);

  function toggleModel(m: ForecastModel) {
    setSelectedModels(prev =>
      prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]
    );
  }

  async function runForecast() {
    if (!selectedModels.length) {
      toastError("Select at least one model");
      return;
    }
    setStatus("training");
    setProgress(0);
    setForecastPoints([]);
    setModelResults([]);

    // Simulate training progress
    const steps = selectedModels.length * 5;
    for (let i = 0; i <= steps; i++) {
      await new Promise(r => setTimeout(r, 180));
      setProgress(Math.round((i / steps) * 100));
    }

    // Generate mock results
    const results: ModelResult[] = selectedModels.map(m => ({
      model: MODEL_INFO[m].label,
      mae:   Math.round(1200 + Math.random() * 800),
      rmse:  Math.round(1800 + Math.random() * 1200),
      mape:  parseFloat((3.5 + Math.random() * 4).toFixed(2)),
      r2:    parseFloat((0.82 + Math.random() * 0.15).toFixed(3)),
      trainingTime: parseFloat((0.8 + Math.random() * 2.5).toFixed(2)),
    }));

    setModelResults(results);
    setForecastPoints(generateMockForecast(horizon));
    setActiveModel(selectedModels.includes("ensemble") ? "ensemble" : selectedModels[0]);
    setStatus("complete");
    setShowConfig(false);
    success("Forecast complete!", `${selectedModels.length} model(s) trained in ${results.reduce((a, r) => a + r.trainingTime, 0).toFixed(1)}s`);
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-left">
          <div className="page-header-icon page-header-icon--purple">
            <TrendingUp size={20} />
          </div>
          <div>
            <h1 className="page-title">Forecasting Workbench</h1>
            <p className="page-subtitle">Train Prophet, XGBoost, and Ensemble models on your datasets</p>
          </div>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setShowConfig(p => !p)}
          >
            <Settings2 size={15} />
            {showConfig ? "Hide Config" : "Show Config"}
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={runForecast}
            disabled={status === "training" || !selectedModels.length}
          >
            {status === "training" ? (
              <><Cpu size={15} className="spin" /> Training... {progress}%</>
            ) : (
              <><Play size={15} /> Run Forecast</>
            )}
          </button>
        </div>
      </div>

      <div className="fw-layout">
        {/* Config Panel */}
        {showConfig && (
          <div className="fw-config">
            <div className="fw-section">
              <div className="fw-section-title">
                <Database size={14} />
                Dataset
              </div>
              <div className="fw-select-wrapper">
                <select
                  className="fw-select"
                  value={selectedDataset.id}
                  onChange={e => {
                    const ds = DEV_DATASETS.find(d => d.id === e.target.value);
                    if (ds) setSelectedDataset(ds);
                  }}
                >
                  {DEV_DATASETS.map(ds => (
                    <option key={ds.id} value={ds.id}>{ds.name}</option>
                  ))}
                </select>
                <ChevronDown size={13} className="fw-select-icon" />
              </div>
              <div className="fw-dataset-meta">
                <span className="fw-meta-tag">{selectedDataset.rows.toLocaleString()} rows</span>
                <span className="fw-meta-tag">Date: {selectedDataset.dateCol}</span>
                <span className="fw-meta-tag">Target: {selectedDataset.valueCol}</span>
              </div>
            </div>

            <div className="fw-section">
              <div className="fw-section-title">
                <Cpu size={14} />
                Models
              </div>
              <div className="fw-model-list">
                {(Object.entries(MODEL_INFO) as [ForecastModel, typeof MODEL_INFO.prophet][]).map(([key, info]) => (
                  <label key={key} className={`fw-model-card${selectedModels.includes(key) ? " fw-model-card--selected" : ""}`}
                    style={{ "--model-color": info.color } as React.CSSProperties}>
                    <input
                      type="checkbox"
                      className="fw-model-checkbox"
                      checked={selectedModels.includes(key)}
                      onChange={() => toggleModel(key)}
                    />
                    <div className="fw-model-dot" />
                    <div className="fw-model-info">
                      <span className="fw-model-name">{info.label}</span>
                      <span className="fw-model-desc">{info.description}</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="fw-section">
              <div className="fw-section-title">
                <Settings2 size={14} />
                Parameters
              </div>
              <div className="fw-params">
                <label className="fw-param">
                  <span className="fw-param-label">Forecast Horizon</span>
                  <div className="fw-param-input-row">
                    <input
                      type="range" min={4} max={52} value={horizon}
                      onChange={e => setHorizon(Number(e.target.value))}
                      className="fw-range"
                    />
                    <span className="fw-param-value">{horizon} weeks</span>
                  </div>
                </label>
                <label className="fw-param">
                  <span className="fw-param-label">Confidence Interval</span>
                  <div className="fw-param-input-row">
                    <input
                      type="range" min={50} max={99} step={5} value={confidenceInterval}
                      onChange={e => setConfidenceInterval(Number(e.target.value))}
                      className="fw-range"
                    />
                    <span className="fw-param-value">{confidenceInterval}%</span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Main Results Area */}
        <div className="fw-main">
          {status === "idle" && (
            <div className="fw-empty">
              <div className="fw-empty-icon">
                <TrendingUp size={40} />
              </div>
              <h3 className="fw-empty-title">Ready to Forecast</h3>
              <p className="fw-empty-desc">Configure your dataset and models, then click Run Forecast to begin training.</p>
              <button type="button" className="btn btn--primary" onClick={runForecast}>
                <Play size={15} /> Run Forecast
              </button>
            </div>
          )}

          {status === "training" && (
            <div className="fw-training">
              <div className="fw-training-header">
                <Cpu size={20} className="spin" />
                <span>Training {selectedModels.length} model{selectedModels.length > 1 ? "s" : ""}...</span>
              </div>
              <div className="fw-progress-bar">
                <div className="fw-progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <p className="fw-training-note">{progress < 40 ? "Loading dataset and feature engineering..." : progress < 75 ? "Training models..." : "Computing metrics and confidence intervals..."}</p>
              <div className="fw-training-models">
                {selectedModels.map(m => (
                  <div key={m} className="fw-training-model">
                    <div className="fw-training-model-dot" style={{ background: MODEL_INFO[m].color }} />
                    <span>{MODEL_INFO[m].label}</span>
                    {progress > 60 && <CheckCircle size={13} style={{ color: MODEL_INFO[m].color }} />}
                  </div>
                ))}
              </div>
              <SkeletonChart height="260px" />
            </div>
          )}

          {status === "complete" && (
            <>
              {/* Model selector tabs */}
              <div className="fw-model-tabs">
                {selectedModels.map(m => (
                  <button
                    key={m}
                    type="button"
                    className={`fw-model-tab${activeModel === m ? " fw-model-tab--active" : ""}`}
                    style={{ "--tab-color": MODEL_INFO[m].color } as React.CSSProperties}
                    onClick={() => setActiveModel(m)}
                  >
                    <span className="fw-model-tab-dot" />
                    {MODEL_INFO[m].label}
                  </button>
                ))}
              </div>

              {/* Chart */}
              <div className="fw-chart-card">
                <div className="fw-chart-header">
                  <div>
                    <h3 className="fw-chart-title">{selectedDataset.valueCol} Forecast</h3>
                    <p className="fw-chart-subtitle">{horizon}-week forecast with {confidenceInterval}% confidence interval � {MODEL_INFO[activeModel].label}</p>
                  </div>
                  <div className="fw-chart-legend">
                    <span className="fw-legend-item fw-legend-item--line" style={{ "--lc": MODEL_INFO[activeModel].color } as React.CSSProperties}>Forecast</span>
                    <span className="fw-legend-item fw-legend-item--band">Confidence Band</span>
                  </div>
                </div>
                <ForecastChart points={forecastPoints} model={activeModel} />
              </div>

              {/* Accuracy Metrics Table */}
              <div className="fw-metrics-card">
                <div className="fw-metrics-header">
                  <Target size={16} />
                  <h3>Model Accuracy Comparison</h3>
                </div>
                <div className="fw-metrics-table-wrap">
                  <table className="fw-metrics-table">
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>MAE</th>
                        <th>RMSE</th>
                        <th>MAPE</th>
                        <th>R�</th>
                        <th>Training Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelResults.map((r, i) => (
                        <tr key={i} className={r.r2 === Math.max(...modelResults.map(x => x.r2)) ? "fw-metrics-best" : ""}>
                          <td><strong>{r.model}</strong>{r.r2 === Math.max(...modelResults.map(x => x.r2)) && <span className="fw-best-badge">Best</span>}</td>
                          <td>{r.mae.toLocaleString()}</td>
                          <td>{r.rmse.toLocaleString()}</td>
                          <td className={r.mape < 5 ? "fw-metric--good" : r.mape < 10 ? "fw-metric--warn" : "fw-metric--bad"}>{r.mape}%</td>
                          <td className={r.r2 > 0.9 ? "fw-metric--good" : r.r2 > 0.75 ? "fw-metric--warn" : "fw-metric--bad"}>{r.r2}</td>
                          <td>{r.trainingTime}s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Actions */}
              <div className="fw-actions">
                <button type="button" className="btn btn--secondary" onClick={() => navigate("/reports/create")}>
                  <ArrowRight size={15} /> Generate Forecast Report
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => { setStatus("idle"); setShowConfig(true); }}>
                  <Activity size={15} /> Run New Forecast
                </button>
              </div>
            </>
          )}

          {status === "error" && (
            <div className="fw-error">
              <AlertCircle size={32} />
              <h3>Forecast Failed</h3>
              <p>Check that your dataset has valid date and numeric columns.</p>
              <button type="button" className="btn btn--primary" onClick={() => setStatus("idle")}>Try Again</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}



