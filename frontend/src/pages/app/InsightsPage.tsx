import { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Lightbulb, 
  RotateCw, 
  Filter, 
  Database, 
  Calendar, 
  AlertOctagon, 
  TrendingUp, 
  Sliders, 
  CheckCircle2, 
  ShieldAlert, 
  Layers, 
  ArrowUpRight, 
  ArrowDownRight, 
  Minus,
  Sparkles,
  HelpCircle
} from 'lucide-react';

import type { 
  Insight, 
  Risk, 
  Opportunity, 
  Recommendation, 
  BusinessHealthMetric, 
  InsightType,
  VisualizationReference,
  ScenarioProjection,
  ScenarioInputVariables
} from '../../types/insights';

import {
  getInsights,
  getBusinessHealth,
  getRisks,
  getOpportunities,
  getRecommendations,
} from '../../services/insightsService';

import { InsightCard } from '../../components/insights/InsightCard';
import { RiskCard, OpportunityCard } from '../../components/insights/RiskAndOpportunityCards';
import { RecommendationCard } from '../../components/insights/RecommendationCard';
import { EvidencePanel, type ExplainableItem } from '../../components/insights/EvidencePanel';
import { WhatIfSimulator } from '../../components/insights/WhatIfSimulator';

interface InsightsPageProps {
  subView?: 'overview' | 'what-if';
}

type TabType = 'overview' | 'insights' | 'risks-opportunities' | 'recommendations' | 'what-if';

