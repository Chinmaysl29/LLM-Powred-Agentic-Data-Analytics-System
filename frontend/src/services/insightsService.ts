/**
 * insightsService.ts
 *
 * Centralized service boundary and development data for Insights & Decision Intelligence.
 *
 * BACKEND INTEGRATION POINTS:
 *   GET  /api/insights               -> getInsights(datasetId, dateRange)
 *   GET  /api/insights/health        -> getBusinessHealth(datasetId)
 *   GET  /api/insights/risks         -> getRisks(datasetId)
 *   GET  /api/insights/opportunities -> getOpportunities(datasetId)
 *   GET  /api/insights/recommendations -> getRecommendations(datasetId)
 *   POST /api/insights/what-if       -> runWhatIfScenario(datasetId, inputs)
 */

import type {
  Insight,
  Risk,
  Opportunity,
  Recommendation,
  BusinessHealthMetric,
  ScenarioInputVariables,
  ScenarioProjection,
} from '../types/insights';

// ---------------------------------------------------------------------------
// Centralized Development Data: Sales Dataset
// ---------------------------------------------------------------------------

const SALES_HEALTH: BusinessHealthMetric[] = [
  {
    id: 'h1',
    label: 'Total Revenue',
    value: '$2.48M',
    subValue: 'vs. baseline $2.10M',
    trend: '+18.4%',
    direction: 'up',
    status: 'positive',
  },
  {
    id: 'h2',
    label: 'Revenue Growth',
    value: '18.4%',
    subValue: 'accelerated in Q3',
    trend: '+4.2% pts',
    direction: 'up',
    status: 'positive',
  },
  {
    id: 'h3',
    label: 'Active Customers',
    value: '14,820',
    subValue: '680 new this month',
    trend: '+6.8%',
    direction: 'up',
    status: 'positive',
  },
  {
    id: 'h4',
    label: 'Detected Issues',
    value: '3',
    subValue: '2 require attention',
    trend: '-1 vs last mo',
    direction: 'down',
    status: 'warning',
  },
];

