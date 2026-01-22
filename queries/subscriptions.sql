-- Extract billing/subscription data from billing database
-- Run in MySQL Workbench, export results to CSV as: data/subscriptions.csv
-- IMPORTANT: Do NOT include 'metadata' column - it contains JSON that breaks CSV parsing!

-- Main subscriptions query (based on DBA's schema)
-- Excludes metadata column to avoid CSV parsing issues
SELECT
    s.id AS subscription_id,
    s.company_id,
    s.customer_id,
    s.stripe_subscription_id,
    sp.name AS product_name,
    s.status,
    s.interval,
    s.current_period_start,
    s.current_period_end,
    s.trial_start,
    s.trial_end,
    s.cancel_at,
    s.canceled_at,
    s.payment_attempts_count,
    s.created_at,
    s.updated_at,
    s.trial_ended,
    s.started_plan,
    si.quantity,
    si.price_id
FROM billing.subscriptions s
JOIN billing.subscription_items si ON s.id = si.subscription_id
JOIN billing.stripe_products sp ON si.product_id = sp.id
WHERE s.created_at >= '2025-01-01'
ORDER BY s.created_at DESC;

-- To verify table structures first, run:
-- DESCRIBE billing.subscriptions;
-- DESCRIBE billing.subscription_items;
-- DESCRIBE billing.stripe_products;

-- DBA's original query (for reference):
-- Filters by specific price_ids for certain products
/*
SELECT
  s.id as "ID",
  sp.name as "PRODUCT",
  s.status as "STATUS",
  s.current_period_start as "SUBSCRIPTION_START",
  s.current_period_end as "SUBSCRIPTION_END",
  s.created_at as "CREATION_DATE",
  s.trial_start as "START TRIAL",
  s.trial_end as "END_TRIAL",
  s.canceled_at as "CANCEL_DATE",
  si.quantity as "QUANTITY"
FROM subscriptions s
JOIN subscription_items si ON s.id = si.subscription_id
JOIN stripe_products sp ON si.product_id = sp.id 
WHERE si.price_id IN ('01KA060FBZGHVYFGH7QCHRC18Q', '01KA062A98A7KJBC6AY6A1FR0V') 
  AND s.created_at BETWEEN '2025-12-18 05:00:00' AND '2026-12-30 04:59:59';
*/

-- Query to join with chatbot.companies for full analysis
SELECT
    c.id AS company_id,
    c.name AS company_name,
    c.createdAt AS company_created_at,
    s.id AS subscription_id,
    sp.name AS product_name,
    s.status AS subscription_status,
    s.current_period_start,
    s.current_period_end,
    s.created_at AS subscription_created_at,
    s.trial_start,
    s.trial_end,
    s.canceled_at,
    si.quantity
FROM chatbot.companies c
LEFT JOIN billing.subscriptions s ON c.id = s.company_id
LEFT JOIN billing.subscription_items si ON s.id = si.subscription_id
LEFT JOIN billing.stripe_products sp ON si.product_id = sp.id
WHERE c.createdAt >= '2025-01-01'
ORDER BY c.createdAt DESC;