export default function InsightsPage({ subView }: InsightsPageProps) {
  const location = useLocation();
  const navigate = useNavigate();

  // Detect initial tab from path or prop
  const isDirectWhatIfRoute = subView === 'what-if' || location.pathname === '/insights/what-if';
  const [selectedTab, setSelectedTab] = useState<TabType | null>(null);
  const activeTab: TabType = isDirectWhatIfRoute ? 'what-if' : (selectedTab ?? 'overview');

  const setActiveTab = (tab: TabType) => {
    if (isDirectWhatIfRoute && tab !== 'what-if') {
      navigate('/insights');
    }
    setSelectedTab(tab);
  };

  // Filter state
  const [selectedDataset, setSelectedDataset] = useState<'sales' | 'marketing'>('sales');
  const [dateRange, setDateRange] = useState<string>('Last 30 Days');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<InsightType | 'all'>('all');

  // Data state
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [healthMetrics, setHealthMetrics] = useState<BusinessHealthMetric[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  // Explainability drawer state
  const [drawerItem, setDrawerItem] = useState<ExplainableItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  // Prepopulated scenario state for what-if handoff
  const [simulatorInitialVars, setSimulatorInitialVars] = useState<Partial<ScenarioInputVariables>>({});

  // Fetch data effect with cancel guard
  useEffect(() => {
    let ignore = false;

    const fetchData = async () => {
      try {
        const [h, ins, r, opp, rec] = await Promise.all([
          getBusinessHealth(selectedDataset),
          getInsights(selectedDataset, dateRange),
          getRisks(selectedDataset),
          getOpportunities(selectedDataset),
          getRecommendations(selectedDataset),
        ]);
        if (!ignore) {
          setHealthMetrics(h);
          setInsights(ins);
          setRisks(r);
          setOpportunities(opp);
          setRecommendations(rec);
          setIsLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          console.error('Failed to load insights:', err);
          setError('Could not retrieve decision intelligence data. Please retry or select another dataset.');
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      ignore = true;
    };
  }, [selectedDataset, dateRange]);

  // Explicit user refresh callback
  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [h, ins, r, opp, rec] = await Promise.all([
        getBusinessHealth(selectedDataset),
        getInsights(selectedDataset, dateRange),
        getRisks(selectedDataset),
        getOpportunities(selectedDataset),
        getRecommendations(selectedDataset),
      ]);
      setHealthMetrics(h);
      setInsights(ins);
      setRisks(r);
      setOpportunities(opp);
      setRecommendations(rec);
    } catch (err) {
      console.error('Failed to refresh insights:', err);
      setError('Could not retrieve decision intelligence data. Please retry or select another dataset.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedDataset, dateRange]);

  // Drawer handlers
  const handleOpenEvidence = (item: ExplainableItem) => {
    setDrawerItem(item);
    setIsDrawerOpen(true);
  };

  const handleCloseEvidence = () => {
    setIsDrawerOpen(false);
    setDrawerItem(null);
  };

  // Hand-off handlers
  const handleOpenVisualization = (refOrInsight: VisualizationReference | Insight) => {
    const ref = 'chartType' in refOrInsight ? refOrInsight : refOrInsight.visualizationReference;
    if (!ref) return;

    navigate('/visualizations', {
      state: {
        dataset: selectedDataset === 'sales' ? 'Global Superstore Sales' : 'Ad Campaign Performance',
        chartType: ref.chartType,
        xAxis: ref.xAxis,
        yAxis: ref.yAxis,
        highlightTitle: ref.title,
      },
    });
  };

  const handleAskAI = (item: ExplainableItem) => {
    const itemSummary =
      'summary' in item && item.summary
        ? item.summary
        : 'rationale' in item
        ? (item as Recommendation).rationale
        : '';
    const prompt = `Can you provide a deep-dive analysis and actionable next steps on the following insight: "${item.title}"? Context: ${itemSummary}`;
    navigate('/analysis', {
      state: {
        question: prompt,
        dataset: selectedDataset === 'sales' ? 'Global Superstore Sales' : 'Ad Campaign Performance',
      },
    });
  };

  const handleSimulateFromRecommendation = (rec: Recommendation) => {
    if (rec.scenarioVariables) {
      setSimulatorInitialVars(rec.scenarioVariables);
    }
    setActiveTab('what-if');
  };

  const handleSimulateFromOpportunity = (opp: Opportunity) => {
    setSimulatorInitialVars({
      marketingSpendDeltaPct: opp.potentialUpside ? 25 : 15,
      priceAdjustmentPct: 5,
      churnRateDeltaPct: -5,
    });
    setActiveTab('what-if');
  };

  const handleSimulatorAskAI = (projection: ScenarioProjection, vars: ScenarioInputVariables) => {
    const spend = vars.marketingSpendDeltaPct ?? vars.marketingSpendDelta;
    const price = vars.priceAdjustmentPct ?? vars.priceDelta;
    const prompt = `I ran a What-If scenario with ${spend >= 0 ? '+' : ''}${spend}% marketing spend and ${price >= 0 ? '+' : ''}${price}% price adjustment. The projected revenue is ${projection.projectedRevenue.projected} (${projection.netImpact} net impact). What are the main operational risks and sensitivity factors?`;
    navigate('/analysis', {
      state: {
        question: prompt,
        dataset: selectedDataset === 'sales' ? 'Global Superstore Sales' : 'Ad Campaign Performance',
      },
    });
  };

  // Filtered insights list
  const filteredInsights = insights.filter((ins) => {
    if (selectedTypeFilter === 'all') return true;
    return ins.type === selectedTypeFilter;
  });

  return (
    <div className="ws-page insights-page-root">
      {/* 1. Header & Context Control Strip */}
      <header className="insights-header">
        <div className="insights-header-left">
          <div className="insights-header-badge">
            <Sparkles size={13} />
            <span>Decision Intelligence</span>
          </div>
          <h1 className="ws-page-heading">Insights & Decision Intelligence</h1>
          <p className="ws-page-sub">
            Evidence-backed business insights, risk factors, growth opportunities, and forward-looking scenario simulations.
          </p>
        </div>

        <div className="insights-controls-bar">
          {/* Dataset Selector */}
          <div className="insights-control-group">
            <Database size={13} className="insights-control-icon" />
            <select
              aria-label="Dataset Source"
              className="insights-select-pill"
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value as 'sales' | 'marketing')}
            >
              <option value="sales">Sales Performance Dataset (Active)</option>
              <option value="marketing">Marketing & Ad Campaign Dataset</option>
            </select>
          </div>

          {/* Date Range Selector */}
          <div className="insights-control-group">
            <Calendar size={13} className="insights-control-icon" />
            <select
              aria-label="Date Range Scope"
              className="insights-select-pill"
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
            >
              <option value="Last 30 Days">Last 30 Days</option>
              <option value="Last 90 Days (Q3)">Last 90 Days (Q3)</option>
              <option value="Year to Date (2024)">Year to Date (2024)</option>
              <option value="All Time">All Available Data</option>
            </select>
          </div>

          {/* Refresh Action */}
          <button
            type="button"
            className={`insights-refresh-btn ${isLoading ? 'loading' : ''}`}
            onClick={handleRefresh}
            disabled={isLoading}
            title="Refresh insights and recompute models"
          >
            <RotateCw size={13} />
            <span>{isLoading ? 'Recomputing...' : 'Refresh'}</span>
          </button>
        </div>
      </header>

      {/* 2. Top Navigation Tabs */}
      <nav className="insights-nav-tabs" aria-label="Insights Sub-navigation">
        <button
          type="button"
          className={`insights-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <Layers size={14} />
          <span>Executive Overview</span>
        </button>

        <button
          type="button"
          className={`insights-tab-btn ${activeTab === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveTab('insights')}
        >
          <Lightbulb size={14} />
          <span>Key Insights ({insights.length})</span>
        </button>

        <button
          type="button"
          className={`insights-tab-btn ${activeTab === 'risks-opportunities' ? 'active' : ''}`}
          onClick={() => setActiveTab('risks-opportunities')}
        >
          <AlertOctagon size={14} />
          <span>Risks & Opportunities</span>
        </button>

        <button
          type="button"
          className={`insights-tab-btn ${activeTab === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveTab('recommendations')}
        >
          <CheckCircle2 size={14} />
          <span>Action Recommendations ({recommendations.length})</span>
        </button>

        <button
          type="button"
          className={`insights-tab-btn what-if-tab ${activeTab === 'what-if' ? 'active' : ''}`}
          onClick={() => setActiveTab('what-if')}
        >
          <Sliders size={14} />
          <span>What-If Analysis Engine</span>
        </button>
      </nav>

      {/* 3. Error Banner */}
      {error && (
        <div className="insights-error-banner" role="alert">
          <ShieldAlert size={18} />
          <div>
            <strong>Computation Error:</strong> {error}
          </div>
          <button type="button" onClick={handleRefresh} className="insights-error-retry">
            Retry
          </button>
        </div>
      )}

      {/* 4. Loading Skeleton State */}
      {isLoading && (
        <div className="insights-loading-state" aria-busy="true">
          <div className="insights-kpi-grid skeleton-pulse">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="insights-kpi-card skeleton" />
            ))}
          </div>
          <div className="insights-section-skeleton skeleton-pulse" />
        </div>
      )}

      {/* 5. Main View Content */}
      {!isLoading && !error && (
        <div className="insights-content-body">
          {/* TAB: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="insights-overview-view">
              {/* Business Health KPI Strip */}
              <section className="insights-section">
                <div className="insights-section-title-bar">
                  <h2 className="insights-section-title">Business Health Summary</h2>
                  <span className="insights-section-badge">Verified Metrics</span>
                </div>
                <div className="insights-kpi-grid">
                  {healthMetrics.map((metric) => (
                    <div key={metric.id} className="insights-kpi-card">
                      <div className="insights-kpi-top">
                        <span className="insights-kpi-label">{metric.label}</span>
                        {metric.trend && (
                          <span className={`insights-kpi-trend ${metric.direction || 'neutral'}`}>
                            {metric.direction === 'up' && <ArrowUpRight size={12} />}
                            {metric.direction === 'down' && <ArrowDownRight size={12} />}
                            {metric.direction === 'neutral' && <Minus size={12} />}
                            {metric.trend}
                          </span>
                        )}
                      </div>
                      <div className="insights-kpi-value">{metric.value}</div>
                      {metric.subValue && (
                        <div className="insights-kpi-sub">{metric.subValue}</div>
                      )}
                    </div>
                  ))}
                </div>
              </section>

              {/* Top Key Insights Preview */}
              <section className="insights-section">
                <div className="insights-section-title-bar">
                  <div>
                    <h2 className="insights-section-title">Top Detected Insights</h2>
                    <p className="insights-section-sub">
                      Empirical data observations paired with explainable AI interpretations.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="insights-link-btn"
                    onClick={() => setActiveTab('insights')}
                  >
                    View All ({insights.length}) →
                  </button>
                </div>
                <div className="insights-cards-grid">
                  {insights.slice(0, 2).map((ins) => (
                    <InsightCard
                      key={ins.id}
                      insight={ins}
                      onViewEvidence={handleOpenEvidence}
                      onOpenVisualization={handleOpenVisualization}
                      onAskAI={handleAskAI}
                    />
                  ))}
                </div>
              </section>

              {/* Risks & Opportunities 2-Column Split */}
              <section className="insights-section">
                <div className="insights-section-title-bar">
                  <div>
                    <h2 className="insights-section-title">Risks & Strategic Opportunities</h2>
                    <p className="insights-section-sub">
                      Proactively detect revenue leakage and high-probability expansion vectors.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="insights-link-btn"
                    onClick={() => setActiveTab('risks-opportunities')}
                  >
                    Full Analysis →
                  </button>
                </div>
                <div className="insights-two-col-grid">
                  {/* Left Column: Top Risk */}
                  <div className="insights-col">
                    <div className="insights-col-header">
                      <AlertOctagon size={16} className="text-red" />
                      <h3>Critical Risk Item</h3>
                    </div>
                    {risks.slice(0, 1).map((r) => (
                      <RiskCard
                        key={r.id}
                        risk={r}
                        onViewEvidence={handleOpenEvidence}
                        onAskAI={handleAskAI}
                      />
                    ))}
                  </div>

                  {/* Right Column: Top Opportunity */}
                  <div className="insights-col">
                    <div className="insights-col-header">
                      <TrendingUp size={16} className="text-green" />
                      <h3>Highest Leverage Opportunity</h3>
                    </div>
                    {opportunities.slice(0, 1).map((opp) => (
                      <OpportunityCard
                        key={opp.id}
                        opportunity={opp}
                        onViewEvidence={handleOpenEvidence}
                        onRunScenario={handleSimulateFromOpportunity}
                        onAskAI={handleAskAI}
                      />
                    ))}
                  </div>
                </div>
              </section>

              {/* What-If Scenario Modeling (Compact Preview) */}
              <section className="insights-section">
                <div className="insights-section-title-bar">
                  <div>
                    <h2 className="insights-section-title">Decision Intelligence Simulation</h2>
                    <p className="insights-section-sub">
                      Simulate the impact of price or marketing changes before making financial commitments.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="insights-link-btn"
                    onClick={() => setActiveTab('what-if')}
                  >
                    Open Full Simulator →
                  </button>
                </div>
                <WhatIfSimulator
                  datasetId={selectedDataset}
                  onAskAI={handleSimulatorAskAI}
                  isCompact={true}
                />
              </section>
            </div>
          )}

          {/* TAB: KEY INSIGHTS */}
          {activeTab === 'insights' && (
            <div className="insights-tab-content">
              {/* Filter Pills */}
              <div className="insights-filter-bar">
                <div className="insights-filter-label">
                  <Filter size={13} />
                  <span>Filter by Insight Type:</span>
                </div>
                <div className="insights-filter-pills">
                  {(['all', 'trend', 'pattern', 'anomaly', 'driver', 'change', 'correlation'] as const).map(
                    (type) => (
                      <button
                        key={type}
                        type="button"
                        className={`insights-filter-pill ${selectedTypeFilter === type ? 'active' : ''}`}
                        onClick={() => setSelectedTypeFilter(type)}
                      >
                        {type === 'all' ? 'All Types' : type.charAt(0).toUpperCase() + type.slice(1)}
                      </button>
                    )
                  )}
                </div>
              </div>

              {filteredInsights.length === 0 ? (
                <div className="insights-empty-state">
                  <Lightbulb size={32} />
                  <h3>No Insights Found</h3>
                  <p>No insights matched the selected filter criteria. Try selecting another filter or dataset.</p>
                </div>
              ) : (
                <div className="insights-cards-grid">
                  {filteredInsights.map((ins) => (
                    <InsightCard
                      key={ins.id}
                      insight={ins}
                      onViewEvidence={handleOpenEvidence}
                      onOpenVisualization={handleOpenVisualization}
                      onAskAI={handleAskAI}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB: RISKS & OPPORTUNITIES */}
          {activeTab === 'risks-opportunities' && (
            <div className="insights-tab-content">
              <div className="insights-two-col-grid">
                {/* Left Column: Risks */}
                <div className="insights-col">
                  <div className="insights-col-header">
                    <AlertOctagon size={16} className="text-red" />
                    <div>
                      <h3>Detected Risks & Vulnerabilities ({risks.length})</h3>
                      <p className="insights-col-sub">Structural risks identified through anomaly detection & trend analysis.</p>
                    </div>
                  </div>
                  <div className="insights-cards-col-stack">
                    {risks.map((risk) => (
                      <RiskCard
                        key={risk.id}
                        risk={risk}
                        onViewEvidence={handleOpenEvidence}
                        onAskAI={handleAskAI}
                      />
                    ))}
                  </div>
                </div>

                {/* Right Column: Opportunities */}
                <div className="insights-col">
                  <div className="insights-col-header">
                    <TrendingUp size={16} className="text-green" />
                    <div>
                      <h3>Growth & Expansion Opportunities ({opportunities.length})</h3>
                      <p className="insights-col-sub">High-efficiency pockets and under-monetized market segments.</p>
                    </div>
                  </div>
                  <div className="insights-cards-col-stack">
                    {opportunities.map((opp) => (
                      <OpportunityCard
                        key={opp.id}
                        opportunity={opp}
                        onViewEvidence={handleOpenEvidence}
                        onRunScenario={handleSimulateFromOpportunity}
                        onAskAI={handleAskAI}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB: RECOMMENDATIONS */}
          {activeTab === 'recommendations' && (
            <div className="insights-tab-content">
              <div className="insights-rec-header-note">
                <HelpCircle size={14} />
                <span>
                  All recommendations are backed by factual data points and transparent boundary conditions. Review assumptions before execution.
                </span>
              </div>
              <div className="insights-cards-grid">
                {recommendations.map((rec) => (
                  <RecommendationCard
                    key={rec.id}
                    recommendation={rec}
                    onViewEvidence={handleOpenEvidence}
                    onRunScenario={handleSimulateFromRecommendation}
                    onAskAI={handleAskAI}
                  />
                ))}
              </div>
            </div>
          )}

          {/* TAB: WHAT-IF SIMULATOR */}
          {activeTab === 'what-if' && (
            <div className="insights-tab-content">
              <WhatIfSimulator
                datasetId={selectedDataset}
                initialVariables={simulatorInitialVars}
                onAskAI={handleSimulatorAskAI}
                isCompact={false}
              />
            </div>
          )}
        </div>
      )}

      {/* 6. Explainability & Evidence Drawer */}
      <EvidencePanel
        isOpen={isDrawerOpen}
        item={drawerItem}
        datasetName={selectedDataset === 'sales' ? 'Global Superstore Sales Dataset' : 'Ad Campaign Spend & Performance'}
        timePeriod={dateRange}
        onClose={handleCloseEvidence}
        onOpenVisualization={handleOpenVisualization}
        onAskAI={handleAskAI}
      />
    </div>
  );
}