const SALES_INSIGHTS: Insight[] = [
  {
    id: 'ins-1',
    type: 'trend',
    title: 'Revenue growth accelerated in Q3',
    summary:
      'Revenue increased 18.4% compared with the previous period, with the strongest positive contribution coming from Electronics and the North America region.',
    observedEvidence: [
      'Total revenue increased from $2.10M to $2.48M across 24 tracking periods.',
      'Electronics generated $1.42M, representing 67.2% of category volume.',
      'North America recorded 40.8% of aggregate sales, outperforming Europe by $82,000.',
    ],
    derivedInterpretation:
      'Observed momentum indicates strong enterprise purchasing cycles in North America alongside new product line releases.',
    metrics: [
      { label: 'Revenue Growth', value: '+18.4%', change: '+$380K', direction: 'up' },
      { label: 'Electronics Sales', value: '+27.1%', change: 'Top category', direction: 'up' },
      { label: 'North America', value: '+22.6%', change: 'Top region', direction: 'up' },
    ],
    drivers: ['Enterprise Laptop adoption', 'Corporate segment expansion', 'Direct sales channel'],
    confidence: 0.94,
    datasetName: 'Sales_Data_2026.xlsx',
    timePeriod: 'Jan 2024 – Dec 2025',
    visualizationReference: {
      chartType: 'Line',
      xAxis: 'orderDate',
      yAxis: 'revenue',
      title: 'Revenue Trend by Order Date',
      description: 'Historical quarterly trajectory showing growth acceleration starting Q3.',
    },
  },
  {
    id: 'ins-2',
    type: 'driver',
    title: 'Corporate segment accounts for 35% of total revenue with highest margin',
    summary:
      'The Corporate segment maintains an average order value 2.4x higher than Consumer accounts, driving $860K in net contribution.',
    observedEvidence: [
      'Corporate customers average $124.50 profit per order versus $58.20 for Consumer accounts.',
      'Repeat order frequency among Corporate accounts reached 4.2 orders annually.',
      'Discount utilization in Corporate remained controlled at 5.8% compared to 12.4% in Small Business.',
    ],
    derivedInterpretation:
      'Corporate clients prioritize service reliability over discounting, delivering resilient gross profit margins.',
    metrics: [
      { label: 'Segment Revenue', value: '$860K', change: '35% share', direction: 'up' },
      { label: 'Avg Order Profit', value: '$124.50', change: '+14.2%', direction: 'up' },
      { label: 'Discount Rate', value: '5.8%', change: '-2.1%', direction: 'down' },
    ],
    drivers: ['High retention contracts', 'Hardware bundling', 'Annual enterprise subscriptions'],
    confidence: 0.91,
    datasetName: 'Sales_Data_2026.xlsx',
    timePeriod: 'Jan 2024 – Dec 2025',
    visualizationReference: {
      chartType: 'Bar',
      xAxis: 'customerSegment',
      yAxis: 'revenue',
      title: 'Customer Segment Distribution',
      description: 'Breakdown of total revenue across Consumer, Corporate, Home Office, and Small Business.',
    },
  },
  {
    id: 'ins-3',
    type: 'anomaly',
    title: 'Disproportionate discount spike in Small Business category during Q2',
    summary:
      'Small Business segment discounts jumped to 16.8% in May without a proportional lift in conversion rate or repeat orders.',
    observedEvidence: [
      'Average discount rate for Small Business rose from 9.4% in Q1 to 16.8% in Q2.',
      'Conversion rate remained flat at 2.5% during the identical promotion period.',
      'Total gross margin contracted by 4.8 percentage points on discounted transactions.',
    ],
    derivedInterpretation:
      'Aggressive promotional discounting compressed margins without stimulating net customer acquisition.',
    metrics: [
      { label: 'Avg Discount', value: '16.8%', change: '+7.4% pts', direction: 'up' },
      { label: 'Conversion', value: '2.5%', change: '0.0% pts', direction: 'neutral' },
      { label: 'Margin Impact', value: '-$34.2K', change: 'Margin drag', direction: 'down' },
    ],
    drivers: ['Seasonal promotional coupons', 'Uncontrolled sales representative overrides'],
    confidence: 0.88,
    datasetName: 'Sales_Data_2026.xlsx',
    timePeriod: 'Jan 2024 – Dec 2025',
    visualizationReference: {
      chartType: 'Scatter',
      xAxis: 'discount',
      yAxis: 'orders',
      title: 'Orders vs. Discount Distribution',
      description: 'Correlation scatter illustrating diminishing order returns at discount rates >12%.',
    },
  },
  {
    id: 'ins-4',
    type: 'correlation',
    title: 'Strong correlation between Tablet bundling and repeat purchases',
    summary:
      'Customers purchasing Tablet bundles demonstrate an 84% higher 90-day repeat purchase probability compared to single-item buyers.',
    observedEvidence: [
      'Bundle attachment rate grew from 11.2% to 24.6% year-over-year.',
      'Repeat order frequency reached 3.1x within 90 days for bundle purchasers.',
      'Return rate was 62% lower for bundled orders than single accessories.',
    ],
    derivedInterpretation:
      'Ecosystem attachment builds switching barriers and stabilizes customer lifetime value.',
    metrics: [
      { label: 'Repeat Rate', value: '42.8%', change: '+18.6% pts', direction: 'up' },
      { label: 'Bundle Attach', value: '24.6%', change: '+13.4% pts', direction: 'up' },
      { label: 'Return Rate', value: '1.8%', change: '-2.9% pts', direction: 'down' },
    ],
    drivers: ['Accessory compatibility', 'Pre-installed software suite'],
    confidence: 0.89,
    datasetName: 'Sales_Data_2026.xlsx',
    timePeriod: 'Jan 2024 – Dec 2025',
    visualizationReference: {
      chartType: 'Bar',
      xAxis: 'product',
      yAxis: 'revenue',
      title: 'Top 10 Products by Revenue',
      description: 'Volume comparison of hardware bundles versus standalone SKUs.',
    },
  },
];

