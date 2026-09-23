import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  AreaChart,
  BarChart3,
  Bell,
  Calendar,
  ChevronDown,
  Database,
  Download,
  FileText,
  Filter,
  LineChart,
  Map as MapIcon,
  MoreVertical,
  PieChart,
  Plus,
  RefreshCw,
  Search,
  ShoppingCart,
  Sparkles,
  Table2,
  Target,
  TrendingUp,
  Users,
  X,
} from 'lucide-react';
import {
  AnimatedCountUp,
  SelfFormingLineChart,
  SelfFormingBarChart,
  SelfFormingDonutChart,
  SelfFormingRankingBars,
  SelfFormingRegionMap,
  SelfFormingScatterChart,
  SelfFormingHeatmap,
  SelfFormingTreemap,
  SelfFormingTable,
  CustomerSegmentChart,
  InvalidConfigMessage,
} from '../../components/animatedGlowVisualizations';
import {
  transformChartData,
  getSensibleDefaults,
  parseDate,
  parseNumeric,
  numberValue,
} from '../../lib/chartDataTransforms';
import type { TransformedChartData } from '../../lib/chartDataTransforms';


type ChartType = 'Line' | 'Bar' | 'Pie' | 'Area' | 'Scatter' | 'Table' | 'Heatmap' | 'Treemap';
type FieldType = 'date' | 'category' | 'number' | 'boolean';
type FilterOperator =
  | 'equals'
  | 'notEquals'
  | 'contains'
  | 'greaterThan'
  | 'lessThan'
  | 'greaterThanOrEqual'
  | 'lessThanOrEqual'
  | 'before'
  | 'after'
  | 'between';
type Granularity = 'Daily' | 'Weekly' | 'Monthly' | 'Quarterly' | 'Yearly';
type TrendChartType = 'Line Chart' | 'Area Chart' | 'Bar Chart' | 'Pie Chart';
type ProductChartType = 'Donut Chart' | 'Pie Chart' | 'Bar Chart';
type SegmentChartType = 'Bar Chart' | 'Pie Chart' | 'Table';
type RegionView = 'Map View' | 'Bar View' | 'Table View';
type DateRangeId = 'all' | '2024' | '2025' | 'q1-2025' | 'last-6';

type CellValue = string | number | boolean | null;
type DataRow = Record<string, CellValue>;

interface VisualizationContextState {
  dataset?: string;
  question?: string;
  chartType?: ChartType;
}

interface DatasetDefinition {
  id: string;
  name: string;
  rowCount: number;
  columns: Record<string, FieldType>;
  rows: DataRow[];
}

interface VisualizationConfig {
  chartType: ChartType;
  xAxis: string;
  yAxis: string;
  groupBy: string;
  filters: ActiveFilter[];
}

interface ActiveFilter {
  id: number;
  field: string;
  operator: FilterOperator;
  value: string;
  valueTo?: string;
}

interface ChartPoint {
  label: string;
  value: number;
  group?: string;
}

interface DraftFilter {
  field: string;
  operator: FilterOperator;
  value: string;
  valueTo: string;
}

const tabs = ['Explore', 'Gallery', 'Saved', 'Templates'] as const;

const chartTypes: { type: ChartType; icon: typeof LineChart }[] = [
  { type: 'Line', icon: LineChart },
  { type: 'Bar', icon: BarChart3 },
  { type: 'Pie', icon: PieChart },
  { type: 'Area', icon: AreaChart },
  { type: 'Scatter', icon: Sparkles },
  { type: 'Table', icon: Table2 },
  { type: 'Heatmap', icon: MapIcon },
  { type: 'Treemap', icon: FileText },
];

const dateRanges: { id: DateRangeId; label: string; start?: string; end?: string }[] = [
  { id: 'all', label: 'Jan 2024 - Dec 2025' },
  { id: '2024', label: '2024', start: '2024-01-01', end: '2024-12-31' },
  { id: '2025', label: '2025', start: '2025-01-01', end: '2025-12-31' },
  { id: 'q1-2025', label: 'Q1 2025', start: '2025-01-01', end: '2025-03-31' },
  { id: 'last-6', label: 'Last 6 months', start: '2025-07-01', end: '2025-12-31' },
];

