"""
Brain Studio Product Usage Analysis Dashboard
Analyze new account activity to understand conversion drop-off
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# Page config
# Updated: 2026-01-22 23:40
st.set_page_config(
    page_title="Jelou Product Usage Analysis",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme with accent colors
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    :root {
        --primary: #00D4AA;
        --secondary: #7C3AED;
        --warning: #F59E0B;
        --danger: #EF4444;
        --bg-dark: #0F0F1A;
        --bg-card: #1A1A2E;
        --text-primary: #FFFFFF;
        --text-secondary: #A0A0B0;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 50%, #16213E 100%);
    }
    
    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--text-primary) !important;
    }
    
    .metric-card {
        background: linear-gradient(145deg, #1A1A2E 0%, #252542 100%);
        border: 1px solid rgba(124, 58, 237, 0.3);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00D4AA, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 8px 0;
    }
    
    .metric-label {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--text-secondary);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .status-active { color: #00D4AA; }
    .status-sandbox { color: #F59E0B; }
    .status-inactive { color: #EF4444; }
    
    .sidebar .stSelectbox label, .sidebar .stDateInput label {
        color: var(--text-secondary) !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
    }
</style>
""", unsafe_allow_html=True)


# --- Data Loading ---
def get_excluded_companies_hash():
    """Get hash of excluded_companies.json to bust cache when it changes"""
    excluded_path = Path("data/excluded_companies.json")
    if excluded_path.exists():
        return excluded_path.stat().st_mtime
    return 0

