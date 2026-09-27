import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Boxes,
  Layers,
  Database,
  Eye,
  RefreshCw,
  Table,
  Sparkles,
  Clock,
  ChevronRight,
  X,
  Loader2,
} from 'lucide-react';
import { datasetService } from '../../services/datasetService';
import { formatFileSize, formatDateTime } from '../../datasetUtils';
import type {
  DataWarehouseCatalog,
  WarehouseColumn,
} from '../../types/datasets';

type WarehouseTab = 'facts' | 'dimensions' | 'views' | 'materialized';

export default function DataWarehousePage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<WarehouseTab>('facts');
  const [catalog, setCatalog] = useState<DataWarehouseCatalog | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshingMvId, setRefreshingMvId] = useState<string | null>(null);

  // Inspector modal state
  const [inspectedTable, setInspectedTable] = useState<{
    name: string;
    description: string;
    columns: WarehouseColumn[];
    query?: string;
  } | null>(null);

  useEffect(() => {
    async function loadCatalog() {
      setIsLoading(true);
      try {
        const data = await datasetService.getWarehouseCatalog();
        setCatalog(data);
      } finally {
        setIsLoading(false);
      }
    }
    loadCatalog();
  }, []);

  if (isLoading || !catalog) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
        <p className="text-xs text-zinc-400 font-mono">Loading Enterprise Data Warehouse...</p>
      </div>
    );
  }

  async function handleRefreshMv(id: string) {
    setRefreshingMvId(id);
    try {
      await datasetService.refreshMaterializedView(id);
      const updated = await datasetService.getWarehouseCatalog();
      setCatalog(updated);
    } finally {
      setRefreshingMvId(null);
    }
  }

  function handleQueryWithAi(tableName: string) {
    navigate(`/analysis?prompt=Perform+an+in-depth+analysis+of+warehouse+table+${encodeURIComponent(tableName)}`);
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2.5">
            <Boxes className="w-6 h-6 text-sky-400" />
            <span>Enterprise Data Warehouse</span>
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Canonical analytical schemas, dimensional models, and high-performance pre-aggregated views.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-xl">
          <button
            onClick={() => setActiveTab('facts')}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'facts'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Fact Tables ({catalog?.factTables.length ?? 3})</span>
          </button>
          <button
            onClick={() => setActiveTab('dimensions')}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'dimensions'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Dimension Tables ({catalog?.dimensionTables.length ?? 3})</span>
          </button>
          <button
            onClick={() => setActiveTab('views')}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'views'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Views ({catalog?.views.length ?? 2})</span>
          </button>
          <button
            onClick={() => setActiveTab('materialized')}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'materialized'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Materialized Views ({catalog?.materializedViews.length ?? 2})</span>
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* FACT TABLES TAB                                                     */}
      {/* =================================================================== */}
      {activeTab === 'facts' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Fact Tables (Transactional & Metric Logs)</h2>
            <span className="text-xs text-zinc-500">Optimized for columnar aggregation & scans</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {catalog?.factTables.map((fact) => (
              <div
                key={fact.id}
                className="group relative p-5 bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 rounded-2xl shadow-lg transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <span className="px-2 py-0.5 text-[10px] font-mono font-medium rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                        FACT
                      </span>
                      <h3 className="text-base font-semibold text-zinc-100 mt-2 font-mono group-hover:text-sky-300 transition-colors">
                        {fact.name}
                      </h3>
                    </div>
                    <span className="text-xs font-mono text-zinc-400">{formatFileSize(fact.sizeBytes)}</span>
                  </div>

                  <p className="text-xs text-zinc-400 line-clamp-2 mt-1 mb-4">{fact.description}</p>

                  <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Total Rows</span>
                      <span className="font-semibold text-zinc-200">{fact.rowCount.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Columns</span>
                      <span className="text-zinc-300 font-mono">{fact.columnCount} cols</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Partition Key</span>
                      <span className="text-zinc-300 font-mono text-[11px] truncate max-w-[170px]">{fact.partitionKey}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 mt-4 border-t border-zinc-800/60">
                  <button
                    onClick={() =>
                      setInspectedTable({
                        name: fact.name,
                        description: fact.description,
                        columns: fact.columns,
                      })
                    }
                    className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium"
                  >
                    <span>View Schema</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => handleQueryWithAi(fact.name)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-200 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
                  >
                    <Sparkles className="w-3 h-3 text-sky-400" />
                    <span>AI Analysis</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* DIMENSION TABLES TAB                                                */}
      {/* =================================================================== */}
      {activeTab === 'dimensions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Dimension Tables (Reference & Context Models)</h2>
            <span className="text-xs text-zinc-500">Slowly Changing Dimensions (SCD Type 2)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {catalog?.dimensionTables.map((dim) => (
              <div
                key={dim.id}
                className="group relative p-5 bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 rounded-2xl shadow-lg transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <span className="px-2 py-0.5 text-[10px] font-mono font-medium rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        DIMENSION
                      </span>
                      <h3 className="text-base font-semibold text-zinc-100 mt-2 font-mono group-hover:text-emerald-300 transition-colors">
                        {dim.name}
                      </h3>
                    </div>
                    <span className="text-xs font-mono text-zinc-400">{formatFileSize(dim.sizeBytes)}</span>
                  </div>

                  <p className="text-xs text-zinc-400 line-clamp-2 mt-1 mb-4">{dim.description}</p>

                  <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Record Count</span>
                      <span className="font-semibold text-zinc-200">{dim.rowCount.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Columns</span>
                      <span className="text-zinc-300 font-mono">{dim.columnCount} cols</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Primary Key</span>
                      <span className="text-emerald-400 font-mono font-medium">{dim.primaryKey}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 mt-4 border-t border-zinc-800/60">
                  <button
                    onClick={() =>
                      setInspectedTable({
                        name: dim.name,
                        description: dim.description,
                        columns: dim.columns,
                      })
                    }
                    className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium"
                  >
                    <span>View Schema</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => handleQueryWithAi(dim.name)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-200 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
                  >
                    <Sparkles className="w-3 h-3 text-sky-400" />
                    <span>AI Analysis</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* VIEWS TAB                                                           */}
      {/* =================================================================== */}
      {activeTab === 'views' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Standard Virtual Views</h2>
            <span className="text-xs text-zinc-500">Real-time query abstractions</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {catalog?.views.map((view) => (
              <div
                key={view.id}
                className="p-5 bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 rounded-2xl shadow-lg space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="px-2 py-0.5 text-[10px] font-mono font-medium rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                      VIEW
                    </span>
                    <h3 className="text-base font-semibold text-zinc-100 mt-2 font-mono">{view.name}</h3>
                  </div>
                  <span className="text-xs text-zinc-500">Refreshed on query</span>
                </div>

                <p className="text-xs text-zinc-400">{view.description}</p>

                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <span className="text-zinc-500">Source Tables:</span>
                  <div className="flex gap-1.5">
                    {view.sourceTables.map((tbl) => (
                      <span key={tbl} className="px-2 py-0.5 rounded bg-zinc-800 font-mono text-[11px] text-zinc-300">
                        {tbl}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800/80 font-mono text-[11px] text-zinc-400 overflow-x-auto">
                  <pre>{view.query}</pre>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => handleQueryWithAi(view.name)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Run Query in AI Analyst</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MATERIALIZED VIEWS TAB                                              */}
      {/* =================================================================== */}
      {activeTab === 'materialized' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Materialized Views (Pre-computed Aggregates)</h2>
            <span className="text-xs text-zinc-500">Cached on disk for sub-second visual rendering</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {catalog?.materializedViews.map((mv) => {
              const isRefreshing = refreshingMvId === mv.id;
              return (
                <div
                  key={mv.id}
                  className="p-5 bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 rounded-2xl shadow-lg space-y-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] font-mono font-medium rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          MATERIALIZED VIEW
                        </span>
                        <span className="text-xs text-zinc-400 font-mono">
                          {mv.rowCount.toLocaleString()} cached rows
                        </span>
                      </div>
                      <h3 className="text-base font-semibold text-zinc-100 mt-2 font-mono">{mv.name}</h3>
                    </div>
                    <span className="text-xs font-mono text-zinc-400">{formatFileSize(mv.sizeBytes)}</span>
                  </div>

                  <p className="text-xs text-zinc-400">{mv.description}</p>

                  <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 text-zinc-400">
                      <Clock className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Cadence: <strong className="text-zinc-300">{mv.refreshInterval}</strong></span>
                    </div>
                    <span className="text-zinc-500">
                      Last refreshed: {formatDateTime(mv.lastRefreshed)}
                    </span>
                  </div>

                  <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800/80 font-mono text-[11px] text-zinc-400 overflow-x-auto max-h-24">
                    <pre>{mv.query}</pre>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <button
                      onClick={() => handleRefreshMv(mv.id)}
                      disabled={isRefreshing}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-sky-400' : ''}`} />
                      <span>{isRefreshing ? 'Recomputing...' : 'Refresh Now'}</span>
                    </button>

                    <button
                      onClick={() => handleQueryWithAi(mv.name)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-colors"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Explore with AI</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Schema Inspector Modal */}
      {inspectedTable && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-2xl bg-zinc-900 border border-zinc-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-950/60">
              <div className="flex items-center gap-2.5">
                <Database className="w-5 h-5 text-sky-400" />
                <div>
                  <h3 className="text-base font-semibold font-mono text-zinc-100">{inspectedTable.name}</h3>
                  <p className="text-xs text-zinc-400">{inspectedTable.description}</p>
                </div>
              </div>
              <button
                onClick={() => setInspectedTable(null)}
                className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Column Definitions</h4>
              <div className="border border-zinc-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-950/80 border-b border-zinc-800 text-zinc-400">
                    <tr>
                      <th className="px-4 py-2.5 font-medium">Column</th>
                      <th className="px-4 py-2.5 font-medium">SQL Type</th>
                      <th className="px-4 py-2.5 font-medium">Nullable</th>
                      <th className="px-4 py-2.5 font-medium">Key Attribute</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60">
                    {inspectedTable.columns.map((col) => (
                      <tr key={col.name} className="hover:bg-zinc-800/30">
                        <td className="px-4 py-2.5 font-mono font-medium text-zinc-200">{col.name}</td>
                        <td className="px-4 py-2.5 font-mono text-sky-400">{col.type}</td>
                        <td className="px-4 py-2.5 text-zinc-400">{col.nullable ? 'YES' : 'NOT NULL'}</td>
                        <td className="px-4 py-2.5">
                          {col.isPrimaryKey && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              PRIMARY KEY
                            </span>
                          )}
                          {col.isForeignKey && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                              FOREIGN KEY
                            </span>
                          )}
                          {!col.isPrimaryKey && !col.isForeignKey && <span className="text-zinc-600">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-800 bg-zinc-950/60">
              <button
                onClick={() => setInspectedTable(null)}
                className="px-4 py-2 text-xs font-medium text-zinc-400 hover:text-zinc-200"
              >
                Close
              </button>
              <button
                onClick={() => {
                  const name = inspectedTable.name;
                  setInspectedTable(null);
                  handleQueryWithAi(name);
                }}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-xl"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Launch in AI Analysis</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
