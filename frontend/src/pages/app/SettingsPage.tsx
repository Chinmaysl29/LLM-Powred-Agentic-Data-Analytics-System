import { useState, useEffect, useCallback } from 'react';
import {
  Sliders,
  Palette,
  Sparkles,
  Database,
  Bell,
  Layers,
  Shield,
  Cpu,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Terminal,
} from 'lucide-react';
import { settingsService } from '../../services/settingsService';
import type {
  AppSettings,
  SettingsCategory,
  DateFormatOption,
  NumberFormatOption,
  LandingPageOption,
  InterfaceDensity,
  AIResponseStyleOption,
  AIAnalysisDepthOption,
  PreviewRowsOption,
} from '../../types/settings';
import { ResetSettingsModal } from '../../components/settings/ResetSettingsModal';
import { DebugInfoModal } from '../../components/settings/DebugInfoModal';

interface NavItemDef {
  id: SettingsCategory;
  label: string;
  icon: typeof Sliders;
  description: string;
}

const CATEGORIES: NavItemDef[] = [
  { id: 'general', label: 'General', icon: Sliders, description: 'Language, date formatting and default starting view.' },
  { id: 'appearance', label: 'Appearance', icon: Palette, description: 'Workspace theme, interface density, and animation behavior.' },
  { id: 'ai', label: 'AI & Analysis', icon: Sparkles, description: 'AI model defaults, reasoning depth, and explainability controls.' },
  { id: 'data', label: 'Data & Analysis', icon: Database, description: 'Dataset preview limits, automatic insights, and retention policies.' },
  { id: 'notifications', label: 'Notifications', icon: Bell, description: 'Manage analysis alerts, report triggers, and system notices.' },
  { id: 'integrations', label: 'Integrations', icon: Layers, description: 'Connect cloud storage, databases, and enterprise data sources.' },
  { id: 'privacy', label: 'Privacy', icon: Shield, description: 'Workspace privacy preferences and conversational context retention.' },
  { id: 'advanced', label: 'Advanced', icon: Cpu, description: 'Performance tuning, diagnostics, and settings reset.' },
];

