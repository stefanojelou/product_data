# Data Export Instructions v2

## Overview

Data exports for Jelou product usage analysis. **Date filter: November 15, 2025 onwards.**

---

## Export Status Summary

| File | Source | Rows | Status |
|------|--------|------|--------|
| signups.csv | MySQL chatbot.companies | 1,263 | ✅ Complete |
| bots.csv | MySQL chatbot.bots | 1,118 | ✅ Complete |
| credit_wallet.csv | MySQL billing.credit_wallet | 418 | ✅ Complete |
| stripe_invoices.csv | MySQL billing.stripe_invoices | 546 | ✅ Complete |
| user_sessions.csv | MySQL (user login sessions) | 899 | ✅ Complete |
| subscriptions.csv | MySQL billing.subscriptions | ~440 | ⚠️ CSV parsing errors |
| wallet_transactions.csv | MySQL billing.wallet_transactions | ~98 | ⚠️ CSV parsing errors |
| workflow_executions.csv | MongoDB workflow_executions_logs | 353 | ✅ Complete |
| company_engagement.csv | MongoDB workflow_executions | 36 | ✅ Complete |
| user_activity_logs.csv | MongoDB user_activity_logs | 4,583 | ✅ Complete |
| analysis_combined.csv | Pre-calculated (from analysis.ipynb) | 457 | ✅ Complete |

---

## MySQL Exports

### 1. Signups ✅
- **File:** `data/signups.csv`
- **Query:** `queries/signups.sql`
- **Database:** chatbot
- **Purpose:** Base list of all accounts

### 2. Bots ✅
- **File:** `data/bots.csv`
- **Query:** `queries/bots.sql`
- **Database:** chatbot
- **Purpose:** Track bot creation and production channel connection
- **Key Field:** `in_production = 1` means production WhatsApp connected

### 3. Credit Wallet ✅
- **File:** `data/credit_wallet.csv`
- **Query:** `queries/credit_wallet.sql`
- **Database:** billing
- **Purpose:** Track conversation usage and free tier exhaustion
- **Key Fields:** 
  - `total_used` - conversations used
  - `free_conversations` - free tier allowance
  - `exceeded_free_tier` (derived) - 1 if they should be paying

### 4. Stripe Invoices ✅
- **File:** `data/stripe_invoices.csv`
- **Query:** `queries/stripe_invoices.sql`
- **Database:** billing
- **Purpose:** Actual payments received
- **Key Fields:** `amount_paid`, `paid_at`, `status`

### 5. User Sessions ✅
- **File:** `data/user_sessions.csv`
- **Query:** `queries/user_sessions.sql`
- **Database:** chatbot
- **Purpose:** Track user login activity for retention analysis
- **Key Fields:** `first_session`, `last_session`, `total_sessions`

### 6. Subscriptions ⚠️ (Needs Re-export)
- **File:** `data/subscriptions.csv`
- **Query:** `queries/subscriptions.sql`
- **Database:** billing
- **Issue:** CSV parsing errors due to embedded JSON in metadata columns
- **Fix:** Re-export without JSON columns, or escape them properly

### 7. Wallet Transactions ⚠️ (Needs Re-export)
- **File:** `data/wallet_transactions.csv`
- **Query:** `queries/wallet_transactions.sql`
- **Database:** billing
- **Issue:** CSV parsing errors
- **Fix:** Re-export with consistent column structure

---

## MongoDB Exports

### Export Steps (MongoDB Compass):

1. Open MongoDB Compass
2. Connect to `workflow-server.xc3enot.mongodb.net`
3. Navigate to `builder` database
4. Select the collection
5. Go to **Aggregations** tab
6. Paste stages from `.js` file
7. Click "Export" → JSON
8. Convert JSON to CSV (use Python or online tool)

### 1. Workflow Executions Logs ✅
- **File:** `data/workflow_executions.csv`
- **Query:** `queries/workflow_executions.js`
- **Collection:** `workflow_executions_logs`
- **Purpose:** Company-level execution summary (already aggregated)
- **Key Fields:** `total_executions`, `completed`, `crashed`

### 2. Company Engagement ✅
- **File:** `data/company_engagement.csv`
- **Query:** `queries/workflow_company_mapping.js`
- **Collection:** `workflow_executions`
- **Purpose:** Sandbox vs Production breakdown, WhatsApp vs Web usage
- **Key Fields:** `sandbox_executions`, `prod_executions`, `whatsapp_executions`, `tested_sandbox`, `went_to_prod`
- **Note:** Filtered for SELF_SERVICE companies only (342 company IDs)

### 3. User Activity Logs ✅
- **File:** `data/user_activity_logs.csv`
- **Query:** `queries/user_activity_logs.js`
- **Collection:** `user_activity_logs`
- **Purpose:** Workflow builder activity (create/update/delete nodes)
- **Key Fields:** `total_actions`, `create_node`, `update_node`, `delete_node`

---

## Current Funnel Metrics (Nov 15, 2025+)

Based on exported data, the actual conversion funnel:

### Brain Studio Funnel (SELF_SERVICE):
```
Signups: 338 (100%)
    ↓
Created Bot: 338 (100%) -- auto-created
    ↓
Executed Workflow: 36 (11%)  ← MAJOR DROP-OFF
    ↓
Tested Sandbox: 29 (9%)
    ↓
Went to Production: 21 (6%)
    ↓
Used Conversations: ? (need credit_wallet join)
    ↓
Exceeded Free Tier: ? (need credit_wallet join)
    ↓
Actually Paid: ? (need stripe_invoices join)
```

### Connect Funnel:
```
Signups: 338 (100%)
    ↓
Started Connect Trial: 109 (32%)
    ↓
Currently Trialing: 32 (9%)
    ↓
Converted to Paid: 3 (0.9%)
```

---

## Key Insight

**89% of signups never execute a single workflow!**

This is the primary drop-off point. Users sign up but don't engage with the product.

---

## Questions Still Open

1. **What do users do after signup?** - Do they log in? Open the builder? Get stuck?
2. **Why don't they execute?** - Is the UI confusing? Are they window shopping?
3. **Connect-specific activity?** - Do they use templates? Create campaigns?

### Tables to Ask DBA About:
- `chatbot.templates` - Template usage
- `chatbot.campaigns` - Campaign creation
- `chatbot.operators` or `team_members` - Team invites
- Any UI event tracking table

---

## How to Re-export CSV with Issues

For `subscriptions.csv` and `wallet_transactions.csv`:

1. **Option A:** Exclude JSON columns from the query
   ```sql
   -- Remove columns like metadata, details, etc.
   SELECT id, company_id, status, ... -- exclude JSON columns
   ```

2. **Option B:** Export as JSON instead of CSV
   - Right-click → Export Resultset → JSON
   - Then use Python to convert:
   ```python
   import pandas as pd
   df = pd.read_json('file.json')
   df.to_csv('file.csv', index=False)
   ```

3. **Option C:** Use Python in MySQL Workbench
   - Export to CSV with proper quoting
   - Ensure all fields are properly escaped
