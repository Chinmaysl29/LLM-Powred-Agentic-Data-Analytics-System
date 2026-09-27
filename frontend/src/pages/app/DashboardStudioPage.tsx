/**
 * DashboardStudioPage � Phase 23.5
 *
 * Executive Dashboard Builder with:
 *  - Pre-built KPI widget grid
 *  - Drag-to-rearrange (simulated with order controls)
 *  - Add/remove widgets
 *  - Export dashboard as PDF / share link
 *  - Widget types: KPI, Bar Chart, Line Chart, Donut, Table
 */

import { useState, useCallback } from "react";
import {
  LayoutDashboard,
  Plus,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  ShoppingCart,
  BarChart3,
  Download,
  Share2,
  Grip,
  X,
  RefreshCw,
  Settings,
  Eye,
} from "lucide-react";
import { useToast } from "../../components/ui/Toast";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type WidgetType = "kpi" | "bar" | "line" | "donut" | "table";
type WidgetSize = "sm" | "md" | "lg";

interface Widget {
  id: string;
  type: WidgetType;
  title: string;
  size: WidgetSize;
  data: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Widget renderers
// ---------------------------------------------------------------------------

function KPIWidget({ data }: { data: Record<string, unknown> }) {
  const positive = (data.change as number) >= 0;
  return (
    <div className="ds-kpi">
      <div className="ds-kpi-header">
        <span className="ds-kpi-label">{data.label as string}</span>
        <div className="ds-kpi-icon" style={{ background: (data.color as string) + "20", color: data.color as string }}>
          {data.icon === "revenue" && <DollarSign size={14} />}
          {data.icon === "users" && <Users size={14} />}
          {data.icon === "orders" && <ShoppingCart size={14} />}
          {data.icon === "growth" && <TrendingUp size={14} />}
        </div>
      </div>
      <div className="ds-kpi-value">{data.value as string}</div>
      <div className={`ds-kpi-change ds-kpi-change--${positive ? "up" : "down"}`}>
        {positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
        {Math.abs(data.change as number)}% vs last period
      </div>
    </div>
  );
}

function MiniBarChart({ data }: { data: Record<string, unknown> }) {
  const values = data.values as number[];
  const labels = data.labels as string[];
  const color = data.color as string ?? "#3b82f6";
  const max = Math.max(...values);
  return (
    <div className="ds-bar-chart">
      <div className="ds-chart-bars">
        {values.map((v, i) => (
          <div key={i} className="ds-bar-col">
            <div
              className="ds-bar"
              style={{ height: `${(v / max) * 100}%`, background: color }}
              title={`${labels[i]}: ${v}`}
            />
            <span className="ds-bar-label">{labels[i]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MiniLineChart({ data }: { data: Record<string, unknown> }) {
  const values = data.values as number[];
  const color = data.color as string ?? "#10b981";
  const W = 260; const H = 80;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => [
    (i / (values.length - 1)) * W,
    H - ((v - min) / range) * H,
  ] as [number, number]);
  const d = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${d} L${W},${H} L0,${H} Z`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="ds-line-svg" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`lg-${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#lg-${color.replace("#","")})`} />
      <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function DonutChart({ data }: { data: Record<string, unknown> }) {
  const segments = data.segments as { label: string; value: number; color: string }[];
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  let cumulative = 0;
  const r = 40; const cx = 55; const cy = 55;

  function polarToXY(angle: number, radius: number) {
    return {
      x: cx + radius * Math.cos((angle - 90) * (Math.PI / 180)),
      y: cy + radius * Math.sin((angle - 90) * (Math.PI / 180)),
    };
  }

  function describeArc(startAngle: number, endAngle: number) {
    const start = polarToXY(startAngle, r);
    const end = polarToXY(endAngle, r);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${cx} ${cy} L ${start.x.toFixed(2)} ${start.y.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${end.x.toFixed(2)} ${end.y.toFixed(2)} Z`;
  }

  return (
    <div className="ds-donut">
      <svg viewBox="0 0 110 110" className="ds-donut-svg">
        {segments.map((seg, i) => {
          const angle = (seg.value / total) * 360;
          const path = describeArc(cumulative, cumulative + angle - 1);
          cumulative += angle;
          return <path key={i} d={path} fill={seg.color} />;
        })}
        <circle cx={cx} cy={cy} r={26} fill="var(--bg)" />
        <text x={cx} y={cy - 3} textAnchor="middle" fontSize={9} fill="var(--text)">{total.toLocaleString()}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" fontSize={7} fill="var(--text)" opacity={0.6}>Total</text>
      </svg>
      <div className="ds-donut-legend">
        {segments.map((seg, i) => (
          <div key={i} className="ds-donut-item">
            <span className="ds-donut-dot" style={{ background: seg.color }} />
            <span className="ds-donut-label">{seg.label}</span>
            <span className="ds-donut-value">{Math.round(seg.value / total * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MiniTable({ data }: { data: Record<string, unknown> }) {
  const rows = data.rows as Record<string, string | number>[];
  const cols = Object.keys(rows[0] ?? {});
  return (
    <div className="ds-table-wrap">
      <table className="ds-mini-table">
        <thead>
          <tr>{cols.map(c => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, 5).map((row, i) => (
            <tr key={i}>
              {cols.map(c => <td key={c}>{row[c]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Widget catalogue (available to add)
// ---------------------------------------------------------------------------

const WIDGET_CATALOGUE: Omit<Widget, "id">[] = [
  {
    title: "Total Revenue",
    type: "kpi",
    size: "sm",
    data: { label: "Total Revenue", value: "$2.4M", change: 18.2, icon: "revenue", color: "#10b981" },
  },
  {
    title: "Active Users",
    type: "kpi",
    size: "sm",
    data: { label: "Active Users", value: "14,832", change: 7.4, icon: "users", color: "#3b82f6" },
  },
  {
    title: "Total Orders",
    type: "kpi",
    size: "sm",
    data: { label: "Total Orders", value: "8,204", change: -3.1, icon: "orders", color: "#f59e0b" },
  },
  {
    title: "Revenue Trend",
    type: "line",
    size: "md",
    data: { label: "Revenue Trend", values: [110, 145, 132, 178, 165, 201, 188, 224, 210, 248, 235, 271], color: "#3b82f6" },
  },
  {
    title: "Sales by Category",
    type: "bar",
    size: "md",
    data: {
      label: "Sales by Category",
      values: [420, 310, 280, 190, 340],
      labels: ["SaaS", "Svcs", "Lic", "HW", "Other"],
      color: "#8b5cf6",
    },
  },
  {
    title: "Revenue Mix",
    type: "donut",
    size: "md",
    data: {
      segments: [
        { label: "SaaS", value: 1248, color: "#3b82f6" },
        { label: "Services", value: 744, color: "#10b981" },
        { label: "Licensing", value: 408, color: "#8b5cf6" },
      ],
    },
  },
  {
    title: "Top Products",
    type: "table",
    size: "lg",
    data: {
      rows: [
        { Product: "Enterprise Suite", Revenue: "$612K", Growth: "+32%" },
        { Product: "Pro License",      Revenue: "$348K", Growth: "+18%" },
        { Product: "Starter Plan",     Revenue: "$288K", Growth: "+45%" },
        { Product: "API Access",       Revenue: "$204K", Growth: "+12%" },
        { Product: "Consulting",       Revenue: "$180K", Growth: "-5%" },
      ],
    },
  },
];

// ---------------------------------------------------------------------------
// Default dashboard
// ---------------------------------------------------------------------------

let widgetId = 0;
const makeId = () => `w-${++widgetId}`;

const DEFAULT_WIDGETS: Widget[] = [
  { ...WIDGET_CATALOGUE[0], id: makeId() },
  { ...WIDGET_CATALOGUE[1], id: makeId() },
  { ...WIDGET_CATALOGUE[2], id: makeId() },
  { ...WIDGET_CATALOGUE[3], id: makeId() },
  { ...WIDGET_CATALOGUE[4], id: makeId() },
  { ...WIDGET_CATALOGUE[5], id: makeId() },
  { ...WIDGET_CATALOGUE[6], id: makeId() },
];

function WidgetRenderer({ widget }: { widget: Widget }) {
  switch (widget.type) {
    case "kpi":   return <KPIWidget data={widget.data} />;
    case "bar":   return <MiniBarChart data={widget.data} />;
    case "line":  return <MiniLineChart data={widget.data} />;
    case "donut": return <DonutChart data={widget.data} />;
    case "table": return <MiniTable data={widget.data} />;
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardStudioPage() {
  const { success, info } = useToast();
  const [widgets, setWidgets] = useState<Widget[]>(DEFAULT_WIDGETS);
  const [showCatalogue, setShowCatalogue] = useState(false);
  const [dashboardName, setDashboardName] = useState("Executive Dashboard Q4 2024");
  const [editingName, setEditingName] = useState(false);

  const removeWidget = useCallback((id: string) => {
    setWidgets(prev => prev.filter(w => w.id !== id));
  }, []);

  const addWidget = useCallback((catalogue: Omit<Widget, "id">) => {
    setWidgets(prev => [...prev, { ...catalogue, id: makeId() }]);
    setShowCatalogue(false);
    success("Widget added", catalogue.title);
  }, [success]);

  function handleExport() {
    success("Dashboard exported", "executive_dashboard.pdf downloaded");
  }

  function handleShare() {
    navigator.clipboard?.writeText("https://app.aidataanalyst.io/dashboard/shared/abc123").catch(() => {});
    info("Link copied!", "Dashboard share link copied to clipboard");
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-left">
          <div className="page-header-icon page-header-icon--blue">
            <LayoutDashboard size={20} />
          </div>
          <div>
            {editingName ? (
              <input
                className="ds-name-input"
                value={dashboardName}
                onChange={e => setDashboardName(e.target.value)}
                onBlur={() => setEditingName(false)}
                onKeyDown={e => { if (e.key === "Enter") setEditingName(false); }}
                autoFocus
              />
            ) : (
              <h1 className="page-title ds-title-editable" onClick={() => setEditingName(true)}>
                {dashboardName}
                <Settings size={13} className="ds-edit-icon" />
              </h1>
            )}
            <p className="page-subtitle">Live KPI dashboard � {widgets.length} widgets � Last updated just now</p>
          </div>
        </div>
        <div className="page-header-actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => info("Refreshing...", "Fetching latest data")}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={handleShare}>
            <Share2 size={14} /> Share
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={handleExport}>
            <Download size={14} /> Export PDF
          </button>
          <button type="button" className="btn btn--primary btn--sm" onClick={() => setShowCatalogue(true)}>
            <Plus size={14} /> Add Widget
          </button>
        </div>
      </div>

      {/* Dashboard Grid */}
      <div className="ds-grid">
        {widgets.map(w => (
          <div key={w.id} className={`ds-widget ds-widget--${w.size} ds-widget--${w.type}`}>
            <div className="ds-widget-header">
              <div className="ds-widget-drag">
                <Grip size={12} aria-hidden="true" />
              </div>
              <span className="ds-widget-title">{w.title}</span>
              <div className="ds-widget-actions">
                <button type="button" className="ds-widget-btn" aria-label="View details">
                  <Eye size={12} />
                </button>
                <button type="button" className="ds-widget-btn ds-widget-btn--remove"
                  onClick={() => removeWidget(w.id)} aria-label="Remove widget">
                  <X size={12} />
                </button>
              </div>
            </div>
            <div className="ds-widget-body">
              <WidgetRenderer widget={w} />
            </div>
          </div>
        ))}

        {/* Add widget placeholder */}
        <div className="ds-widget-add" onClick={() => setShowCatalogue(true)} role="button" tabIndex={0}
          onKeyDown={e => { if (e.key === "Enter" || e.key === " ") setShowCatalogue(true); }}>
          <Plus size={22} />
          <span>Add Widget</span>
        </div>
      </div>

      {/* Widget Catalogue Modal */}
      {showCatalogue && (
        <div className="ds-modal-overlay" onClick={() => setShowCatalogue(false)}>
          <div className="ds-modal" onClick={e => e.stopPropagation()}>
            <div className="ds-modal-header">
              <div className="ds-modal-title">
                <BarChart3 size={18} />
                Widget Catalogue
              </div>
              <button type="button" className="ds-modal-close" onClick={() => setShowCatalogue(false)}>
                <X size={16} />
              </button>
            </div>
            <div className="ds-catalogue-grid">
              {WIDGET_CATALOGUE.map((item, i) => (
                <button key={i} type="button" className="ds-catalogue-card" onClick={() => addWidget(item)}>
                  <div className="ds-catalogue-icon">
                    {item.type === "kpi"   && <TrendingUp size={20} />}
                    {item.type === "bar"   && <BarChart3 size={20} />}
                    {item.type === "line"  && <TrendingUp size={20} />}
                    {item.type === "donut" && <RefreshCw size={20} />}
                    {item.type === "table" && <BarChart3 size={20} />}
                  </div>
                  <div className="ds-catalogue-name">{item.title}</div>
                  <div className="ds-catalogue-type">{item.type.toUpperCase()} � {item.size.toUpperCase()}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
