-- Extract credit wallet data from billing.credit_wallet
-- Shows conversation credits, free tier usage, and if users exceeded free tier
-- Run in MySQL Workbench, export results to CSV as: data/credit_wallet.csv

SELECT 
    id,
    company_id,
    balance,
    total_purchased,
    total_used,
    seats,
    seats_used,
    free_conversations,
    plan_tier_id,
    current_period_start,
    current_period_end,
    last_reset_at,
    last_processed_at,
    version,
    free_tier_allowances,
    created_at,
    updated_at,
    -- Derived fields for analysis
    CASE 
        WHEN total_used > free_conversations THEN 1 
        ELSE 0 
    END AS exceeded_free_tier,
    CASE 
        WHEN total_used > free_conversations THEN total_used - free_conversations 
        ELSE 0 
    END AS paid_conversations,
    CASE 
        WHEN free_conversations > 0 THEN ROUND(total_used / free_conversations * 100, 2)
        ELSE 0 
    END AS free_tier_usage_pct
FROM billing.credit_wallet
ORDER BY created_at DESC;

-- Note: Filter by company_id if you want to focus on specific signups
-- WHERE company_id IN (SELECT id FROM chatbot.companies WHERE createdAt >= '2025-11-01')