const SALES_RISKS: Risk[] = [
  {
    id: 'risk-1',
    title: 'Customer churn elevated in Consumer segment during Q4',
    summary:
      'Consumer segment repeat purchase frequency declined by 5.1%, indicating possible attrition following promotional periods.',
    impact: 'High',
    evidence: [
      { label: 'Churn Rate', value: '+8.2%', direction: 'up' },
      { label: 'Repeat Purchases', value: '-5.1%', direction: 'down' },
      { label: 'Order Frequency', value: '-3.7%', direction: 'down' },
    ],
    contributingFactors: [
      'Post-holiday engagement drop-off',
      'Increased competitor pricing pressure in mid-tier electronics',
      'Longer shipping fulfillment delays during peak periods',
    ],
    observedData: [
      'Observed 90-day repurchase rate fell from 28.4% to 23.3%.',
      'Customer support inquiries regarding warranty service rose 14%.',
    ],
    confidence: 0.86,
    visualizationReference: {
      chartType: 'Line',
      title: 'Customer Trend by Order Date',
    },
  },
  {
    id: 'risk-2',
    title: 'Geographic concentration in top 2 regional markets',
    summary:
      'North America and Europe account for 78% of aggregate sales, leaving revenue vulnerable to regional macroeconomic headwinds.',
    impact: 'Medium',
    evidence: [
      { label: 'Top 2 Share', value: '78.4%', direction: 'up' },
      { label: 'South America', value: '4.2%', direction: 'down' },
      { label: 'Asia Share', value: '17.4%', direction: 'neutral' },
    ],
    contributingFactors: [
      'Limited localized distributor network in South America',
      'Import tariff shifts affecting retail pricing',
    ],
    observedData: [
      'South American quarterly revenue contracted 2.8% in Q4.',
      'Currency fluctuations created a 6.2% pricing delta in overseas markets.',
    ],
    confidence: 0.9,
    visualizationReference: {
      chartType: 'Bar',
      title: 'Revenue by Region Distribution',
    },
  },
];

const SALES_OPPORTUNITIES: Opportunity[] = [
  {
    id: 'opp-1',
    title: 'Expand Electronics accessory bundling into European Corporate accounts',
    summary:
      'European Corporate accounts currently exhibit high satisfaction but a 14% lower accessory attachment rate than North America.',
    potentialImpact: '+$140K – $180K annual revenue',
    growth: '+31.4% potential',
    strongestSegments: ['Corporate Accounts', 'Germany', 'United Kingdom'],
    evidence: [
      { label: 'EU Corp Accounts', value: '1,420', direction: 'up' },
      { label: 'Current Attach Rate', value: '18.2%', direction: 'down' },
      { label: 'NA Attach Benchmark', value: '32.6%', direction: 'up' },
    ],
    observedData: [
      'Germany and UK Corporate accounts have 94% on-time payment records.',
      'Accessory bundle margins average 48% versus 24% on base laptop units.',
    ],
    confidence: 0.89,
    scenarioHint: 'Model a 10% marketing spend shift to European B2B campaigns in What-If simulator.',
  },
  {
    id: 'opp-2',
    title: 'Re-engage dormant Q2 purchasers with personalized lifecycle flows',
    summary:
      'Over 2,100 customers who completed high-value orders in Q2 have not placed an order in 180+ days.',
    potentialImpact: '+$85K – $110K recovered revenue',
    growth: '+12.6% recovery',
    strongestSegments: ['Consumer Electronics', 'Home & Living'],
    evidence: [
      { label: 'Dormant Accounts', value: '2,140', direction: 'neutral' },
      { label: 'Historical AOV', value: '$138.00', direction: 'up' },
      { label: 'Expected Winback', value: '8.4%', direction: 'up' },
    ],
    observedData: [
      'Historical winback campaigns yielded a 9.2% reactivation rate.',
      'Customer lifetime value increases 34% once a second purchase occurs.',
    ],
    confidence: 0.85,
    scenarioHint: 'Evaluate customer churn reduction from 14% to 11% in Decision Intelligence.',
  },
];

