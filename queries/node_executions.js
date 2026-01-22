// MongoDB Aggregation: Node executions by WORKFLOW
// Run in MongoDB Compass > Aggregations tab on: workflow-server.builder.node_executions
// Export to JSON, convert to CSV: data/node_executions.csv
// Date filter: Nov 15, 2025 onwards
// WARNING: Might timeout - use execution_activity_logs instead if needed
[
  {
    "$match": {
      "createdAt": { "$gte": ISODate("2025-11-15T00:00:00.000Z") }
    }
  },
  {
    "$group": {
      "_id": "$Node.workflowId",
      "total_node_executions": { "$sum": 1 },
      "success_count": { "$sum": { "$cond": [{ "$eq": ["$type", "SUCCESS"] }, 1, 0] } },
      "failed_count": { "$sum": { "$cond": [{ "$eq": ["$type", "FAILED"] }, 1, 0] } },
      "node_types_used": { "$addToSet": "$Node.nodeTypeId" },
      "has_ai_agent": { "$max": { "$cond": [{ "$eq": ["$Node.nodeTypeId", 21] }, 1, 0] } },
      "first_node_exec": { "$min": "$createdAt" },
      "last_node_exec": { "$max": "$createdAt" }
    }
  },
  {
    "$project": {
      "_id": 0,
      "workflow_id": "$_id",
      "total_node_executions": 1,
      "success_count": 1,
      "failed_count": 1,
      "node_type_count": { "$size": "$node_types_used" },
      "has_ai_agent": { "$eq": ["$has_ai_agent", 1] },
      "first_node_exec": 1,
      "last_node_exec": 1
    }
  },
  { "$sort": { "total_node_executions": -1 } }
]

// Node type 21 = AI Agent (main paid feature)
