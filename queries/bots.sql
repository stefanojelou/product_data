-- Extract bot data from chatbot.bots
-- This shows which companies have created bots and connected production channels
-- Run in MySQL Workbench, export results to CSV as: data/bots.csv
-- NOTE: Excluding JSON columns (properties, channelCredentials, propertiesAuth) 
--       as they break CSV parsing due to embedded commas/quotes

SELECT 
    id AS bot_id,
    name AS bot_name,
    imageUrl AS image_url,
    accesstoken,
    socketId AS socket_id,
    type,
    templateId AS template_id,
    connected,
    multiLanguage AS multi_language,
    companyId AS company_id,
    hsmCount AS hsm_count,
    hsmDailyLimit AS hsm_daily_limit,
    language,
    state,
    inProduction AS in_production,
    createdAt AS created_at,
    updatedAt AS updated_at,
    routerId AS router_id
FROM chatbot.bots
WHERE createdAt >= '2025-11-01'
ORDER BY createdAt DESC;

-- Alternative: Aggregated view per company
-- Shows how many bots each company has and if any are in production

/*
SELECT 
    companyId AS company_id,
    COUNT(*) AS total_bots,
    SUM(CASE WHEN inProduction = 1 THEN 1 ELSE 0 END) AS production_bots,
    SUM(CASE WHEN connected = 1 THEN 1 ELSE 0 END) AS connected_bots,
    MIN(createdAt) AS first_bot_created,
    MAX(createdAt) AS last_bot_created,
    GROUP_CONCAT(DISTINCT type) AS bot_types,
    GROUP_CONCAT(DISTINCT state) AS bot_states
FROM chatbot.bots
WHERE createdAt >= '2025-11-01'
GROUP BY companyId
ORDER BY first_bot_created DESC;
*/
