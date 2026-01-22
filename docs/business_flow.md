# Jelou Product Usage - Business Flow Documentation

## Overview

Jelou has two main products with different billing models:
1. **Brain Studio** - Usage-based (free tier + pay per conversation)
2. **Connect** - Subscription-based ($20/month with 14-day trial)

**Analysis Period:** November 15, 2025 onwards

---

## 1. Signup Flow

```
User Signup (chatbot.companies)
       │
       ├── plan = SELF_SERVICE (organic signups, expected to self-convert)
       ├── plan = ENTERPRISE (sales-assisted, different flow)
       ├── plan = SMB / POCKET (other tiers)
       │
       └── Auto-creates Brain Studio subscription (FREE, amount=0)
           └── Also auto-creates a Bot
```

**Key Tables:**
- `chatbot.companies` - Main signup/account table
- `billing.subscriptions` - Subscription records (auto-created for Brain Studio)
- `chatbot.bots` - Auto-created on signup

---

## 2. Brain Studio Activation Flow (Updated)

Based on MongoDB workflow execution data, we now track the **execution journey**:

```
Signup (338 SELF_SERVICE users)
   │
   ▼
Bot Auto-Created (338 = 100%)
   │
   ▼
User Opens Workflow Builder
   │  └── MongoDB: user_activity_logs (CREATE_NODE, UPDATE_NODE, DELETE_NODE)
   │
   ▼
User Executes Workflow ← MAJOR DROP-OFF (only 11% reach this!)
   │  └── MongoDB: workflow_executions
   │
   ├─────────────────────────────┐
   │                             │
   ▼                             ▼
Sandbox Testing (29)        Production Execution (21)
   │  └── isDebug=true          │  └── isDebug=false
   │                             │
   │                             ▼
   │                        WhatsApp Channel (?)
   │                             │  └── channel="WHATSAPP"
   │                             │
   └──────────────┬──────────────┘
                  │
                  ▼
        Free Conversations Used
           │  └── credit_wallet.total_used
           │
           ▼
        Exceeded Free Tier
           │  └── total_used > free_conversations
           │
           ▼
        Actually Paid
              └── stripe_invoices.amount_paid > 0
```

### Execution Stages (NEW)

| Stage | Count | % of Signups | Data Source |
|-------|-------|--------------|-------------|
| Signup | 338 | 100% | chatbot.companies |
| Created Bot | 338 | 100% | chatbot.bots (auto-created) |
| Executed Workflow | 36 | 11% | MongoDB workflow_executions |
| Tested Sandbox | 29 | 9% | workflow_executions (sandbox_executions > 0) |
| Went to Production | 21 | 6% | workflow_executions (prod_executions > 0) |

**Key Insight:** 89% of users never execute a single workflow!

---

## 3. Connect Product Flow

```
User Wants Connect Features
   │
   ▼
Starts 14-Day Trial (status = TRIALING)
   │  └── billing.subscriptions.trial_start / trial_end
   │  └── amount = $20/month
   │
   ▼
Trial Ends
   │
   ├── Adds Credit Card → status = ACTIVE (paying)
   │
   └── No Credit Card → status = CANCELED/UNPAID
```

### Connect Conversion (Nov 15, 2025+)

| Stage | Count | % of Signups | % of Previous |
|-------|-------|--------------|---------------|
| Signup | 338 | 100% | - |
| Started Trial | 109 | 32% | 32% |
| Currently Trialing | 32 | 9% | 29% |
| Converted to Paid | 3 | 0.9% | 2.8% |

---

## 4. User Journey Sankey Diagram

The Streamlit dashboard now includes a **Sankey diagram** that visualizes:

1. **Brain Studio Path:** Signup → Created Bot → Executed Workflow → Sandbox → Production
2. **Connect Path:** Signup → Connect Trial → Paid
3. **Overlap:** Users who engaged with both products

```
                    ┌─────────────────────────────────────┐
                    │                                     │
    ┌───────────────┴───────────────┐                     │
    │                               │                     │
    ▼                               ▼                     ▼
Created Bot ─────────────────► Executed ──► Sandbox ──► Production
(338)        No Execution      (36)         (29)        (21)
             (302 = 89%!)
    │
    │
    ▼
Connect Trial ──────────────────────────────────────────► Paid
(109)              Still Trialing (32)                    (3)
```

