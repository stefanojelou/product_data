-- Extract Stripe invoices from billing.stripe_invoices
-- Shows actual payments made by customers
-- Run in MySQL Workbench, export results to CSV as: data/stripe_invoices.csv

SELECT 
    id,
    stripe_invoice_id,
    invoice_number,
    company_id,
    customer_id,
    subscription_id,
    payment_intent_id,
    charge_id,
    payment_method_id,
    status,
    billing_reason,
    collection_method,
    subtotal,
    tax,
    total,
    amount_due,
    amount_paid,
    currency,
    due_date,
    paid_at,
    period_start,
    period_end,
    hosted_invoice_url,
    invoice_pdf,
    description,
    created_at,
    updated_at
FROM billing.stripe_invoices
WHERE period_start >= '2025-11-01'
   OR created_at >= '2025-11-01'
ORDER BY paid_at DESC, created_at DESC;

-- Summary: Companies that actually paid
/*
SELECT 
    company_id,
    COUNT(*) AS invoice_count,
    SUM(amount_paid) AS total_paid,
    SUM(total) AS total_invoiced,
    COUNT(CASE WHEN amount_paid > 0 THEN 1 END) AS paid_invoices,
    COUNT(CASE WHEN status = 'paid' THEN 1 END) AS paid_status_count,
    MIN(paid_at) AS first_payment,
    MAX(paid_at) AS last_payment,
    GROUP_CONCAT(DISTINCT status) AS invoice_statuses,
    GROUP_CONCAT(DISTINCT billing_reason) AS billing_reasons
FROM billing.stripe_invoices
WHERE period_start >= '2025-11-01' OR created_at >= '2025-11-01'
GROUP BY company_id
ORDER BY total_paid DESC;
*/