@st.cache_data
def load_data(_excluded_hash=None):
    """Load CSV data from the data/ directory"""
    data = {}
    data_path = Path("data")
    
    # Load each CSV if it exists
    files = {
        'signups': 'signups.csv',
        'subscriptions': 'subscriptions.csv',
        'bots': 'bots.csv',
        'credit_wallet': 'credit_wallet.csv',
        'stripe_invoices': 'stripe_invoices.csv',
        'wallet_transactions': 'wallet_transactions.csv',
        'workflow_executions': 'workflow_executions.csv',
        'node_executions': 'node_executions.csv',
        'user_activity': 'user_activity_logs.csv',
        'user_sessions': 'user_sessions.csv',
        'analysis': 'analysis_combined.csv',
        'company_engagement': 'company_engagement.csv',
        'template_usage': 'template_usage_connect.csv',
        'sessions_duration': 'sessions_duration.csv'
    }
    
    for key, filename in files.items():
        filepath = data_path / filename
        if filepath.exists():
            try:
                # Special handling for subscriptions.csv which has JSON in metadata column
                if key == 'subscriptions':
                    # Read line by line to handle embedded JSON
                    import csv
                    rows = []
                    with open(filepath, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        headers = next(reader)
                        for row in reader:
                            if len(row) >= 5:  # At least have key columns
                                # Pad or truncate row to match header length
                                if len(row) < len(headers):
                                    row = row + [''] * (len(headers) - len(row))
                                elif len(row) > len(headers):
                                    row = row[:len(headers)]
                                rows.append(row)
                    df = pd.DataFrame(rows, columns=headers)
                else:
                    df = pd.read_csv(filepath, on_bad_lines='skip')
                
                # Parse date columns - be more specific to avoid false matches
                date_cols = [c for c in df.columns if c.endswith('_at') or c.endswith('_date') or c in ['created_at', 'updated_at', 'first_subscription', 'first_execution', 'last_execution', 'paid_at']]
                for col in date_cols:
                    try:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    except:
                        pass
                data[key] = df
            except Exception as e:
                st.warning(f"Error loading {filename}: {e}")
                data[key] = None
        else:
            data[key] = None
    
    # Filter out internal Jelou users (@jelou.ai emails)
    if data['signups'] is not None:
        # Check if email column exists and filter out jelou.ai emails
        if 'email' in data['signups'].columns:
            before_count = len(data['signups'])
            data['signups'] = data['signups'][
                ~data['signups']['email'].str.contains('@jelou.ai', case=False, na=False)
            ]
            after_count = len(data['signups'])
            print(f"[INFO] Filtered out {before_count - after_count} internal @jelou.ai users")
        
        # Also filter by company slug containing 'jelou' (catches test accounts)
        if 'slug' in data['signups'].columns:
            before_count = len(data['signups'])
            data['signups'] = data['signups'][
                ~data['signups']['slug'].str.contains('jelou', case=False, na=False)
            ]
            after_count = len(data['signups'])
            print(f"[INFO] Filtered out {before_count - after_count} jelou-related company slugs")
    
        # Filter out test companies from excluded_companies.json
        excluded_companies_path = data_path / "excluded_companies.json"
        if excluded_companies_path.exists():
            try:
                import json
                with open(excluded_companies_path, 'r', encoding='utf-8') as f:
                    excluded_data = json.load(f)
                excluded_names = [name.strip().lower() for name in excluded_data.get('excluded_companies', [])]
                
                if 'company_name' in data['signups'].columns and len(excluded_names) > 0:
                    before_count = len(data['signups'])
                    data['signups'] = data['signups'][
                        ~data['signups']['company_name'].str.strip().str.lower().isin(excluded_names)
                    ]
                    after_count = len(data['signups'])
                    print(f"[INFO] Filtered out {before_count - after_count} test companies from excluded_companies.json")
            except Exception as e:
                print(f"[WARNING] Could not load excluded_companies.json: {e}")
    
    # Build corrected analysis with all data sources
    if data['signups'] is not None:
        data['analysis'] = create_corrected_analysis(data)
    
    return data


def create_corrected_analysis(data):
    """Create corrected analysis using all data sources including bots and payments"""
    # If analysis_combined.csv already has all columns (pre-calculated in notebook), just return it
    # This avoids re-processing and column conflicts
    existing_analysis = data.get('analysis')
    if existing_analysis is not None and 'retained_week1' in existing_analysis.columns and 'bot_count' in existing_analysis.columns:
        # The notebook already processed everything - apply global exclusions and return
        result = existing_analysis.copy()
        
        # Merge session duration if not already there but file exists
        sessions_duration = data.get('sessions_duration')
        if sessions_duration is not None and 'total_time_minutes' not in result.columns:
            sd = sessions_duration.copy()
            sd.columns = ['company_id', 'total_time_minutes', 'avg_session_minutes', 'session_count']
            sd['company_id'] = pd.to_numeric(sd['company_id'], errors='coerce')
            result['company_id'] = pd.to_numeric(result['company_id'], errors='coerce')
            result = result.merge(sd, on='company_id', how='left')
            result['total_time_minutes'] = result['total_time_minutes'].fillna(0)
            result['avg_session_minutes'] = result['avg_session_minutes'].fillna(0)
            result['session_count_sd'] = result['session_count'].fillna(0)

        # Filter out internal Jelou users (@jelou.ai emails) and jelou slugs
        if 'email' in result.columns:
            before_count = len(result)
            result = result[~result['email'].astype(str).str.contains('@jelou.ai', case=False, na=False)]
            # Also filter out impersonate emails
            result = result[~result['email'].astype(str).str.contains('impersonate', case=False, na=False)]
            after_count = len(result)
            print(f"[INFO] Filtered out {before_count - after_count} internal/impersonate users from analysis_combined.csv")

        if 'slug' in result.columns:
            before_count = len(result)
            result = result[~result['slug'].astype(str).str.contains('jelou', case=False, na=False)]
            after_count = len(result)
            print(f"[INFO] Filtered out {before_count - after_count} jelou-related company slugs from analysis_combined.csv")

        # Filter out excluded companies from JSON
        excluded_path = Path("data/excluded_companies.json")
        if excluded_path.exists() and 'company_name' in result.columns:
            try:
                import json
                with open(excluded_path, 'r', encoding='utf-8') as f:
                    excluded_data = json.load(f)
                excluded_names = [name.strip().lower() for name in excluded_data.get('excluded_companies', [])]
                
                if len(excluded_names) > 0:
                    before_count = len(result)
                    result = result[~result['company_name'].str.strip().str.lower().isin(excluded_names)]
                    print(f"[INFO] Filtered out {before_count - len(result)} test companies from analysis_combined.csv")
            except Exception as e:
                print(f"[WARNING] Could not filter analysis data: {e}")

        # Merge node type flags from nodes_used.csv if not already present
        node_type_cols = [c for c in result.columns if c.startswith('node_type_')]
        if len(node_type_cols) == 0:
            nodes_path = Path("data/nodes_used.csv")
            if nodes_path.exists():
                try:
                    nodes_df = pd.read_csv(nodes_path, on_bad_lines='skip')
                    nodes_df['company_id'] = pd.to_numeric(nodes_df['company_id'], errors='coerce')
                    nodes_df['nodeTypeId'] = pd.to_numeric(nodes_df['nodeTypeId'], errors='coerce')
                    
                    # Top 5 node types by total nodes_created
                    node_type_totals = (
                        nodes_df.groupby('nodeTypeId')['nodes_created']
                        .sum()
                        .sort_values(ascending=False)
                    )
                    top_5_types = node_type_totals.head(5).index.tolist()
                    
                    # Create flags per company
                    nodes_df['node_type_group'] = np.where(
                        nodes_df['nodeTypeId'].isin(top_5_types),
                        nodes_df['nodeTypeId'],
                        'other'
                    )
                    
                    node_flags = (
                        nodes_df.groupby(['company_id', 'node_type_group'])['nodes_created']
                        .sum()
                        .unstack(fill_value=0)
                    )
                    node_flags = (node_flags > 0).astype(int)
                    
                    # Rename columns with human-readable labels
                    NODE_TYPE_ID_TO_NAME = {
                        3: 'node_type_message',
                        5: 'node_type_code',
                        14: 'node_type_conditional',
                        16: 'node_type_skill',
                        18: 'node_type_memory',
                    }
                    def _node_type_flag_name(value):
                        if value == 'other':
                            return 'node_type_other'
                        if isinstance(value, str):
                            value = float(value)
                        int_val = int(value)
                        return NODE_TYPE_ID_TO_NAME.get(int_val, f"node_type_{int_val}")
                    
                    node_flags = node_flags.rename(columns=_node_type_flag_name).reset_index()
                    
                    # Merge into result
                    result['company_id'] = pd.to_numeric(result['company_id'], errors='coerce')
                    result = result.merge(node_flags, on='company_id', how='left')
                    
                    # Fill NaN with 0 for node type columns
                    node_type_flag_cols = [c for c in node_flags.columns if c != 'company_id']
                    for col in node_type_flag_cols:
                        if col in result.columns:
                            result[col] = result[col].fillna(0).astype(int)
                    
                    # Calculate total nodes created per company
                    total_nodes = nodes_df.groupby('company_id')['nodes_created'].sum().reset_index()
                    total_nodes.columns = ['company_id', 'total_nodes_created']
                    result = result.merge(total_nodes, on='company_id', how='left')
                    result['total_nodes_created'] = result['total_nodes_created'].fillna(0).astype(int)
                    
                    # Create 'created_node' flag (any node type)
                    result['created_node'] = (result[node_type_flag_cols].sum(axis=1) > 0).astype(int)
                    
                    print(f"[INFO] Merged node type flags from nodes_used.csv: {node_type_flag_cols}")
                except Exception as e:
                    print(f"[WARNING] Could not merge node type flags: {e}")
        
        return result
    
    # Otherwise, build from signups
    signups = data['signups'].copy()
    subscriptions = data.get('subscriptions')
    bots = data.get('bots')
    credit_wallet = data.get('credit_wallet')
    stripe_invoices = data.get('stripe_invoices')
    
    # --- Subscription info with PRODUCT differentiation ---
    if subscriptions is not None and len(subscriptions) > 0:
        # Ensure company_id types match for merging
        subscriptions['company_id'] = pd.to_numeric(subscriptions['company_id'], errors='coerce')
        
        companies_with_subs = subscriptions['company_id'].dropna().unique()
        signups['has_subscription'] = signups['company_id'].isin(companies_with_subs)
        
        # Check for active/trialing
        active_companies = subscriptions[subscriptions['status'] == 'ACTIVE']['company_id'].unique()
        trialing_companies = subscriptions[subscriptions['status'] == 'TRIALING']['company_id'].unique()
        signups['has_active'] = signups['company_id'].isin(active_companies)
        signups['has_trialing'] = signups['company_id'].isin(trialing_companies)
        
        # --- BRAIN STUDIO specific ---
        # Matches: "Brain studio", "Brain conversaciones"
        brain_subs = subscriptions[subscriptions['product_name'].str.contains('Brain', case=False, na=False)]
        brain_companies = brain_subs['company_id'].unique()
        signups['has_brain_studio'] = signups['company_id'].isin(brain_companies)
        
        brain_active = brain_subs[brain_subs['status'] == 'ACTIVE']['company_id'].unique()
        signups['brain_active'] = signups['company_id'].isin(brain_active)
        
        # --- CONNECT specific ---
        # Matches: "Connect", "Plan Connect"
        connect_subs = subscriptions[subscriptions['product_name'].str.contains('Connect', case=False, na=False)]
        connect_companies = connect_subs['company_id'].unique()
        signups['has_connect'] = signups['company_id'].isin(connect_companies)
        
        connect_active = connect_subs[connect_subs['status'] == 'ACTIVE']['company_id'].unique()
        connect_trialing = connect_subs[connect_subs['status'] == 'TRIALING']['company_id'].unique()
        signups['connect_active'] = signups['company_id'].isin(connect_active)
        signups['connect_trialing'] = signups['company_id'].isin(connect_trialing)
        
        # Debug: Log product detection counts
        print(f"[DEBUG] Brain subs found: {len(brain_subs)}, companies: {len(brain_companies)}")
        print(f"[DEBUG] Connect subs found: {len(connect_subs)}, companies: {len(connect_companies)}")
    else:
        signups['has_subscription'] = False
        signups['has_active'] = False
        signups['has_trialing'] = False
        signups['has_brain_studio'] = False
        signups['brain_active'] = False
        signups['has_connect'] = False
        signups['connect_active'] = False
        signups['connect_trialing'] = False
    
    # --- Bot info (CRITICAL for correct funnel) ---
    if bots is not None and len(bots) > 0:
        bot_companies = bots['company_id'].unique()
        signups['has_bot'] = signups['company_id'].isin(bot_companies)
        
        # Live in Production - the key metric! (state = 1 AND in_production = 1)
        prod_bots = bots[(bots['in_production'] == 1) & (bots['state'] == 1)]
        prod_companies = prod_bots['company_id'].unique()
        signups['has_prod_channel'] = signups['company_id'].isin(prod_companies)
        
        # Bot count per company
        bot_counts = bots.groupby('company_id').size().reset_index(name='bot_count')
        signups = signups.merge(bot_counts, on='company_id', how='left')
        signups['bot_count'] = signups['bot_count'].fillna(0).astype(int)
    else:
        signups['has_bot'] = False
        signups['has_prod_channel'] = False
        signups['bot_count'] = 0
    
    # --- Credit wallet / conversation usage ---
    if credit_wallet is not None and len(credit_wallet) > 0:
        used_companies = credit_wallet[credit_wallet['total_used'] > 0]['company_id'].unique()
        signups['used_conversations'] = signups['company_id'].isin(used_companies)
        
        exceeded_companies = credit_wallet[credit_wallet['exceeded_free_tier'] == 1]['company_id'].unique()
        signups['exceeded_free_tier'] = signups['company_id'].isin(exceeded_companies)
    else:
        signups['used_conversations'] = False
        signups['exceeded_free_tier'] = False
    
    # --- Payment info (the ultimate conversion!) ---
    if stripe_invoices is not None and len(stripe_invoices) > 0:
        paid_invoices = stripe_invoices[stripe_invoices['amount_paid'] > 0]
        paid_companies = paid_invoices['company_id'].unique()
        signups['actually_paid'] = signups['company_id'].isin(paid_companies)
        
        # Total paid per company
        paid_summary = paid_invoices.groupby('company_id')['amount_paid'].sum().reset_index()
        paid_summary.columns = ['company_id', 'total_paid']
        signups = signups.merge(paid_summary, on='company_id', how='left')
        signups['total_paid'] = signups['total_paid'].fillna(0)
    else:
        signups['actually_paid'] = False
        signups['total_paid'] = 0

    # --- Template usage (Connect conversion step) ---
    template_usage = data.get('template_usage')
    if template_usage is not None and len(template_usage) > 0:
        tu = template_usage.copy()
        tu['company_id'] = pd.to_numeric(tu['company_id'], errors='coerce')
        tu_summary = tu.groupby('company_id').agg({
            'total_events': 'sum',
            'created_templates': 'sum'
        }).reset_index()
        
        signups = signups.merge(tu_summary, on='company_id', how='left')
        signups['created_templates'] = signups['created_templates'].fillna(0).astype(int)
        signups['has_template_usage'] = signups['created_templates'] > 0
    else:
        signups['created_templates'] = 0
        signups['has_template_usage'] = False

    # --- Engagement usage (Brain Studio funnel steps) ---
    engagement = data.get('company_engagement')
    if engagement is not None and len(engagement) > 0:
        eng = engagement.copy()
        eng['company_id'] = pd.to_numeric(eng['company_id'], errors='coerce')
        
        # Merge engagement metrics
        signups = signups.merge(eng[['company_id', 'sandbox_executions', 'prod_executions']], on='company_id', how='left')
        
        signups['has_workflow'] = (signups['sandbox_executions'].fillna(0) + signups['prod_executions'].fillna(0)) > 0
        signups['has_sandbox'] = signups['sandbox_executions'].fillna(0) > 0
        signups['has_prod_exec'] = signups['prod_executions'].fillna(0) > 0
    else:
        signups['has_workflow'] = False
        signups['has_sandbox'] = False
        signups['has_prod_exec'] = False
    
    # --- Session Durations (Correlation analysis) ---
    sessions_duration = data.get('sessions_duration')
    if sessions_duration is not None and len(sessions_duration) > 0:
        sd = sessions_duration.copy()
        # The CSV has columns: _id, tiempoTotalMinutos, promedioSesionMinutos, totalSesiones
        sd.columns = ['company_id', 'total_time_minutes', 'avg_session_minutes', 'session_count']
        sd['company_id'] = pd.to_numeric(sd['company_id'], errors='coerce')
        
        signups = signups.merge(sd, on='company_id', how='left')
        signups['total_time_minutes'] = signups['total_time_minutes'].fillna(0)
        signups['avg_session_minutes'] = signups['avg_session_minutes'].fillna(0)
        signups['session_count_sd'] = signups['session_count'].fillna(0) # Rename to avoid conflict with existing session_count if any
    else:
        signups['total_time_minutes'] = 0
        signups['avg_session_minutes'] = 0
        signups['session_count_sd'] = 0
    
    return signups


def create_analysis(signups, subscriptions):
    """Legacy function - kept for compatibility"""
    # Get subscription summary per company
    sub_summary = subscriptions.groupby('company_id').agg({
        'subscription_id': 'count',
        'status': lambda x: list(x.unique()),
        'product_name': lambda x: list(x.unique()),
        'created_at': 'min'
    }).reset_index()
    sub_summary.columns = ['company_id', 'subscription_count', 'statuses', 'products', 'first_subscription']
    
    # Check for active subscriptions
    sub_summary['has_active'] = sub_summary['statuses'].apply(lambda x: 'ACTIVE' in x if isinstance(x, list) else False)
    sub_summary['has_trialing'] = sub_summary['statuses'].apply(lambda x: 'TRIALING' in x if isinstance(x, list) else False)
    # Use case-insensitive pattern matching to catch all variants
    # Brain: "Brain studio", "Brain conversaciones"
    # Connect: "Connect", "Plan Connect"
    sub_summary['has_brain_studio'] = sub_summary['products'].apply(
        lambda x: any('brain' in str(p).lower() for p in x) if isinstance(x, list) else False
    )
    sub_summary['has_connect'] = sub_summary['products'].apply(
        lambda x: any('connect' in str(p).lower() for p in x) if isinstance(x, list) else False
    )
    
    # Add has_subscription flag to signups
    companies_with_subs = subscriptions['company_id'].unique()
    signups = signups.copy()
    signups['has_subscription'] = signups['company_id'].isin(companies_with_subs)
    
    # Merge with signups
    analysis = signups.merge(sub_summary, on='company_id', how='left')
    analysis['subscription_count'] = analysis['subscription_count'].fillna(0).astype(int)
    
    # Fill boolean columns properly
    for col in ['has_active', 'has_trialing', 'has_brain_studio', 'has_connect']:
        if col in analysis.columns:
            analysis[col] = analysis[col].fillna(False).astype(bool)
    
    return analysis


def make_tz_naive(series):
    """Convert a datetime series to timezone-naive, handling both tz-aware and tz-naive inputs"""
    if series is None:
        return None
    # Parse to datetime first (handles strings with Z suffix like "2025-11-03T17:24:56.996Z")
    series = pd.to_datetime(series, errors='coerce', utc=True)
    # Convert to naive by removing timezone (converts to UTC first, then removes tz)
    if hasattr(series, 'dt') and series.dt.tz is not None:
        return series.dt.tz_convert(None)
    return series


def calculate_retention_curve(signups_df, user_sessions_df=None):
    """
    Calculate retention curve using pre-calculated retention flags from analysis_combined.csv.
    
    The retention flags are calculated in the Jupyter notebook as:
    - retained_day1: last_activity >= 1 day after signup
    - retained_week1: last_activity >= 7 days after signup
    - retained_week2: last_activity >= 14 days after signup
    - retained_week3: last_activity >= 21 days after signup
    - retained_week4: last_activity >= 28 days after signup
    
    For each period, we only count signups that are OLD ENOUGH to be measured.
    
    Args:
        signups_df: DataFrame with pre-calculated retention columns (from analysis_combined.csv)
        user_sessions_df: (Optional, kept for compatibility but not used if retention flags exist)
    
    Returns:
        DataFrame with period and retention_rate columns
    """
    if signups_df is None or len(signups_df) == 0:
        return None
    
    try:
        df = signups_df.copy()
        
        # Check if we have pre-calculated retention flags
        has_retention_flags = all(col in df.columns for col in ['retained_day1', 'retained_week1', 'days_since_signup'])
        
        if has_retention_flags:
            # Use pre-calculated flags from analysis_combined.csv
            # These are already correctly calculated in the notebook
            
            periods = [
                ('Day 1', 'retained_day1', 7),       # Need 7 days of age to measure day 1
                ('Week 1', 'retained_week1', 14),   # Need 14 days to measure week 1
                ('Week 2', 'retained_week2', 21),   # Need 21 days to measure week 2
                ('Week 3', 'retained_week3', 28),   # Need 28 days to measure week 3
                ('Week 4', 'retained_week4', 35),   # Need 35 days to measure week 4
                ('Week 5', 'retained_week5', 42),   # Need 42 days to measure week 5
                ('Week 6', 'retained_week6', 49),   # Need 49 days to measure week 6
                ('Week 7', 'retained_week7', 56),   # Need 56 days to measure week 7
                ('Week 8', 'retained_week8', 63),   # Need 63 days to measure week 8
            ]
            
            retention_data = []
            
            # Add Day 0 as 100% baseline (all signups are "retained" at signup)
            total_signups = len(df)
            retention_data.append({
                'period': 'Day 0',
                'retention_rate': 100.0,
                'eligible': total_signups,
                'retained': total_signups
            })
            
            for period_name, flag_col, min_age in periods:
                if flag_col not in df.columns:
                    continue
                    
                # Only count signups old enough to be measured
                eligible = df[df['days_since_signup'] >= min_age]
                
                if len(eligible) == 0:
                    continue
                
                # Count retained
                retained = eligible[eligible[flag_col] == True]
                rate = len(retained) / len(eligible) * 100
                
                retention_data.append({
                    'period': period_name,
                    'retention_rate': rate,
                    'eligible': len(eligible),
                    'retained': len(retained)
                })
            
            if len(retention_data) == 0:
                return None
            
            return pd.DataFrame(retention_data)
        
        # Fallback: Calculate from session data if no pre-calculated flags
        if user_sessions_df is None or len(user_sessions_df) == 0:
            return None
        
        # Ensure proper types
        sessions = user_sessions_df.copy()
        
        # Convert company_id to numeric for matching
        df['company_id'] = pd.to_numeric(df['company_id'], errors='coerce')
        sessions['company_id'] = pd.to_numeric(sessions['company_id'], errors='coerce')
        
        # Parse session dates and make tz-naive
        sessions['first_session'] = make_tz_naive(sessions['first_session'])
        sessions['last_session'] = make_tz_naive(sessions['last_session'])
        
        # Also make signup created_at tz-naive before merge
        df['created_at_naive'] = make_tz_naive(df['created_at'])
        
        # Merge with sessions
        merged = df.merge(
            sessions[['company_id', 'first_session', 'last_session', 'days_active', 'total_sessions']],
            on='company_id',
            how='left'
        )
        
        # Calculate days from signup to last session
        merged['signup_date'] = merged['created_at_naive'].dt.normalize()
        merged['last_active_date'] = merged['last_session'].dt.normalize()
        merged['days_to_last'] = (merged['last_active_date'] - merged['signup_date']).dt.days
        
        # Get today as tz-naive
        today = pd.Timestamp.now().normalize()
        merged['days_since_signup'] = (today - merged['signup_date']).dt.days
        
        # Define retention periods
        periods = [
            ('Day 1', 1, 7),
            ('Week 1', 7, 14),
            ('Week 2', 14, 21),
            ('Week 3', 21, 28),
            ('Week 4', 28, 35),
            ('Week 5', 35, 42),
            ('Week 6', 42, 49),
            ('Week 7', 49, 56),
            ('Week 8', 56, 63),
        ]
        
        retention_data = []
        
        # Add Day 0 as 100% baseline
        total_signups = len(merged)
        retention_data.append({
            'period': 'Day 0',
            'eligible_signups': total_signups,
            'still_active': total_signups,
            'retention_rate': 100.0
        })
        
        for period_name, period_days, min_age in periods:
            # Only consider signups old enough
            eligible = merged[merged['days_since_signup'] >= min_age]
            
            if len(eligible) == 0:
                continue
            
            # Retained if last activity >= period_days after signup
            active_at_period = eligible[
                eligible['days_to_last'].notna() & 
                (eligible['days_to_last'] >= period_days)
            ]
            
            retention_rate = len(active_at_period) / len(eligible) * 100 if len(eligible) > 0 else 0
            
            retention_data.append({
                'period': period_name,
                'eligible_signups': len(eligible),
                'still_active': len(active_at_period),
                'retention_rate': retention_rate
            })
        
        if len(retention_data) == 0:
            return None
        
        return pd.DataFrame(retention_data)
    
    except Exception as e:
        # Log error but don't crash the app
        import traceback
        print(f"Retention curve calculation error: {e}")
        traceback.print_exc()
        return None


def calculate_cohort_retention(signups_df):
    """
    Calculate retention rates by signup week cohort.
    
    Groups users by the week they signed up and calculates retention rates
    for each cohort using pre-calculated retention flags.
    
    Args:
        signups_df: DataFrame with signup data and retention flags
        
    Returns:
        DataFrame with cohort retention data (one row per signup week)
    """
    if signups_df is None or len(signups_df) == 0:
        return None
    
    df = signups_df.copy()
    
    # Check for required columns
    required_cols = ['created_at', 'retained_day1', 'retained_week1', 'days_since_signup']
    if not all(col in df.columns for col in required_cols):
        return None
    
    # Create signup week column (Monday start)
    df['signup_week'] = df['created_at'].dt.to_period('W-SUN').dt.start_time
    
    # Define retention periods with their flag columns and minimum age requirements
    periods = [
        ('Day 1', 'retained_day1', 7),
        ('Week 1', 'retained_week1', 14),
        ('Week 2', 'retained_week2', 21),
        ('Week 3', 'retained_week3', 28),
        ('Week 4', 'retained_week4', 35),
        ('Week 5', 'retained_week5', 42),
        ('Week 6', 'retained_week6', 49),
        ('Week 7', 'retained_week7', 56),
        ('Week 8', 'retained_week8', 63),
    ]
    
    cohort_data = []
    
    # Group by signup week
    for week, group in df.groupby('signup_week'):
        # Create week range label (Mon - Sun) with total signups
        week_start = week
        week_end = week + pd.Timedelta(days=6)
        total_signups = len(group)
        cohort_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')} ({total_signups})"
        
        cohort = {
            'signup_week': week,
            'cohort_label': cohort_label,
            'total_signups': total_signups
        }
        
        # Calculate retention for each period
        for period_name, flag_col, min_age in periods:
            if flag_col not in group.columns:
                cohort[period_name] = None
                cohort[f'{period_name}_eligible'] = 0
                cohort[f'{period_name}_retained'] = 0
                continue
            
            # Only count users old enough to measure this retention period
            eligible = group[group['days_since_signup'] >= min_age]
            
            if len(eligible) == 0:
                cohort[period_name] = None  # Not enough data yet
                cohort[f'{period_name}_eligible'] = 0
                cohort[f'{period_name}_retained'] = 0
            else:
                retained = eligible[eligible[flag_col] == True]
                rate = len(retained) / len(eligible) * 100
                cohort[period_name] = rate
                cohort[f'{period_name}_eligible'] = len(eligible)
                cohort[f'{period_name}_retained'] = len(retained)
        
        cohort_data.append(cohort)
    
    if len(cohort_data) == 0:
        return None
    
    result = pd.DataFrame(cohort_data)
    result = result.sort_values('signup_week', ascending=True)
    
    return result


def render_cohort_heatmap(cohort_data):
    """Render a heatmap showing retention by signup week cohort"""
    if cohort_data is None or len(cohort_data) == 0:
        st.info("No cohort data available")
        return
    
    # Prepare data for heatmap
    periods = ['Day 1', 'Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8']
    
    # Filter to periods that have data
    available_periods = [p for p in periods if p in cohort_data.columns and cohort_data[p].notna().any()]
    
    if len(available_periods) == 0:
        st.info("Not enough retention data to display cohort heatmap")
        return
    
    # Create matrix for heatmap
    cohort_labels = cohort_data['cohort_label'].tolist()
    z_data = []
    text_data = []
    hover_text = []
    
    for _, row in cohort_data.iterrows():
        z_row = []
        text_row = []
        hover_row = []
        for period in available_periods:
            val = row.get(period)
            eligible = row.get(f'{period}_eligible', 0)
            retained = row.get(f'{period}_retained', 0)
            
            if pd.isna(val) or val is None:
                z_row.append(None)
                text_row.append("—")
                hover_row.append(f"Week: {row['cohort_label']}<br>{period}: Not enough data yet<br>Signups: {row['total_signups']}")
            else:
                z_row.append(val)
                text_row.append(f"{val:.0f}% ({retained}/{eligible})")
                hover_row.append(f"Week: {row['cohort_label']}<br>{period}: {val:.1f}%<br>Retained: {retained}/{eligible}<br>Total signups: {row['total_signups']}")
        z_data.append(z_row)
        text_data.append(text_row)
        hover_text.append(hover_row)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=available_periods,
        y=cohort_labels,
        colorscale=[
            [0, '#EF4444'],      # Red for low retention
            [0.25, '#F59E0B'],   # Orange
            [0.5, '#FBBF24'],    # Yellow
            [0.75, '#10B981'],   # Green
            [1, '#00D4AA']       # Teal for high retention
        ],
        zmin=0,
        zmax=100,
        text=text_data,
        texttemplate="%{text}",
        textfont={"size": 11, "color": "white"},
        hovertext=hover_text,
        hovertemplate="%{hovertext}<extra></extra>",
        colorbar=dict(
            title="Retention %",
            ticksuffix="%"
        )
    ))
    
    fig.update_layout(
        title="Cohort Retention Heatmap (by Signup Week)",
        xaxis_title="Time After Signup",
        yaxis_title="Signup Week",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Space Grotesk"),
        height=max(300, len(cohort_data) * 35 + 100),  # Dynamic height based on cohorts
        yaxis=dict(autorange="reversed")  # Newest cohorts at top
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show summary table below
    with st.expander("📊 View Cohort Data Table", expanded=False):
        display_cols = ['cohort_label', 'total_signups'] + available_periods
        display_df = cohort_data[display_cols].copy()
        display_df.columns = ['Signup Week', 'Signups'] + available_periods
        
        # Format percentages
        for period in available_periods:
            display_df[period] = display_df[period].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
            )
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Signup Week": st.column_config.TextColumn("Week", width="small"),
                "Signups": st.column_config.NumberColumn("Signups", width="small"),
            }
        )