### Overlap Analysis

The Sankey diagram reveals whether users who execute workflows are the same ones who try Connect:
- **Overlap count** shows companies that did BOTH
- Helps identify if Brain Studio engagement correlates with Connect adoption

---

## 5. Data Sources Summary

### MySQL - chatbot database:
| Table | Key Fields | Purpose |
|-------|------------|---------|
| `companies` | id, plan, createdAt, inProduction | Signups |
| `bots` | companyId, inProduction, type, createdAt | Bot/Channel tracking |

### MySQL - billing database:
| Table | Key Fields | Purpose |
|-------|------------|---------|
| `subscriptions` | company_id, status, product_name, trial_* | Subscription status |
| `credit_wallet` | company_id, balance, total_used, free_conversations | Usage credits |
| `wallet_transactions` | company_id, action, amount, created_at | Charge records |
| `stripe_invoices` | company_id, amount_paid, paid_at, status | Actual payments |
| `payment_methods` | customer_id | Credit cards on file |

### MongoDB - workflow-server.builder:
| Collection | Key Fields | Purpose |
|------------|------------|---------|
| `workflow_executions` | data.company.id, isDebug, data.channel | Actual execution with sandbox/prod breakdown |
| `workflow_executions_logs` | company.id, status.completed | Pre-aggregated execution logs |
| `user_activity_logs` | workflowId, userOperation | Builder activity (create/update/delete nodes) |
| `node_executions` | Node.workflowId, type | Node-level execution details |

---

## 6. Corrected Conversion Funnel

### Brain Studio (Usage-Based):

| Stage | How to Measure | Table/Field |
|-------|----------------|-------------|
| 1. Signup | Account created | `chatbot.companies` |
| 2. Created Bot | Has at least 1 bot | `chatbot.bots` (auto-created) |
| 3. Executed Workflow | Ran workflow in builder | MongoDB `workflow_executions` |
| 4. Tested Sandbox | `isDebug=true` execution | `workflow_executions` sandbox_executions > 0 |
| 5. Went to Production | `isDebug=false` execution | `workflow_executions` prod_executions > 0 |
| 6. Used Conversations | Had real chats | `credit_wallet.total_used > 0` |
| 7. Exceeded Free Tier | Billable usage | `total_used > free_conversations` |
| 8. Actually Paid | Payment received | `stripe_invoices.amount_paid > 0` |

### Connect (Subscription):

| Stage | How to Measure | Table/Field |
|-------|----------------|-------------|
| 1. Signup | Account created | `chatbot.companies` |
| 2. Started Trial | Has Connect subscription | `subscriptions.product = 'Connect'` |
| 3. In Trial | `status = TRIALING` | `subscriptions.status` |
| 4. Converted to Paid | `status = ACTIVE` | `subscriptions.status = 'ACTIVE'` |

---

## 7. Key Findings

### Primary Drop-off Point
**89% of signups never execute a workflow!**

This means:
- Users sign up but don't engage with the core product
- The onboarding or first-time experience may be confusing
- Users might be "window shopping" without intent to use

### Connect Adoption
- 32% of signups start a Connect trial
- Only 2.8% of trials convert to paid
- Trial-to-paid conversion is a major issue

### What We Still Don't Know
1. Do users even log in after signup?
2. Do they open the workflow builder?
3. Where exactly do they get stuck?
4. What Connect features do they use (templates, campaigns)?

---

## 8. Dashboard Features

The Streamlit dashboard (`app.py`) now includes:

| Page | Features |
|------|----------|
| **Overview** | KPI cards, pie charts, retention curves, daily signups |
| **Activation Funnel** | Sankey diagram, Brain Studio funnel, Connect funnel |
| **Company Data** | Filterable table with retention filters |
| **Company Explorer** | Individual company deep-dive |

### Filters Available
- **Date Range:** Default Nov 15, 2025 onwards
- **Plan Type:** SELF_SERVICE, ENTERPRISE, etc.
- **Retention Filters:** Week 1/2/3/4 active

---

## 9. Next Steps

1. **Understand the 89% drop-off**
   - Why don't users execute workflows?
   - Is the UI confusing? Are they missing onboarding?

2. **Track Connect-specific activity**
   - Templates usage
   - Campaigns created
   - Operators added

3. **Implement event tracking**
   - Track UI clicks and page views
   - Identify where users abandon