const datasets: DatasetDefinition[] = [
  {
    id: 'sales',
    name: 'Sales_Data_2026.xlsx',
    rowCount: 20450,
    columns: {
      orderDate: 'date',
      productCategory: 'category',
      product: 'category',
      customerSegment: 'category',
      region: 'category',
      revenue: 'number',
      profit: 'number',
      orders: 'number',
      quantity: 'number',
      discount: 'number',
      customers: 'number',
      conversionRate: 'number',
    },
    rows: [
      ['2024-01-12', 'Electronics', 'Laptop', 'Consumer', 'North America', 124000, 34200, 820, 960, 6, 640, 3.1],
      ['2024-02-10', 'Clothing', 'Jacket', 'Corporate', 'Europe', 86000, 23600, 640, 880, 12, 520, 2.8],
      ['2024-03-15', 'Home & Living', 'Desk', 'Home Office', 'Asia', 72000, 19400, 510, 610, 8, 430, 2.5],
      ['2024-04-20', 'Electronics', 'Smartphone', 'Consumer', 'North America', 142000, 40800, 970, 1120, 5, 710, 3.4],
      ['2024-05-16', 'Books', 'Business Books', 'Small Business', 'South America', 38000, 11200, 460, 720, 15, 310, 2.2],
      ['2024-06-18', 'Electronics', 'Tablet', 'Corporate', 'Europe', 112000, 30200, 760, 820, 7, 590, 3.0],
      ['2024-07-22', 'Home & Living', 'Office Chair', 'Consumer', 'Asia', 94000, 26800, 690, 740, 10, 530, 2.9],
      ['2024-08-19', 'Clothing', 'Sneakers', 'Consumer', 'North America', 98000, 25100, 710, 990, 14, 610, 3.0],
      ['2024-09-14', 'Electronics', 'Monitor', 'Corporate', 'Europe', 118000, 32600, 800, 870, 9, 600, 3.2],
      ['2024-10-12', 'Home & Living', 'Bookshelf', 'Home Office', 'Asia', 76000, 18200, 540, 620, 11, 440, 2.6],
      ['2024-11-20', 'Electronics', 'Headphones', 'Consumer', 'North America', 132000, 37400, 910, 1300, 8, 700, 3.5],
      ['2024-12-18', 'Clothing', 'Winter Coat', 'Small Business', 'Europe', 106000, 28400, 760, 890, 13, 570, 2.9],
      ['2025-01-11', 'Electronics', 'Laptop', 'Corporate', 'North America', 158000, 44800, 1040, 1180, 5, 780, 3.6],
      ['2025-02-13', 'Books', 'Fiction Bundle', 'Consumer', 'Asia', 46000, 12600, 520, 780, 18, 390, 2.4],
      ['2025-03-17', 'Home & Living', 'Desk', 'Home Office', 'Europe', 90000, 24600, 650, 700, 9, 510, 2.9],
      ['2025-04-12', 'Electronics', 'Smartwatch', 'Consumer', 'North America', 128000, 35200, 860, 990, 7, 680, 3.3],
      ['2025-05-19', 'Clothing', 'Shirt', 'Small Business', 'South America', 64000, 16400, 610, 840, 16, 480, 2.5],
      ['2025-06-15', 'Electronics', 'Tablet', 'Corporate', 'Asia', 136000, 38400, 920, 980, 6, 720, 3.4],
      ['2025-07-12', 'Home & Living', 'Office Chair', 'Consumer', 'North America', 118000, 31600, 790, 850, 10, 620, 3.1],
      ['2025-08-18', 'Electronics', 'Monitor', 'Corporate', 'Europe', 146000, 41400, 960, 1010, 7, 730, 3.5],
      ['2025-09-16', 'Books', 'Business Books', 'Home Office', 'Asia', 52000, 14800, 560, 820, 14, 430, 2.6],
      ['2025-10-14', 'Clothing', 'Sneakers', 'Consumer', 'North America', 122000, 30200, 830, 1080, 12, 660, 3.2],
      ['2025-11-11', 'Electronics', 'Headphones', 'Small Business', 'Europe', 138000, 39800, 940, 1360, 9, 700, 3.4],
      ['2025-12-09', 'Home & Living', 'Desk', 'Corporate', 'Asia', 108000, 28600, 740, 800, 8, 580, 3.0],
    ].map(([orderDate, productCategory, product, customerSegment, region, revenue, profit, orders, quantity, discount, customers, conversionRate]) => ({
      orderDate, productCategory, product, customerSegment, region, revenue, profit, orders, quantity, discount, customers, conversionRate,
    })),
  },
  {
    id: 'marketing',
    name: 'Marketing_Spend_2025.csv',
    rowCount: 12840,
    columns: {
      orderDate: 'date',
      productCategory: 'category',
      product: 'category',
      customerSegment: 'category',
      region: 'category',
      revenue: 'number',
      profit: 'number',
      orders: 'number',
      quantity: 'number',
      discount: 'number',
      customers: 'number',
      conversionRate: 'number',
    },
    rows: [
      ['2024-01-08', 'Search', 'Brand Campaign', 'Consumer', 'North America', 76000, 21000, 520, 610, 9, 460, 2.7],
      ['2024-02-14', 'Social', 'Launch Ads', 'Small Business', 'Europe', 68000, 17600, 470, 540, 14, 390, 2.4],
      ['2024-03-19', 'Email', 'Retention Flow', 'Corporate', 'Asia', 54000, 19400, 430, 450, 4, 360, 3.2],
      ['2024-04-16', 'Search', 'Competitor Campaign', 'Consumer', 'North America', 92000, 24400, 650, 720, 11, 540, 2.9],
      ['2024-05-21', 'Display', 'Awareness Banners', 'Home Office', 'South America', 42000, 9200, 360, 410, 18, 280, 2.0],
      ['2024-06-12', 'Social', 'Creator Program', 'Consumer', 'Europe', 88000, 23600, 620, 700, 13, 520, 2.8],
      ['2024-07-18', 'Email', 'Lifecycle Campaign', 'Corporate', 'Asia', 64000, 21800, 480, 500, 5, 410, 3.4],
      ['2024-08-10', 'Search', 'High Intent', 'Small Business', 'North America', 104000, 30200, 720, 800, 8, 610, 3.3],
      ['2024-09-13', 'Display', 'Retargeting', 'Consumer', 'Europe', 58000, 15600, 420, 470, 15, 350, 2.5],
      ['2024-10-11', 'Social', 'Holiday Teasers', 'Home Office', 'Asia', 84000, 22600, 610, 690, 12, 510, 2.9],
      ['2024-11-20', 'Search', 'Holiday Search', 'Consumer', 'North America', 118000, 34800, 810, 910, 7, 690, 3.5],
      ['2024-12-15', 'Email', 'Holiday Offers', 'Corporate', 'Europe', 96000, 31600, 690, 710, 6, 570, 3.7],
      ['2025-01-09', 'Social', 'New Year Launch', 'Consumer', 'North America', 98000, 27200, 720, 820, 10, 610, 3.1],
      ['2025-02-11', 'Display', 'Pipeline Nurture', 'Small Business', 'South America', 52000, 13200, 410, 470, 17, 330, 2.3],
      ['2025-03-18', 'Search', 'High Intent', 'Corporate', 'Asia', 112000, 33600, 780, 850, 7, 650, 3.6],
      ['2025-04-14', 'Email', 'Expansion Flow', 'Consumer', 'Europe', 74000, 25400, 560, 590, 5, 470, 3.4],
      ['2025-05-15', 'Social', 'Creator Program', 'Consumer', 'North America', 126000, 35800, 860, 970, 11, 720, 3.4],
      ['2025-06-19', 'Search', 'Brand Campaign', 'Corporate', 'Europe', 108000, 32200, 750, 820, 8, 620, 3.3],
      ['2025-07-12', 'Display', 'Awareness Banners', 'Home Office', 'Asia', 66000, 16800, 510, 560, 16, 420, 2.6],
      ['2025-08-16', 'Social', 'Launch Ads', 'Consumer', 'North America', 134000, 38200, 930, 1040, 10, 760, 3.5],
      ['2025-09-13', 'Email', 'Retention Flow', 'Corporate', 'Europe', 82000, 29400, 610, 640, 5, 520, 3.6],
      ['2025-10-10', 'Search', 'Competitor Campaign', 'Small Business', 'Asia', 96000, 26800, 690, 760, 9, 570, 3.1],
      ['2025-11-17', 'Social', 'Holiday Teasers', 'Consumer', 'North America', 142000, 40400, 980, 1110, 12, 790, 3.6],
      ['2025-12-12', 'Email', 'Holiday Offers', 'Corporate', 'Europe', 116000, 39800, 800, 830, 6, 660, 3.8],
    ].map(([orderDate, productCategory, product, customerSegment, region, revenue, profit, orders, quantity, discount, customers, conversionRate]) => ({
      orderDate, productCategory, product, customerSegment, region, revenue, profit, orders, quantity, discount, customers, conversionRate,
    })),
  },
];