def render_retention_chart(retention_data, title_suffix="", color='#00D4AA'):
    """Render a single retention curve chart with metrics"""
    if retention_data is not None and len(retention_data) > 0:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=retention_data['period'],
            y=retention_data['retention_rate'],
            mode='lines+markers',
            name='Retention Rate',
            line=dict(color=color, width=3),
            marker=dict(size=10, color=color),
            hovertemplate='%{x}<br>%{y:.1f}% still active<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"Retention Curve: {title_suffix}",
            xaxis_title="Time After Signup",
            yaxis_title="% of Users Still Active",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Space Grotesk"),
            yaxis=dict(range=[0, 105], ticksuffix='%'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Retention metrics
        day1_ret = retention_data[retention_data['period'] == 'Day 1']['retention_rate'].values
        week1_ret = retention_data[retention_data['period'] == 'Week 1']['retention_rate'].values
        week4_ret = retention_data[retention_data['period'] == 'Week 4']['retention_rate'].values
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            eligible = retention_data['eligible_signups'].iloc[0] if len(retention_data) > 0 else 0
            st.metric("Eligible Signups", eligible, help="Signups old enough to measure retention")
        with col2:
            if len(day1_ret) > 0:
                st.metric("Day 1", f"{day1_ret[0]:.1f}%", help="% active on day 1")
        with col3:
            if len(week1_ret) > 0:
                st.metric("Week 1", f"{week1_ret[0]:.1f}%", help="% active after 1 week")
        with col4:
            if len(week4_ret) > 0:
                st.metric("Week 4", f"{week4_ret[0]:.1f}%", help="% active after 4 weeks")
    else:
        st.info("Not enough data to calculate retention curve for this segment.")


def generate_sample_data():
    """Generate sample data for demo purposes"""
    np.random.seed(42)
    n_companies = 200
    
    # Signups
    signups = pd.DataFrame({
        'company_id': range(1, n_companies + 1),
        'company_name': [f"Company_{i}" for i in range(1, n_companies + 1)],
        'created_at': pd.date_range(start='2025-01-01', periods=n_companies, freq='2H'),
    })
    
    # Simulate activity - 30% have any activity
    active_companies = np.random.choice(signups['company_id'], size=int(n_companies * 0.3), replace=False)
    
    # Workflow executions
    exec_records = []
    for cid in active_companies:
        n_execs = np.random.randint(1, 50)
        company_name = f"Company_{cid}"
        for _ in range(n_execs):
            exec_records.append({
                'company_id': cid,
                'company_name': company_name,
                'is_debug': np.random.random() > 0.3,  # 70% sandbox
                'channel': np.random.choice(['web', 'whatsapp', 'facebook'], p=[0.6, 0.3, 0.1]),
                'status': np.random.choice(['completed', 'failed', 'pending'], p=[0.8, 0.15, 0.05]),
                'created_at': pd.Timestamp('2025-01-01') + pd.Timedelta(days=np.random.randint(0, 15))
            })
    workflow_executions = pd.DataFrame(exec_records) if exec_records else pd.DataFrame()
    
    # Node executions
    node_types = ['message', 'condition', 'api_call', 'ai_response', 'input', 'loop', 'delay', 'webhook']
    node_records = []
    for cid in active_companies:
        n_nodes = np.random.randint(1, 20)
        for _ in range(n_nodes):
            node_records.append({
                'company_id': cid,
                'node_type': np.random.choice(node_types),
                'created_at': pd.Timestamp('2025-01-01') + pd.Timedelta(days=np.random.randint(0, 15))
            })
    node_executions = pd.DataFrame(node_records) if node_records else pd.DataFrame()
    
    # Subscriptions
    subscriptions = pd.DataFrame({
        'company_id': signups['company_id'],
        'status': np.random.choice(['trial', 'active', 'canceled', 'expired'], size=n_companies, p=[0.7, 0.05, 0.1, 0.15]),
        'trial_start': signups['created_at'],
        'trial_end': signups['created_at'] + pd.Timedelta(days=14),
        'stripe_subscription_id': [f"sub_{i}" if np.random.random() > 0.95 else None for i in range(n_companies)],
    })
    
    return {
        'signups': signups,
        'subscriptions': subscriptions,
        'workflow_executions': workflow_executions,
        'node_executions': node_executions,
        'user_activity': None
    }


# --- Helper Functions ---
def get_analysis_df(data):
    """Get analysis DataFrame, falling back to signups if analysis not available"""
    analysis = data.get('analysis')
    if analysis is not None and not analysis.empty:
        return analysis
    return data.get('signups')


# --- Analysis Functions ---
def calculate_metrics(data, date_range):
    """Calculate key metrics from the data"""
    analysis = get_analysis_df(data)
    subscriptions = data['subscriptions']
    executions = data.get('workflow_executions')
    
    if analysis is None:
        return None
    
    # Filter by date range
    mask = (analysis['created_at'] >= pd.Timestamp(date_range[0])) & \
           (analysis['created_at'] <= pd.Timestamp(date_range[1]))
    filtered = analysis[mask]
    
    total_signups = len(filtered)
    if total_signups == 0:
        return None
    
    # Use analysis columns if available
    if 'has_subscription' in filtered.columns:
        with_subscription = filtered['has_subscription'].sum()
        has_active = filtered['has_active'].sum() if 'has_active' in filtered.columns else 0
        has_brain = filtered['has_brain_studio'].sum() if 'has_brain_studio' in filtered.columns else 0
        has_connect = filtered['has_connect'].sum() if 'has_connect' in filtered.columns else 0
    else:
        with_subscription = 0
        has_active = 0
        has_brain = 0
        has_connect = 0
    
    # Production status from signups
    in_production = filtered['in_production'].sum() if 'in_production' in filtered.columns else 0
    
    # Plan breakdown
    self_service = len(filtered[filtered['plan'] == 'SELF_SERVICE']) if 'plan' in filtered.columns else 0
    enterprise = len(filtered[filtered['plan'] == 'ENTERPRISE']) if 'plan' in filtered.columns else 0
    
    # Activity from MongoDB (if available)
    if executions is not None and len(executions) > 0:
        company_ids = set(filtered['company_id'])
        active_companies = set(executions['company_id'].unique())
        with_activity = len(company_ids & active_companies)
        
        sandbox_companies = set(executions[executions['is_debug'] == True]['company_id'].unique())
        prod_companies = set(executions[executions['is_debug'] == False]['company_id'].unique())
        sandbox_only = len((sandbox_companies - prod_companies) & company_ids)
        went_to_prod = len(prod_companies & company_ids)
    else:
        with_activity = 0
        sandbox_only = 0
        went_to_prod = 0
    
    return {
        'total_signups': total_signups,
        'with_subscription': with_subscription,
        'has_active': has_active,
        'has_brain_studio': has_brain,
        'has_connect': has_connect,
        'in_production': in_production,
        'self_service': self_service,
        'enterprise': enterprise,
        'with_activity': with_activity,
        'sandbox_only': sandbox_only,
        'went_to_prod': went_to_prod,
        'subscription_rate': with_subscription / total_signups * 100 if total_signups > 0 else 0,
        'production_rate': in_production / total_signups * 100 if total_signups > 0 else 0,
    }


def build_funnel_data(data, date_range, plan_filter="All Plans"):
    """Build CORRECTED activation funnel data based on actual product usage"""
    analysis = get_analysis_df(data)
    
    if analysis is None:
        return None
    
    # Filter by date
    mask = (analysis['created_at'] >= pd.Timestamp(date_range[0])) & \
           (analysis['created_at'] <= pd.Timestamp(date_range[1]))
    filtered = analysis[mask]
    
    # Apply plan filter
    if plan_filter != "All Plans" and 'plan' in filtered.columns:
        filtered = filtered[filtered['plan'] == plan_filter]
    
    total = len(filtered)
    if total == 0:
        return None
    
    # Build CORRECTED funnel using new data sources
    # Stage 1: Signup (total)
    # Stage 2: Created Bot (from bots.csv)
    has_bot = filtered['has_bot'].sum() if 'has_bot' in filtered.columns else 0
    
    # Stage 3: Production Channel (bots.in_production = 1) - THE KEY DROP-OFF
    has_prod_channel = filtered['has_prod_channel'].sum() if 'has_prod_channel' in filtered.columns else 0
    
    # Stage 4: Used Conversations (credit_wallet.total_used > 0)
    used_conversations = filtered['used_conversations'].sum() if 'used_conversations' in filtered.columns else 0
    
    # Stage 5: Exceeded Free Tier (credit_wallet.exceeded_free_tier = 1)
    exceeded_free = filtered['exceeded_free_tier'].sum() if 'exceeded_free_tier' in filtered.columns else 0
    
    # Stage 6: Actually Paid (stripe_invoices.amount_paid > 0)
    actually_paid = filtered['actually_paid'].sum() if 'actually_paid' in filtered.columns else 0
    
    stages = ['Signup', 'Created Bot', 'Production Channel', 'Used Conversations', 'Exceeded Free Tier', 'Actually Paid']
    counts = [total, has_bot, has_prod_channel, used_conversations, exceeded_free, actually_paid]
    
    funnel_df = pd.DataFrame({
        'Stage': stages,
        'Count': counts,
        'Percentage': [c/total*100 if total else 0 for c in counts]
    })
    
    # Add drop-off analysis
    funnel_df['Drop-off'] = funnel_df['Count'].diff().fillna(0).astype(int)
    funnel_df['Drop-off %'] = (funnel_df['Drop-off'].abs() / funnel_df['Count'].shift(1) * 100).fillna(0).round(1)
    
    return funnel_df


# --- Authentication ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "jelouproduct2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 Restricted Access")
            st.text_input(
                "Enter Password", type="password", on_change=password_entered, key="password"
            )
            if "password_correct" in st.session_state:
                st.error("😕 Password incorrect")
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 Restricted Access")
            st.text_input(
                "Enter Password", type="password", on_change=password_entered, key="password"
            )
            st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

# --- Main App ---
def main():
    if not check_password():
        st.stop()
        
    # Sidebar
    st.sidebar.markdown("## 🧠 Jelou Analytics")
    st.sidebar.markdown("---")
    
    # Load data (pass excluded companies hash to bust cache when JSON changes)
    data = load_data(_excluded_hash=get_excluded_companies_hash())
    
    # Check what data we have
    has_signups = data['signups'] is not None
    has_bots = data['bots'] is not None
    has_wallet = data['credit_wallet'] is not None
    has_invoices = data['stripe_invoices'] is not None
    has_mongo = data['workflow_executions'] is not None
    
    # Show data status
    loaded = []
    missing = []
    if has_signups: loaded.append("signups")
    else: missing.append("signups")
    if has_bots: loaded.append("bots")
    else: missing.append("bots")
    if has_wallet: loaded.append("credit_wallet")
    else: missing.append("credit_wallet")
    if has_invoices: loaded.append("stripe_invoices")
    else: missing.append("stripe_invoices")
    
    if len(missing) == 0:
        st.sidebar.success(f"✅ All key data loaded ({len(loaded)} files)")
    elif has_signups and has_bots:
        st.sidebar.info(f"📊 Core data loaded. Missing: {', '.join(missing)}")
    else:
        st.sidebar.warning(f"⚠️ Missing: {', '.join(missing)}")
    
    # Date range filter
    st.sidebar.markdown("### Filters")
    
    # Default start date: November 15, 2025
    default_start = datetime(2025, 11, 15).date()
    
    if data['signups'] is not None:
        data_min_date = data['signups']['created_at'].min().date()
        data_max_date = data['signups']['created_at'].max().date()
        # Use Nov 15 2025 or data min, whichever is later
        min_date = max(data_min_date, default_start) if data_min_date < default_start else data_min_date
        max_date = data_max_date
    else:
        min_date = default_start
        max_date = datetime.now().date()
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=default_start,
        max_value=max_date
    )
    
    if len(date_range) != 2:
        date_range = (min_date, max_date)
    
    # Plan type filter (global)
    plan_options = ["All Plans", "SELF_SERVICE", "ENTERPRISE", "SMB", "POCKET"]
    plan_filter = st.sidebar.selectbox(
        "Plan Type",
        plan_options,
        index=0,
        help="Filter all metrics by plan type. SELF_SERVICE = organic signups expected to convert on their own."
    )
    
    # Navigation
    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio(
        "View",
        ["Overview", "Activation Funnel", "Company Data", "Company Explorer"],
        label_visibility="collapsed"
    )
    
    # Main content
    if page == "Overview":
        render_overview(data, date_range, plan_filter)
    elif page == "Activation Funnel":
        render_funnel(data, date_range, plan_filter)
    elif page == "Company Data":
        render_company_data(data, date_range, plan_filter)
    else:
        render_company_explorer(data, date_range, plan_filter)