export default function SettingsPage() {
  const [activeCategory, setActiveCategory] = useState<SettingsCategory>('general');
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [initialSettings, setInitialSettings] = useState<AppSettings | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Modals
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [isDebugModalOpen, setIsDebugModalOpen] = useState(false);

  // Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string, _type: 'info' | 'success' = 'success') => {
    void _type;
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Load settings on mount
  const loadSettings = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await settingsService.getSettings();
      setSettings(JSON.parse(JSON.stringify(data)));
      setInitialSettings(JSON.parse(JSON.stringify(data)));
    } catch {
      setLoadError('Unable to load application settings. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Check dirty state for active category
  const isCategoryDirty = useCallback(() => {
    if (!settings || !initialSettings) return false;
    if (activeCategory === 'integrations') return false;
    return JSON.stringify(settings[activeCategory]) !== JSON.stringify(initialSettings[activeCategory]);
  }, [settings, initialSettings, activeCategory]);

  // Save changes for current settings
  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await settingsService.updateSettings(settings);
      setSettings(JSON.parse(JSON.stringify(updated)));
      setInitialSettings(JSON.parse(JSON.stringify(updated)));
      setSaveSuccess(true);
      showToast('Settings saved successfully.');
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch {
      showToast('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Cancel/revert changes for active category
  const handleCancel = () => {
    if (!initialSettings || !settings) return;
    if (activeCategory === 'integrations') return;
    setSettings({
      ...settings,
      [activeCategory]: JSON.parse(JSON.stringify(initialSettings[activeCategory])),
    });
  };

  // Confirm Reset Settings
  const handleConfirmReset = async () => {
    try {
      const reset = await settingsService.resetSettings();
      setSettings(JSON.parse(JSON.stringify(reset)));
      setInitialSettings(JSON.parse(JSON.stringify(reset)));
      showToast('Settings have been reset to default values.');
    } catch {
      showToast('Failed to reset settings.');
    }
  };

  if (loading) {
    return (
      <div className="ws-page settings-page-container">
        <div className="settings-loading-skeleton">
          <Loader2 size={32} className="settings-spinner" />
          <p>Loading application settings...</p>
        </div>
      </div>
    );
  }

  if (loadError || !settings) {
    return (
      <div className="ws-page settings-page-container">
        <div className="settings-error-state">
          <AlertCircle size={36} className="settings-danger-icon" />
          <h2>Unable to load settings</h2>
          <p>{loadError || 'Something went wrong while loading your preferences.'}</p>
          <button type="button" className="settings-btn-primary" onClick={loadSettings}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const activeDef = CATEGORIES.find((c) => c.id === activeCategory) || CATEGORIES[0];

  return (
    <div className="ws-page settings-page-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="settings-toast" role="status" aria-live="polite">
          <CheckCircle2 size={16} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <header className="settings-page-header">
        <div>
          <h1 className="ws-page-heading">Settings</h1>
          <p className="ws-page-sub">Configure how AI Data Analyst works for you.</p>
        </div>
      </header>

      {/* Mobile Category Dropdown */}
      <div className="settings-mobile-selector">
        <label htmlFor="settings-cat-select">Select Settings Category</label>
        <select
          id="settings-cat-select"
          className="settings-select settings-select--full"
          value={activeCategory}
          onChange={(e) => setActiveCategory(e.target.value as SettingsCategory)}
        >
          {CATEGORIES.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.label}
            </option>
          ))}
        </select>
      </div>

      {/* Desktop Split Layout */}
      <div className="settings-layout">
        {/* ── Left Settings Navigation ── */}
        <nav className="settings-sidebar-nav" aria-label="Settings categories">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                className={`settings-nav-item ${isActive ? 'settings-nav-item--active' : ''}`}
                onClick={() => setActiveCategory(cat.id)}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon size={17} className="settings-nav-icon" />
                <span className="settings-nav-label">{cat.label}</span>
              </button>
            );
          })}
        </nav>

        {/* ── Right Settings Content Panel ── */}
        <main className="settings-content-panel">
          <div className="settings-panel-card">
            {/* Panel Header */}
            <div className="settings-panel-header">
              <div className="settings-panel-header-left">
                <activeDef.icon size={20} className="settings-panel-icon" />
                <div>
                  <h2 className="settings-panel-title">{activeDef.label}</h2>
                  <p className="settings-panel-desc">{activeDef.description}</p>
                </div>
              </div>
              {saveSuccess && (
                <span className="settings-saved-pill">
                  <CheckCircle2 size={13} />
                  Saved
                </span>
              )}
            </div>

            {/* Panel Body by Category */}
            <div className="settings-panel-body">
              {/* ── 1. General ── */}
              {activeCategory === 'general' && (
                <div className="settings-category-body">
                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="gen-lang">Language</label>
                      <p>Active platform interface language</p>
                    </div>
                    <select
                      id="gen-lang"
                      className="settings-select"
                      value={settings.general.language}
                      onChange={() => showToast('English is currently the platform standard.')}
                    >
                      <option value="en">English (US)</option>
                    </select>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="gen-date">Date Format</label>
                      <p>Format applied to dataset timestamps and report schedules</p>
                    </div>
                    <select
                      id="gen-date"
                      className="settings-select"
                      value={settings.general.dateFormat}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          general: { ...settings.general, dateFormat: e.target.value as DateFormatOption },
                        })
                      }
                    >
                      <option value="DD/MM/YYYY">DD/MM/YYYY (31/12/2026)</option>
                      <option value="MM/DD/YYYY">MM/DD/YYYY (12/31/2026)</option>
                      <option value="YYYY-MM-DD">YYYY-MM-DD (2026-12-31)</option>
                    </select>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="gen-num">Number Format</label>
                      <p>Digit grouping and decimal representation</p>
                    </div>
                    <select
                      id="gen-num"
                      className="settings-select"
                      value={settings.general.numberFormat}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          general: { ...settings.general, numberFormat: e.target.value as NumberFormatOption },
                        })
                      }
                    >
                      <option value="1,234.56">1,234.56 (Standard)</option>
                      <option value="1.234,56">1.234,56 (European)</option>
                    </select>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="gen-landing">Default Landing Page</label>
                      <p>Page presented upon workspace authentication</p>
                    </div>
                    <select
                      id="gen-landing"
                      className="settings-select"
                      value={settings.general.defaultLandingPage}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          general: { ...settings.general, defaultLandingPage: e.target.value as LandingPageOption },
                        })
                      }
                    >
                      <option value="/dashboard">Dashboard</option>
                      <option value="/analysis">AI Analysis</option>
                      <option value="/datasets">Datasets</option>
                      <option value="/visualizations">Visualizations</option>
                      <option value="/insights">Insights & Decision Intelligence</option>
                      <option value="/reports">Reports</option>
                    </select>
                  </div>
                </div>
              )}

              {/* ── 2. Appearance ── */}
              {activeCategory === 'appearance' && (
                <div className="settings-category-body">
                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label>Theme</label>
                      <p>Application visual scheme</p>
                    </div>
                    <div className="settings-locked-pill">Dark (Platform Standard)</div>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label>Interface Density</label>
                      <p>Controls padding across data tables, card grids, and lists</p>
                    </div>
                    <div className="settings-segmented-group" role="radiogroup" aria-label="Interface Density">
                      <button
                        type="button"
                        role="radio"
                        aria-checked={settings.appearance.density === 'comfortable'}
                        className={`settings-segmented-btn ${settings.appearance.density === 'comfortable' ? 'settings-segmented-btn--active' : ''}`}
                        onClick={() =>
                          setSettings({
                            ...settings,
                            appearance: { ...settings.appearance, density: 'comfortable' as InterfaceDensity },
                          })
                        }
                      >
                        Comfortable
                      </button>
                      <button
                        type="button"
                        role="radio"
                        aria-checked={settings.appearance.density === 'compact'}
                        className={`settings-segmented-btn ${settings.appearance.density === 'compact' ? 'settings-segmented-btn--active' : ''}`}
                        onClick={() =>
                          setSettings({
                            ...settings,
                            appearance: { ...settings.appearance, density: 'compact' as InterfaceDensity },
                          })
                        }
                      >
                        Compact
                      </button>
                    </div>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="app-anim">Animations</label>
                      <p>Enable micro-animations, self-forming visualizations, and transitions</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="app-anim"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.appearance.animations}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            appearance: { ...settings.appearance, animations: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="app-motion">Reduce Motion</label>
                      <p>Minimize non-essential motion effects and dynamic transforms</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="app-motion"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.appearance.reduceMotion}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            appearance: { ...settings.appearance, reduceMotion: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>
                </div>
              )}

              {/* ── 3. AI & Analysis ── */}
              {activeCategory === 'ai' && (
                <div className="settings-category-body">
                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label>Default AI Model</label>
                      <p>Model engine utilized for analytical queries and planning</p>
                    </div>
                    <div className="settings-locked-pill">Automatic (Optimized Selection)</div>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="ai-style">Response Style</label>
                      <p>Controls phrasing length and verbosity of generated insights</p>
                    </div>
                    <select
                      id="ai-style"
                      className="settings-select"
                      value={settings.ai.responseStyle}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          ai: { ...settings.ai, responseStyle: e.target.value as AIResponseStyleOption },
                        })
                      }
                    >
                      <option value="Concise">Concise (Bullet-points only)</option>
                      <option value="Balanced">Balanced (Executive overview)</option>
                      <option value="Detailed">Detailed (In-depth analysis)</option>
                    </select>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="ai-depth">Analysis Depth</label>
                      <p>Defines how deep statistical correlations and patterns are evaluated</p>
                    </div>
                    <select
                      id="ai-depth"
                      className="settings-select"
                      value={settings.ai.analysisDepth}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          ai: { ...settings.ai, analysisDepth: e.target.value as AIAnalysisDepthOption },
                        })
                      }
                    >
                      <option value="Quick">Quick (Surface patterns)</option>
                      <option value="Balanced">Balanced (Standard EDA)</option>
                      <option value="Deep">Deep (Multi-factor root cause)</option>
                    </select>
                  </div>

                  <div className="settings-subgroup-title">Explainability & Reasoning</div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="ai-reasoning">Explain AI Reasoning</label>
                      <p>Show step-by-step reasoning steps behind analytical conclusions</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="ai-reasoning"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.ai.explainReasoning}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            ai: { ...settings.ai, explainReasoning: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="ai-evidence">Show Supporting Evidence</label>
                      <p>Include dataset references and statistical tables in insights</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="ai-evidence"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.ai.showEvidence}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            ai: { ...settings.ai, showEvidence: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="ai-assumptions">Show Assumptions</label>
                      <p>Explicitly list business and statistical assumptions</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="ai-assumptions"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.ai.showAssumptions}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            ai: { ...settings.ai, showAssumptions: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="ai-confidence">Show Confidence</label>
                      <p>Present statistical confidence scores and margin of error</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="ai-confidence"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.ai.showConfidence}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            ai: { ...settings.ai, showConfidence: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="ai-recs">Generate Recommendations</label>
                      <p>Provide actionable prescriptive interventions with timeframe and impact</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="ai-recs"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.ai.generateRecommendations}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            ai: { ...settings.ai, generateRecommendations: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>
                </div>
              )}

              {/* ── 4. Data & Analysis ── */}
              {activeCategory === 'data' && (
                <div className="settings-category-body">
                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="data-preview">Default Preview Rows</label>
                      <p>Number of dataset rows initially rendered in preview grid</p>
                    </div>
                    <select
                      id="data-preview"
                      className="settings-select"
                      value={settings.data.previewRows}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          data: { ...settings.data, previewRows: Number(e.target.value) as PreviewRowsOption },
                        })
                      }
                    >
                      <option value={50}>50 rows</option>
                      <option value={100}>100 rows (Recommended)</option>
                      <option value={250}>250 rows</option>
                      <option value={500}>500 rows</option>
                    </select>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="data-types">Automatically Detect Data Types</label>
                      <p>Infer categorical, temporal, and numeric schemas on upload</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="data-types"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.data.autoDetectTypes}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            data: { ...settings.data, autoDetectTypes: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="data-insights">Automatically Generate Insights</label>
                      <p>Trigger automated preliminary EDA when dataset validation completes</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="data-insights"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.data.autoGenerateInsights}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            data: { ...settings.data, autoGenerateInsights: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="data-viz">Automatically Generate Visualizations</label>
                      <p>Synthesize chart distributions and choropleths during analysis</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="data-viz"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.data.autoGenerateVisualizations}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            data: { ...settings.data, autoGenerateVisualizations: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="data-history">Save Analysis History</label>
                      <p>Archive conversation steps and analysis queries for replay</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="data-history"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.data.saveAnalysisHistory}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            data: { ...settings.data, saveAnalysisHistory: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="data-retain">Retain Uploaded Datasets</label>
                      <p>Persist uploaded CSV and tabular files in project storage</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="data-retain"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.data.retainDatasets}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            data: { ...settings.data, retainDatasets: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>
                </div>
              )}

              {/* ── 5. Notifications ── */}
              {activeCategory === 'notifications' && (
                <div className="settings-category-body">
                  <div className="settings-subgroup-title">Analysis Alerts</div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="notif-analysis">Analysis Completed</label>
                      <p>Receive notice when a long-running statistical analysis finishes</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="notif-analysis"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.notifications.analysisCompleted}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            notifications: { ...settings.notifications, analysisCompleted: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="notif-dataset">Dataset Processing</label>
                      <p>Alert when schema validation and row ingestion finish</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="notif-dataset"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.notifications.datasetProcessing}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            notifications: { ...settings.notifications, datasetProcessing: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-subgroup-title">Reports</div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="notif-report">Report Generated</label>
                      <p>Notify when executive business report compilation completes</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="notif-report"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.notifications.reportGenerated}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            notifications: { ...settings.notifications, reportGenerated: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="notif-report-fail">Report Generation Failed</label>
                      <p>Urgent notice if an executive report compilation encounters errors</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="notif-report-fail"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.notifications.reportGenerationFailed}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            notifications: { ...settings.notifications, reportGenerationFailed: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-subgroup-title">System Notices</div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="notif-sys">System Notifications</label>
                      <p>Maintenance windows, storage limit warnings, and security events</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="notif-sys"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.notifications.systemNotifications}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            notifications: { ...settings.notifications, systemNotifications: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="notif-prod">Product Updates</label>
                      <p>Announcements about new AI models and chart visualization types</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="notif-prod"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.notifications.productUpdates}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            notifications: { ...settings.notifications, productUpdates: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>
                </div>
              )}

              {/* ── 6. Integrations ── */}
              {activeCategory === 'integrations' && (
                <div className="settings-category-body">
                  <div className="settings-integration-list">
                    <div className="settings-integration-item">
                      <div className="settings-integration-meta">
                        <div className="settings-integration-badge">Google Drive</div>
                        <div>
                          <div className="settings-integration-title">Google Drive Connector</div>
                          <p className="settings-integration-desc">
                            Directly synchronize CSV spreadsheets and data folders from Google Workspace.
                          </p>
                        </div>
                      </div>
                      <div className="settings-integration-action">
                        <span className="settings-status-tag">Not connected</span>
                        <button
                          type="button"
                          className="settings-btn-secondary"
                          onClick={() => showToast('Google Drive connector architecture scheduled for subsequent phase.', 'info')}
                        >
                          Connect
                        </button>
                      </div>
                    </div>

                    <div className="settings-integration-item">
                      <div className="settings-integration-meta">
                        <div className="settings-integration-badge">PostgreSQL</div>
                        <div>
                          <div className="settings-integration-title">Enterprise SQL Database</div>
                          <p className="settings-integration-desc">
                            Execute direct read-only analytical queries against PostgreSQL or MySQL instances.
                          </p>
                        </div>
                      </div>
                      <div className="settings-integration-action">
                        <span className="settings-status-tag">Not connected</span>
                        <button
                          type="button"
                          className="settings-btn-secondary"
                          onClick={() => showToast('Database connector architecture scheduled for subsequent phase.', 'info')}
                        >
                          Connect
                        </button>
                      </div>
                    </div>

                    <div className="settings-integration-item">
                      <div className="settings-integration-meta">
                        <div className="settings-integration-badge">REST API</div>
                        <div>
                          <div className="settings-integration-title">External Analytical APIs</div>
                          <p className="settings-integration-desc">
                            Ingest live streaming metrics via webhook endpoints and custom auth tokens.
                          </p>
                        </div>
                      </div>
                      <div className="settings-integration-action">
                        <span className="settings-status-tag">Not connected</span>
                        <button
                          type="button"
                          className="settings-btn-secondary"
                          onClick={() => showToast('External API connector architecture scheduled for subsequent phase.', 'info')}
                        >
                          Manage
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── 7. Privacy ── */}
              {activeCategory === 'privacy' && (
                <div className="settings-category-body">
                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="priv-analysis">Analysis History</label>
                      <p>Save previous dataset queries and analytical results for future reference</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="priv-analysis"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.privacy.saveAnalysisHistory}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            privacy: { ...settings.privacy, saveAnalysisHistory: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="priv-conv">Conversation History</label>
                      <p>Save chat turns with the AI Analyst to resume past threads</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="priv-conv"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.privacy.saveConversationHistory}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            privacy: { ...settings.privacy, saveConversationHistory: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="priv-context">Use Previous Analysis Context</label>
                      <p>Allow AI Data Analyst to use relevant previous analysis context when available</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="priv-context"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.privacy.usePreviousAnalysisContext}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            privacy: { ...settings.privacy, usePreviousAnalysisContext: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>
                </div>
              )}

              {/* ── 8. Advanced ── */}
              {activeCategory === 'advanced' && (
                <div className="settings-category-body">
                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="adv-render">Enable Optimized Rendering</label>
                      <p>Use hardware-accelerated canvas transforms and SVG virtualization</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="adv-render"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.advanced.optimizedRendering}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            advanced: { ...settings.advanced, optimizedRendering: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label htmlFor="adv-exp">Experimental Features</label>
                      <p>Preview developmental visualizations and beta statistical forecasts</p>
                    </div>
                    <label className="settings-toggle-wrapper">
                      <input
                        id="adv-exp"
                        type="checkbox"
                        className="settings-toggle-input"
                        checked={settings.advanced.experimentalFeatures}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            advanced: { ...settings.advanced, experimentalFeatures: e.target.checked },
                          })
                        }
                      />
                      <span className="settings-toggle-switch" aria-hidden="true" />
                    </label>
                  </div>

                  <div className="settings-control-group">
                    <div className="settings-control-meta">
                      <label>Diagnostic Information</label>
                      <p>Inspect client application runtime variables and rendering parameters</p>
                    </div>
                    <button
                      type="button"
                      className="settings-btn-secondary"
                      onClick={() => setIsDebugModalOpen(true)}
                    >
                      <Terminal size={14} />
                      View Diagnostics
                    </button>
                  </div>

                  <div className="settings-reset-card">
                    <div>
                      <div className="settings-reset-title">Reset Settings</div>
                      <p className="settings-reset-desc">
                        Restore all application preferences to factory default values.
                        Your datasets, reports, analyses, and account credentials are preserved.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="settings-btn-warning"
                      onClick={() => setIsResetModalOpen(true)}
                    >
                      <RotateCcw size={14} />
                      Reset Settings
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Panel Footer Actions (Only for configurable categories) */}
            {activeCategory !== 'integrations' && (
              <div className="settings-panel-footer">
                <div className="settings-dirty-status">
                  {isCategoryDirty() ? (
                    <span className="settings-dirty-badge">Unsaved changes in this category</span>
                  ) : (
                    <span className="settings-clean-badge">All changes saved</span>
                  )}
                </div>

                <div className="settings-actions-group">
                  <button
                    type="button"
                    className="settings-btn-secondary"
                    onClick={handleCancel}
                    disabled={!isCategoryDirty() || saving}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="settings-btn-primary"
                    onClick={handleSave}
                    disabled={saving}
                  >
                    {saving ? (
                      <>
                        <Loader2 size={14} className="settings-spinner" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save size={14} />
                        Save Changes
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Confirmation & Diagnostic Modals */}
      <ResetSettingsModal
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
        onConfirmReset={handleConfirmReset}
      />

      <DebugInfoModal
        isOpen={isDebugModalOpen}
        onClose={() => setIsDebugModalOpen(false)}
      />
    </div>
  );
}