const operatorLabels: Record<FilterOperator, string> = {
  equals: 'Equals',
  notEquals: 'Not equals',
  contains: 'Contains',
  greaterThan: 'Greater than',
  lessThan: 'Less than',
  greaterThanOrEqual: 'Greater than or equal',
  lessThanOrEqual: 'Less than or equal',
  before: 'Before',
  after: 'After',
  between: 'Between',
};

function fieldLabel(field: string): string {
  return field.replace(/([A-Z])/g, ' $1').replace(/^./, (char) => char.toUpperCase());
}

function formatCompact(value: number, prefix = ''): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${prefix}${(value / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${prefix}${(value / 1_000).toFixed(1)}K`;
  return `${prefix}${Math.round(value).toLocaleString()}`;
}

function getDateKey(value: CellValue | Date, granularity: Granularity): string {
  const date = value instanceof Date ? value : parseDate(value);
  if (!date) return 'Unknown';
  const year = date.getFullYear();
  const month = date.getMonth();
  if (granularity === 'Daily') return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  if (granularity === 'Weekly') {
    const start = new Date(year, 0, 1);
    const week = Math.ceil((((date.getTime() - start.getTime()) / 86400000) + start.getDay() + 1) / 7);
    return `W${week} '${String(year).slice(-2)}`;
  }
  if (granularity === 'Quarterly') return `Q${Math.floor(month / 3) + 1} '${String(year).slice(-2)}`;
  if (granularity === 'Yearly') return String(year);
  return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}

function filterByDateRange(rows: DataRow[], dateRangeId: DateRangeId): DataRow[] {
  const range = dateRanges.find((item) => item.id === dateRangeId);
  if (!range?.start || !range.end) return rows;
  const start = parseDate(range.start);
  const end = parseDate(range.end);
  if (!start || !end) return rows;
  end.setHours(23, 59, 59, 999);

  return rows.filter((row) => {
    const current = parseDate(row.orderDate);
    return current ? current >= start && current <= end : false;
  });
}

function applyFilter(row: DataRow, filter: ActiveFilter, fieldType: FieldType): boolean {
  const value = row[filter.field];
  if (fieldType === 'number') {
    const actual = parseNumeric(value);
    const target = parseNumeric(filter.value);
    if (actual === null || target === null) return true;
    if (filter.operator === 'equals') return actual === target;
    if (filter.operator === 'greaterThan') return actual > target;
    if (filter.operator === 'lessThan') return actual < target;
    if (filter.operator === 'greaterThanOrEqual') return actual >= target;
    if (filter.operator === 'lessThanOrEqual') return actual <= target;
    if (filter.operator === 'notEquals') return actual !== target;
    return true;
  }

  if (fieldType === 'date') {
    const actual = parseDate(value);
    const target = parseDate(filter.value);
    const targetTo = filter.valueTo ? parseDate(filter.valueTo) : null;
    if (!actual || !target) return true;
    if (filter.operator === 'before') return actual < target;
    if (filter.operator === 'after') return actual > target;
    if (filter.operator === 'between') return targetTo ? actual >= target && actual <= targetTo : true;
    return actual.toDateString() === target.toDateString();
  }

  const actualText = String(value ?? '').toLowerCase().trim();
  const targetText = filter.value.toLowerCase().trim();
  if (filter.operator === 'notEquals') return actualText !== targetText;
  if (filter.operator === 'contains') return actualText.includes(targetText);
  return actualText === targetText;
}

function applyFilters(rows: DataRow[], filters: ActiveFilter[], columns: Record<string, FieldType>): DataRow[] {
  return rows.filter((row) => filters.every((filter) => applyFilter(row, filter, columns[filter.field])));
}

function aggregateCategory(rows: DataRow[], category: string, metric: string, limit = 8): ChartPoint[] {
  const buckets = new Map<string, number>();
  rows.forEach((row) => {
    const label = String(row[category] ?? 'Unknown').trim();
    if (!label || label === 'null' || label === 'undefined') return;
    const val = parseNumeric(row[metric]) ?? 0;
    buckets.set(label, (buckets.get(label) ?? 0) + val);
  });
  return Array.from(buckets.entries())
    .map(([label, value]) => ({ label, value: Math.round(value * 100) / 100 }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

function aggregateTrend(rows: DataRow[], metric: string, granularity: Granularity): ChartPoint[] {
  const buckets = new Map<string, { label: string; date: Date; value: number }>();
  rows.forEach((row) => {
    const d = parseDate(row.orderDate);
    if (!d) return;
    const key = getDateKey(d, granularity);
    const val = parseNumeric(row[metric]) ?? 0;
    const existing = buckets.get(key) ?? { label: key, date: d, value: 0 };
    existing.value += val;
    if (d < existing.date) existing.date = d;
    buckets.set(key, existing);
  });

  return Array.from(buckets.values())
    .sort((a, b) => a.date.getTime() - b.date.getTime())
    .map(({ label, value }) => ({ label, value: Math.round(value * 100) / 100 }));
}

function getFieldOptions(columns: Record<string, FieldType>, type?: FieldType): string[] {
  return Object.entries(columns)
    .filter(([, fieldType]) => !type || fieldType === type)
    .map(([field]) => field);
}

function getOperators(fieldType: FieldType): FilterOperator[] {
  if (fieldType === 'number') return ['equals', 'greaterThan', 'lessThan', 'greaterThanOrEqual', 'lessThanOrEqual', 'notEquals'];
  if (fieldType === 'date') return ['before', 'after', 'between', 'equals'];
  return ['equals', 'notEquals', 'contains'];
}

function SelectControl({
  label,
  value,
  options,
  onChange,
  icon,
  className = '',
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <label className={`viz-select-label ${className}`}>
      <span className="sr-only">{label}</span>
      {icon}
      <select className="viz-select" value={value} onChange={(event) => onChange(event.target.value)} aria-label={label}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown size={14} aria-hidden="true" />
    </label>
  );
}

function FieldSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="viz-field">
      <span>{label}</span>
      <select className="viz-select" value={value} onChange={(event) => onChange(event.target.value)} aria-label={label}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option ? fieldLabel(option) : 'None'}
          </option>
        ))}
      </select>
    </label>
  );
}

