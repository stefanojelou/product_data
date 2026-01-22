# Jelou Product Usage Analysis Plan

## Objective

Understand why ~10 daily signups have near-0% conversion to paying customers or production WhatsApp channels.

**Analysis Period:** November 15, 2025 onwards  
**Focus:** SELF_SERVICE plan users (organic signups expected to self-convert)

---

## 1. Current Findings

### Key Insight: 89% Never Execute a Workflow

```
SELF_SERVICE Signups: 338 (100%)
    │
    ├── Created Bot: 338 (100%) ← auto-created on signup
    │
    ├── Executed Workflow: 36 (11%) ← MAJOR DROP-OFF HERE
    │       │
    │       ├── Tested Sandbox: 29 (9%)
    │       │
    │       └── Went to Production: 21 (6%)
    │
    └── Started Connect Trial: 109 (32%)
            │
            ├── Currently Trialing: 32 (9%)
            │
            └── Converted to Paid: 3 (0.9%)
```

### Conversion Rates

| Metric | Value | Insight |
|--------|-------|---------|
| Signup → Execute | 11% | 89% drop-off at first engagement |
| Execute → Production | 58% | Those who try it, often go to prod |
| Connect Trial → Paid | 2.8% | Very low trial conversion |
| Overall Signup → Paid | <1% | Confirms the problem |

### Retention Analysis

| Week | Retention Rate | Users |
|------|----------------|-------|
| Week 1 | ~45% | Still logging in |
| Week 2 | ~25% | Significant drop |
| Week 3 | ~15% | Further decline |
| Week 4 | ~10% | Long-term users |

---

## 2. Questions Answered

| Question | Answer | Source |
|----------|--------|--------|
| Where is the biggest drop-off? | Signup → First Execution (89% lost) | MongoDB workflow_executions |
| Do users who execute go to production? | 58% of executors reach production | company_engagement.csv |
| Does Brain Studio engagement predict Connect? | Overlap analysis in Sankey diagram | Dashboard |
| What's the trial-to-paid conversion? | 2.8% (3 of 109) | subscriptions.csv |

---

## 3. Questions Still Open

### Post-Signup Behavior
| Question | Data Needed | Status |
|----------|-------------|--------|
| Do users log in after signup? | user_sessions.csv | ✅ Have data |
| Do they open the workflow builder? | user_activity_logs | ✅ Have data |
| Where do they get stuck in the builder? | More granular event tracking | ❌ Not available |
| Do they start building but abandon? | Session recordings or events | ❌ Not available |

### Connect-Specific Activity
| Question | Data Needed | Status |
|----------|-------------|--------|
| Do trial users create templates? | templates table | ❓ Ask DBA |
| Do they set up campaigns? | campaigns table | ❓ Ask DBA |
| Do they invite team members? | operators/team_members table | ❓ Ask DBA |
| What Connect features do they use? | Feature usage tracking | ❓ Ask DBA |

---

## 4. Data Sources

### Completed Exports

| File | Rows | Source | Purpose |
|------|------|--------|---------|
| signups.csv | 1,263 | MySQL chatbot.companies | Base accounts |
| bots.csv | 1,118 | MySQL chatbot.bots | Bot creation |
| credit_wallet.csv | 418 | MySQL billing.credit_wallet | Usage credits |
| stripe_invoices.csv | 546 | MySQL billing.stripe_invoices | Payments |
| user_sessions.csv | 899 | MySQL | Login activity |
| workflow_executions.csv | 353 | MongoDB workflow_executions_logs | Execution summary |
| company_engagement.csv | 36 | MongoDB workflow_executions | Sandbox/prod breakdown |
| user_activity_logs.csv | 4,583 | MongoDB | Builder activity |
| analysis_combined.csv | 457 | Pre-calculated | Combined metrics |

### Data Issues

| File | Issue | Fix |
|------|-------|-----|
| subscriptions.csv | CSV parsing errors | Re-export without JSON columns |
| wallet_transactions.csv | CSV parsing errors | Re-export with consistent structure |

---

## 5. Dashboard Implementation

### Completed Features

| Page | Features |
|------|----------|
| **Overview** | KPI cards, pie charts (subscriptions, Connect status), retention curves (Overall/Brain/Connect), daily signups chart |
| **Activation Funnel** | Sankey diagram showing user journey, Brain Studio funnel with execution stages, Connect funnel |
| **Company Data** | Filterable table, retention-based filters (Week 1-4 active), export capability |
| **Company Explorer** | Individual company deep-dive, activity timeline |

### Filters

- **Date Range:** Nov 15, 2025 onwards (default)
- **Plan Type:** SELF_SERVICE, ENTERPRISE, SMB, POCKET
- **Internal Filter:** Excludes @jelou.ai emails and jelou slugs

---

## 6. Recommended Next Steps

### Immediate (This Week)

1. **Fix CSV exports**
   - Re-export subscriptions.csv without JSON columns
   - Re-export wallet_transactions.csv

2. **Analyze the 89% drop-off**
   - Cross-reference user_sessions with workflow_executions
   - Identify: Do they log in but not execute? Or not log in at all?

3. **Ask DBA about Connect tables**
   - templates, campaigns, operators
   - Any UI event tracking

### Short-term (Next 2 Weeks)

4. **Deep-dive on executors**
   - What do the 36 companies that executed do differently?
   - Time from signup to first execution
   - Features they use

5. **Improve retention analysis**
   - Add cohort analysis by signup week
   - Compare retention by plan type

### Medium-term (This Quarter)

6. **Implement event tracking**
   - Track UI clicks and page views
   - Identify abandonment points

7. **User interviews**
   - Contact users who signed up but didn't execute
   - Understand their intent and blockers

---

## 7. Hypothesis to Test

Based on the data, potential reasons for low conversion:

| Hypothesis | How to Validate |
|------------|-----------------|
| Users don't understand the product | Check if they log in but don't act |
| Onboarding is confusing | Check time-to-first-action |
| Wrong audience (window shoppers) | Check source/referrer data |
| Technical barriers | Check error rates in executions |
| Pricing concerns | Check if they view pricing but don't convert |

---

## 8. Success Metrics

### Target Improvements

| Metric | Current | Target | Impact |
|--------|---------|--------|--------|
| Signup → Execute | 11% | 25% | 2.3x more engaged users |
| Execute → Production | 58% | 70% | Better completion |
| Trial → Paid | 2.8% | 10% | 3.6x more revenue |

### How to Track

1. Weekly dashboard review
2. Cohort analysis by signup week
3. A/B test onboarding changes

---

## 9. Files Reference

| File | Purpose |
|------|---------|
| `app.py` | Streamlit dashboard |
| `analysis.ipynb` | Jupyter notebook for data analysis |
| `docs/analysis_plan.md` | This document |
| `docs/business_flow.md` | Business flow documentation |
| `queries/export_instructions_v2.md` | Data export instructions |
| `queries/*.sql` | MySQL queries |
| `queries/*.js` | MongoDB aggregation queries |
| `data/*.csv` | Exported data files |
