# 🔄 Dashboard Update Instructions

Follow these steps to refresh the Jelou Product Usage Analysis dashboard with the latest data.

---

## 🏗️ Prerequisites
- **Access to MongoDB:** You need to run queries on the production/logs clusters.
- **Access to SQL Database:** You need to run queries on the `chatbot` database.
- **Python Environment:** Ensure you have `pandas`, `jupyter`, and `streamlit` installed.

---

## 📥 Step 1: Export Fresh Data
Run the following queries and save the results as **CSV files** in the `data/` directory. 

| File Name | Query Location | Source DB |
| :--- | :--- | :--- |
| `signups.csv` | `queries/signups.sql` | SQL (MySQL) |
| `subscriptions.csv` | `queries/subscriptions.sql` | SQL (MySQL) |
| `bots.csv` | `queries/bots.sql` | SQL (MySQL) |
| `stripe_invoices.csv` | `queries/stripe_invoices.sql` | SQL (MySQL) |
| `company_engagement.csv` | `queries/workflow_company_mapping.js` | MongoDB (Logs) |
| `template_usage_connect.csv` | `queries/template_logs.js` | MongoDB (Logs) |
| `user_sessions.csv` | `queries/user_sessions.js` | MongoDB (Logs) |

> **Note:** Ensure all dates are exported in ISO format if possible.

---

## ⚙️ Step 2: Process Data (Jupyter Notebook)
The dashboard relies on pre-calculated metrics (retention, flags, and merged sources) to stay fast.

1. Open `analysis.ipynb`.
2. **Run All Cells**.
3. Verify that the final cell output says: `✅ Saved: data/analysis_combined.csv`.
4. (Optional) Check for warnings about "Internal Jelou accounts" to ensure your test/internal data is being filtered correctly.

---

## 🚀 Step 3: Launch the Dashboard
Once the `analysis_combined.csv` is updated, the dashboard will pick up the changes automatically or upon a manual refresh.

```bash
# In the project root
python -m streamlit run app.py
```

---

## 🔍 Troubleshooting & Maintenance

### 1. Filtering Internal/Test Accounts
If new test accounts appear, add their names to `data/excluded_companies.json`. The dashboard and notebook use this file to filter out noise.

### 2. Date Range Issues
The dashboard defaults to **November 15, 2025**. If you need to change this, update the `default_start` variable in `app.py`.

### 3. Missing Steps in Funnel
If a step in the funnel (e.g., "Created Template") shows 0, ensure the corresponding CSV (e.g., `template_usage_connect.csv`) was exported correctly and the notebook was rerun to include it in the combined dataset.

### 4. Locked CSV Files
If you get a `PermissionError` when running the notebook or exporting, close any Excel or preview windows that have the `.csv` files open.

