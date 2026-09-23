export type ChartType = 'Line' | 'Bar' | 'Pie' | 'Area' | 'Scatter' | 'Table' | 'Heatmap' | 'Treemap';
export type FieldType = 'date' | 'category' | 'number' | 'boolean';

export type CellValue = string | number | boolean | null;
export type DataRow = Record<string, CellValue>;

export interface ActiveFilter {
  id: number;
  field: string;
  operator: string;
  value: string;
  valueTo?: string;
}

export interface VisualizationConfig {
  chartType: ChartType;
  xAxis: string;
  yAxis: string;
  groupBy: string;
  filters: ActiveFilter[];
}

export interface ChartPoint {
  label: string;
  value: number;
  group?: string;
}

export interface ScatterPoint {
  x: number;
  y: number;
  label: string;
  group?: string;
}

export interface HeatmapCell {
  row: string;
  col: string;
  value: number;
  intensity: number; // 0 to 1
}

export interface HeatmapData {
  rowField: string;
  colField: string;
  valField: string;
  rowLabels: string[];
  colLabels: string[];
  cells: HeatmapCell[];
  minVal: number;
  maxVal: number;
}

export interface TreemapNode {
  id: string;
  label: string;
  parent?: string;
  value: number;
  percent: number;
  colorIndex: number;
}

export interface TreemapData {
  items: TreemapNode[];
  total: number;
}

export interface TableColumnDef {
  key: string;
  label: string;
  type: FieldType;
}

export interface TableData {
  columns: TableColumnDef[];
  rows: DataRow[];
  totalCount: number;
}

export interface TransformedChartData {
  type: ChartType;
  isValid: boolean;
  validationMessage?: string;
  points?: ChartPoint[];
  scatterPoints?: ScatterPoint[];
  scatterBounds?: { minX: number; maxX: number; minY: number; maxY: number };
  heatmapData?: HeatmapData;
  treemapData?: TreemapData;
  tableData?: TableData;
}

// ---------------------------------------------------------------------------
// Centralized Normalization Pipeline
// ---------------------------------------------------------------------------

