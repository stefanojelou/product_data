// MongoDB Aggregation: User activity in Brain Studio
// Run in MongoDB Compass > Aggregations tab on: workflow-server.builder.user_activity_logs
// Export to JSON, convert to CSV: data/user_activity_logs.csv
// Date filter: Nov 15, 2025 onwards
// WARNING: Might timeout - try with smaller date range if needed
[
  {
    "$match": {
      "createdAt": { "$gte": ISODate("2025-11-15T00:00:00.000Z") }
    }
  },
  {
    "$group": {
      "_id": "$workflowId",
      "total_actions": { "$sum": 1 },
      "create_node": { "$sum": { "$cond": [{ "$eq": ["$userOperation", "CREATE_NODE"] }, 1, 0] } },
      "update_node": { "$sum": { "$cond": [{ "$eq": ["$userOperation", "UPDATE_NODE"] }, 1, 0] } },
      "delete_node": { "$sum": { "$cond": [{ "$eq": ["$userOperation", "DELETE_NODE"] }, 1, 0] } },
      "users": { "$addToSet": "$user" },
      "node_types_used": { "$addToSet": "$nodeTypeId" },
      "first_activity": { "$min": "$createdAt" },
      "last_activity": { "$max": "$createdAt" }
    }
  },
  {
    "$project": {
      "_id": 0,
      "workflow_id": "$_id",
      "total_actions": 1,
      "create_node": 1,
      "update_node": 1,
      "delete_node": 1,
      "user_count": { "$size": "$users" },
      "node_type_count": { "$size": "$node_types_used" },
      "first_activity": 1,
      "last_activity": 1
    }
  },
  { "$sort": { "total_actions": -1 } }
]
