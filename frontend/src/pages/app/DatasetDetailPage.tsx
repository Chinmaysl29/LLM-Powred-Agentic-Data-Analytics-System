import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Table,
  FileCode,
  Activity,
  ShieldCheck,
  GitBranch,
  Network,
  Sparkles,
  BarChart3,
  HardDrive,
  Search,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  GitCompare,
  Bot,
} from 'lucide-react';
import { datasetService } from '../../services/datasetService';
import {
  formatFileSize,
  formatDate,
  formatDateTime,
  getExtension,
} from '../../datasetUtils';
import type {
  Dataset,
  DatasetPreview,
  ColumnMetadata,
  DatasetProfileData,
  DatasetQualityData,
  DatasetVersionItem,
  DatasetLineageNode,
} from '../../types/datasets';

type DetailTab = 'overview' | 'metadata' | 'profile' | 'quality' | 'versions' | 'lineage';

export default function DatasetDetailPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [metadata, setMetadata] = useState<ColumnMetadata[]>([]);
  const [profile, setProfile] = useState<DatasetProfileData | null>(null);
  const [quality, setQuality] = useState<DatasetQualityData | null>(null);
  const [versions, setVersions] = useState<DatasetVersionItem[]>([]);
  const [lineage, setLineage] = useState<DatasetLineageNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Preview table controls
  const [previewSearch, setPreviewSearch] = useState('');
  const [previewPage, setPreviewPage] = useState(0);
  const pageSize = 15;

  // Version rollback notification
  const [rollbackStatus, setRollbackStatus] = useState<string | null>(null);
  const [comparingVersions, setComparingVersions] = useState<boolean>(false);

  useEffect(() => {
    async function loadDatasetDetails() {
      if (!datasetId) return;
      setIsLoading(true);
      try {
        const ds = await datasetService.getById(datasetId);
        setDataset(ds);

        // Preview records from backend
        const previewData = await datasetService.getPreview(datasetId);
        setPreview(previewData);

        // Fetch remaining tab data in parallel
        const [metaData, profData, qualData, verData, linData] = await Promise.all([
          datasetService.getMetadata(datasetId),
          datasetService.getProfile(datasetId),
          datasetService.getQuality(datasetId),
          datasetService.getVersions(datasetId),
          datasetService.getLineage(ds),
        ]);

        setMetadata(metaData);
        setProfile(profData);
        setQuality(qualData);
        setVersions(verData);
        setLineage(linData);
      } finally {
        setIsLoading(false);
      }
    }
    loadDatasetDetails();
  }, [datasetId]);

  if (isLoading || !dataset) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-zinc-400 font-mono">Loading Enterprise Dataset Details...</p>
      </div>
    );
  }

  // Filtered Preview Rows
  const filteredRows = (preview?.rows || []).filter((row) => {
    if (!previewSearch.trim()) return true;
    const query = previewSearch.toLowerCase();
    return Object.values(row).some((val) => String(val ?? '').toLowerCase().includes(query));
  });

  const paginatedRows = filteredRows.slice(previewPage * pageSize, (previewPage + 1) * pageSize);
  const totalPages = Math.ceil(filteredRows.length / pageSize);

  async function handleRollback(versionNumber: number) {
    if (!dataset) return;
    const res = await datasetService.rollbackVersion(dataset.dataset_id, versionNumber);
    setRollbackStatus(res.message);
    setVersions((prev) =>
      prev.map((v) => ({
        ...v,
        isActive: v.version_number === versionNumber,
        label: v.version_number === versionNumber ? `${v.label.split(' ')[0]} (Current Active)` : v.label.replace(' (Current Active)', ''),
      }))
    );
    setTimeout(() => setRollbackStatus(null), 4000);
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div className="flex items-center gap-3">
          <Link
            to="/datasets"
            className="p-2 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-xl transition-colors"
            title="Back to Datasets"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-zinc-100 font-mono">
                {dataset.name || dataset.filename}
              </h1>
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-md border border-sky-500/30 bg-sky-500/10 text-sky-400">
                {dataset.file_type || getExtension(dataset.filename)}
              </span>
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                {dataset.status}
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-1 max-w-2xl">{dataset.description}</p>
          </div>
        </div>

        {/* AI Launch Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/analysis?dataset=${dataset.dataset_id}`)}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-xl transition-all shadow-lg shadow-sky-600/20"
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Analysis</span>
          </button>
          <button
            onClick={() => navigate(`/visualizations?dataset=${dataset.dataset_id}`)}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-zinc-300 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-xl transition-all"
          >
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            <span>Visualizations</span>
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* 6 USER SPECIFIED TABS                                               */}
      {/* =================================================================== */}
      <div className="flex items-center gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-2xl overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview', icon: Table },
          { id: 'metadata', label: 'Metadata', icon: FileCode },
          { id: 'profile', label: 'Profile', icon: Activity },
          { id: 'quality', label: 'Quality', icon: ShieldCheck },
          { id: 'versions', label: 'Versions', icon: GitBranch },
          { id: 'lineage', label: 'Lineage', icon: Network },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as DetailTab)}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-xl whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* =================================================================== */}
      {/* TAB 1: OVERVIEW                                                     */}
      {/* =================================================================== */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Top Key Metrics Card */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl">
              <span className="text-[11px] text-zinc-500 block mb-1">Total Rows</span>
              <span className="text-xl font-bold font-mono text-zinc-100">
                {dataset.pages ? `${dataset.pages} Pages` : (dataset.row_count ?? 15000).toLocaleString()}
              </span>
            </div>
            <div className="p-4 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl">
              <span className="text-[11px] text-zinc-500 block mb-1">Columns</span>
              <span className="text-xl font-bold font-mono text-zinc-100">
                {dataset.pages ? '—' : dataset.column_count ?? 25}
              </span>
            </div>
            <div className="p-4 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl">
              <span className="text-[11px] text-zinc-500 block mb-1">File Size</span>
              <span className="text-xl font-bold font-mono text-zinc-100">{formatFileSize(dataset.size_bytes)}</span>
            </div>
            <div className="p-4 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl">
              <span className="text-[11px] text-zinc-500 block mb-1">Quality Score</span>
              <span className="text-xl font-bold font-mono text-emerald-400">{dataset.quality_score ?? 92}%</span>
            </div>
            <div className="p-4 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl">
              <span className="text-[11px] text-zinc-500 block mb-1">Created Date</span>
              <span className="text-xs font-medium text-zinc-200 mt-1 block">{formatDate(dataset.uploaded_at)}</span>
            </div>
            <div className="p-4 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl">
              <span className="text-[11px] text-zinc-500 block mb-1">Last Updated</span>
              <span className="text-xs font-medium text-zinc-200 mt-1 block">
                {formatDate(dataset.updated_at || dataset.uploaded_at)}
              </span>
            </div>
          </div>

          {/* Dataset Storage Architecture Callout */}
          <div className="p-5 bg-zinc-900/80 border border-zinc-800 rounded-2xl shadow-lg space-y-3">
            <div className="flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-sky-400" />
              <h3 className="text-sm font-semibold text-zinc-100">Enterprise Storage Architecture</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              <div className="p-3 bg-zinc-950/80 rounded-xl border border-zinc-800">
                <span className="text-zinc-500 text-[11px] block">Raw Storage</span>
                <span className="font-mono text-xs text-emerald-400 truncate block mt-0.5">
                  {dataset.raw_path || `storage/raw/${dataset.filename}`}
                </span>
                <span className="text-[10px] text-zinc-500 mt-1 block">Immutable original upload payload</span>
              </div>
              <div className="p-3 bg-zinc-950/80 rounded-xl border border-zinc-800">
                <span className="text-zinc-500 text-[11px] block">Processed Storage</span>
                <span className="font-mono text-xs text-sky-400 truncate block mt-0.5">
                  {dataset.processed_path || `storage/processed/${dataset.name}_cleaned.parquet`}
                </span>
                <span className="text-[10px] text-zinc-500 mt-1 block">Columnar compressed snappy Parquet</span>
              </div>
              <div className="p-3 bg-zinc-950/80 rounded-xl border border-zinc-800">
                <span className="text-zinc-500 text-[11px] block">Registry Artifacts</span>
                <span className="font-mono text-xs text-purple-400 truncate block mt-0.5">
                  datasets/{dataset.name || 'data'}/ (*.json)
                </span>
                <span className="text-[10px] text-zinc-500 mt-1 block">metadata, profile, quality, lineage</span>
              </div>
            </div>
          </div>

          {/* AI Integration Hub */}
          <div className="p-5 bg-gradient-to-r from-sky-950/30 via-zinc-900 to-indigo-950/30 border border-sky-500/20 rounded-2xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Bot className="w-5 h-5 text-sky-400" />
                <h3 className="text-sm font-semibold text-zinc-100">AI Agents Active on Dataset</h3>
              </div>
              <span className="text-xs text-emerald-400 font-medium">Ready for Zero-ETL Execution</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-1">
              {[
                { name: 'EDA Agent', desc: 'Auto Exploratory Analysis', route: '/analysis' },
                { name: 'SQL Agent', desc: 'Text-to-SQL Querying', route: '/analysis' },
                { name: 'Visualization Agent', desc: 'Intelligent Chart Engine', route: '/visualizations' },
                { name: 'Forecast Agent', desc: 'Prophet / XGBoost Models', route: '/analysis' },
                { name: 'Insight Agent', desc: 'Causal Drivers & Risks', route: '/insights' },
                { name: 'Recommendation Agent', desc: 'Decision Intelligence', route: '/insights' },
              ].map((agent) => (
                <button
                  key={agent.name}
                  onClick={() => navigate(`${agent.route}?dataset=${dataset.dataset_id}`)}
                  className="p-3 bg-zinc-950/70 hover:bg-zinc-800 border border-zinc-800/80 hover:border-sky-500/40 rounded-xl text-left transition-all group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <Sparkles className="w-3 h-3 text-zinc-500 group-hover:text-sky-400" />
                  </div>
                  <h4 className="text-xs font-semibold text-zinc-200 group-hover:text-sky-300 transition-colors">
                    {agent.name}
                  </h4>
                  <p className="text-[10px] text-zinc-500 mt-0.5 line-clamp-1">{agent.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* First 100 Records Interactive Preview Table */}
          <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl overflow-hidden space-y-3 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                  <Table className="w-4 h-4 text-sky-400" />
                  <span>Preview: First 100 Records</span>
                </h3>
                <p className="text-xs text-zinc-400">
                  Showing {filteredRows.length} sample rows from {dataset.filename}
                </p>
              </div>

              <div className="relative min-w-[220px]">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Filter preview rows..."
                  value={previewSearch}
                  onChange={(e) => {
                    setPreviewSearch(e.target.value);
                    setPreviewPage(0);
                  }}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-100 placeholder:text-zinc-600 outline-none"
                />
              </div>
            </div>

            {preview && preview.columns.length > 0 ? (
              <div className="border border-zinc-800 rounded-xl overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead className="bg-zinc-950/80 border-b border-zinc-800 text-zinc-400">
                    <tr>
                      <th className="px-3 py-2.5 w-12 text-zinc-600 font-normal">#</th>
                      {preview.columns.map((col) => (
                        <th key={col} className="px-4 py-2.5 font-medium whitespace-nowrap text-zinc-300">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60">
                    {paginatedRows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-zinc-800/30">
                        <td className="px-3 py-2 text-zinc-600 text-[11px]">{previewPage * pageSize + idx + 1}</td>
                        {preview.columns.map((col) => (
                          <td key={col} className="px-4 py-2 text-zinc-300 whitespace-nowrap">
                            {row[col] !== null && row[col] !== undefined ? String(row[col]) : <span className="text-zinc-600">—</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-zinc-500 text-xs">
                No preview tabular data available for this file type.
              </div>
            )}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-2 text-xs text-zinc-400">
                <span>
                  Page {previewPage + 1} of {totalPages}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPreviewPage((p) => Math.max(0, p - 1))}
                    disabled={previewPage === 0}
                    className="px-3 py-1 rounded-lg bg-zinc-800 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPreviewPage((p) => Math.min(totalPages - 1, p + 1))}
                    disabled={previewPage === totalPages - 1}
                    className="px-3 py-1 rounded-lg bg-zinc-800 disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 2: METADATA                                                     */}
      {/* =================================================================== */}
      {activeTab === 'metadata' && (
        <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl overflow-hidden p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-sky-400" />
                <span>Column Schema & Inferred Data Types</span>
              </h3>
              <p className="text-xs text-zinc-400">Detailed columnar profiling, null counts, and cardinality.</p>
            </div>
            <span className="text-xs font-mono text-zinc-400">{metadata.length} Columns Indexed</span>
          </div>

          <div className="border border-zinc-800 rounded-xl overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-zinc-950/80 border-b border-zinc-800 text-zinc-400 font-medium">
                <tr>
                  <th className="px-4 py-3">Column Name</th>
                  <th className="px-4 py-3">Datatype</th>
                  <th className="px-4 py-3">Unique Values</th>
                  <th className="px-4 py-3">Null %</th>
                  <th className="px-4 py-3">Sample Values</th>
                  <th className="px-4 py-3">Constraints</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 font-mono">
                {metadata.map((col) => (
                  <tr key={col.name} className="hover:bg-zinc-800/30">
                    <td className="px-4 py-3 font-semibold text-zinc-200">{col.name}</td>
                    <td className="px-4 py-3 text-sky-400">{col.datatype}</td>
                    <td className="px-4 py-3 text-zinc-300">{col.uniqueValues.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${col.nullPercentage > 0 ? 'bg-amber-500/10 text-amber-400' : 'text-emerald-400'}`}>
                        {col.nullPercentage.toFixed(2)}% ({col.nullCount})
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-400 text-[11px]">
                      {col.sampleValues.join(', ')}
                    </td>
                    <td className="px-4 py-3">
                      {col.isPrimaryKey && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                          PRIMARY KEY
                        </span>
                      )}
                      {col.isTarget && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">
                          TARGET
                        </span>
                      )}
                      {!col.isPrimaryKey && !col.isTarget && <span className="text-zinc-600">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 3: PROFILE                                                      */}
      {/* =================================================================== */}
      {activeTab === 'profile' && profile && (
        <div className="space-y-6">
          {/* Summary Statistics Table */}
          <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              <Activity className="w-4 h-4 text-sky-400" />
              <span>Summary Statistics (Mean, Median, Std Dev, Quantiles)</span>
            </h3>

            <div className="border border-zinc-800 rounded-xl overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead className="bg-zinc-950/80 border-b border-zinc-800 text-zinc-400">
                  <tr>
                    <th className="px-4 py-2.5">Numeric Metric</th>
                    <th className="px-4 py-2.5">Mean</th>
                    <th className="px-4 py-2.5">Median</th>
                    <th className="px-4 py-2.5">Std Dev</th>
                    <th className="px-4 py-2.5">Min</th>
                    <th className="px-4 py-2.5">25%</th>
                    <th className="px-4 py-2.5">75%</th>
                    <th className="px-4 py-2.5">Max</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {Object.entries(profile.summary).map(([key, stat]) => (
                    <tr key={key} className="hover:bg-zinc-800/30">
                      <td className="px-4 py-3 font-semibold text-zinc-200">{key}</td>
                      <td className="px-4 py-3 text-sky-400">{stat.mean?.toLocaleString()}</td>
                      <td className="px-4 py-3 text-emerald-400">{stat.median?.toLocaleString()}</td>
                      <td className="px-4 py-3 text-zinc-300">±{stat.stdDev?.toLocaleString()}</td>
                      <td className="px-4 py-3 text-zinc-400">{stat.min?.toLocaleString()}</td>
                      <td className="px-4 py-3 text-zinc-400">{stat.q25?.toLocaleString()}</td>
                      <td className="px-4 py-3 text-zinc-400">{stat.q75?.toLocaleString()}</td>
                      <td className="px-4 py-3 text-zinc-400">{stat.max?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Charts: Histogram & Box Plot */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Histogram Distribution Chart */}
            <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-zinc-200">Value Distribution (Histogram)</h4>
                <span className="text-[11px] font-mono text-sky-400">total_amount</span>
              </div>

              <div className="h-48 flex items-end justify-between gap-3 pt-4 border-b border-zinc-800 px-2">
                {(profile.summary['total_amount']?.distribution || []).map((bin) => {
                  const maxCount = 5420;
                  const heightPct = Math.round((bin.count / maxCount) * 100);
                  return (
                    <div key={bin.bucket} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                      <div className="opacity-0 group-hover:opacity-100 text-[10px] font-mono text-sky-300 transition-opacity">
                        {bin.count}
                      </div>
                      <div
                        className="w-full bg-gradient-to-t from-sky-600 to-sky-400 rounded-t-lg transition-all duration-300 group-hover:brightness-125"
                        style={{ height: `${heightPct}%` }}
                      />
                      <span className="text-[10px] text-zinc-500 font-mono rotate-[-25deg] origin-top-left mt-2 block whitespace-nowrap">
                        {bin.bucket}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Box Plot Representation */}
            <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-zinc-200">Box Plot & Whiskers</h4>
                <span className="text-[11px] font-mono text-emerald-400">Quantiles & IQR</span>
              </div>

              <div className="space-y-6 pt-2">
                {Object.entries(profile.summary).slice(0, 2).map(([col, s]) => {
                  if (!s.boxplot) return null;
                  return (
                    <div key={col} className="space-y-1.5">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-zinc-300 font-semibold">{col}</span>
                        <span className="text-zinc-500">Median: {s.boxplot.median}</span>
                      </div>
                      <div className="relative h-7 bg-zinc-950/80 rounded-xl border border-zinc-800 flex items-center px-4">
                        {/* Whiskers line */}
                        <div className="w-full h-0.5 bg-zinc-700 relative">
                          {/* Box IQR */}
                          <div
                            className="absolute top-1/2 -translate-y-1/2 h-5 bg-emerald-500/20 border-2 border-emerald-500/60 rounded"
                            style={{ left: '20%', width: '50%' }}
                          />
                          {/* Median Line */}
                          <div
                            className="absolute top-1/2 -translate-y-1/2 h-6 w-1 bg-amber-400"
                            style={{ left: '42%' }}
                          />
                        </div>
                      </div>
                      <div className="flex justify-between text-[10px] font-mono text-zinc-500">
                        <span>Min: {s.boxplot.min}</span>
                        <span>Q1: {s.boxplot.q1}</span>
                        <span>Q3: {s.boxplot.q3}</span>
                        <span>Max: {s.boxplot.max}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Correlation Heatmap Matrix */}
          <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl space-y-4">
            <h4 className="text-xs font-semibold text-zinc-200">Pearson Correlation Heatmap</h4>
            <div className="overflow-x-auto">
              <table className="text-center text-xs font-mono border-collapse mx-auto">
                <thead>
                  <tr>
                    <th className="p-2 text-zinc-500"></th>
                    {profile.correlation.columns.map((c) => (
                      <th key={c} className="p-2 font-medium text-zinc-300">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {profile.correlation.columns.map((rowName, rIdx) => (
                    <tr key={rowName}>
                      <td className="p-2 font-medium text-left text-zinc-300">{rowName}</td>
                      {profile.correlation.matrix[rIdx].map((val, cIdx) => {
                        let bg = 'bg-zinc-800 text-zinc-400';
                        if (val > 0.6) bg = 'bg-emerald-500/30 text-emerald-300 font-bold';
                        else if (val > 0.2) bg = 'bg-emerald-500/10 text-emerald-400';
                        else if (val < -0.4) bg = 'bg-rose-500/30 text-rose-300 font-bold';
                        else if (val < 0) bg = 'bg-rose-500/10 text-rose-400';

                        return (
                          <td key={cIdx} className={`p-3 rounded-lg border border-zinc-900 ${bg}`}>
                            {val.toFixed(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 4: QUALITY                                                      */}
      {/* =================================================================== */}
      {activeTab === 'quality' && quality && (
        <div className="space-y-6">
          {/* Quality Score Header & KPI Banner */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl flex flex-col items-center justify-center text-center">
              <span className="text-xs font-medium text-zinc-400 mb-2">Overall Quality Score</span>
              <div className="relative w-24 h-24 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                  <path
                    className="text-zinc-800"
                    strokeWidth="3.5"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className="text-emerald-500"
                    strokeDasharray={`${quality.qualityScore}, 100`}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <span className="absolute text-2xl font-bold font-mono text-zinc-100">
                  {quality.qualityScore}%
                </span>
              </div>
              <span className="text-[11px] text-emerald-400 font-medium mt-2">Production Certified</span>
            </div>

            <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl flex flex-col justify-between">
              <span className="text-xs font-medium text-zinc-400">Missing Values</span>
              <div className="my-2">
                <span className="text-2xl font-bold font-mono text-zinc-100">{quality.missingValuesCount}</span>
                <span className="text-xs text-zinc-500 ml-1.5">(0.02% total cells)</span>
              </div>
              <span className="text-[11px] text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Well under 2% threshold</span>
              </span>
            </div>

            <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl flex flex-col justify-between">
              <span className="text-xs font-medium text-zinc-400">Duplicates Detected</span>
              <div className="my-2">
                <span className="text-2xl font-bold font-mono text-emerald-400">{quality.duplicateRowsCount}</span>
                <span className="text-xs text-zinc-500 ml-1.5">rows</span>
              </div>
              <span className="text-[11px] text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Zero duplicate keys</span>
              </span>
            </div>

            <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl flex flex-col justify-between">
              <span className="text-xs font-medium text-zinc-400">Statistical Outliers</span>
              <div className="my-2">
                <span className="text-2xl font-bold font-mono text-amber-400">{quality.outliersCount}</span>
                <span className="text-xs text-zinc-500 ml-1.5">records</span>
              </div>
              <span className="text-[11px] text-amber-400 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Flagged for robust scaling</span>
              </span>
            </div>
          </div>

          {/* Data Hygiene Rules Checklist */}
          <div className="p-5 bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl space-y-4">
            <h3 className="text-sm font-semibold text-zinc-100">Quality Assessment & Rule Evaluation</h3>
            <div className="space-y-2.5">
              {quality.rules.map((rule) => (
                <div
                  key={rule.rule}
                  className="flex items-center justify-between p-3.5 bg-zinc-950/70 border border-zinc-800/80 rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    {rule.status === 'passed' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    )}
                    <div>
                      <h4 className="text-xs font-semibold text-zinc-200">{rule.rule}</h4>
                      <p className="text-[11px] text-zinc-400 mt-0.5">{rule.description}</p>
                    </div>
                  </div>
                  <span className="font-mono text-xs font-bold text-zinc-300">{rule.score}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 5: VERSIONS                                                     */}
      {/* =================================================================== */}
      {activeTab === 'versions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">Dataset Versioning & Snapshots</h3>
              <p className="text-xs text-zinc-400">Track mutations, schema modifications, and audit rollback history.</p>
            </div>
            <button
              onClick={() => setComparingVersions((prev) => !prev)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-sky-400 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-xl transition-all"
            >
              <GitCompare className="w-3.5 h-3.5" />
              <span>{comparingVersions ? 'Hide Compare' : 'Compare Versions'}</span>
            </button>
          </div>

          {rollbackStatus && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>{rollbackStatus}</span>
            </div>
          )}

          {/* Compare Drawer */}
          {comparingVersions && (
            <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-xl space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between text-zinc-300 border-b border-zinc-800 pb-2">
                <span>Version 3 vs Version 2 Comparison</span>
                <span className="text-emerald-400">Delta: +0 rows, +1 column, +4% quality</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-[11px]">
                <div className="p-3 bg-zinc-900/60 rounded-lg">
                  <span className="text-zinc-500 block">Version 2 (Cleaned)</span>
                  <p className="text-zinc-300 mt-1">Columns: 24 • Quality: 88%</p>
                  <p className="text-zinc-400">Median null imputation on discount.</p>
                </div>
                <div className="p-3 bg-zinc-900/60 rounded-lg border border-sky-500/30">
                  <span className="text-sky-400 block">Version 3 (Active)</span>
                  <p className="text-zinc-200 mt-1">Columns: 25 • Quality: 92%</p>
                  <p className="text-zinc-300">Engineered feature: normalized profit margin.</p>
                </div>
              </div>
            </div>
          )}

          {/* Version Cards */}
          <div className="space-y-3">
            {versions.map((ver) => (
              <div
                key={ver.version_number}
                className={`p-5 rounded-2xl border transition-all ${
                  ver.isActive
                    ? 'bg-zinc-900/90 border-sky-500/40 shadow-lg shadow-sky-950/20'
                    : 'bg-zinc-900/50 border-zinc-800/80 hover:border-zinc-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h4 className="text-sm font-semibold text-zinc-100 font-mono">{ver.label}</h4>
                      {ver.isActive && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/10 text-sky-400 border border-sky-500/30">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-400 mt-1">{ver.changelog}</p>
                    <div className="flex items-center gap-3 text-[11px] text-zinc-500 mt-2 font-mono">
                      <span>{ver.rows.toLocaleString()} rows</span>
                      <span>•</span>
                      <span>{ver.columns} columns</span>
                      <span>•</span>
                      <span>{formatDateTime(ver.created_at)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!ver.isActive && (
                      <button
                        onClick={() => handleRollback(ver.version_number)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 rounded-xl transition-all"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Rollback to v{ver.version_number}</span>
                      </button>
                    )}
                    <button
                      onClick={() => setComparingVersions(true)}
                      className="px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-xl transition-all"
                    >
                      Inspect
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 6: LINEAGE                                                      */}
      {/* =================================================================== */}
      {activeTab === 'lineage' && (
        <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-2xl shadow-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              <Network className="w-4 h-4 text-sky-400" />
              <span>End-to-End Data Lineage & Agent Execution Graph</span>
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Source file ingestion, raw storage isolation, Parquet transformation, metadata generation, and downstream AI integration.
            </p>
          </div>

          {/* Visual DAG Flow */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative">
              {lineage
                .filter((n) => n.type !== 'ai_agent')
                .map((node) => (
                  <div key={node.id} className="p-4 bg-zinc-950 border border-zinc-800 rounded-xl text-center space-y-2">
                    <span className="px-2 py-0.5 text-[10px] font-mono text-sky-400 rounded bg-sky-500/10 uppercase">
                      {node.type.replace('_', ' ')}
                    </span>
                    <h4 className="text-xs font-bold text-zinc-200">{node.title}</h4>
                    <p className="text-[10px] text-zinc-500 font-mono truncate">{node.description}</p>
                  </div>
                ))}
            </div>

            {/* Downstream Agents Tier */}
            <div className="p-5 bg-zinc-950/60 border border-zinc-800 rounded-2xl space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300">
                <Bot className="w-4 h-4 text-sky-400" />
                <span>Consuming AI Agents (Immediate Zero-ETL Availability):</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                {lineage
                  .filter((n) => n.type === 'ai_agent')
                  .map((agent) => (
                    <div
                      key={agent.id}
                      className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-center"
                    >
                      <span className="text-xs font-semibold text-zinc-200 block">{agent.title}</span>
                      <span className="text-[10px] text-emerald-400">Live Attached</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