const SALES_RECOMMENDATIONS: Recommendation[] = [
  {
    id: 'rec-1',
    title: 'Investigate rationalizing promotional discounts in Small Business segment',
    summary: 'Evaluate reducing Small Business promotional discounts above 12% to protect gross margin.',
    rationale:
      'Observed data indicates that Small Business discount rates exceeding 12% do not deliver meaningful incremental volume, compressing gross margin by 4.8%.',
    evidence: [
      { label: 'Current Discount', value: '16.8%', direction: 'up' },
      { label: 'Volume Elasticity', value: '0.24', direction: 'neutral' },
      { label: 'Margin Recovery', value: '+$34K', direction: 'up' },
    ],
    supportingEvidence: [
      'Discount rates exceeding 12% in Small Business exhibit poor price elasticity (0.24).',
      'Average margin compressed by 4.8 percentage points during aggressive promotional weeks.',
      'Customer churn remained identical between accounts receiving 8% vs 16% discount.',
    ],
    effort: 'Low',
    expectedImpact: 'Estimated gross profit improvement of $30,000–$45,000 without sacrificing customer volume.',
    assumptions: [
      'Demand elasticity remains constant between 8% and 12% discount tiers.',
      'Competitor discount promotions do not exceed 15% in Q1.',
    ],
    scenarioReference: {
      scenarioName: 'Discount Optimization Scenario',
      defaultVariables: {
        marketingSpendDelta: 5,
        priceDelta: 4,
        churnDelta: -1,
      },
    },
    scenarioVariables: {
      marketingSpendDelta: 5,
      priceDelta: 4,
      churnDelta: -1,
    },
  },
  {
    id: 'rec-2',
    title: 'Explore structured B2B accessory bundling program in Europe',
    summary: 'Introduce high-margin accessory attachments to European corporate accounts.',
    rationale:
      'European Corporate accounts show strong baseline retention but lag North America by 14.4 percentage points in accessory attachment.',
    evidence: [
      { label: 'Addressable Accounts', value: '1,420', direction: 'up' },
      { label: 'Target Attach Rate', value: '28.0%', direction: 'up' },
      { label: 'Potential Contribution', value: '+$160K', direction: 'up' },
    ],
    supportingEvidence: [
      'European Corporate attachment rate is 13.6% compared to 28.0% in North America.',
      '1,420 high-volume enterprise customer accounts currently order hardware without accessories.',
      'Customer surveys cite lack of packaged bundling as the primary friction point.',
    ],
    effort: 'Medium',
    expectedImpact: 'Estimated $140,000–$180,000 in higher-margin revenue over 12 months.',
    assumptions: [
      'European supply chain can fulfill accessory demand within standard 4-day delivery window.',
      'B2B sales team is incentivized on bundled margin rather than standalone unit volume.',
    ],
    scenarioReference: {
      scenarioName: 'European B2B Expansion',
      defaultVariables: {
        marketingSpendDelta: 15,
        priceDelta: 0,
        churnDelta: -3,
        region: 'Europe',
      },
    },
    scenarioVariables: {
      marketingSpendDelta: 15,
      priceDelta: 0,
      churnDelta: -3,
      region: 'Europe',
    },
  },
];

// ---------------------------------------------------------------------------
// Centralized Development Data: Marketing Dataset
// ---------------------------------------------------------------------------

