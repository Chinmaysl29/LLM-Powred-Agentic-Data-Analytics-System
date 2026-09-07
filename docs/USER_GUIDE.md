# AI Data Analyst OS — User & Business Analyst Guide

## Welcome
AI Data Analyst OS provides automated dataset intelligence, predictive forecasting, and strategic business recommendations through natural language interaction.

---

## Step 1: Uploading Your Dataset
1. Navigate to **Datasets** on the sidebar.
2. Drag and drop your `.csv`, `.xlsx`, or `.parquet` file.
3. The platform automatically scans your data and presents:
   - Total rows and columns
   - Data types and missing value detection
   - Data Quality Score (0 to 100%)

---

## Step 2: Natural Language Analytics
Type business questions into the analyst console:
- *"What were our top 5 products by revenue last quarter?"*
- *"Are there any anomalies in our monthly operational expenses?"*
- *"Show me customer churn correlation against discount rates."*

The system writes and validates ANSI SQL queries behind the scenes, executes them safely, and renders charts (bar, line, scatter).

---

## Step 3: Generating Time-Series Forecasts
1. Select **Forecasting** from the navigation menu.
2. Choose your target column (e.g. `revenue`, `units_sold`, `inventory_level`).
3. Set your projection horizon (e.g., 14, 30, or 90 days).
4. Click **Run Forecast**.
5. The system backtests ARIMA, Prophet, and XGBoost, selects the optimal model, and provides lower/upper 95% confidence intervals.

---

## Step 4: Strategic Recommendations & Reports
Click **Generate Insights** to produce:
- Cost Optimization opportunities
- Pricing adjustment recommendations
- Inventory stockout mitigation plans
- Export ready-to-share PDF / XLSX Executive Reports