export function parseNumeric(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string') {
    // Strip dollar signs, commas, and trailing/leading whitespace
    const cleaned = value.replace(/[$,\s]/g, '').trim();
    if (!cleaned) return null;
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function numberValue(value: unknown, fallback = 0): number {
  const parsed = parseNumeric(value);
  return parsed !== null ? parsed : fallback;
}

export function parseDate(value: unknown): Date | null {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  if (typeof value !== 'string') return null;
  const str = value.trim();
  if (!str) return null;

  // Match ISO YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss
  const isoMatch = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(str);
  if (isoMatch) {
    const year = parseInt(isoMatch[1], 10);
    const month = parseInt(isoMatch[2], 10) - 1;
    const day = parseInt(isoMatch[3], 10);
    const d = new Date(year, month, day);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  // Match US date MM/DD/YYYY or M/D/YYYY
  const usMatch = /^(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(str);
  if (usMatch) {
    const month = parseInt(usMatch[1], 10) - 1;
    const day = parseInt(usMatch[2], 10);
    const year = parseInt(usMatch[3], 10);
    const d = new Date(year, month, day);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  // General Date.parse (handles 'Jan 1, 2026', '15 Jan 2026', etc.)
  const parsedTime = Date.parse(str);
  if (!Number.isNaN(parsedTime)) {
    const d = new Date(parsedTime);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  return null;
}

export function normalizeOrderDate(rawDate: unknown): Date | null {
  return parseDate(rawDate);
}

export function dateValue(value: CellValue): Date | null {
  return parseDate(value);
}

export function formatDateLabel(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function detectFieldType(values: unknown[]): FieldType {
  const nonNull = values.filter((v) => v !== null && v !== undefined && v !== '');
  if (nonNull.length === 0) return 'category';

  let numericCount = 0;
  let dateCount = 0;
  let booleanCount = 0;

  for (const v of nonNull) {
    if (typeof v === 'boolean' || v === 'true' || v === 'false') {
      booleanCount++;
      continue;
    }
    if (parseNumeric(v) !== null) {
      numericCount++;
    }
    if (parseDate(v) !== null) {
      dateCount++;
    }
  }

  const threshold = nonNull.length * 0.7;
  if (numericCount >= threshold) return 'number';
  if (dateCount >= threshold) return 'date';
  if (booleanCount >= threshold) return 'boolean';
  return 'category';
}

export function formatFieldLabel(field: string): string {
  if (!field) return '';
  return field.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Field Validation
// ---------------------------------------------------------------------------

export function validateChartConfig(
  columns: Record<string, FieldType>,
  config: VisualizationConfig
): { isValid: boolean; message?: string } {
  const xType = columns[config.xAxis];
  const yType = columns[config.yAxis];
  const groupType = config.groupBy ? columns[config.groupBy] : undefined;

  switch (config.chartType) {
    case 'Scatter':
      if (xType !== 'number') {
        return {
          isValid: false,
          message: `Scatter charts require a numeric X-axis. Currently "${formatFieldLabel(config.xAxis)}" is a ${xType ?? 'unknown'} field. Please select a metric like Orders, Quantity, or Customers for the X-axis.`,
        };
      }
      if (yType !== 'number') {
        return {
          isValid: false,
          message: `Scatter charts require a numeric Y-axis. Currently "${formatFieldLabel(config.yAxis)}" is a ${yType ?? 'unknown'} field. Please select a metric like Revenue or Profit.`,
        };
      }
      return { isValid: true };

    case 'Heatmap':
      if (yType !== 'number') {
        return {
          isValid: false,
          message: `Heatmaps require a numeric value for cell intensity. Please select a numeric field for the Y-axis.`,
        };
      }
      if (!config.groupBy) {
        return {
          isValid: false,
          message: `Heatmaps require both rows and columns. Please select a categorical field for "Group by" to define heatmap rows (e.g., Customer Segment or Product Category).`,
        };
      }
      if (groupType !== 'category' && groupType !== 'date') {
        return {
          isValid: false,
          message: `Heatmap rows ("Group by") must be a categorical or date field.`,
        };
      }
      return { isValid: true };

    case 'Pie':
      if (yType !== 'number') {
        return {
          isValid: false,
          message: `Pie charts require a numeric Y-axis to compute slice proportions.`,
        };
      }
      if (xType === 'number') {
        return {
          isValid: false,
          message: `Pie charts require a categorical X-axis for slices (e.g., Product Category, Region, or Segment).`,
        };
      }
      return { isValid: true };

    case 'Line':
    case 'Area':
      if (yType !== 'number') {
        return {
          isValid: false,
          message: `${config.chartType} charts require a numeric Y-axis to plot values over time or category.`,
        };
      }
      return { isValid: true };

    case 'Bar':
      if (yType !== 'number') {
        return {
          isValid: false,
          message: `Bar charts require a numeric Y-axis for bar heights.`,
        };
      }
      return { isValid: true };

    case 'Treemap':
      if (yType !== 'number') {
        return {
          isValid: false,
          message: `Treemaps require a numeric value to size the tiles. Please select a metric for the Y-axis.`,
        };
      }
      return { isValid: true };

    case 'Table':
    default:
      return { isValid: true };
  }
}

// ---------------------------------------------------------------------------
// Sensible Fallback Defaults
// ---------------------------------------------------------------------------

export interface SensibleChartFields {
  xAxis: string;
  yAxis: string;
  groupBy: string;
}

export function getSensibleDefaults(
  targetChartType: ChartType,
  columns: Record<string, FieldType>,
  current?: Partial<VisualizationConfig>
): SensibleChartFields {
  const numericFields = Object.keys(columns).filter((col) => columns[col] === 'number');
  const categoricalFields = Object.keys(columns).filter((col) => columns[col] === 'category');
  const dateFields = Object.keys(columns).filter((col) => columns[col] === 'date');
  const allFields = Object.keys(columns);

  let nextX = current?.xAxis ?? (dateFields[0] || categoricalFields[0] || allFields[0] || 'orderDate');
  let nextY = current?.yAxis ?? (numericFields[0] || 'revenue');
  let nextGroup = current?.groupBy ?? '';

  switch (targetChartType) {
    case 'Scatter': {
      // Must have numeric X and numeric Y
      if (columns[nextY] !== 'number') {
        nextY = numericFields.includes('revenue') ? 'revenue' : (numericFields[0] ?? 'revenue');
      }

      if (columns[nextX] !== 'number') {
        // Pick a numeric field different from Y
        const availableX = numericFields.filter((f) => f !== nextY);
        nextX = availableX.includes('orders')
          ? 'orders'
          : (availableX[0] ?? (numericFields[1] || nextY));
      }
      break;
    }

    case 'Heatmap': {
      // Must have categorical X, categorical GroupBy, and numeric Y
      if (columns[nextY] !== 'number') {
        nextY = numericFields.includes('revenue') ? 'revenue' : (numericFields[0] ?? 'revenue');
      }

      if (columns[nextX] !== 'category' && columns[nextX] !== 'date') {
        nextX = categoricalFields.includes('region')
          ? 'region'
          : (categoricalFields[0] ?? (dateFields[0] || 'region'));
      }

      if (!nextGroup || (columns[nextGroup] !== 'category' && columns[nextGroup] !== 'date') || nextGroup === nextX) {
        const availableGroup = categoricalFields.filter((f) => f !== nextX);
        nextGroup = availableGroup.includes('customerSegment')
          ? 'customerSegment'
          : (availableGroup.includes('productCategory')
              ? 'productCategory'
              : (availableGroup[0] ?? 'customerSegment'));
      }
      break;
    }

    case 'Pie': {
      if (columns[nextY] !== 'number') {
        nextY = numericFields[0] ?? 'revenue';
      }

      if (columns[nextX] === 'number') {
        nextX = categoricalFields.includes('productCategory')
          ? 'productCategory'
          : (categoricalFields[0] ?? 'productCategory');
      }
      break;
    }

    case 'Line':
    case 'Area': {
      if (columns[nextY] !== 'number') {
        nextY = numericFields[0] ?? 'revenue';
      }

      // If X is numeric (left over from scatter), change back to date or category
      if (columns[nextX] === 'number') {
        nextX = dateFields[0] ?? (categoricalFields[0] || 'orderDate');
      }
      break;
    }

    case 'Bar': {
      if (columns[nextY] !== 'number') {
        nextY = numericFields[0] ?? 'revenue';
      }

      if (columns[nextX] === 'number') {
        nextX = categoricalFields[0] ?? 'customerSegment';
      }
      break;
    }

    case 'Treemap': {
      if (columns[nextY] !== 'number') {
        nextY = numericFields[0] ?? 'revenue';
      }

      if (columns[nextX] === 'number') {
        nextX = categoricalFields.includes('productCategory')
          ? 'productCategory'
          : (categoricalFields[0] ?? 'productCategory');
      }

      if (!nextGroup) {
        nextGroup = categoricalFields.find((f) => f !== nextX) ?? '';
      }
      break;
    }

    default:
      break;
  }

  return {
    xAxis: nextX,
    yAxis: nextY,
    groupBy: nextGroup,
  };
}

// ---------------------------------------------------------------------------
// Centralized Chart Data Transformation
// ---------------------------------------------------------------------------

export function transformChartData(
  rows: DataRow[],
  columns: Record<string, FieldType>,
  config: VisualizationConfig
): TransformedChartData {
  const validation = validateChartConfig(columns, config);
  if (!validation.isValid) {
    return {
      type: config.chartType,
      isValid: false,
      validationMessage: validation.message,
    };
  }

  const { chartType, xAxis, yAxis, groupBy } = config;

  switch (chartType) {
    case 'Scatter': {
      const validPoints: ScatterPoint[] = [];
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;

      rows.forEach((row, idx) => {
        const rawX = row[xAxis];
        const rawY = row[yAxis];
        if (typeof rawX !== 'number' || typeof rawY !== 'number') return;
        if (!Number.isFinite(rawX) || !Number.isFinite(rawY)) return;

        minX = Math.min(minX, rawX);
        maxX = Math.max(maxX, rawX);
        minY = Math.min(minY, rawY);
        maxY = Math.max(maxY, rawY);

        const label = String(row.product ?? row.productCategory ?? `Row ${idx + 1}`);
        const group = groupBy ? String(row[groupBy] ?? '') : undefined;

        validPoints.push({ x: rawX, y: rawY, label, group });
      });

      if (minX === Infinity) {
        minX = 0;
        maxX = 100;
      }
      if (minY === Infinity) {
        minY = 0;
        maxY = 100;
      }
      if (minX === maxX) maxX = minX + 1;
      if (minY === maxY) maxY = minY + 1;

      return {
        type: 'Scatter',
        isValid: true,
        scatterPoints: validPoints.slice(0, 36),
        scatterBounds: { minX, maxX, minY, maxY },
      };
    }

    case 'Heatmap': {
      const rowField = groupBy || 'customerSegment';
      const colField = xAxis;
      const valField = yAxis;

      const rowLabelSet = new Set<string>();
      const colLabelSet = new Set<string>();
      const matrix = new Map<string, number>();

      rows.forEach((row) => {
        const rVal = String(row[rowField] ?? 'Other');
        const cVal = String(row[colField] ?? 'Other');
        const v = numberValue(row[valField]);

        rowLabelSet.add(rVal);
        colLabelSet.add(cVal);

        const key = `${rVal}:::${cVal}`;
        matrix.set(key, (matrix.get(key) ?? 0) + v);
      });

      const rowLabels = Array.from(rowLabelSet).slice(0, 8);
      const colLabels = Array.from(colLabelSet).slice(0, 8);

      let minVal = Infinity;
      let maxVal = -Infinity;

      const cells: HeatmapCell[] = [];

      rowLabels.forEach((r) => {
        colLabels.forEach((c) => {
          const val = matrix.get(`${r}:::${c}`) ?? 0;
          minVal = Math.min(minVal, val);
          maxVal = Math.max(maxVal, val);
          cells.push({ row: r, col: c, value: val, intensity: 0 });
        });
      });

      if (minVal === Infinity) minVal = 0;
      if (maxVal === -Infinity) maxVal = 1;
      const range = maxVal - minVal || 1;

      cells.forEach((cell) => {
        cell.intensity = Math.max(0.08, (cell.value - minVal) / range);
      });

      return {
        type: 'Heatmap',
        isValid: true,
        heatmapData: {
          rowField,
          colField,
          valField,
          rowLabels,
          colLabels,
          cells,
          minVal,
          maxVal,
        },
      };
    }

    case 'Treemap': {
      // Primary category = xAxis, subcategory = groupBy
      const buckets = new Map<string, { label: string; parent?: string; value: number }>();
      let total = 0;

      rows.forEach((row) => {
        const cat = String(row[xAxis] ?? 'Other');
        const sub = groupBy ? String(row[groupBy] ?? '') : '';
        const v = numberValue(row[yAxis]);
        total += v;

        const key = sub ? `${cat}::${sub}` : cat;
        const existing = buckets.get(key) ?? {
          label: sub ? `${cat} - ${sub}` : cat,
          parent: sub ? cat : undefined,
          value: 0,
        };
        existing.value += v;
        buckets.set(key, existing);
      });

      const sorted = Array.from(buckets.values())
        .filter((item) => item.value > 0)
        .sort((a, b) => b.value - a.value)
        .slice(0, 10);

      const items: TreemapNode[] = sorted.map((item, idx) => ({
        id: `tree-${idx}`,
        label: item.label,
        parent: item.parent,
        value: item.value,
        percent: total > 0 ? (item.value / total) * 100 : 0,
        colorIndex: idx,
      }));

      return {
        type: 'Treemap',
        isValid: true,
        treemapData: { items, total },
      };
    }

    case 'Table': {
      // Show chosen X, Y, GroupBy fields, plus any other relevant columns
      const selectedKeys = [xAxis, yAxis, groupBy].filter(Boolean);
      const remainingKeys = Object.keys(columns).filter((k) => !selectedKeys.includes(k));
      const orderedKeys = [...selectedKeys, ...remainingKeys].slice(0, 6);

      const tableColumns: TableColumnDef[] = orderedKeys.map((key) => ({
        key,
        label: formatFieldLabel(key),
        type: columns[key] ?? 'category',
      }));

      return {
        type: 'Table',
        isValid: true,
        tableData: {
          columns: tableColumns,
          rows: rows.slice(0, 30),
          totalCount: rows.length,
        },
      };
    }

    case 'Pie': {
      const buckets = new Map<string, number>();

      rows.forEach((row) => {
        const label = String(row[xAxis] ?? 'Other');
        const v = numberValue(row[yAxis]);
        buckets.set(label, (buckets.get(label) ?? 0) + v);
      });

      const sorted = Array.from(buckets.entries())
        .map(([label, value]) => ({ label, value }))
        .sort((a, b) => b.value - a.value);

      const top6 = sorted.slice(0, 6);
      const otherValue = sorted.slice(6).reduce((acc, curr) => acc + curr.value, 0);

      if (otherValue > 0) {
        top6.push({ label: 'Other', value: otherValue });
      }

      return {
        type: 'Pie',
        isValid: true,
        points: top6,
      };
    }

    case 'Line':
    case 'Area': {
      const isDate = columns[xAxis] === 'date' || rows.some((r) => parseDate(r[xAxis]) !== null);
      const buckets = new Map<string, { label: string; date?: Date; value: number }>();

      rows.forEach((row) => {
        const v = parseNumeric(row[yAxis]) ?? 0;
        const d = isDate ? parseDate(row[xAxis]) : null;

        if (d) {
          const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
          const label = formatDateLabel(d);
          const existing = buckets.get(key) ?? { label, date: d, value: 0 };
          existing.value += v;
          buckets.set(key, existing);
        } else {
          const rawLabel = String(row[xAxis] ?? 'Unknown').trim();
          const existing = buckets.get(rawLabel) ?? { label: rawLabel, value: 0 };
          existing.value += v;
          buckets.set(rawLabel, existing);
        }
      });

      const points = Array.from(buckets.values());

      if (isDate) {
        // Chronological sort: Jan 1, Jan 2, Jan 3... NOT alphabetical!
        points.sort((a, b) => {
          const tA = a.date?.getTime() ?? 0;
          const tB = b.date?.getTime() ?? 0;
          return tA - tB;
        });
      }

      return {
        type: chartType,
        isValid: true,
        points: points.slice(0, 20).map(({ label, value }) => ({
          label,
          value: Number.isFinite(value) ? Math.round(value * 100) / 100 : 0,
        })),
      };
    }

    case 'Bar':
    default: {
      const isDate = columns[xAxis] === 'date' || rows.some((r) => parseDate(r[xAxis]) !== null);
      const buckets = new Map<string, { label: string; date?: Date; group?: string; value: number }>();

      rows.forEach((row) => {
        const v = parseNumeric(row[yAxis]) ?? 0;
        const group = groupBy ? String(row[groupBy] ?? '').trim() : undefined;
        const d = isDate ? parseDate(row[xAxis]) : null;

        if (d) {
          const dateKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
          const key = group ? `${dateKey}::${group}` : dateKey;
          const label = formatDateLabel(d);
          const existing = buckets.get(key) ?? { label, date: d, group, value: 0 };
          existing.value += v;
          buckets.set(key, existing);
        } else {
          const rawLabel = String(row[xAxis] ?? 'Unknown').trim();
          const key = group ? `${rawLabel}::${group}` : rawLabel;
          const existing = buckets.get(key) ?? { label: rawLabel, group, value: 0 };
          existing.value += v;
          buckets.set(key, existing);
        }
      });

      const points = Array.from(buckets.values());

      if (isDate) {
        // Chronological sort for dates
        points.sort((a, b) => {
          const tA = a.date?.getTime() ?? 0;
          const tB = b.date?.getTime() ?? 0;
          return tA - tB;
        });
      } else {
        // Magnitude sort for categories
        points.sort((a, b) => b.value - a.value);
      }

      return {
        type: 'Bar',
        isValid: true,
        points: points.slice(0, 16).map(({ label, group, value }) => ({
          label,
          group,
          value: Number.isFinite(value) ? Math.round(value * 100) / 100 : 0,
        })),
      };
    }
  }
}