const MARKETING_HEALTH: BusinessHealthMetric[] = [
  {
    id: 'mh1',
    label: 'Total Spend',
    value: '$1.46M',
    subValue: 'across 4 digital channels',
    trend: '+12.1%',
    direction: 'up',
    status: 'neutral',
  },
  {
    id: 'mh2',
    label: 'CAC Efficiency',
    value: '$48.20',
    subValue: 'improved from $54.10',
    trend: '-10.9%',
    direction: 'down',
    status: 'positive',
  },
  {
    id: 'mh3',
    label: 'Acquired Customers',
    value: '18,460',
    subValue: 'via search & social',
    trend: '+14.2%',
    direction: 'up',
    status: 'positive',
  },
  {
    id: 'mh4',
    label: 'Channel Anomalies',
    value: '2',
    subValue: 'Display saturation detected',
    trend: 'Needs review',
    direction: 'neutral',
    status: 'warning',
  },
];

const MARKETING_INSIGHTS: Insight[] = [
  {
    id: 'm-ins-1',
    type: 'driver',
    title: 'Paid Search generates 42% of customer acquisitions at lowest CAC',
    summary:
      'High Intent search campaigns delivered 7,750 customer conversions at an average customer acquisition cost of $38.40, outperforming display banners by 2.6x.',
    observedEvidence: [
      'Search channel spend of $540K generated $1.12M in attributable first-order value.',
      'Conversion rate on branded search keywords reached 3.6% compared to 2.0% on Display.',
    ],
    derivedInterpretation:
      'High-intent search captures prospects with existing purchase intent, producing superior ROAS.',
    metrics: [
      { label: 'Attributable Rev', value: '$1.12M', change: '45% share', direction: 'up' },
      { label: 'Search CAC', value: '$38.40', change: '-14.8%', direction: 'down' },
      { label: 'Search ROAS', value: '2.84x', change: '+0.4x', direction: 'up' },
    ],
    drivers: ['Brand keyword defense', 'Negative keyword optimization'],
    confidence: 0.95,
    datasetName: 'Marketing_Spend_2025.csv',
    timePeriod: 'Jan 2024 – Dec 2025',
    visualizationReference: {
      chartType: 'Bar',
      xAxis: 'productCategory',
      yAxis: 'revenue',
      title: 'Attributable Revenue by Channel',
    },
  },
  {
    id: 'm-ins-2',
    type: 'pattern',
    title: 'Diminishing returns observed in Display Awareness campaigns above $45K monthly',
    summary:
      'When Display ad spend exceeded $45,000 monthly, incremental customer acquisition cost increased by 38% with no measurable lift in branded search query volume.',
    observedEvidence: [
      'Display conversion rate declined from 2.4% at $30K spend to 1.7% at $58K spend.',
      'Frequency capping exceeded 7 impressions per unique cookie in Q3.',
    ],
    derivedInterpretation:
      'Audience saturation in retargeting pools is driving up ad frequency without expanding net reach.',
    metrics: [
      { label: 'Incremental CAC', value: '$72.10', change: '+38.2%', direction: 'up' },
      { label: 'Conversion Rate', value: '1.7%', change: '-0.7% pts', direction: 'down' },
    ],
    drivers: ['Audience fatigue', 'Sub-optimal frequency caps'],
    confidence: 0.91,
    datasetName: 'Marketing_Spend_2025.csv',
    timePeriod: 'Jan 2024 – Dec 2025',
    visualizationReference: {
      chartType: 'Line',
      xAxis: 'orderDate',
      yAxis: 'orders',
      title: 'Display Spend vs. Conversion Rate Trend',
    },
  },
];

// ---------------------------------------------------------------------------
// Simulation Engine: Deterministic Scenario Projection
// ---------------------------------------------------------------------------

