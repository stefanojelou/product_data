-- Node creation usage (counts by nodeTypeId per company_id)
-- Output file: data/nodes_usage.csv
--
-- Definition:
--   "Node created" == a row in `jelou_workflows.nodes` (createdAt) that is not soft-deleted.
--
-- Notes:
-- - No SELF_SERVICE filter here (filter later in pandas using signups.plan if needed)
-- - company_id is resolved via: nodes.workflowId -> workflows.appId -> apps.companyId
-- - Removed join to node_types since schema is unknown; using nodeTypeId directly.

USE jelou_workflows;
SELECT
    a.companyId AS company_id,
    n.nodeTypeId,
    COUNT(*) AS nodes_created,
    MIN(n.createdAt) AS first_node_at,
    MAX(n.createdAt) AS last_node_at
FROM jelou_workflows.nodes n
JOIN jelou_workflows.workflows w
  ON w.id = n.workflowId
 AND w.deletedAt IS NULL
JOIN jelou_workflows.apps a
  ON a.id = w.appId
WHERE n.deletedAt IS NULL
GROUP BY
    a.companyId,
    n.nodeTypeId
ORDER BY
    a.companyId,
    nodes_created DESC;
