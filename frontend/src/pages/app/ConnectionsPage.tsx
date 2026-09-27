import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Database,
  Globe,
  Plus,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  Server,
  Eye,
  EyeOff,
  Activity,
} from 'lucide-react';
import { datasetService } from '../../services/datasetService';
import type {
  DatabaseConnection,
  ApiConnection,
  DatabaseEngine,
  ApiType,
  ApiAuthType,
  ApiHeader,
} from '../../types/datasets';

const DEFAULT_PORTS: Record<DatabaseEngine, number> = {
  PostgreSQL: 5432,
  MySQL: 3306,
  MongoDB: 27017,
  'SQL Server': 1433,
  Oracle: 1521,
};

export default function ConnectionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') === 'api' ? 'api' : 'database';
  const [activeTab, setActiveTab] = useState<'database' | 'api'>(initialTab);

  const [dbConnections, setDbConnections] = useState<DatabaseConnection[]>([]);
  const [apiConnections, setApiConnections] = useState<ApiConnection[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Database Connection Form State
  const [isAddingDb, setIsAddingDb] = useState(false);
  const [dbName, setDbName] = useState('');
  const [dbEngine, setDbEngine] = useState<DatabaseEngine>('PostgreSQL');
  const [dbHost, setDbHost] = useState('');
  const [dbPort, setDbPort] = useState<number>(5432);
  const [dbDatabase, setDbDatabase] = useState('');
  const [dbUsername, setDbUsername] = useState('');
  const [dbPassword, setDbPassword] = useState('');
  const [showDbPassword, setShowDbPassword] = useState(false);
  const [dbSsl, setDbSsl] = useState(true);

  const [isTestingDb, setIsTestingDb] = useState(false);
  const [dbTestResult, setDbTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // API Connection Form State
  const [isAddingApi, setIsAddingApi] = useState(false);
  const [apiName, setApiName] = useState('');
  const [apiType, setApiType] = useState<ApiType>('REST API');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [apiEndpoint, setApiEndpoint] = useState('');
  const [apiAuthType, setApiAuthType] = useState<ApiAuthType>('bearer');
  const [apiKey, setApiKey] = useState('');
  const [apiKeyHeader, setApiKeyHeader] = useState('Authorization');
  const [apiHeaders, setApiHeaders] = useState<ApiHeader[]>([{ key: 'Content-Type', value: 'application/json' }]);

  const [isTestingApi, setIsTestingApi] = useState(false);
  const [apiTestResult, setApiTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [dbs, apis] = await Promise.all([
          datasetService.listDatabaseConnections(),
          datasetService.listApiConnections(),
        ]);
        setDbConnections(dbs);
        setApiConnections(apis);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
        <p className="text-xs text-zinc-400 font-mono">Loading Enterprise Connectors...</p>
      </div>
    );
  }

  function handleEngineChange(engine: DatabaseEngine) {
    setDbEngine(engine);
    setDbPort(DEFAULT_PORTS[engine]);
  }

  async function handleTestDb() {
    setIsTestingDb(true);
    setDbTestResult(null);
    try {
      const res = await datasetService.testDatabaseConnection({
        engine: dbEngine,
        host: dbHost || 'localhost',
        port: dbPort,
        database: dbDatabase || 'main',
        username: dbUsername || 'root',
      });
      setDbTestResult({ success: res.success, message: `${res.message} (${res.latencyMs}ms)` });
    } catch {
      setDbTestResult({ success: false, message: 'Connection refused. Check hostname, port, or firewall.' });
    } finally {
      setIsTestingDb(false);
    }
  }

  async function handleSaveDb() {
    if (!dbName.trim() || !dbHost.trim() || !dbDatabase.trim()) {
      setDbTestResult({ success: false, message: 'Please specify Connection Name, Host, and Database.' });
      return;
    }

    const saved = await datasetService.saveDatabaseConnection({
      name: dbName.trim(),
      engine: dbEngine,
      host: dbHost.trim(),
      port: dbPort,
      database: dbDatabase.trim(),
      username: dbUsername.trim() || 'reader',
      ssl: dbSsl,
      status: 'connected',
    });

    setDbConnections((prev) => [saved, ...prev]);
    setIsAddingDb(false);
    resetDbForm();
  }

  function resetDbForm() {
    setDbName('');
    setDbHost('');
    setDbDatabase('');
    setDbUsername('');
    setDbPassword('');
    setDbTestResult(null);
  }

  function addHeader() {
    setApiHeaders((prev) => [...prev, { key: '', value: '' }]);
  }

  function updateHeader(index: number, field: 'key' | 'value', val: string) {
    setApiHeaders((prev) => {
      const updated = [...prev];
      updated[index][field] = val;
      return updated;
    });
  }

  function removeHeader(index: number) {
    setApiHeaders((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleTestApi() {
    setIsTestingApi(true);
    setApiTestResult(null);
    try {
      const res = await datasetService.testApiConnection({
        type: apiType,
        baseUrl: apiBaseUrl || 'https://api.example.com',
      });
      setApiTestResult({ success: res.success, message: `${res.message} (${res.latencyMs}ms)` });
    } catch {
      setApiTestResult({ success: false, message: 'API request timed out or returned HTTP 500.' });
    } finally {
      setIsTestingApi(false);
    }
  }

  async function handleSaveApi() {
    if (!apiName.trim() || !apiBaseUrl.trim()) {
      setApiTestResult({ success: false, message: 'Please specify Connection Name and Base URL.' });
      return;
    }

    const saved = await datasetService.saveApiConnection({
      name: apiName.trim(),
      type: apiType,
      baseUrl: apiBaseUrl.trim(),
      endpoint: apiEndpoint.trim() || undefined,
      authType: apiAuthType,
      apiKey: apiKey ? '***' : undefined,
      apiKeyHeader,
      headers: apiHeaders.filter((h) => h.key.trim() !== ''),
      status: 'connected',
    });

    setApiConnections((prev) => [saved, ...prev]);
    setIsAddingApi(false);
    resetApiForm();
  }

  function resetApiForm() {
    setApiName('');
    setApiBaseUrl('');
    setApiEndpoint('');
    setApiKey('');
    setApiTestResult(null);
  }

  function getEngineBadge(engine: DatabaseEngine) {
    const colors: Record<DatabaseEngine, { bg: string; text: string; border: string }> = {
      PostgreSQL: { bg: 'bg-sky-500/10', text: 'text-sky-400', border: 'border-sky-500/30' },
      MySQL: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
      MongoDB: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
      'SQL Server': { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
      Oracle: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
    };
    const c = colors[engine] || colors.PostgreSQL;
    return (
      <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-md border ${c.bg} ${c.text} ${c.border}`}>
        {engine}
      </span>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Banner / Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2.5">
            <Server className="w-6 h-6 text-sky-400" />
            <span>Data Connections</span>
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Connect live relational databases, NoSQL stores, and external REST / GraphQL APIs.
          </p>
        </div>

        {/* Tab switchers */}
        <div className="flex items-center gap-2 p-1 bg-zinc-900 border border-zinc-800 rounded-xl">
          <button
            onClick={() => {
              setActiveTab('database');
              setSearchParams({ tab: 'database' });
            }}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'database'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Database Connections ({dbConnections.length})</span>
          </button>
          <button
            onClick={() => {
              setActiveTab('api');
              setSearchParams({ tab: 'api' });
            }}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'api'
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>API Connections ({apiConnections.length})</span>
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* DATABASE CONNECTIONS TAB                                            */}
      {/* =================================================================== */}
      {activeTab === 'database' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-zinc-200">Configured Database Engines</h2>
              <p className="text-xs text-zinc-400">PostgreSQL • MySQL • MongoDB • SQL Server • Oracle</p>
            </div>
            <button
              onClick={() => setIsAddingDb((prev) => !prev)}
              className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-xl shadow-lg shadow-sky-600/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>{isAddingDb ? 'Cancel' : 'Connect Database'}</span>
            </button>
          </div>

          {/* Add Database Form Drawer */}
          {isAddingDb && (
            <div className="p-6 bg-zinc-900/90 border border-sky-500/30 rounded-2xl shadow-xl space-y-5 animate-in fade-in duration-200">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-sky-400" />
                  <h3 className="text-sm font-semibold text-zinc-100">Add New Database Connection</h3>
                </div>
                <span className="text-xs text-zinc-500">Read-only connection recommended for analytics</span>
              </div>

              {/* Engine Selector */}
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-2">Select Engine</label>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                  {(['PostgreSQL', 'MySQL', 'MongoDB', 'SQL Server', 'Oracle'] as DatabaseEngine[]).map((engine) => (
                    <button
                      key={engine}
                      type="button"
                      onClick={() => handleEngineChange(engine)}
                      className={`p-3 rounded-xl border text-center font-medium text-xs transition-all ${
                        dbEngine === engine
                          ? 'border-sky-500 bg-sky-500/15 text-sky-300 shadow-sm'
                          : 'border-zinc-800 bg-zinc-950/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200'
                      }`}
                    >
                      {engine}
                    </button>
                  ))}
                </div>
              </div>

              {/* Form Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Connection Name</label>
                  <input
                    type="text"
                    value={dbName}
                    onChange={(e) => setDbName(e.target.value)}
                    placeholder="e.g. Production Analytics DB"
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Host</label>
                  <input
                    type="text"
                    value={dbHost}
                    onChange={(e) => setDbHost(e.target.value)}
                    placeholder="e.g. pg-db.internal or localhost"
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Port</label>
                  <input
                    type="number"
                    value={dbPort}
                    onChange={(e) => setDbPort(Number(e.target.value))}
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Database Name</label>
                  <input
                    type="text"
                    value={dbDatabase}
                    onChange={(e) => setDbDatabase(e.target.value)}
                    placeholder="e.g. ai_analyst_warehouse"
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Username</label>
                  <input
                    type="text"
                    value={dbUsername}
                    onChange={(e) => setDbUsername(e.target.value)}
                    placeholder="e.g. bi_reader"
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Password</label>
                  <div className="relative">
                    <input
                      type={showDbPassword ? 'text' : 'password'}
                      value={dbPassword}
                      onChange={(e) => setDbPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none pr-9"
                    />
                    <button
                      type="button"
                      onClick={() => setShowDbPassword((prev) => !prev)}
                      className="absolute right-2.5 top-2 text-zinc-500 hover:text-zinc-300"
                    >
                      {showDbPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>

              {/* SSL toggle & Feedback */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
                <label className="flex items-center gap-2.5 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={dbSsl}
                    onChange={(e) => setDbSsl(e.target.checked)}
                    className="rounded border-zinc-700 bg-zinc-950 text-sky-500 focus:ring-0 w-4 h-4"
                  />
                  <span>Enable SSL / TLS encryption</span>
                </label>

                {dbTestResult && (
                  <div
                    className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg border ${
                      dbTestResult.success
                        ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                    }`}
                  >
                    {dbTestResult.success ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 shrink-0" />}
                    <span>{dbTestResult.message}</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={handleTestDb}
                  disabled={isTestingDb}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-xl transition-all"
                >
                  {isTestingDb ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5 text-sky-400" />}
                  <span>Test Connection</span>
                </button>
                <button
                  type="button"
                  onClick={handleSaveDb}
                  className="flex items-center gap-2 px-5 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-xl transition-all shadow-md shadow-sky-600/20"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Save Connection</span>
                </button>
              </div>
            </div>
          )}

          {/* Database Connections Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {dbConnections.map((conn) => (
              <div
                key={conn.id}
                className="group relative p-5 bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 rounded-2xl shadow-lg transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-xl bg-zinc-800/80 border border-zinc-700 text-sky-400">
                        <Database className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-zinc-100 group-hover:text-sky-300 transition-colors">
                          {conn.name}
                        </h4>
                        <p className="text-xs text-zinc-400 font-mono mt-0.5">
                          {conn.host}:{conn.port}/{conn.database}
                        </p>
                      </div>
                    </div>
                    {getEngineBadge(conn.engine)}
                  </div>

                  <div className="grid grid-cols-2 gap-2 my-4 p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60 text-xs">
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Tables Indexed</span>
                      <span className="font-semibold text-zinc-200">{conn.tablesCount ?? 45} tables</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Latency</span>
                      <span className="font-mono text-emerald-400 font-medium">{conn.latencyMs ?? 18}ms</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-zinc-800/60 text-xs">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>Connected</span>
                  </div>
                  <span className="text-[11px] text-zinc-500">
                    Checked {new Date(conn.lastTestedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* API CONNECTIONS TAB                                                 */}
      {/* =================================================================== */}
      {activeTab === 'api' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-zinc-200">Configured API Connectors</h2>
              <p className="text-xs text-zinc-400">REST API • GraphQL API with dynamic headers and authentication</p>
            </div>
            <button
              onClick={() => setIsAddingApi((prev) => !prev)}
              className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-xl shadow-lg shadow-sky-600/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>{isAddingApi ? 'Cancel' : 'Connect API'}</span>
            </button>
          </div>

          {/* Add API Form Drawer */}
          {isAddingApi && (
            <div className="p-6 bg-zinc-900/90 border border-sky-500/30 rounded-2xl shadow-xl space-y-5 animate-in fade-in duration-200">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-sky-400" />
                  <h3 className="text-sm font-semibold text-zinc-100">Configure API Connector</h3>
                </div>
                <div className="flex gap-2">
                  {(['REST API', 'GraphQL API'] as ApiType[]).map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setApiType(t)}
                      className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                        apiType === t ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30' : 'bg-zinc-800 text-zinc-400'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Core Details */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Connector Name</label>
                  <input
                    type="text"
                    value={apiName}
                    onChange={(e) => setApiName(e.target.value)}
                    placeholder="e.g. Stripe Billing or Salesforce CRM"
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Base URL</label>
                  <input
                    type="text"
                    value={apiBaseUrl}
                    onChange={(e) => setApiBaseUrl(e.target.value)}
                    placeholder="https://api.stripe.com/v1"
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Authentication Method</label>
                  <select
                    value={apiAuthType}
                    onChange={(e) => setApiAuthType(e.target.value as ApiAuthType)}
                    className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                  >
                    <option value="none">No Authentication</option>
                    <option value="bearer">Bearer Token</option>
                    <option value="apiKey">API Key (Header / Query)</option>
                    <option value="basic">Basic Auth</option>
                  </select>
                </div>

                {apiAuthType !== 'none' && (
                  <div className="space-y-3">
                    {apiAuthType === 'apiKey' && (
                      <div>
                        <label className="block text-xs font-medium text-zinc-400 mb-1">Header / Param Name</label>
                        <input
                          type="text"
                          value={apiKeyHeader}
                          onChange={(e) => setApiKeyHeader(e.target.value)}
                          placeholder="e.g. X-API-Key or Authorization"
                          className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                        />
                      </div>
                    )}
                    <div>
                      <label className="block text-xs font-medium text-zinc-400 mb-1">
                        {apiAuthType === 'bearer' ? 'Bearer Token' : 'API Key Secret'}
                      </label>
                      <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="sk_live_..."
                        className="w-full px-3.5 py-2 text-xs bg-zinc-950 border border-zinc-800 focus:border-sky-500 rounded-xl text-zinc-100 outline-none"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Dynamic Headers Section */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-300">Custom Request Headers</label>
                  <button
                    type="button"
                    onClick={addHeader}
                    className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Header</span>
                  </button>
                </div>

                <div className="space-y-2">
                  {apiHeaders.map((header, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="Header Key (e.g. X-Workspace-ID)"
                        value={header.key}
                        onChange={(e) => updateHeader(idx, 'key', e.target.value)}
                        className="flex-1 px-3 py-1.5 text-xs bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100 outline-none"
                      />
                      <input
                        type="text"
                        placeholder="Value"
                        value={header.value}
                        onChange={(e) => updateHeader(idx, 'value', e.target.value)}
                        className="flex-1 px-3 py-1.5 text-xs bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100 outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => removeHeader(idx)}
                        className="p-1.5 text-zinc-500 hover:text-rose-400 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {apiTestResult && (
                <div
                  className={`flex items-center gap-2 text-xs p-3 rounded-xl border ${
                    apiTestResult.success
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                  }`}
                >
                  {apiTestResult.success ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                  <span>{apiTestResult.message}</span>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={handleTestApi}
                  disabled={isTestingApi}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-xl transition-all"
                >
                  {isTestingApi ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5 text-sky-400" />}
                  <span>Test Connection</span>
                </button>
                <button
                  type="button"
                  onClick={handleSaveApi}
                  className="flex items-center gap-2 px-5 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 rounded-xl transition-all shadow-md shadow-sky-600/20"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Save Connection</span>
                </button>
              </div>
            </div>
          )}

          {/* API Connections Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {apiConnections.map((api) => (
              <div
                key={api.id}
                className="group relative p-5 bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 rounded-2xl shadow-lg transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-xl bg-zinc-800/80 border border-zinc-700 text-sky-400">
                        <Globe className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-zinc-100 group-hover:text-sky-300 transition-colors">
                          {api.name}
                        </h4>
                        <p className="text-xs text-zinc-400 font-mono mt-0.5 truncate max-w-[200px]">
                          {api.baseUrl}
                        </p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 text-xs font-semibold rounded-md border border-purple-500/30 bg-purple-500/10 text-purple-300">
                      {api.type}
                    </span>
                  </div>

                  <div className="my-4 p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60 space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Auth Method</span>
                      <span className="text-zinc-300 font-medium capitalize">{api.authType}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Ping Response</span>
                      <span className="font-mono text-emerald-400 font-medium">{api.latencyMs ?? 95}ms</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-zinc-800/60 text-xs">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>Active Endpoint</span>
                  </div>
                  <span className="text-[11px] text-zinc-500">
                    Tested {new Date(api.lastTestedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