function EmptyChart({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <div className="viz-empty" role="status">
      <strong>No data available for the selected filters.</strong>
      <button type="button" onClick={onClearFilters}>Clear filters</button>
    </div>
  );
}

function MetricChart({
  type,
  data,
  transformed,
  ariaLabel,
  onClearFilters,
  onResetConfig,
  replayKey,
}: {
  type: ChartType | TrendChartType | ProductChartType | SegmentChartType | RegionView;
  data?: ChartPoint[];
  transformed?: TransformedChartData;
  ariaLabel: string;
  onClearFilters: () => void;
  onResetConfig?: () => void;
  replayKey?: string | number;
}) {
  if (transformed) {
    if (!transformed.isValid) {
      return (
        <InvalidConfigMessage
          message={transformed.validationMessage}
          onReset={onResetConfig}
        />
      );
    }

    if (transformed.type === 'Table') {
      return <SelfFormingTable tableData={transformed.tableData} ariaLabel={ariaLabel} replayKey={replayKey} />;
    }

    if (transformed.type === 'Pie') {
      return (
        <SelfFormingDonutChart
          data={transformed.points ?? []}
          ariaLabel={ariaLabel}
          isPie
          replayKey={replayKey}
        />
      );
    }

    if (transformed.type === 'Bar') {
      return <SelfFormingBarChart data={transformed.points ?? []} ariaLabel={ariaLabel} replayKey={replayKey} />;
    }

    if (transformed.type === 'Scatter') {
      return (
        <SelfFormingScatterChart
          scatterPoints={transformed.scatterPoints}
          bounds={transformed.scatterBounds}
          ariaLabel={ariaLabel}
          replayKey={replayKey}
        />
      );
    }

    if (transformed.type === 'Heatmap') {
      return <SelfFormingHeatmap heatmapData={transformed.heatmapData} ariaLabel={ariaLabel} replayKey={replayKey} />;
    }

    if (transformed.type === 'Treemap') {
      return <SelfFormingTreemap treemapData={transformed.treemapData} ariaLabel={ariaLabel} replayKey={replayKey} />;
    }

    if (transformed.type === 'Area') {
      return (
        <SelfFormingLineChart
          data={transformed.points ?? []}
          ariaLabel={ariaLabel}
          isArea
          replayKey={replayKey}
        />
      );
    }

    return (
      <SelfFormingLineChart
        data={transformed.points ?? []}
        ariaLabel={ariaLabel}
        isArea={false}
        replayKey={replayKey}
      />
    );
  }

  if (!data || data.length === 0) return <EmptyChart onClearFilters={onClearFilters} />;

  if (type === 'Table' || type === 'Table View') {
    return (
      <SelfFormingTable
        tableData={{
          columns: [
            { key: 'label', label: 'Category', type: 'category' },
            { key: 'value', label: 'Value', type: 'number' },
          ],
          rows: data.map((d) => ({ label: d.label, value: d.value })),
          totalCount: data.length,
        }}
        ariaLabel={ariaLabel}
        replayKey={replayKey}
      />
    );
  }

  if (type === 'Pie' || type === 'Donut Chart' || type === 'Pie Chart') {
    return (
      <SelfFormingDonutChart
        data={data}
        ariaLabel={ariaLabel}
        isPie={type === 'Pie' || type === 'Pie Chart'}
        replayKey={replayKey}
      />
    );
  }

  if (type === 'Bar' || type === 'Bar Chart' || type === 'Bar View') {
    return <SelfFormingBarChart data={data} ariaLabel={ariaLabel} replayKey={replayKey} />;
  }

  return (
    <SelfFormingLineChart
      data={data}
      ariaLabel={ariaLabel}
      isArea={type === 'Area' || type === 'Area Chart'}
      replayKey={replayKey}
    />
  );
}

function RegionChart({
  view,
  data,
  filteredRows,
  onClearFilters,
  replayKey,
}: {
  view: RegionView;
  data: ChartPoint[];
  filteredRows?: DataRow[];
  onClearFilters: () => void;
  replayKey?: string | number;
}) {
  if (view !== 'Map View') {
    return (
      <MetricChart
        type={view}
        data={data}
        ariaLabel="Revenue by region"
        onClearFilters={onClearFilters}
        replayKey={replayKey}
      />
    );
  }
  return <SelfFormingRegionMap data={data} filteredRows={filteredRows} replayKey={replayKey} />;
}

function MiniPreview({ kind }: { kind: string }) {
  if (kind === 'donut') return <div className="viz-mini-donut" aria-hidden="true" />;
  if (kind === 'bars') return <div className="viz-mini-bars" aria-hidden="true"><span /><span /><span /><span /></div>;
  if (kind === 'map') return <div className="viz-mini-map" aria-hidden="true" />;
  return <svg viewBox="0 0 120 46" aria-hidden="true"><polyline points="0,38 20,28 38,20 56,24 76,13 96,10 120,3" /></svg>;
}