def render_overview(data, date_range, plan_filter="All Plans"):
    """Render the overview page with CORRECTED metrics"""
    st.markdown("# 📊 Product Usage Overview")
    
    # Get filtered data
    analysis = get_analysis_df(data)
    if analysis is None:
        st.error("No data available")
        return
    
    # Apply date filter
    mask = (analysis['created_at'] >= pd.Timestamp(date_range[0])) & \
           (analysis['created_at'] <= pd.Timestamp(date_range[1]))
    filtered = analysis[mask].copy()
    
    # Apply plan filter
    if plan_filter != "All Plans" and 'plan' in filtered.columns:
        filtered = filtered[filtered['plan'] == plan_filter]
    
    if len(filtered) == 0:
        st.warning("No data for selected filters")
        return
    
    # Calculate CORRECTED metrics from filtered data
    total_signups = len(filtered)
    days_in_range = max(1, (date_range[1] - date_range[0]).days)
    avg_per_day = total_signups / days_in_range
    
    # Corrected funnel metrics - OVERALL
    has_bot = filtered['has_bot'].sum() if 'has_bot' in filtered.columns else 0
    has_prod_channel = filtered['has_prod_channel'].sum() if 'has_prod_channel' in filtered.columns else 0
    used_conversations = filtered['used_conversations'].sum() if 'used_conversations' in filtered.columns else 0
    exceeded_free = filtered['exceeded_free_tier'].sum() if 'exceeded_free_tier' in filtered.columns else 0
    actually_paid = filtered['actually_paid'].sum() if 'actually_paid' in filtered.columns else 0
    
    # BRAIN STUDIO specific metrics
    has_brain = filtered['has_brain_studio'].sum() if 'has_brain_studio' in filtered.columns else 0
    brain_active = filtered['brain_active'].sum() if 'brain_active' in filtered.columns else 0
    
    # CONNECT specific metrics
    has_connect = filtered['has_connect'].sum() if 'has_connect' in filtered.columns else 0
    connect_active = filtered['connect_active'].sum() if 'connect_active' in filtered.columns else 0
    connect_trialing = filtered['connect_trialing'].sum() if 'connect_trialing' in filtered.columns else 0
    
    # Rates
    bot_rate = has_bot / total_signups * 100 if total_signups > 0 else 0
    prod_rate = has_prod_channel / total_signups * 100 if total_signups > 0 else 0
    paid_rate = actually_paid / total_signups * 100 if total_signups > 0 else 0
    brain_rate = has_brain / total_signups * 100 if total_signups > 0 else 0
    connect_rate = has_connect / total_signups * 100 if total_signups > 0 else 0
    
    # Data explanation with key insight
    st.markdown(f"""
    ### 📋 Data Summary
    **Showing:** {total_signups} signups from **{date_range[0]}** to **{date_range[1]}** 
    {f'(filtered to **{plan_filter}** plan)' if plan_filter != "All Plans" else '(all plans)'}
    """)
    
    # KEY INSIGHT CALLOUT
    st.error(f"""
    🚨 **Key Insight - Production Channel Drop-off:**
    
    - **{has_bot}** ({bot_rate:.1f}%) created a bot ✓
    - **{has_prod_channel}** ({prod_rate:.1f}%) connected a production WhatsApp channel ⚠️
    - **{actually_paid}** ({paid_rate:.1f}%) actually paid ❌
    
    **The massive drop-off is at "Bot → Production Channel"** ({bot_rate:.0f}% → {prod_rate:.1f}%). 
    Users create bots but don't connect a real WhatsApp number to production!
    """)
    
    st.markdown("---")
    
    # Key metrics row - CORRECTED FUNNEL
    st.markdown("### 🎯 Corrected Conversion Funnel")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="Total Signups",
            value=total_signups,
            delta=f"{avg_per_day:.1f}/day avg"
        )
    
    with col2:
        st.metric(
            label="Created Bot",
            value=has_bot,
            delta=f"{bot_rate:.1f}%"
        )
    
    with col3:
        st.metric(
            label="Production Channel",
            value=has_prod_channel,
            delta=f"{prod_rate:.1f}%",
            delta_color="inverse" if prod_rate < 10 else "normal"
        )
    
    with col4:
        st.metric(
            label="Exceeded Free Tier",
            value=exceeded_free,
            delta=f"{exceeded_free/total_signups*100:.1f}%" if total_signups > 0 else "0%"
        )
    
    with col5:
        st.metric(
            label="Actually Paid",
            value=actually_paid,
            delta=f"{paid_rate:.1f}%",
            delta_color="inverse" if paid_rate < 5 else "normal"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- BRAIN STUDIO vs CONNECT Section ---
    st.markdown("### 🧠 Brain Studio vs 🔗 Connect")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🧠 Brain Studio (Usage-Based)")
        st.caption("Free tier + pay per conversation after limit")
        
        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            st.metric("Has Brain Sub", has_brain, f"{brain_rate:.1f}%")
        with bcol2:
            st.metric("Active", brain_active, f"{brain_active/total_signups*100:.1f}%" if total_signups > 0 else "0%")
        with bcol3:
            st.metric("Exceeded Free", exceeded_free, f"{exceeded_free/total_signups*100:.1f}%" if total_signups > 0 else "0%")
        
        # Brain funnel explanation
        if has_brain > 0:
            st.info(f"""
            **Brain Studio Funnel:**
            - {has_brain} users have Brain Studio subscription (free)
            - {exceeded_free} exceeded free conversation tier
            - Conversion to paid: {exceeded_free/has_brain*100:.1f}% of Brain users
            """)
    
    with col2:
        st.markdown("#### 🔗 Connect ($20/mo Subscription)")
        st.caption("14-day trial, then paid monthly")
        
        ccol1, ccol2, ccol3 = st.columns(3)
        with ccol1:
            st.metric("Started Trial", has_connect, f"{connect_rate:.1f}%")
        with ccol2:
            st.metric("Trialing", connect_trialing, f"{connect_trialing/total_signups*100:.1f}%" if total_signups > 0 else "0%")
        with ccol3:
            st.metric("Active (Paid)", connect_active, f"{connect_active/total_signups*100:.1f}%" if total_signups > 0 else "0%")
        
        # Connect funnel explanation
        if has_connect > 0:
            trial_to_paid = connect_active / has_connect * 100 if has_connect > 0 else 0
            st.info(f"""
            **Connect Funnel:**
            - {has_connect} users started Connect trial
            - {connect_trialing} currently in trial
            - {connect_active} converted to paid
            - Trial → Paid conversion: {trial_to_paid:.1f}%
            """)
    
    st.markdown("---")
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        # Corrected funnel breakdown pie
        no_bot = total_signups - has_bot
        bot_no_prod = has_bot - has_prod_channel
        
        fig = go.Figure(data=[go.Pie(
            labels=['No Bot', 'Bot Only (No Prod)', 'Production Channel', 'Actually Paid'],
            values=[no_bot, bot_no_prod, max(0, has_prod_channel - actually_paid), actually_paid],
            hole=0.6,
            marker_colors=['#EF4444', '#F59E0B', '#7C3AED', '#00D4AA']
        )])
        fig.update_layout(
            title="Conversion Status (Corrected Funnel)",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Space Grotesk")
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Daily signups trend
        daily = filtered.groupby(filtered['created_at'].dt.date).size().reset_index()
        daily.columns = ['date', 'count']
        
        fig = px.area(daily, x='date', y='count', 
                     title="Daily Signups",
                     color_discrete_sequence=['#7C3AED'])
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Space Grotesk")
        )
        st.plotly_chart(fig, use_container_width=True)

    # Weekly signups (same week boundaries as cohort heatmap: W-SUN)
    st.markdown("### 📅 Weekly Signups (WoW % Change)")
    st.markdown("*Weeks run Mon → Sun (W-SUN), matching the cohort heatmap.*")

    if 'created_at' in filtered.columns and filtered['created_at'].notna().any():
        weekly = (
            filtered.assign(signup_week=filtered['created_at'].dt.to_period('W-SUN').dt.start_time)
            .groupby('signup_week')
            .size()
            .reset_index(name='signups')
            .sort_values('signup_week', ascending=True)
        )

        weekly['prev_signups'] = weekly['signups'].shift(1)
        weekly['wow_pct_change'] = np.where(
            weekly['prev_signups'].fillna(0) > 0,
            (weekly['signups'] - weekly['prev_signups']) / weekly['prev_signups'] * 100,
            np.nan
        )

        weekly['week_end'] = weekly['signup_week'] + pd.Timedelta(days=6)
        weekly['week_label'] = weekly.apply(
            lambda r: f"{pd.Timestamp(r['signup_week']).strftime('%b %d')} - {pd.Timestamp(r['week_end']).strftime('%b %d')}",
            axis=1
        )

        fig_weekly = make_subplots(specs=[[{"secondary_y": True}]])

        fig_weekly.add_trace(
            go.Bar(
                x=weekly['week_label'],
                y=weekly['signups'],
                name="Signups",
                marker_color="#7C3AED",
                hovertemplate="Week: %{x}<br>Signups: %{y:,}<extra></extra>",
            ),
            secondary_y=False,
        )

        fig_weekly.add_trace(
            go.Scatter(
                x=weekly['week_label'],
                y=weekly['wow_pct_change'],
                name="WoW % Change",
                mode="lines+markers",
                line=dict(color="#F59E0B", width=3),
                marker=dict(size=8),
                hovertemplate="Week: %{x}<br>WoW % Change: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=True,
        )

        fig_weekly.update_layout(
            title="Weekly Signups and Week-over-Week Change",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Space Grotesk"),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            margin=dict(t=70, b=40),
        )
        fig_weekly.update_yaxes(title_text="Signups", secondary_y=False)
        fig_weekly.update_yaxes(title_text="WoW % Change", secondary_y=True, ticksuffix="%", rangemode="tozero")

        st.plotly_chart(fig_weekly, use_container_width=True)

    # --- NEW: Engagement & Session Analysis ---
    st.markdown("---")
    st.markdown("### ⏱️ Engagement & Session Analysis")
    st.markdown("*Correlation between time spent in the app and funnel progression.*")

    if 'total_time_minutes' in filtered.columns:
        ecol1, ecol2, ecol3 = st.columns(3)
        
        with ecol1:
            total_minutes = filtered['total_time_minutes'].sum()
            st.metric("Total Time in App", f"{total_minutes:,.0f} min", f"{total_minutes/60:,.1f} hours")
        
        with ecol2:
            avg_minutes = filtered[filtered['total_time_minutes'] > 0]['total_time_minutes'].mean()
            st.metric("Avg. Time per Account", f"{avg_minutes:.1f} min" if not np.isnan(avg_minutes) else "0 min")
            
        with ecol3:
            active_accounts = (filtered['total_time_minutes'] > 0).sum()
            st.metric("Active Accounts (Logged in)", f"{active_accounts}", f"{active_accounts/total_signups*100:.1f}%")

        # Correlation Chart: Time vs Funnel Step
        st.markdown("#### 📈 How does usage time correlate with conversion?")
        
        # Define funnel stages for mapping
        def get_funnel_stage(row):
            if row.get('actually_paid', False): return '4. Paid'
            if row.get('has_prod_channel', False): return '3. Production'
            if row.get('has_bot', False): return '2. Created Bot'
            if row.get('total_time_minutes', 0) > 0: return '1. Logged In'
            return '0. Signup Only'

        corr_df = filtered.copy()
        corr_df['Funnel Stage'] = corr_df.apply(get_funnel_stage, axis=1)
        
        # Group by stage and calculate avg time
        stage_summary = corr_df.groupby('Funnel Stage')['total_time_minutes'].agg(['mean', 'count']).reset_index()
        stage_summary.columns = ['Funnel Stage', 'Avg Minutes', 'Account Count']
        
        fig_corr = px.bar(
            stage_summary, 
            x='Funnel Stage', 
            y='Avg Minutes',
            text='Avg Minutes',
            title="Average Time in App by Funnel Stage",
            labels={'Avg Minutes': 'Avg. Minutes Spent'},
            color='Funnel Stage',
            color_discrete_sequence=['#6B7280', '#A855F7', '#F59E0B', '#7C3AED', '#10B981']
        )
        fig_corr.update_traces(texttemplate='%{text:.1f} min', textposition='outside')
        fig_corr.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Space Grotesk")
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        
        st.info("💡 **Insight:** This chart shows if users who reach later stages of the funnel (like Production or Paid) actually spend more time in the application during their journey.")
    else:
        st.info("ℹ️ Session duration data not available in the current dataset.")
    
    # --- RETENTION CURVE SECTION ---
    st.markdown("---")
    st.markdown("### 📈 User Retention Curve")
    st.markdown("*Retention = % of users still active X days after signup*")
    
    user_sessions = data.get('user_sessions')
    
    if user_sessions is not None and len(user_sessions) > 0:
        # Calculate retention for all groups
        overall_ret = calculate_retention_curve(filtered, user_sessions)
        brain_ret = None
        connect_ret = None
        
        if 'has_brain_studio' in filtered.columns:
            brain_users = filtered[filtered['has_brain_studio'] == True]
            if len(brain_users) > 0:
                brain_ret = calculate_retention_curve(brain_users, user_sessions)
        
        if 'has_connect' in filtered.columns:
            connect_users = filtered[filtered['has_connect'] == True]
            if len(connect_users) > 0:
                connect_ret = calculate_retention_curve(connect_users, user_sessions)
        
        if overall_ret is not None:
            fig = go.Figure()
            
            # Add overall trace
            fig.add_trace(go.Scatter(
                x=overall_ret['period'],
                y=overall_ret['retention_rate'],
                mode='lines+markers',
                name='Overall',
                line=dict(color='#7C3AED', width=3),
                marker=dict(size=8),
                hovertemplate='Overall<br>%{x}: %{y:.1f}%<extra></extra>'
            ))
            
            # Add Brain Studio trace
            if brain_ret is not None:
                fig.add_trace(go.Scatter(
                    x=brain_ret['period'],
                    y=brain_ret['retention_rate'],
                    mode='lines+markers',
                    name='Brain Studio',
                    line=dict(color='#00D4AA', width=3),
                    marker=dict(size=8),
                    hovertemplate='Brain Studio<br>%{x}: %{y:.1f}%<extra></extra>'
                ))
            
            # Add Connect trace
            if connect_ret is not None:
                fig.add_trace(go.Scatter(
                    x=connect_ret['period'],
                    y=connect_ret['retention_rate'],
                    mode='lines+markers',
                    name='Connect',
                    line=dict(color='#F59E0B', width=3),
                    marker=dict(size=8),
                    hovertemplate='Connect<br>%{x}: %{y:.1f}%<extra></extra>'
                ))
            
            fig.update_layout(
                title="Retention by Product",
                xaxis_title="Time After Signup",
                yaxis_title="% of Users Still Active",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Space Grotesk"),
                yaxis=dict(range=[0, 105], ticksuffix='%'),
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show retention metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                eligible = overall_ret['eligible'].iloc[0] if 'eligible' in overall_ret.columns else len(filtered)
                st.metric("Eligible Signups", f"{eligible:,}", help="Signups old enough to measure")
            with col2:
                day1 = overall_ret[overall_ret['period'] == 'Day 1']['retention_rate'].values
                st.metric("Day 1", f"{day1[0]:.1f}%" if len(day1) > 0 else "N/A")
            with col3:
                week1 = overall_ret[overall_ret['period'] == 'Week 1']['retention_rate'].values
                st.metric("Week 1", f"{week1[0]:.1f}%" if len(week1) > 0 else "N/A")
            with col4:
                week4 = overall_ret[overall_ret['period'] == 'Week 4']['retention_rate'].values
                st.metric("Week 4", f"{week4[0]:.1f}%" if len(week4) > 0 else "N/A")
            
            # Explanation of why Brain Studio/Connect > Overall
            st.info("💡 **Note:** Brain Studio and Connect users show higher retention because they are *engaged* users who activated a product. Overall includes all signups, including those who never engaged.")
        else:
            st.info("Not enough data to calculate retention curves.")
    else:
        st.info("📊 User session data not available. Export `user_sessions.csv` from MongoDB to see retention curves.")
    
    # --- COHORT RETENTION BY SIGNUP WEEK ---
    st.markdown("### 📅 Retention by Signup Week Cohort")
    st.markdown("*Each row shows retention rates for users who signed up that week*")
    
    cohort_retention = calculate_cohort_retention(filtered)
    
    if cohort_retention is not None and len(cohort_retention) > 0:
        render_cohort_heatmap(cohort_retention)
    else:
        st.info("Not enough data to calculate cohort retention. Ensure `analysis_combined.csv` has retention flags (retained_day1, retained_week1, etc.).")
    
    st.markdown("---")
    
    # Second row - Plan breakdown (only show if not filtering by plan)
    if plan_filter == "All Plans":
        st.markdown("### Plan Breakdown")
        col1, col2 = st.columns(2)
        
        self_service = len(filtered[filtered['plan'] == 'SELF_SERVICE']) if 'plan' in filtered.columns else 0
        enterprise = len(filtered[filtered['plan'] == 'ENTERPRISE']) if 'plan' in filtered.columns else 0
        other_plans = total_signups - self_service - enterprise
        
        with col1:
            # Plan type pie
            fig = go.Figure(data=[go.Pie(
                labels=['Self-Service', 'Enterprise', 'Other'],
                values=[self_service, enterprise, other_plans],
                hole=0.5,
                marker_colors=['#7C3AED', '#3B82F6', '#6B7280']
            )])
            fig.update_layout(
                title="Signups by Plan Type",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Space Grotesk")
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Product breakdown
            has_brain = filtered['has_brain_studio'].sum() if 'has_brain_studio' in filtered.columns else 0
            has_connect = filtered['has_connect'].sum() if 'has_connect' in filtered.columns else 0
            
            fig = go.Figure(data=[go.Pie(
                labels=['Brain Studio', 'Connect'],
                values=[has_brain, has_connect],
                marker_colors=['#00D4AA', '#F59E0B'],
                hole=0.4,
                textinfo='label+value+percent',
                textposition='outside'
            )])
            fig.update_layout(
                title="Subscriptions by Product",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Space Grotesk"),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        # Show product breakdown for filtered plan
        st.markdown(f"### {plan_filter} Plan Details")
        col1, col2 = st.columns(2)
        
        with col1:
            has_brain = filtered['has_brain_studio'].sum() if 'has_brain_studio' in filtered.columns else 0
            has_connect = filtered['has_connect'].sum() if 'has_connect' in filtered.columns else 0
            
            fig = go.Figure(data=[go.Pie(
                labels=['Brain Studio', 'Connect'],
                values=[has_brain, has_connect],
                marker_colors=['#00D4AA', '#F59E0B'],
                hole=0.4,
                textinfo='label+value+percent',
                textposition='outside'
            )])
            fig.update_layout(
                title=f"Subscriptions by Product ({plan_filter})",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Space Grotesk"),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Connect funnel details
            connect_trialing = filtered['connect_trialing'].sum() if 'connect_trialing' in filtered.columns else 0
            connect_active = filtered['connect_active'].sum() if 'connect_active' in filtered.columns else 0
            
            fig = go.Figure(data=[go.Pie(
                labels=['Trialing', 'Active (Paid)'],
                values=[connect_trialing, connect_active],
                marker_colors=['#F59E0B', '#00D4AA'],
                hole=0.4,
                textinfo='label+value+percent',
                textposition='outside'
            )])
            fig.update_layout(
                title=f"Connect Status ({plan_filter})",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Space Grotesk"),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)


def render_funnel(data, date_range, plan_filter="All Plans"):
    """Render the activation funnel page with Brain Studio vs Connect tabs"""
    st.markdown("# 🔄 Activation Funnel")
    st.markdown(f"*Where are users dropping off?* {'(' + plan_filter + ' only)' if plan_filter != 'All Plans' else ''}")
    
    # Tabs for different funnel views
    tab1, tab2, tab3 = st.tabs(["📊 Overall Funnel", "🧠 Brain Studio", "🔗 Connect"])
    
    with tab1:
        st.markdown("### 📊 User Journey Sankey Diagram")
        st.caption("*See how users flow through Brain Studio and Connect, and identify overlaps*")
        
        # Get filtered analysis data
        analysis = get_analysis_df(data)
        engagement = data.get('company_engagement')
        
        if analysis is not None:
            mask = (analysis['created_at'] >= pd.Timestamp(date_range[0])) & \
                   (analysis['created_at'] <= pd.Timestamp(date_range[1]))
            filtered = analysis[mask].copy()
            if plan_filter != "All Plans" and 'plan' in filtered.columns:
                filtered = filtered[filtered['plan'] == plan_filter]
            
            # --- Shared Funnel Metrics ---
            total = len(filtered)
            if total == 0:
                st.warning("No data in the selected date range.")
            else:
                has_bot = filtered['has_bot'].sum() if 'has_bot' in filtered.columns else 0
                has_connect = filtered['has_connect'].sum() if 'has_connect' in filtered.columns else 0
                has_template = filtered['has_template_usage'].sum() if 'has_template_usage' in filtered.columns else 0
                connect_active = filtered['connect_active'].sum() if 'connect_active' in filtered.columns else 0

                # ============================================================
                # COLUMN 2: Created Node vs Did Not Create Node
                # ============================================================
                node_type_cols = [col for col in filtered.columns if col.startswith('node_type_')]
                node_type_other_col = 'node_type_other' if 'node_type_other' in node_type_cols else None
                node_type_base_cols_orig = [col for col in node_type_cols if col != 'node_type_other']
                node_type_order = []
                node_type_counts = pd.Series(dtype=int)
                node_type_group = pd.Series(index=filtered.index, dtype=object)
                created_node_flag = pd.Series(False, index=filtered.index)

                if len(node_type_cols) > 0:
                    node_type_base_cols = (
                        filtered[node_type_base_cols_orig].fillna(0).sum()
                        .sort_values(ascending=False)
                        .head(5)
                        .index.tolist()
                    )
                    node_type_order = node_type_base_cols + ([node_type_other_col] if node_type_other_col else [])

                    node_type_matrix = filtered[node_type_order].fillna(0).astype(int)
                    created_node_flag = node_type_matrix.sum(axis=1) > 0

                    # Exclusive assignment: first matching flag (ordered by popularity)
                    idx_arr = node_type_matrix.to_numpy().argmax(axis=1)
                    node_type_group = pd.Series(
                        np.where(created_node_flag, np.array(node_type_order)[idx_arr], None),
                        index=filtered.index
                    )
                    node_type_counts = node_type_group.value_counts()

                # Fallback if no node_type flags but total_nodes_created exists
                if created_node_flag.sum() == 0 and 'total_nodes_created' in filtered.columns:
                    created_node_flag = filtered['total_nodes_created'].fillna(0) > 0

                created_node_count = int(created_node_flag.sum())
                did_not_create_node_count = total - created_node_count

                # Add created_node_flag to filtered for downstream calculations
                filtered = filtered.copy()
                filtered['_created_node'] = created_node_flag
                filtered['_node_type_group'] = node_type_group

                # ============================================================
                # COLUMN 4: Engagement metrics (Ran Workflows, Connect Trial, Cross-Product)
                # ============================================================
                engagement = data.get('company_engagement')
                executed_workflow = 0
                tested_sandbox = 0
                went_to_prod = 0
                eng_company_ids = set()
                connect_company_ids = set()

                if engagement is not None and len(engagement) > 0:
                    filtered_company_ids = set(filtered['company_id'].dropna().astype(int).unique())
                    eng_filtered = engagement[engagement['company_id'].isin(filtered_company_ids)]
                    eng_company_ids = set(eng_filtered['company_id'].dropna().astype(int).unique())
                    executed_workflow = len(eng_company_ids)
                    tested_sandbox = len(eng_filtered[eng_filtered['sandbox_executions'] > 0]) if 'sandbox_executions' in eng_filtered.columns else 0
                    went_to_prod = len(eng_filtered[eng_filtered['prod_executions'] > 0]) if 'prod_executions' in eng_filtered.columns else 0

                if 'has_connect' in filtered.columns:
                    connect_company_ids = set(filtered[filtered['has_connect'] == True]['company_id'].dropna().astype(int).unique())

                # Cross-product = ran workflow AND started connect
                cross_product_ids = eng_company_ids & connect_company_ids
                cross_product_count = len(cross_product_ids)

                # Ran workflows only (not connect)
                ran_workflows_only_ids = eng_company_ids - connect_company_ids
                ran_workflows_count = len(ran_workflows_only_ids)

                # Connect trial only (not ran workflow)
                connect_trial_only_ids = connect_company_ids - eng_company_ids
                connect_trial_count = len(connect_trial_only_ids)

                # ============================================================
                # Per-company flags for flow calculation
                # ============================================================
                filtered['_ran_workflow'] = filtered['company_id'].isin(eng_company_ids)
                filtered['_connect_trial'] = filtered['company_id'].isin(connect_company_ids)
                filtered['_cross_product'] = filtered['company_id'].isin(cross_product_ids)
                filtered['_ran_workflow_only'] = filtered['company_id'].isin(ran_workflows_only_ids)
                filtered['_connect_trial_only'] = filtered['company_id'].isin(connect_trial_only_ids)

                # Column 4 engagement (any of the 3)
                filtered['_col4_engaged'] = filtered['_ran_workflow'] | filtered['_connect_trial']

                # ============================================================
                # COLUMN 5 & 6: Final outcomes
                # ============================================================
                # Sandbox/Production from engagement data
                sandbox_ids = set()
                prod_ids = set()
                if engagement is not None and len(engagement) > 0:
                    filtered_company_ids = set(filtered['company_id'].dropna().astype(int).unique())
                    eng_filtered = engagement[engagement['company_id'].isin(filtered_company_ids)]
                    if 'sandbox_executions' in eng_filtered.columns:
                        sandbox_ids = set(eng_filtered[eng_filtered['sandbox_executions'] > 0]['company_id'].unique())
                    if 'prod_executions' in eng_filtered.columns:
                        prod_ids = set(eng_filtered[eng_filtered['prod_executions'] > 0]['company_id'].unique())

                filtered['_sandbox'] = filtered['company_id'].isin(sandbox_ids)
                filtered['_production'] = filtered['company_id'].isin(prod_ids)
                filtered['_templates'] = filtered['has_template_usage'] == True if 'has_template_usage' in filtered.columns else False
                filtered['_paid_connect'] = filtered['connect_active'] == True if 'connect_active' in filtered.columns else False

                # ============================================================
                # Calculate flow values for each path
                # ============================================================
                # Node type -> Col4 flows
                node_type_to_col4 = {}
                for col in node_type_order:
                    mask = filtered['_node_type_group'] == col
                    sub = filtered[mask]
                    to_ran = int((sub['_ran_workflow_only']).sum())
                    to_connect = int((sub['_connect_trial_only']).sum())
                    to_cross = int((sub['_cross_product']).sum())
                    to_dropped = int((~sub['_col4_engaged']).sum())
                    node_type_to_col4[col] = {'ran': to_ran, 'connect': to_connect, 'cross': to_cross, 'dropped': to_dropped}

                # Did Not Create -> Col4/NoFurtherActions
                no_node_mask = ~filtered['_created_node']
                no_node = filtered[no_node_mask]
                no_node_to_ran = int((no_node['_ran_workflow_only']).sum())
                no_node_to_connect = int((no_node['_connect_trial_only']).sum())
                no_node_to_cross = int((no_node['_cross_product']).sum())
                no_node_no_action = int((~no_node['_col4_engaged']).sum())

                # Col4 -> Col5
                # Ran Workflows -> Sandbox or Dropped
                ran_mask = filtered['_ran_workflow_only']
                ran_to_sandbox = int((filtered[ran_mask]['_sandbox']).sum())
                ran_to_dropped = int(ran_mask.sum()) - ran_to_sandbox

                # Connect Trial -> Templates or Dropped
                connect_mask = filtered['_connect_trial_only']
                connect_to_templates = int((filtered[connect_mask]['_templates']).sum())
                connect_to_dropped = int(connect_mask.sum()) - connect_to_templates

                # Cross Product -> split to Sandbox and Templates
                cross_mask = filtered['_cross_product']
                cross_to_sandbox = int((filtered[cross_mask]['_sandbox']).sum())
                cross_to_templates = int((filtered[cross_mask]['_templates']).sum())
                cross_to_dropped = int(cross_mask.sum()) - cross_to_sandbox - cross_to_templates
                if cross_to_dropped < 0:
                    cross_to_dropped = 0

                # Col5 -> Col6
                # Sandbox -> Production or Dropped
                sandbox_mask = filtered['_sandbox']
                sandbox_to_prod = int((filtered[sandbox_mask]['_production']).sum())
                sandbox_to_dropped = int(sandbox_mask.sum()) - sandbox_to_prod

                # Templates -> Paid Connect or Dropped
                templates_mask = filtered['_templates']
                templates_to_paid = int((filtered[templates_mask]['_paid_connect']).sum())
                templates_to_dropped = int(templates_mask.sum()) - templates_to_paid

                # Final column 6 totals
                final_production = int(filtered['_production'].sum())
                final_paid = int(filtered['_paid_connect'].sum())
                final_no_further = no_node_no_action
                final_dropped = total - final_production - final_paid - final_no_further

                # ============================================================
                # BUILD SANKEY NODES
                # Column 1: Signups (idx 0)
                # Column 2: Created Node (idx 1), Did Not Create Node (idx 2)
                # Column 3: Node Types (idx 3-8, dynamic based on node_type_order)
                # Column 4: Ran Workflows (idx 9), Connect Trial (idx 10), Cross-Product (idx 11)
                # Column 5: Validated in Sandbox (idx 12), Created Templates (idx 13)
                # Column 6: Live in Production (idx 14), Paid Connect (idx 15), Dropped Off (idx 16), No Further Actions (idx 17)
                # ============================================================
                pct = lambda v: f"{v/total*100:.1f}%" if total > 0 else "0%"

                labels = [
                    f"Signups (100%)",                                      # 0
                    f"Created Node ({pct(created_node_count)})",            # 1
                    f"Did Not Create Node ({pct(did_not_create_node_count)})",  # 2
                ]

                # Column 3: Node types (indices 3 to 3+len(node_type_order)-1)
                # Human-readable node type labels
                NODE_TYPE_DISPLAY_NAMES = {
                    'node_type_message': 'Message',
                    'node_type_code': 'Code',
                    'node_type_conditional': 'Conditional',
                    'node_type_skill': 'Skill',
                    'node_type_memory': 'Memory',
                    'node_type_other': 'Other',
                    # Fallback for numeric IDs (backward compatibility)
                    'node_type_3': 'Message',
                    'node_type_5': 'Code',
                    'node_type_14': 'Conditional',
                    'node_type_16': 'Skill',
                    'node_type_18': 'Memory',
                }
                node_type_start_idx = len(labels)
                node_type_indices = {}
                for col in node_type_order:
                    count = int(node_type_counts.get(col, 0))
                    label_name = NODE_TYPE_DISPLAY_NAMES.get(col, col.replace('node_type_', 'Type '))
                    labels.append(f"{label_name} ({pct(count)})")
                    node_type_indices[col] = len(labels) - 1

                # Column 4
                idx_ran_workflows = len(labels)
                labels.append(f"Ran Workflows ({pct(ran_workflows_count + cross_product_count)})")
                idx_connect_trial = len(labels)
                labels.append(f"Started Connect Trial ({pct(connect_trial_count + cross_product_count)})")
                idx_cross_product = len(labels)
                labels.append(f"Cross-Product ({pct(cross_product_count)})")

                # Column 5
                idx_sandbox = len(labels)
                labels.append(f"Validated in Sandbox ({pct(int(filtered['_sandbox'].sum()))})")
                idx_templates = len(labels)
                labels.append(f"Created Templates ({pct(int(filtered['_templates'].sum()))})")

                # Column 6 (Final - sums to 100%)
                idx_production = len(labels)
                labels.append(f"Live in Production ({pct(final_production)})")
                idx_paid = len(labels)
                labels.append(f"Paid Connect ({pct(final_paid)})")
                idx_dropped = len(labels)
                labels.append(f"Dropped Off ({pct(final_dropped)})")
                idx_no_further = len(labels)
                labels.append(f"No Further Actions ({pct(final_no_further)})")

                # ============================================================
                # NODE COLORS
                # ============================================================
                node_colors = [
                    "#7C3AED",  # 0 Signups (Purple)
                    "#38BDF8",  # 1 Created Node (Light Blue)
                    "#94A3B8",  # 2 Did Not Create Node (Gray)
                ]
                # Node types
                for col in node_type_order:
                    if col == 'node_type_other':
                        node_colors.append("#64748B")  # Other (Slate)
                    else:
                        node_colors.append("#60A5FA")  # Node Type (Blue)
                # Column 4
                node_colors.append("#8B5CF6")  # Ran Workflows (Violet)
                node_colors.append("#F59E0B")  # Connect Trial (Amber)
                node_colors.append("#00D4AA")  # Cross-Product (Teal)
                # Column 5
                node_colors.append("#A855F7")  # Sandbox (Light Purple)
                node_colors.append("#FBBF24")  # Templates (Yellow)
                # Column 6
                node_colors.append("#10B981")  # Production (Green)
                node_colors.append("#00D4AA")  # Paid (Teal)
                node_colors.append("#EF4444")  # Dropped Off (Red)
                node_colors.append("#6B7280")  # No Further Actions (Gray)

                # ============================================================
                # BUILD SANKEY LINKS
                # ============================================================
                links_source = []
                links_target = []
                links_value = []
                links_color = []

                def add_link(src, tgt, val, color):
                    if val > 0:
                        links_source.append(src)
                        links_target.append(tgt)
                        links_value.append(val)
                        links_color.append(color)

                # Column 1 -> Column 2: Signups -> Created Node / Did Not Create Node
                add_link(0, 1, created_node_count, "rgba(56, 189, 248, 0.5)")
                add_link(0, 2, did_not_create_node_count, "rgba(148, 163, 184, 0.4)")

                # Column 2 -> Column 3: Created Node -> Node Types
                for col in node_type_order:
                    count = int(node_type_counts.get(col, 0))
                    add_link(1, node_type_indices[col], count, "rgba(96, 165, 250, 0.5)")

                # Column 3 -> Column 4/6: Node Types -> Ran Workflows / Connect Trial / Cross-Product / Dropped
                for col in node_type_order:
                    flows = node_type_to_col4.get(col, {})
                    src_idx = node_type_indices[col]
                    add_link(src_idx, idx_ran_workflows, flows.get('ran', 0), "rgba(139, 92, 246, 0.4)")
                    add_link(src_idx, idx_connect_trial, flows.get('connect', 0), "rgba(245, 158, 11, 0.4)")
                    add_link(src_idx, idx_cross_product, flows.get('cross', 0), "rgba(0, 212, 170, 0.4)")
                    add_link(src_idx, idx_dropped, flows.get('dropped', 0), "rgba(239, 68, 68, 0.3)")

                # Column 2 -> Column 4/6: Did Not Create Node -> Ran Workflows / Connect Trial / Cross-Product / No Further Actions
                add_link(2, idx_ran_workflows, no_node_to_ran, "rgba(139, 92, 246, 0.4)")
                add_link(2, idx_connect_trial, no_node_to_connect, "rgba(245, 158, 11, 0.4)")
                add_link(2, idx_cross_product, no_node_to_cross, "rgba(0, 212, 170, 0.4)")
                add_link(2, idx_no_further, no_node_no_action, "rgba(107, 114, 128, 0.4)")

                # Column 4 -> Column 5/6: Ran Workflows -> Sandbox / Dropped
                add_link(idx_ran_workflows, idx_sandbox, ran_to_sandbox, "rgba(168, 85, 247, 0.5)")
                add_link(idx_ran_workflows, idx_dropped, ran_to_dropped, "rgba(239, 68, 68, 0.3)")

                # Column 4 -> Column 5/6: Connect Trial -> Templates / Dropped
                add_link(idx_connect_trial, idx_templates, connect_to_templates, "rgba(251, 191, 36, 0.5)")
                add_link(idx_connect_trial, idx_dropped, connect_to_dropped, "rgba(239, 68, 68, 0.3)")

                # Column 4 -> Column 5/6: Cross-Product -> Sandbox / Templates / Dropped
                add_link(idx_cross_product, idx_sandbox, cross_to_sandbox, "rgba(0, 212, 170, 0.4)")
                add_link(idx_cross_product, idx_templates, cross_to_templates, "rgba(0, 212, 170, 0.4)")
                add_link(idx_cross_product, idx_dropped, cross_to_dropped, "rgba(239, 68, 68, 0.3)")

                # Column 5 -> Column 6: Sandbox -> Production / Dropped
                add_link(idx_sandbox, idx_production, sandbox_to_prod, "rgba(16, 185, 129, 0.5)")
                add_link(idx_sandbox, idx_dropped, sandbox_to_dropped, "rgba(239, 68, 68, 0.3)")

                # Column 5 -> Column 6: Templates -> Paid Connect / Dropped
                add_link(idx_templates, idx_paid, templates_to_paid, "rgba(0, 212, 170, 0.5)")
                add_link(idx_templates, idx_dropped, templates_to_dropped, "rgba(239, 68, 68, 0.3)")

                # ============================================================
                # CREATE SANKEY FIGURE
                # ============================================================
                fig = go.Figure(go.Sankey(
                    node=dict(
                        pad=20,
                        thickness=25,
                        line=dict(color="black", width=0.5),
                        label=labels,
                        color=node_colors,
                        customdata=labels,
                        hovertemplate="%{label}: %{value} companies<extra></extra>"
                    ),
                    link=dict(
                        source=links_source,
                        target=links_target,
                        value=links_value,
                        color=links_color
                    )
                ))

                fig.update_layout(
                    title="User Journey: From Signup to Conversion",
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Space Grotesk", size=13),
                    height=700
                )
                st.plotly_chart(fig, use_container_width=True)

                # Narrative Summary
                st.markdown("### 📖 The Story of the Data")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **1. Node Creation**
                    - Out of **{total}** signups, **{created_node_count}** ({pct(created_node_count)}) created at least one node.
                    - **{did_not_create_node_count}** ({pct(did_not_create_node_count)}) did not create any nodes.

                    **2. Engagement Funnel**
                    - **{ran_workflows_count + cross_product_count}** ran workflows, **{connect_trial_count + cross_product_count}** started Connect trial.
                    - Cross-product adoption: **{cross_product_count}** ({pct(cross_product_count)}) use both Brain and Connect.
                    """)
                with col2:
                    st.markdown(f"""
                    **3. Final Outcomes (Column 6 = 100%)**
                    - Live in Production: **{final_production}** ({pct(final_production)})
                    - Paid Connect: **{final_paid}** ({pct(final_paid)})
                    - Dropped Off: **{final_dropped}** ({pct(final_dropped)})
                    - No Further Actions: **{final_no_further}** ({pct(final_no_further)})
                    """)

                with st.expander("🔍 Glosario de Variables"):
                    st.markdown("""
                    | Variable | Definición Técnica | Origen de Datos |
                    | :--- | :--- | :--- |
                    | **Signups** | Cuentas creadas en el periodo seleccionado. | `chatbot.companies` |
                    | **Created Node** | Usuarios que crearon al menos un nodo en el builder. | `node_type_*` flags |
                    | **Did Not Create Node** | Usuarios que no crearon ningún nodo. | Inverse of Created Node |
                    | **Ran Workflows** | Usuarios que ejecutaron al menos un workflow. | MongoDB `workflow_executions` |
                    | **Validated in Sandbox** | Ejecuciones en modo depuración (`isDebug=true`). | MongoDB `workflow_executions` |
                    | **Live in Production** | Bot activo con canal de producción conectado (`state=1 AND in_production=1`). | `chatbot.bots` |
                    | **Created Templates** | Usuarios que crearon plantillas en Connect. | `template_logs` |
                    | **Paid Connect** | Suscripción Connect en estado 'ACTIVE'. | `billing.subscriptions` |
                    | **No Further Actions** | Usuarios que no crearon nodos ni hicieron engagement. | Exclusion logic |
                    """)
        else:
            st.error("No data available")
    
    with tab2:
        st.markdown("### 🧠 Brain Studio Funnel")
        st.caption("Free tier + usage-based billing (pay per conversation after free limit)")
        
        # Recalculate metrics for this tab
        analysis = get_analysis_df(data)
        engagement = data.get('company_engagement')
        
        if analysis is not None:
            mask = (analysis['created_at'] >= pd.Timestamp(date_range[0])) & \
                   (analysis['created_at'] <= pd.Timestamp(date_range[1]))
            filtered = analysis[mask].copy()
            if plan_filter != "All Plans" and 'plan' in filtered.columns:
                filtered = filtered[filtered['plan'] == plan_filter]
            
            total = len(filtered)
            has_bot = filtered['has_bot'].sum() if 'has_bot' in filtered.columns else 0
            used_conv = filtered['used_conversations'].sum() if 'used_conversations' in filtered.columns else 0
            exceeded = filtered['exceeded_free_tier'].sum() if 'exceeded_free_tier' in filtered.columns else 0
            actually_paid = filtered['actually_paid'].sum() if 'actually_paid' in filtered.columns else 0
            
            # Get execution data from engagement
            executed_workflow = 0
            tested_sandbox = 0
            went_to_prod = 0
            if engagement is not None and len(engagement) > 0:
                filtered_company_ids = set(filtered['company_id'].dropna().astype(int).unique())
                eng_filtered = engagement[engagement['company_id'].isin(filtered_company_ids)]
                executed_workflow = len(eng_filtered)
                tested_sandbox = len(eng_filtered[eng_filtered['sandbox_executions'] > 0]) if 'sandbox_executions' in eng_filtered.columns else 0
                went_to_prod = len(eng_filtered[eng_filtered['prod_executions'] > 0]) if 'prod_executions' in eng_filtered.columns else 0
            
            # Brain Studio funnel with execution steps
            brain_funnel = pd.DataFrame({
                'Stage': [
                    'Signup', 
                    'Created Bot', 
                    'Executed Workflow', 
                    'Tested Sandbox', 
                    'Went to Production', 
                    'Used Conversations', 
                    'Exceeded Free Tier',
                    'Actually Paid'
                ],
                'Count': [
                    int(total), 
                    int(has_bot), 
                    int(executed_workflow), 
                    int(tested_sandbox), 
                    int(went_to_prod), 
                    int(used_conv), 
                    int(exceeded),
                    int(actually_paid)
                ]
            })
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = go.Figure(go.Funnel(
                    y=brain_funnel['Stage'],
                    x=brain_funnel['Count'],
                    textposition="inside",
                    textinfo="value+percent initial",
                    marker=dict(color=['#7C3AED', '#00D4AA', '#8B5CF6', '#A855F7', '#F59E0B', '#10B981', '#FBBF24', '#00D4AA']),
                    connector=dict(line=dict(color="#404060", width=2))
                ))
                fig.update_layout(
                    title="Brain Studio Conversion Path",
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Space Grotesk", size=14),
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📉 Drop-off Analysis")
                for i in range(1, len(brain_funnel)):
                    prev = brain_funnel.iloc[i-1]
                    curr = brain_funnel.iloc[i]
                    dropoff_pct = ((prev['Count'] - curr['Count']) / prev['Count'] * 100) if prev['Count'] > 0 else 0
                    retention_pct = (curr['Count'] / prev['Count']) if prev['Count'] > 0 else 0
                    
                    st.markdown(f"**{prev['Stage']} → {curr['Stage']}:** {dropoff_pct:.0f}% drop")
                    st.progress(retention_pct)
                
                st.markdown("---")
                if total > 0:
                    st.error(f"🔴 **{100 - (went_to_prod / total * 100):.0f}%** never execute in production")
            
            st.info(f"""
            **Brain Studio Revenue Model:**
            - Users get **free conversations** (typically 50)
            - After exceeding free tier, they pay **per conversation**
            - Currently **{exceeded}** users ({exceeded/total*100:.1f}% of signups) have exceeded free tier
            """)
    
    with tab3:
        st.markdown("### 🔗 Connect Funnel")
        st.caption("$20/month subscription with 14-day free trial (optional add-on)")
        
        # Get filtered analysis data
        analysis = get_analysis_df(data)
        if analysis is not None:
            mask = (analysis['created_at'] >= pd.Timestamp(date_range[0])) & \
                   (analysis['created_at'] <= pd.Timestamp(date_range[1]))
            filtered = analysis[mask].copy()
            if plan_filter != "All Plans" and 'plan' in filtered.columns:
                filtered = filtered[filtered['plan'] == plan_filter]
            
            total = len(filtered)
            has_connect = filtered['has_connect'].sum() if 'has_connect' in filtered.columns else 0
            connect_trial = filtered['connect_trialing'].sum() if 'connect_trialing' in filtered.columns else 0
            has_template = filtered['has_template_usage'].sum() if 'has_template_usage' in filtered.columns else 0
            connect_active = filtered['connect_active'].sum() if 'connect_active' in filtered.columns else 0
            
            # Connect funnel starts from users who started trial (100% base)
            connect_funnel = pd.DataFrame({
                'Stage': ['Started Connect Trial', 'Currently Trialing', 'Created Template', 'Converted to Paid'],
                'Count': [has_connect, connect_trial, has_template, connect_active]
            })
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = go.Figure(go.Funnel(
                    y=connect_funnel['Stage'],
                    x=connect_funnel['Count'],
                    textposition="inside",
                    textinfo="value+percent initial",
                    marker=dict(color=['#F59E0B', '#3B82F6', '#8B5CF6', '#00D4AA']),
                    connector=dict(line=dict(color="#404060", width=2))
                ))
                fig.update_layout(
                    title="Connect Subscription Path",
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Space Grotesk", size=14),
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📊 Connect Adoption")
                adoption_pct = (has_connect / total * 100) if total > 0 else 0
                st.metric("Signups who tried Connect", f"{has_connect}", f"{adoption_pct:.1f}% of {total}")
                
                st.markdown("### 📉 Drop-off Analysis")
                if has_connect > 0:
                    churn_pct = 100 - (connect_trial / has_connect * 100)
                    st.markdown(f"**Trial → Still Trialing:** {churn_pct:.0f}% churned")
                    st.progress(connect_trial / has_connect if has_connect > 0 else 0)
                    
                    convert_pct = (connect_active / has_connect * 100) if has_connect > 0 else 0
                    st.markdown(f"**Trial → Paid:** {convert_pct:.1f}% converted")
                    st.progress(connect_active / has_connect if has_connect > 0 else 0)
            
            trial_to_paid = connect_active / has_connect * 100 if has_connect > 0 else 0
            st.info(f"""
            **Connect Revenue Model:**
            - 14-day free trial, then $20/month
            - **{has_connect}** users started trial ({has_connect/total*100:.1f}% of signups)
            - **{connect_active}** converted to paid
            - **Trial → Paid conversion: {trial_to_paid:.1f}%**
            """)


def render_company_data(data, date_range, plan_filter="All Plans"):
    """Render the company data browsing page"""
    st.markdown("# 📋 Company Data")
    st.markdown("*Browse and filter all company signups*")
    
    analysis = get_analysis_df(data)
    if analysis is None:
        st.error("No data available")
        return
    
    # Apply date filter
    mask = (analysis['created_at'] >= pd.Timestamp(date_range[0])) & \
           (analysis['created_at'] <= pd.Timestamp(date_range[1]))
    filtered = analysis[mask].copy()
    
    # Apply plan filter
    if plan_filter != "All Plans" and 'plan' in filtered.columns:
        filtered = filtered[filtered['plan'] == plan_filter]
    
    # Create signup week column for filtering
    filtered['signup_week'] = filtered['created_at'].dt.to_period('W-SUN').dt.start_time
    
    # Build signup week options with range labels
    week_options = {}
    for week in sorted(filtered['signup_week'].dropna().unique()):
        week_start = pd.Timestamp(week)
        week_end = week_start + pd.Timedelta(days=6)
        label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        week_options[label] = week_start
    
    # Signup week filter
    st.markdown("**Signup Week Filter:**")
    selected_week = st.selectbox(
        "Filter by signup week",
        options=["All Weeks"] + list(week_options.keys()),
        index=0,
        label_visibility="collapsed"
    )
    
    # Apply signup week filter
    if selected_week != "All Weeks":
        selected_week_start = week_options[selected_week]
        filtered = filtered[filtered['signup_week'] == selected_week_start]
    
    st.markdown(f"**Showing {len(filtered)} companies** from {date_range[0]} to {date_range[1]} ({plan_filter}){f' - {selected_week}' if selected_week != 'All Weeks' else ''}")
    
    # Check if analysis_combined.csv already has session data (from notebook preprocessing)
    has_session_data = 'last_session' in filtered.columns and 'days_active' in filtered.columns
    
    # If not, merge with user sessions 
    if not has_session_data:
        user_sessions = data.get('user_sessions')
        if user_sessions is not None and len(user_sessions) > 0:
            sessions_copy = user_sessions.copy()
            sessions_copy['company_id'] = pd.to_numeric(sessions_copy['company_id'], errors='coerce')
            
            # Parse session dates
            sessions_copy['last_session'] = make_tz_naive(sessions_copy['last_session'])
            sessions_copy['first_session'] = make_tz_naive(sessions_copy['first_session'])
            
            # Merge session data
            filtered = filtered.merge(
                sessions_copy[['company_id', 'first_session', 'last_session', 'days_active', 'total_sessions']],
                on='company_id',
                how='left'
            )
            has_session_data = True
    
    # Calculate days since last session for activity filters
    if has_session_data and 'last_session' in filtered.columns:
        # Make sure last_session is datetime
        if filtered['last_session'].dtype == 'object':
            filtered['last_session'] = pd.to_datetime(filtered['last_session'], errors='coerce')
        filtered['last_session'] = make_tz_naive(filtered['last_session'])
        
        today = pd.Timestamp.now().normalize()
        filtered['days_since_last_session'] = (today - filtered['last_session']).dt.days
    
    # Quick filters - Row 1: Status filters
    st.markdown("**Status Filters:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        show_with_bot = st.checkbox("Has Bot", value=False)
    with col2:
        show_with_subscription = st.checkbox("Has Subscription", value=False)
    with col3:
        show_production = st.checkbox("In Production", value=False)
    with col4:
        show_paid = st.checkbox("Actually Paid", value=False)
    
    # Quick filters - Row 2: Retention filters (active X weeks after signup)
    # Use pre-calculated flags from analysis_combined.csv
    has_retention_flags = 'retained_week1' in filtered.columns
    
    st.markdown("**Retention Filters** *(still active X weeks after signup)*:")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        show_retained_day1 = st.checkbox("Day 1 Active", value=False, help="Still active 1+ day after signup")
    with col2:
        show_retained_week1 = st.checkbox("Week 1 Active", value=False, help="Still active 7+ days after signup")
    with col3:
        show_retained_week2 = st.checkbox("Week 2 Active", value=False, help="Still active 14+ days after signup")
    with col4:
        show_retained_week3 = st.checkbox("Week 3 Active", value=False, help="Still active 21+ days after signup")
    with col5:
        show_retained_week4 = st.checkbox("Week 4 Active", value=False, help="Still active 28+ days after signup")
    
    # Initialize recent activity filter vars (not shown but available)
    show_active_week1 = show_active_week2 = show_active_week3 = show_active_week4 = False
    
    # Apply status filters
    if show_with_bot and 'has_bot' in filtered.columns:
        filtered = filtered[filtered['has_bot'] == True]
    if show_with_subscription and 'has_subscription' in filtered.columns:
        filtered = filtered[filtered['has_subscription'] == True]
    if show_production and 'has_prod_channel' in filtered.columns:
        filtered = filtered[filtered['has_prod_channel'] == True]
    if show_paid and 'actually_paid' in filtered.columns:
        filtered = filtered[filtered['actually_paid'] == True]
    
    # Apply retention filters - use pre-calculated flags from analysis_combined.csv
    # These show companies that were still active X days after their signup
    if show_retained_day1:
        if 'retained_day1' in filtered.columns:
            filtered = filtered[filtered['retained_day1'] == True]
        elif 'days_to_last_activity' in filtered.columns:
            filtered = filtered[filtered['days_to_last_activity'] >= 1]
    
    if show_retained_week1:
        if 'retained_week1' in filtered.columns:
            filtered = filtered[filtered['retained_week1'] == True]
        elif 'days_to_last_activity' in filtered.columns:
            filtered = filtered[filtered['days_to_last_activity'] >= 7]
    
    if show_retained_week2:
        if 'retained_week2' in filtered.columns:
            filtered = filtered[filtered['retained_week2'] == True]
        elif 'days_to_last_activity' in filtered.columns:
            filtered = filtered[filtered['days_to_last_activity'] >= 14]
    
    if show_retained_week3:
        if 'retained_week3' in filtered.columns:
            filtered = filtered[filtered['retained_week3'] == True]
        elif 'days_to_last_activity' in filtered.columns:
            filtered = filtered[filtered['days_to_last_activity'] >= 21]
    
    if show_retained_week4:
        if 'retained_week4' in filtered.columns:
            filtered = filtered[filtered['retained_week4'] == True]
        elif 'days_to_last_activity' in filtered.columns:
            filtered = filtered[filtered['days_to_last_activity'] >= 28]
    
    # Search box
    search = st.text_input("🔍 Search by company name or slug", "")
    if search:
        name_match = filtered['company_name'].str.contains(search, case=False, na=False) if 'company_name' in filtered.columns else False
        slug_match = filtered['slug'].str.contains(search, case=False, na=False) if 'slug' in filtered.columns else False
        filtered = filtered[name_match | slug_match]
    
    st.markdown(f"**{len(filtered)} companies match filters**")
    
    # Select columns to display
    display_cols = ['company_id', 'company_name', 'slug', 'plan', 'created_at']
    
    # Add status columns if they exist
    status_cols = [
        'has_bot', 'has_workflow', 'has_sandbox', 'has_prod_channel', 
        'has_connect', 'has_template_usage', 'actually_paid', 'total_paid'
    ]
    for col in status_cols:
        if col in filtered.columns:
            display_cols.append(col)
    
    # Add activity columns if available
    activity_cols = [
        'last_session', 'days_active', 'total_sessions', 'days_since_signup', 
        'days_to_last_activity', 'total_time_minutes', 'avg_session_minutes'
    ]
    for col in activity_cols:
        if col in filtered.columns:
            display_cols.append(col)
    
    # Add retention flags if available
    retention_cols = ['retained_day1', 'retained_week1', 'retained_week2', 'retained_week3', 'retained_week4']
    for col in retention_cols:
        if col in filtered.columns:
            display_cols.append(col)
    
    # Filter to only existing columns
    display_cols = [c for c in display_cols if c in filtered.columns]
    
    # Sort by created_at descending (newest first)
    if 'created_at' in filtered.columns:
        filtered = filtered.sort_values('created_at', ascending=False)
    
    # Display dataframe
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        height=500,
        column_config={
            "company_id": st.column_config.NumberColumn("ID", width="small"),
            "company_name": st.column_config.TextColumn("Company Name", width="medium"),
            "slug": st.column_config.TextColumn("Slug", width="medium"),
            "plan": st.column_config.TextColumn("Plan", width="small"),
            "created_at": st.column_config.DatetimeColumn("Signup Date", format="YYYY-MM-DD"),
            "has_bot": st.column_config.CheckboxColumn("Bot", width="small", help="Created a bot"),
            "has_workflow": st.column_config.CheckboxColumn("Workflow", width="small", help="Executed a workflow"),
            "has_sandbox": st.column_config.CheckboxColumn("Sandbox", width="small", help="Tested in sandbox"),
            "has_prod_channel": st.column_config.CheckboxColumn("Prod", width="small", help="Connected production channel"),
            "has_connect": st.column_config.CheckboxColumn("Connect", width="small", help="Started Connect trial"),
            "has_template_usage": st.column_config.CheckboxColumn("Templates", width="small", help="Created at least one template"),
            "actually_paid": st.column_config.CheckboxColumn("Paid", width="small", help="Actually paid"),
            "total_paid": st.column_config.NumberColumn("$ Paid", format="$%.2f"),
            "last_session": st.column_config.DatetimeColumn("Last Login", format="YYYY-MM-DD"),
            "days_active": st.column_config.NumberColumn("Days Active", width="small"),
            "total_sessions": st.column_config.NumberColumn("Sessions", width="small"),
            "total_time_minutes": st.column_config.NumberColumn("Time (min)", width="small", format="%.0f"),
            "avg_session_minutes": st.column_config.NumberColumn("Avg Sess (min)", width="small", format="%.1f"),
            "days_since_signup": st.column_config.NumberColumn("Age (days)", width="small"),
            "days_to_last_activity": st.column_config.NumberColumn("Active Until", width="small", help="Days from signup to last activity"),
            "retained_day1": st.column_config.CheckboxColumn("D1", width="small", help="Still active 1+ day after signup"),
            "retained_week1": st.column_config.CheckboxColumn("W1", width="small", help="Still active 7+ days after signup"),
            "retained_week2": st.column_config.CheckboxColumn("W2", width="small", help="Still active 14+ days after signup"),
            "retained_week3": st.column_config.CheckboxColumn("W3", width="small", help="Still active 21+ days after signup"),
            "retained_week4": st.column_config.CheckboxColumn("W4", width="small", help="Still active 28+ days after signup"),
        }
    )
    
    # Download button
    csv = filtered[display_cols].to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name=f"company_data_{date_range[0]}_{date_range[1]}.csv",
        mime="text/csv"
    )


def render_company_explorer(data, date_range, plan_filter="All Plans"):
    """Render the company explorer page for deep-diving into individual companies"""
    st.markdown("# 🔍 Company Explorer")
    st.markdown("*Deep dive into a specific company's activity*")
    
    analysis = get_analysis_df(data)
    if analysis is None:
        st.error("No data available")
        return
    
    # Get list of companies for selection
    companies = analysis[['company_id', 'company_name', 'slug']].drop_duplicates()
    companies = companies.sort_values('company_name')
    
    # Create display options
    company_options = {
        f"{row['company_name']} ({row['slug']})": row['company_id'] 
        for _, row in companies.iterrows() 
        if pd.notna(row['company_name'])
    }
    
    # Company selector
    selected_display = st.selectbox(
        "Select a company",
        options=[""] + list(company_options.keys()),
        index=0,
        help="Start typing to search for a company"
    )
    
    if not selected_display:
        st.info("👆 Select a company above to see their details")
        return
    
    selected_company_id = company_options[selected_display]
    company_data = analysis[analysis['company_id'] == selected_company_id].iloc[0]
    
    # Company header
    st.markdown(f"## {company_data.get('company_name', 'Unknown')}")
    st.markdown(f"**Slug:** `{company_data.get('slug', 'N/A')}` | **ID:** `{selected_company_id}`")
    
    # Basic info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Plan", company_data.get('plan', 'N/A'))
    with col2:
        signup_date = company_data.get('created_at')
        if pd.notna(signup_date):
            days_ago = (pd.Timestamp.now() - pd.Timestamp(signup_date)).days
            st.metric("Signup Date", pd.Timestamp(signup_date).strftime('%Y-%m-%d'), f"{days_ago} days ago")
        else:
            st.metric("Signup Date", "N/A")
    with col3:
        environment = company_data.get('environment', 'N/A')
        st.metric("Environment", environment)
    
    st.markdown("---")
    
    # Status indicators
    st.markdown("### 📊 Status")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        has_bot = company_data.get('has_bot', False)
        st.metric("Created Bot", "✅ Yes" if has_bot else "❌ No")
    
    with col2:
        has_prod = company_data.get('has_prod_channel', False)
        st.metric("Production Channel", "✅ Yes" if has_prod else "❌ No")
    
    with col3:
        has_sub = company_data.get('has_subscription', False)
        st.metric("Has Subscription", "✅ Yes" if has_sub else "❌ No")
    
    with col4:
        has_brain = company_data.get('has_brain_studio', False)
        st.metric("Brain Studio", "✅ Yes" if has_brain else "❌ No")
    
    with col5:
        has_connect = company_data.get('has_connect', False)
        st.metric("Connect", "✅ Yes" if has_connect else "❌ No")
    
    st.markdown("---")
    
    # Payment info
    st.markdown("### 💰 Payment Status")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        actually_paid = company_data.get('actually_paid', False)
        st.metric("Actually Paid", "✅ Yes" if actually_paid else "❌ No")
    
    with col2:
        total_paid = company_data.get('total_paid', 0)
        st.metric("Total Paid", f"${total_paid:.2f}" if pd.notna(total_paid) else "$0.00")
    
    with col3:
        exceeded_free = company_data.get('exceeded_free_tier', False)
        st.metric("Exceeded Free Tier", "✅ Yes" if exceeded_free else "❌ No")
    
    st.markdown("---")
    
    # Related data sections
    st.markdown("### 📁 Related Data")
    
    # Subscriptions
    subscriptions = data.get('subscriptions')
    if subscriptions is not None and len(subscriptions) > 0:
        company_subs = subscriptions[subscriptions['company_id'] == selected_company_id]
        if len(company_subs) > 0:
            with st.expander(f"📋 Subscriptions ({len(company_subs)})", expanded=True):
                sub_cols = ['subscription_id', 'product_name', 'status', 'created_at', 'trial_start', 'trial_end']
                sub_cols = [c for c in sub_cols if c in company_subs.columns]
                st.dataframe(company_subs[sub_cols], use_container_width=True)
        else:
            st.info("No subscriptions found for this company")
    
    # Bots
    bots = data.get('bots')
    if bots is not None and len(bots) > 0:
        # Convert company_id to numeric for comparison
        bots_copy = bots.copy()
        bots_copy['company_id'] = pd.to_numeric(bots_copy['company_id'], errors='coerce')
        company_bots = bots_copy[bots_copy['company_id'] == selected_company_id]
        if len(company_bots) > 0:
            with st.expander(f"🤖 Bots ({len(company_bots)})", expanded=False):
                bot_cols = ['bot_id', 'name', 'type', 'state', 'created_at']
                bot_cols = [c for c in bot_cols if c in company_bots.columns]
                st.dataframe(company_bots[bot_cols] if bot_cols else company_bots, use_container_width=True)
        else:
            st.info("No bots found for this company")
    
    # Wallet transactions
    wallet_txns = data.get('wallet_transactions')
    if wallet_txns is not None and len(wallet_txns) > 0:
        wallet_copy = wallet_txns.copy()
        wallet_copy['company_id'] = pd.to_numeric(wallet_copy['company_id'], errors='coerce')
        company_txns = wallet_copy[wallet_copy['company_id'] == selected_company_id]
        if len(company_txns) > 0:
            with st.expander(f"💳 Wallet Transactions ({len(company_txns)})", expanded=False):
                txn_cols = ['action', 'amount', 'balance_after', 'reason', 'created_at']
                txn_cols = [c for c in txn_cols if c in company_txns.columns]
                st.dataframe(company_txns[txn_cols] if txn_cols else company_txns, use_container_width=True)
        else:
            st.info("No wallet transactions found for this company")
    
    # Stripe invoices
    invoices = data.get('stripe_invoices')
    if invoices is not None and len(invoices) > 0:
        invoices_copy = invoices.copy()
        invoices_copy['company_id'] = pd.to_numeric(invoices_copy['company_id'], errors='coerce')
        company_invoices = invoices_copy[invoices_copy['company_id'] == selected_company_id]
        if len(company_invoices) > 0:
            with st.expander(f"🧾 Invoices ({len(company_invoices)})", expanded=False):
                inv_cols = ['invoice_id', 'amount_paid', 'status', 'paid_at', 'created_at']
                inv_cols = [c for c in inv_cols if c in company_invoices.columns]
                st.dataframe(company_invoices[inv_cols] if inv_cols else company_invoices, use_container_width=True)
        else:
            st.info("No invoices found for this company")
    
    # User sessions
    sessions = data.get('user_sessions')
    if sessions is not None and len(sessions) > 0:
        sessions_copy = sessions.copy()
        sessions_copy['company_id'] = pd.to_numeric(sessions_copy['company_id'], errors='coerce')
        company_sessions = sessions_copy[sessions_copy['company_id'] == selected_company_id]
        if len(company_sessions) > 0:
            with st.expander(f"🔑 User Sessions ({len(company_sessions)})", expanded=False):
                session_cols = ['first_session', 'last_session', 'total_sessions', 'user_count', 'days_active']
                session_cols = [c for c in session_cols if c in company_sessions.columns]
                st.dataframe(company_sessions[session_cols] if session_cols else company_sessions, use_container_width=True)
        else:
            st.info("No session data found for this company")


if __name__ == "__main__":
    main()

