-- Extract payment methods from billing.payment_methods
-- Shows which customers have added a credit card
-- Run in MySQL Workbench, export results to CSV as: data/payment_methods.csv

-- First, check the columns in the table
-- DESCRIBE billing.payment_methods;

-- Basic query (adjust column names based on actual schema)
SELECT 
    pm.*
FROM billing.payment_methods pm
ORDER BY pm.created_at DESC;

-- If you need to link to companies via customers table:
/*
SELECT 
    pm.id AS payment_method_id,
    pm.customer_id,
    c.company_id,
    pm.type,
    pm.created_at
FROM billing.payment_methods pm
JOIN billing.customers c ON pm.customer_id = c.id
ORDER BY pm.created_at DESC;
*/

-- Aggregated: Which companies have payment methods on file?
/*
SELECT 
    c.company_id,
    COUNT(pm.id) AS payment_methods_count,
    MIN(pm.created_at) AS first_payment_method_added
FROM billing.payment_methods pm
JOIN billing.customers c ON pm.customer_id = c.id
GROUP BY c.company_id
ORDER BY first_payment_method_added DESC;
*/

