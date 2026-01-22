-- Extract wallet transactions from billing.wallet_transactions
-- Shows actual charges and credits for conversation usage
-- Run in MySQL Workbench, export results to CSV as: data/wallet_transactions.csv

SELECT 
    id AS transaction_id,
    wallet_id,
    company_id,
    action,
    balance_after,
    reason,
    details,
    product_id,
    amount,
    status,
    created_at
FROM billing.wallet_transactions
WHERE created_at >= '2025-11-01'
ORDER BY created_at DESC;

-- Aggregated view: Total charges per company
/*
SELECT 
    company_id,
    COUNT(*) AS total_transactions,
    SUM(CASE WHEN action = 'CHARGE' OR action = 'DEBIT' THEN 1 ELSE 0 END) AS charge_count,
    SUM(CASE WHEN action = 'CHARGE' OR action = 'DEBIT' THEN amount ELSE 0 END) AS total_charged,
    SUM(CASE WHEN action = 'CREDIT' OR action = 'TOPUP' THEN amount ELSE 0 END) AS total_credited,
    MIN(created_at) AS first_transaction,
    MAX(created_at) AS last_transaction,
    GROUP_CONCAT(DISTINCT action) AS action_types,
    GROUP_CONCAT(DISTINCT status) AS statuses
FROM billing.wallet_transactions
WHERE created_at >= '2025-11-01'
GROUP BY company_id
ORDER BY total_charged DESC;
*/