export default function VisualizationsPage() {
  const location = useLocation();
  const context = (location.state as VisualizationContextState | null) ?? {};
  const initialDataset = datasets.find((dataset) => dataset.name === context.dataset)?.id ?? datasets[0].id;
  const [datasetId, setDatasetId] = useState(initialDataset);
  const [dateRangeId, setDateRangeId] = useState<DateRangeId>('all');
  const [compareEnabled, setCompareEnabled] = useState(false);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>('Explore');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [renderTrigger, setRenderTrigger] = useState(0);
  const [trendType, setTrendType] = useState<TrendChartType>('Line Chart');
  const [granularity, setGranularity] = useState<Granularity>('Monthly');
  const [productType, setProductType] = useState<ProductChartType>('Donut Chart');
  const [segmentType, setSegmentType] = useState<SegmentChartType>('Bar Chart');
  const [regionView, setRegionView] = useState<RegionView>('Map View');
  const [config, setConfig] = useState<VisualizationConfig>(() => {
    const defaultType = context.chartType ?? 'Line';
    return {
      chartType: defaultType,
      xAxis: 'orderDate',
      yAxis: 'customers',
      groupBy: '',
      filters: [],
    };
  });

  const dataset = useMemo(() => datasets.find((item) => item.id === datasetId) ?? datasets[0], [datasetId]);
  const numericFields = useMemo(() => getFieldOptions(dataset.columns, 'number'), [dataset]);
  const categoricalFields = useMemo(() => getFieldOptions(dataset.columns, 'category'), [dataset]);
  const allFields = useMemo(() => Object.keys(dataset.columns), [dataset]);
  const [draftFilter, setDraftFilter] = useState<DraftFilter>({
    field: 'region',
    operator: 'equals',
    value: 'North America',
    valueTo: '',
  });

  const dateRows = useMemo(() => filterByDateRange(dataset.rows, dateRangeId), [dataset.rows, dateRangeId]);
  const filteredRows = useMemo(() => applyFilters(dateRows, config.filters, dataset.columns), [config.filters, dataset.columns, dateRows]);
  
  const builderTransformed = useMemo(() => {
    return transformChartData(filteredRows, dataset.columns, config);
  }, [filteredRows, dataset.columns, config]);

  const trendData = useMemo(() => aggregateTrend(filteredRows, 'revenue', granularity), [filteredRows, granularity]);
  const productData = useMemo(() => aggregateCategory(filteredRows, 'productCategory', 'revenue', 6), [filteredRows]);
  const segmentData = useMemo(() => aggregateCategory(filteredRows, 'customerSegment', 'revenue', 6), [filteredRows]);
  const regionData = useMemo(() => aggregateCategory(filteredRows, 'region', 'revenue', 6), [filteredRows]);
  const topProductData = useMemo(() => aggregateCategory(filteredRows, 'product', 'revenue', 10), [filteredRows]);

  const totalRevenue = filteredRows.reduce((sum, row) => sum + numberValue(row.revenue), 0);
  const totalOrders = filteredRows.reduce((sum, row) => sum + numberValue(row.orders), 0);
  const totalCustomers = filteredRows.reduce((sum, row) => sum + numberValue(row.customers), 0);
  const conversionAverage = filteredRows.length
    ? filteredRows.reduce((sum, row) => sum + numberValue(row.conversionRate), 0) / filteredRows.length
    : 0;
  const previousRows = dataset.rows.filter((row) => !dateRows.includes(row)).slice(-Math.max(1, filteredRows.length));
  const previousRevenue = previousRows.reduce((sum, row) => sum + numberValue(row.revenue), 0);
  const revenueTrend = previousRevenue > 0 ? ((totalRevenue - previousRevenue) / previousRevenue) * 100 : 0;
  const filteredBySearch = search.trim()
    ? [config.yAxis, config.xAxis, config.groupBy, ...config.filters.map((filter) => filter.field)]
      .some((value) => fieldLabel(value).toLowerCase().includes(search.trim().toLowerCase()))
    : true;

  const clearFilters = () => setConfig((current) => ({ ...current, filters: [] }));

  function updateConfig(patch: Partial<VisualizationConfig>) {
    setConfig((current) => ({ ...current, ...patch }));
  }

  function handleChartTypeChange(nextType: ChartType) {
    const sensible = getSensibleDefaults(nextType, dataset.columns, config);
    setConfig((prev) => ({
      ...prev,
      chartType: nextType,
      xAxis: sensible.xAxis,
      yAxis: sensible.yAxis,
      groupBy: sensible.groupBy,
    }));
  }

  function handleAutoFixConfig() {
    const sensible = getSensibleDefaults(config.chartType, dataset.columns, config);
    setConfig((prev) => ({
      ...prev,
      xAxis: sensible.xAxis,
      yAxis: sensible.yAxis,
      groupBy: sensible.groupBy,
    }));
  }

  function handleDatasetChange(nextDatasetId: string) {
    const nextDataset = datasets.find((item) => item.id === nextDatasetId) ?? datasets[0];
    const nextCategoricalFields = getFieldOptions(nextDataset.columns, 'category');
    const nextAllFields = Object.keys(nextDataset.columns);
    setDatasetId(nextDataset.id);
    const sensible = getSensibleDefaults(config.chartType, nextDataset.columns, config);
    setConfig((current) => ({
      ...current,
      xAxis: nextDataset.columns[current.xAxis] ? current.xAxis : sensible.xAxis,
      yAxis: nextDataset.columns[current.yAxis] ? current.yAxis : sensible.yAxis,
      groupBy: current.groupBy && nextDataset.columns[current.groupBy] ? current.groupBy : sensible.groupBy,
      filters: current.filters.filter((filter) => nextDataset.columns[filter.field]),
    }));
    setDraftFilter({
      field: nextCategoricalFields[0] ?? nextAllFields[0],
      operator: 'equals',
      value: '',
      valueTo: '',
    });
  }

  function handleApplyFilter() {
    const fieldType = dataset.columns[draftFilter.field];
    const value = draftFilter.value.trim();
    if (!fieldType || !value) return;
    const operator = getOperators(fieldType).includes(draftFilter.operator) ? draftFilter.operator : getOperators(fieldType)[0];
    setConfig((current) => ({
      ...current,
      filters: [...current.filters, { id: Date.now(), field: draftFilter.field, operator, value, valueTo: draftFilter.valueTo }],
    }));
    setIsFilterOpen(false);
  }

  function handleUpdateVisualization() {
    setIsUpdating(true);
    setRenderTrigger((current) => current + 1);
    window.setTimeout(() => setIsUpdating(false), 200);
  }

  const animationKey = useMemo(() => {
    return [
      datasetId,
      dateRangeId,
      config.chartType,
      config.xAxis,
      config.yAxis,
      config.groupBy,
      config.filters.map((f) => `${f.field}:${f.operator}:${f.value}`).join(';'),
      trendType,
      granularity,
      productType,
      segmentType,
      regionView,
      renderTrigger,
      isUpdating ? 'updating' : 'stable',
    ].join('|');
  }, [datasetId, dateRangeId, config, trendType, granularity, productType, segmentType, regionView, renderTrigger, isUpdating]);

  const kpis = [
    { label: 'Total Revenue', rawValue: totalRevenue, prefix: '$', formatCompact: true, trend: `${Math.abs(revenueTrend).toFixed(1)}%`, direction: revenueTrend >= 0 ? 'up' : 'down', icon: TrendingUp },
    { label: 'Total Orders', rawValue: totalOrders, formatCompact: true, trend: `${filteredRows.length} rows`, direction: 'up', icon: ShoppingCart },
    { label: 'Active Customers', rawValue: totalCustomers, formatCompact: true, trend: compareEnabled ? 'comparison on' : 'current period', direction: 'up', icon: Users },
    { label: 'Conversion Rate', rawValue: conversionAverage, suffix: '%', decimals: 2, trend: `${config.filters.length} filters`, direction: config.filters.length ? 'down' : 'up', icon: Target },
  ] as const;

  const recentVisualizations = [
    { title: `${fieldLabel(config.yAxis)} by ${fieldLabel(config.xAxis)}`, when: 'Just now', kind: config.chartType.toLowerCase() },
    { title: 'Product Distribution', when: '1 day ago', kind: 'donut' },
    { title: 'Customer Segments', when: '2 days ago', kind: 'bars' },
    { title: 'Regional Analysis', when: '3 days ago', kind: 'map' },
  ];

  const insights = [
    {
      title: filteredRows.length ? 'Strongest Category' : 'No Matching Rows',
      body: filteredRows.length
        ? `${productData[0]?.label ?? 'Category'} leads ${fieldLabel(config.yAxis).toLowerCase()} at ${formatCompact(productData[0]?.value ?? 0, '$')}.`
        : 'Clear or adjust filters to restore chart results.',
      icon: TrendingUp,
    },
    {
      title: 'Top Segment',
      body: `${segmentData[0]?.label ?? 'No segment'} contributes the strongest share for the selected metric.`,
      icon: Users,
    },
    {
      title: 'Best Region',
      body: `${regionData[0]?.label ?? 'No region'} is the highest regional contributor in this view.`,
      icon: MapIcon,
    },
  ] as const;

  const currentFieldType = dataset.columns[draftFilter.field] ?? 'category';
  const draftOptions = Array.from(new Set(dataset.rows.map((row) => String(row[draftFilter.field] ?? '')).filter(Boolean)));

  return (
    <div className="viz-workspace">
      <header className="viz-commandbar" aria-label="Visualization workspace actions">
        <label className="viz-search">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search visualizations</span>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search datasets, visualizations, or ask AI..." />
        </label>
        <div className="viz-command-actions">
          <button type="button" className="viz-action-primary" onClick={() => updateConfig({ chartType: 'Line', xAxis: 'orderDate', yAxis: 'revenue', groupBy: 'productCategory', filters: [] })}><Plus size={15} aria-hidden="true" /> New Visualization</button>
          <div className="viz-popover-wrap">
            <button type="button" className="viz-icon-button" aria-label="Notifications" aria-expanded={isNotificationsOpen} onClick={() => setIsNotificationsOpen((current) => !current)}><Bell size={16} /></button>
            {isNotificationsOpen && (
              <div className="viz-popover" role="status">
                <strong>Visualization ready</strong>
                <span>{fieldLabel(config.yAxis)} view updated from {filteredRows.length} rows.</span>
              </div>
            )}
          </div>
          <div className="viz-popover-wrap">
            <button type="button" className="viz-user-button" aria-label="User menu" aria-expanded={isUserMenuOpen} onClick={() => setIsUserMenuOpen((current) => !current)}>U <ChevronDown size={13} aria-hidden="true" /></button>
            {isUserMenuOpen && (
              <div className="viz-popover" role="menu">
                <Link to="/profile" role="menuitem">Profile</Link>
                <Link to="/settings" role="menuitem">Settings</Link>
              </div>
            )}
          </div>
        </div>
      </header>

      <section className="viz-header" aria-labelledby="visualizations-heading">
        <div>
          <h1 id="visualizations-heading">Visualizations</h1>
          <p>Turn your data into powerful visual stories</p>
        </div>
        <span>Create <span aria-hidden="true">-</span> Customize <span aria-hidden="true">-</span> Share <span aria-hidden="true">-</span> Gain Insights</span>
      </section>

      <nav className="viz-tabs" aria-label="Visualization workspace tabs">
        {tabs.map((tab) => (
          <button key={tab} type="button" className={activeTab === tab ? 'viz-tab viz-tab--active' : 'viz-tab'} onClick={() => setActiveTab(tab)} aria-current={activeTab === tab ? 'page' : undefined}>
            {tab}
          </button>
        ))}
      </nav>

      <section className="viz-contextbar" aria-label="Dataset context">
        <div className="viz-context-left">
          <Database size={16} aria-hidden="true" />
          <span>Dataset</span>
          <SelectControl
            label="Dataset"
            value={datasetId}
            options={datasets.map((item) => ({ value: item.id, label: item.name }))}
            onChange={handleDatasetChange}
            className="viz-select--dataset"
          />
          <span className="viz-muted">{filteredRows.length.toLocaleString()} of {dataset.rowCount.toLocaleString()} rows <span aria-hidden="true">-</span> {Object.keys(dataset.columns).length} columns</span>
          <span className="viz-loaded">Loaded</span>
        </div>
        <div className="viz-context-right">
          <SelectControl
            label="Date range"
            value={dateRangeId}
            options={dateRanges.map((range) => ({ value: range.id, label: range.label }))}
            onChange={(value) => setDateRangeId(value as DateRangeId)}
            icon={<Calendar size={14} aria-hidden="true" />}
          />
          <button type="button" className={compareEnabled ? 'viz-select viz-select--active' : 'viz-select'} onClick={() => setCompareEnabled((current) => !current)} aria-pressed={compareEnabled}>Compare</button>
        </div>
      </section>

      {context.question && <p className="viz-context-note">Generated from analysis prompt: "{context.question}"</p>}
      {!filteredBySearch && <p className="viz-context-note">No visualization metadata matched the current search.</p>}

      <section className="viz-kpi-grid" aria-label="Key metrics">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <article key={kpi.label} className={`viz-kpi viz-kpi--${kpi.direction}`}>
              <div className="viz-kpi-icon"><Icon size={20} aria-hidden="true" /></div>
              <div>
                <p>{kpi.label}</p>
                <strong>
                  {filteredRows.length ? (
                    <AnimatedCountUp
                      targetValue={kpi.rawValue}
                      prefix={'prefix' in kpi ? kpi.prefix : ''}
                      suffix={'suffix' in kpi ? kpi.suffix : ''}
                      decimals={'decimals' in kpi ? kpi.decimals : 0}
                      formatAsCompact={'formatCompact' in kpi ? kpi.formatCompact : false}
                      replayKey={animationKey}
                    />
                  ) : '-'}
                </strong>
                <span>{kpi.direction === 'up' ? 'Up' : 'Down'} {kpi.trend} <em>vs. baseline</em></span>
              </div>
            </article>
          );
        })}
      </section>

      <div className="viz-main-grid">
        <div className="viz-chart-grid-area">
          <section className="viz-card viz-card--wide" aria-labelledby="revenue-trend-heading" aria-busy={isUpdating}>
            <div className="viz-card-header">
              <div><h2 id="revenue-trend-heading">Revenue Trend</h2><p>{granularity} revenue across selected data</p></div>
              <div className="viz-card-actions">
                <SelectControl label="Revenue trend chart type" value={trendType} options={['Line Chart', 'Area Chart', 'Bar Chart', 'Pie Chart'].map((value) => ({ value, label: value }))} onChange={(value) => setTrendType(value as TrendChartType)} />
                <SelectControl label="Revenue trend granularity" value={granularity} options={['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'].map((value) => ({ value, label: value }))} onChange={(value) => setGranularity(value as Granularity)} />
                <button type="button" aria-label="Download revenue trend" onClick={() => window.alert('Revenue trend export prepared for the current view.')}><Download size={16} /></button>
              </div>
            </div>
            {isUpdating ? <div className="viz-loading">Updating visualization...</div> : <MetricChart type={trendType} data={trendData} ariaLabel={`${granularity} revenue trend`} onClearFilters={clearFilters} replayKey={animationKey} />}
          </section>

          <section className="viz-card" aria-labelledby="product-category-heading">
            <div className="viz-card-header">
              <h2 id="product-category-heading">Sales by Product Category</h2>
              <SelectControl label="Product category chart type" value={productType} options={['Donut Chart', 'Pie Chart', 'Bar Chart'].map((value) => ({ value, label: value }))} onChange={(value) => setProductType(value as ProductChartType)} />
            </div>
            <MetricChart type={productType} data={productData} ariaLabel="Sales by product category" onClearFilters={clearFilters} replayKey={animationKey} />
          </section>

          <section className="viz-card" aria-labelledby="top-products-heading">
            <div className="viz-card-header compact"><h2 id="top-products-heading">Top 10 Products</h2><p>By revenue</p></div>
            {topProductData.length === 0 ? <EmptyChart onClearFilters={clearFilters} /> : (
              <SelfFormingRankingBars data={topProductData} replayKey={animationKey} />
            )}
          </section>

          <section className="viz-card" aria-labelledby="segments-heading">
            <div className="viz-card-header">
              <h2 id="segments-heading">Customer Segment Distribution</h2>
              <SelectControl label="Customer segment chart type" value={segmentType} options={['Bar Chart', 'Pie Chart', 'Table'].map((value) => ({ value, label: value }))} onChange={(value) => setSegmentType(value as SegmentChartType)} />
            </div>
            {segmentData.length === 0 ? (
              <EmptyChart onClearFilters={clearFilters} />
            ) : (
              <CustomerSegmentChart chartType={segmentType} data={segmentData} replayKey={animationKey} />
            )}
          </section>

          <section className="viz-card" aria-labelledby="region-heading">
            <div className="viz-card-header">
              <h2 id="region-heading">Revenue by Region</h2>
              <SelectControl label="Region view" value={regionView} options={['Map View', 'Bar View', 'Table View'].map((value) => ({ value, label: value }))} onChange={(value) => setRegionView(value as RegionView)} />
            </div>
            <RegionChart view={regionView} data={regionData} filteredRows={filteredRows} onClearFilters={clearFilters} replayKey={animationKey} />
          </section>

          <section className="viz-card viz-card--wide" aria-labelledby="builder-preview-heading">
            <div className="viz-card-header">
              <div>
                <h2 id="builder-preview-heading">
                  {config.chartType === 'Table'
                    ? `${dataset.name} Data Table`
                    : `${fieldLabel(config.yAxis)} by ${fieldLabel(config.xAxis)}`}
                </h2>
                <p>
                  {config.chartType === 'Table'
                    ? `${filteredRows.length} records (${Object.keys(dataset.columns).length} columns)`
                    : config.groupBy
                    ? `Grouped by ${fieldLabel(config.groupBy)}`
                    : 'Single series'}
                </p>
              </div>
              <span className="viz-loaded">{config.chartType}</span>
            </div>
            {isUpdating ? (
              <div className="viz-loading">Updating visualization...</div>
            ) : (
              <MetricChart
                type={config.chartType}
                transformed={builderTransformed}
                ariaLabel={`${config.chartType} chart for ${fieldLabel(config.yAxis)} by ${fieldLabel(config.xAxis)}`}
                onClearFilters={clearFilters}
                onResetConfig={handleAutoFixConfig}
                replayKey={`${animationKey}-${renderTrigger}`}
              />
            )}
          </section>
        </div>

        <aside className="viz-builder" aria-labelledby="builder-heading">
          <div className="viz-builder-title"><Sparkles size={16} aria-hidden="true" /><div><h2 id="builder-heading">Visualization Builder</h2><p>Customize your chart</p></div></div>
          <fieldset>
            <legend>Chart Type</legend>
            <div className="viz-type-grid">
              {chartTypes.map(({ type, icon: Icon }) => (
                <button
                  key={type}
                  type="button"
                  className={config.chartType === type ? 'viz-type viz-type--active' : 'viz-type'}
                  onClick={() => handleChartTypeChange(type)}
                  aria-pressed={config.chartType === type}
                >
                  <Icon size={17} aria-hidden="true" />
                  {type}
                </button>
              ))}
            </div>
          </fieldset>
          <FieldSelect
            label={config.chartType === 'Scatter' ? 'X-axis (Numeric)' : 'X-axis'}
            value={config.xAxis}
            options={config.chartType === 'Scatter' ? numericFields : allFields}
            onChange={(xAxis) => updateConfig({ xAxis })}
          />
          <FieldSelect
            label="Y-axis"
            value={config.yAxis}
            options={numericFields}
            onChange={(yAxis) => updateConfig({ yAxis })}
          />
          <FieldSelect
            label={config.chartType === 'Heatmap' ? 'Secondary Category (Group by)' : 'Group by (Optional)'}
            value={config.groupBy}
            options={['', ...categoricalFields]}
            onChange={(groupBy) => updateConfig({ groupBy })}
          />

          {config.filters.length > 0 && (
            <div className="viz-filter-chips" aria-label="Active filters">
              {config.filters.map((filter) => (
                <button key={filter.id} type="button" onClick={() => updateConfig({ filters: config.filters.filter((item) => item.id !== filter.id) })} aria-label={`Remove filter ${fieldLabel(filter.field)}`}>
                  {fieldLabel(filter.field)} {operatorLabels[filter.operator]} {filter.value}{filter.valueTo ? ` - ${filter.valueTo}` : ''} <X size={12} aria-hidden="true" />
                </button>
              ))}
            </div>
          )}

          {isFilterOpen && (
            <div className="viz-filter-panel">
              <FieldSelect
                label="Filter field"
                value={draftFilter.field}
                options={allFields}
                onChange={(field) => {
                  const nextType = dataset.columns[field];
                  setDraftFilter({ field, operator: getOperators(nextType)[0], value: '', valueTo: '' });
                }}
              />
              <label className="viz-field">
                <span>Operator</span>
                <select className="viz-select" value={draftFilter.operator} onChange={(event) => setDraftFilter((current) => ({ ...current, operator: event.target.value as FilterOperator }))}>
                  {getOperators(currentFieldType).map((operator) => <option key={operator} value={operator}>{operatorLabels[operator]}</option>)}
                </select>
              </label>
              <label className="viz-field">
                <span>Value</span>
                {currentFieldType === 'category' || currentFieldType === 'boolean' ? (
                  <select className="viz-select" value={draftFilter.value} onChange={(event) => setDraftFilter((current) => ({ ...current, value: event.target.value }))}>
                    <option value="">Select value</option>
                    {draftOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                ) : (
                  <input className="viz-input" type={currentFieldType === 'date' ? 'date' : 'number'} value={draftFilter.value} onChange={(event) => setDraftFilter((current) => ({ ...current, value: event.target.value }))} />
                )}
              </label>
              {draftFilter.operator === 'between' && (
                <label className="viz-field">
                  <span>End value</span>
                  <input className="viz-input" type="date" value={draftFilter.valueTo} onChange={(event) => setDraftFilter((current) => ({ ...current, valueTo: event.target.value }))} />
                </label>
              )}
              <div className="viz-filter-actions">
                <button type="button" onClick={handleApplyFilter}>Apply</button>
                <button type="button" onClick={() => setIsFilterOpen(false)}>Cancel</button>
              </div>
            </div>
          )}

          <button type="button" className="viz-filter" onClick={() => setIsFilterOpen((current) => !current)}><Filter size={15} aria-hidden="true" /> Add Filter</button>
          <button type="button" className="viz-update" onClick={handleUpdateVisualization} disabled={isUpdating}><RefreshCw size={15} aria-hidden="true" /> {isUpdating ? 'Updating visualization...' : 'Update Visualization'}</button>
        </aside>
      </div>

      <div className="viz-bottom-grid">
        <section className="viz-card" aria-labelledby="viz-insights-heading">
          <div className="viz-card-header"><h2 id="viz-insights-heading">Insights from Your Data</h2><Link to="/insights">View all -&gt;</Link></div>
          <div className="viz-insight-grid">
            {insights.map((insight) => {
              const Icon = insight.icon;
              return <article key={insight.title} className="viz-insight"><Icon size={18} aria-hidden="true" /><h3>{insight.title}</h3><p>{insight.body}</p></article>;
            })}
          </div>
        </section>
        <section className="viz-card" aria-labelledby="recent-viz-heading">
          <div className="viz-card-header"><h2 id="recent-viz-heading">Recent Visualizations</h2><Link to="/visualizations">View all -&gt;</Link></div>
          <div className="viz-recent-grid">
            {recentVisualizations.map((item) => (
              <article key={item.title} className="viz-recent">
                <MiniPreview kind={item.kind} />
                <div><h3>{item.title}</h3><span>{item.when}</span></div>
                <button type="button" aria-label={`${item.title} options`}><MoreVertical size={14} /></button>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
