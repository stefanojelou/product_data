# Jelou Product Usage Analysis

Dashboard to analyze Brain Studio product usage for new account conversion.

## Problem

~10-18 new signups per day with ~0% conversion to:
- Adding a credit card
- Connecting a production channel

**Key question**: What are these new accounts doing? Did they try anything, even in sandbox?

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Export Data

Follow the instructions in `queries/export_instructions.md` to export data from:

| Source | File | Database |
|--------|------|----------|
| MySQL | `data/signups.csv` | chatbot.companies |
| MySQL | `data/subscriptions.csv` | billing.subscriptions |
| MongoDB | `data/workflow_executions.csv` | workflow-server.builder |
| MongoDB | `data/node_executions.csv` | workflow-server.builder |
| MongoDB | `data/user_activity_logs.csv` | workflow-server.builder |

### 3. Run Dashboard

```bash
streamlit run app.py
```

The app will open at http://localhost:8501

## Features

### Overview
- Total signups with daily average
- Activity rate (% with any execution)
- Sandbox-only vs production users
- Paid conversion rate

### Activation Funnel
- Visual funnel: Signup → Execution → Sandbox → Production → Paid
- Drop-off analysis between each stage

### Brain Studio Deep Dive
- Sandbox vs Production execution breakdown
- Channel distribution (Web, WhatsApp, Facebook)
- Top node types used
- Activity over time

### Company Explorer
- Searchable table of all companies
- Filter by activity status, subscription status
- Export to CSV

## Data Sources

### MySQL
- `chatbot.companies` - New signups
- `billing.subscriptions` - Payment/trial status
- `billing.customers` - Stripe customer info

### MongoDB (workflow-server.builder)
- `workflow_executions` - Sandbox/production runs
- `node_executions` - Which nodes are used
- `user_activity_logs` - User actions (CREATE_NODE, UPDATE_NODE)
- `versions` - Workflow versions created

## Sample Data

If no CSV files are present, the app generates sample data for demo purposes.

## Key Metrics

| Metric | What it answers |
|--------|-----------------|
| Activity Rate | % of signups that did anything |
| Sandbox Only | Tested but never went live |
| Production Rate | % that connected a real channel |
| Paid Rate | % that added payment |
| Time to First Action | Days between signup and first execution |