export function calculateScenarioProjection(
  baselineRevenueOrDatasetId: number | string = 'sales',
  baselineOrdersOrInputs?: number | ScenarioInputVariables,
  baselineCustomersArg = 14_820,
  inputsArg?: ScenarioInputVariables
): ScenarioProjection {
  let baselineRevenue = 2_480_000;
  let baselineOrders = 18_420;
  let baselineCustomers = 14_820;
  let inputs: ScenarioInputVariables;

  if (typeof baselineRevenueOrDatasetId === 'string') {
    const isMkt = baselineRevenueOrDatasetId === 'marketing';
    baselineRevenue = isMkt ? 1_460_000 : 2_480_000;
    baselineOrders = isMkt ? 12_400 : 18_420;
    baselineCustomers = isMkt ? 10_800 : 14_820;
    inputs = (baselineOrdersOrInputs as ScenarioInputVariables) || {
      marketingSpendDelta: 0,
      priceDelta: 0,
      churnDelta: 0,
    };
  } else {
    baselineRevenue = baselineRevenueOrDatasetId;
    baselineOrders = typeof baselineOrdersOrInputs === 'number' ? baselineOrdersOrInputs : 18_420;
    baselineCustomers = baselineCustomersArg;
    inputs = inputsArg || {
      marketingSpendDelta: 0,
      priceDelta: 0,
      churnDelta: 0,
    };
  }

  const marketingSpendDelta = inputs.marketingSpendDeltaPct ?? inputs.marketingSpendDelta ?? 0;
  const priceDelta = inputs.priceAdjustmentPct ?? inputs.priceDelta ?? 0;
  const churnDelta = inputs.churnRateDeltaPct ?? inputs.churnDelta ?? 0;

  // Elasticity coefficients:
  // Marketing Spend elasticity on orders: ~0.35
  // Price elasticity on demand: -0.45
  // Churn effect on active customer base: -0.75
  const marketingMultiplier = 1 + (marketingSpendDelta / 100) * 0.35;
  const priceMultiplier = 1 + (priceDelta / 100);
  const demandFromPriceMultiplier = 1 - (priceDelta / 100) * 0.45;
  const churnMultiplier = 1 - (churnDelta / 100) * 0.75;

  const orderMultiplier = Math.max(0.4, marketingMultiplier * demandFromPriceMultiplier);
  const projOrders = Math.round(baselineOrders * orderMultiplier);

  // Revenue = Baseline * order volume factor * price realization factor
  const projRevenue = Math.round(baselineRevenue * orderMultiplier * priceMultiplier);
  const projCustomers = Math.round(baselineCustomers * (1 + (marketingSpendDelta / 100) * 0.25) * churnMultiplier);

  const revChangePct = ((projRevenue - baselineRevenue) / baselineRevenue) * 100;
  const ordChangePct = ((projOrders - baselineOrders) / baselineOrders) * 100;
  const custChangePct = ((projCustomers - baselineCustomers) / baselineCustomers) * 100;

  const baselineConv = 3.1;
  const projConv = Math.max(1.0, Math.min(5.5, baselineConv * (1 + (priceDelta < 0 ? 0.08 : -0.06))));
  const convChangePct = ((projConv - baselineConv) / baselineConv) * 100;

  const netImpactDollar = projRevenue - baselineRevenue;
  const netImpactFormatted = (netImpactDollar >= 0 ? '+$' : '-$') + Math.abs(Math.round(netImpactDollar / 1000)).toLocaleString() + 'K';

  const riskAssessment: 'Low' | 'Moderate' | 'Elevated' =
    Math.abs(priceDelta) > 20 || Math.abs(marketingSpendDelta) > 50
      ? 'Elevated'
      : Math.abs(priceDelta) > 8 || Math.abs(marketingSpendDelta) > 20
      ? 'Moderate'
      : 'Low';

  const formatMillions = (num: number) => `$${(num / 1_000_000).toFixed(2)}M`;

  const assumptions: string[] = [
    `Marketing spend adjusted by ${marketingSpendDelta >= 0 ? '+' : ''}${marketingSpendDelta}% assuming constant channel mix.`,
    `Product price adjusted by ${priceDelta >= 0 ? '+' : ''}${priceDelta}% with an estimated price elasticity of demand of -0.45.`,
    `Customer churn delta of ${churnDelta >= 0 ? '+' : ''}${churnDelta}% applied to 90-day retention baseline.`,
    'Macroeconomic conditions and competitor pricing assumed stable over simulation horizon.',
  ];

  const drivers: string[] = [
    marketingSpendDelta > 0 ? 'Increased top-of-funnel acquisition' : 'Reduced acquisition marketing expenditure',
    priceDelta > 0 ? 'Higher average realization per unit' : 'Volume stimulation via competitive pricing',
    churnDelta < 0 ? 'Improved customer lifetime retention' : 'Customer attrition drag on compounding growth',
  ];

  return {
    revenue: {
      baseline: baselineRevenue,
      projected: projRevenue,
      changePercent: Math.round(revChangePct * 10) / 10,
      formatPrefix: '$',
    },
    orders: {
      baseline: baselineOrders,
      projected: projOrders,
      changePercent: Math.round(ordChangePct * 10) / 10,
    },
    customers: {
      baseline: baselineCustomers,
      projected: projCustomers,
      changePercent: Math.round(custChangePct * 10) / 10,
    },
    conversionRate: {
      baseline: baselineConv,
      projected: Math.round(projConv * 10) / 10,
      changePercent: Math.round(convChangePct * 10) / 10,
      formatSuffix: '%',
    },
    projectedRevenue: {
      baseline: formatMillions(baselineRevenue),
      projected: formatMillions(projRevenue),
      delta: `${revChangePct >= 0 ? '+' : ''}${revChangePct.toFixed(1)}%`,
      direction: revChangePct > 0 ? 'up' : revChangePct < 0 ? 'down' : 'neutral',
    },
    netImpact: netImpactFormatted,
    confidenceInterval: '± 4.2% margin of error',
    projectedCustomers: {
      baseline: baselineCustomers.toLocaleString(),
      projected: projCustomers.toLocaleString(),
      delta: `${custChangePct >= 0 ? '+' : ''}${custChangePct.toFixed(1)}%`,
      direction: custChangePct > 0 ? 'up' : custChangePct < 0 ? 'down' : 'neutral',
    },
    projectedCac: {
      baseline: '$142',
      projected: `$${Math.round(142 * (1 + (marketingSpendDelta / 100) * 0.15))}`,
      delta: `${marketingSpendDelta >= 0 ? '+' : ''}${Math.round(marketingSpendDelta * 0.15)}%`,
      direction: marketingSpendDelta > 0 ? 'up' : marketingSpendDelta < 0 ? 'down' : 'neutral',
    },
    riskAssessment,
    assumptions,
    drivers,
  };
}

