-- Extract new company signups from chatbot.companies
-- Run in MySQL Workbench, export results to CSV as: data/signups.csv

SELECT 
    id AS company_id,
    name AS company_name,
    slug,
    type,
    plan,
    email,
    clientId AS client_id,
    inProduction AS in_production,
    state,
    environment,
    category,
    country,
    timezone,
    adCampaignSource AS ad_campaign_source,
    enableSelfUnlock AS enable_self_unlock,
    ownerId AS owner_id,
    organizationId AS organization_id,
    createdAt AS created_at,
    updatedAt AS updated_at,
    enableProductionAt AS enable_production_at,
    disableProductionAt AS disable_production_at
FROM chatbot.companies
WHERE createdAt >= '2025-01-01'
ORDER BY createdAt DESC;

-- Useful fields from the schema:
-- id              - Primary key
-- name            - Company name
-- slug            - URL slug
-- type            - Company type
-- plan            - Current plan (important for conversion analysis!)
-- email           - Contact email
-- inProduction    - Boolean: are they in production?
-- state           - Account state
-- environment     - Environment type
-- category        - Business category
-- country         - Country (for geo analysis)
-- adCampaignSource - How they found Jelou (attribution!)
-- enableProductionAt - When they went to production (key metric!)
-- disableProductionAt - When they left production
-- ownerId         - User who owns the company
-- organizationId  - Parent organization

-- Quick count by date:
-- SELECT DATE(createdAt) as fecha, COUNT(*) as registros
-- FROM chatbot.companies
-- WHERE createdAt >= '2025-01-01'
-- GROUP BY DATE(createdAt)
-- ORDER BY fecha DESC;