// ---------------------------------------------------------------------------
// Service Boundary Methods
// ---------------------------------------------------------------------------

export async function getBusinessHealth(datasetId = 'sales'): Promise<BusinessHealthMetric[]> {
  // Simulates realistic asynchronous service response
  await new Promise((r) => setTimeout(r, 60));
  return datasetId === 'marketing' ? MARKETING_HEALTH : SALES_HEALTH;
}

export async function getInsights(datasetId = 'sales', _dateRange?: string): Promise<Insight[]> {
  await new Promise((r) => setTimeout(r, 70));
  return datasetId === 'marketing' ? MARKETING_INSIGHTS : SALES_INSIGHTS;
}

export async function getRisks(datasetId = 'sales'): Promise<Risk[]> {
  await new Promise((r) => setTimeout(r, 50));
  return datasetId === 'marketing' ? [] : SALES_RISKS;
}

export async function getOpportunities(datasetId = 'sales'): Promise<Opportunity[]> {
  await new Promise((r) => setTimeout(r, 50));
  return datasetId === 'marketing' ? [] : SALES_OPPORTUNITIES;
}

export async function getRecommendations(datasetId = 'sales'): Promise<Recommendation[]> {
  await new Promise((r) => setTimeout(r, 50));
  return datasetId === 'marketing' ? [] : SALES_RECOMMENDATIONS;
}

export async function runWhatIfScenario(
  datasetId = 'sales',
  inputs: ScenarioInputVariables
): Promise<ScenarioProjection> {
  await new Promise((r) => setTimeout(r, 120));
  return calculateScenarioProjection(datasetId, inputs);
}
