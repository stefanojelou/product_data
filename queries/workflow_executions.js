// MongoDB Query: Workflow execution LOGS by company
// Run in MongoDB Compass > Aggregations tab on: workflow-server.builder.workflow_executions_logs
// Export to JSON, convert to CSV: data/workflow_executions.csv
// Date filter: Nov 15, 2025 onwards
// NOTE: Pre-aggregated table, much faster! Filter for SELF_SERVICE in Python.

[
  {
    "$match": {
      "createdAt": { "$gte": ISODate("2025-11-15T00:00:00.000Z") }
    }
  },
  {
    "$group": {
      "_id": "$company.id",
      "company_name": { "$first": "$company.name" },
      "total_executions": { "$sum": "$total" },
      "completed": { "$sum": "$status.completed" },
      "waiting": { "$sum": "$status.waiting" },
      "processing": { "$sum": "$status.processing" },
      "crashed": { "$sum": "$status.crashed" },
      "skills_used": { "$addToSet": "$skill.name" },
      "first_execution": { "$min": "$createdAt" },
      "last_execution": { "$max": "$createdAt" }
    }
  },
  {
    "$project": {
      "_id": 0,
      "company_id": "$_id",
      "company_name": 1,
      "total_executions": 1,
      "completed": 1,
      "waiting": 1,
      "crashed": 1,
      "skill_count": { "$size": "$skills_used" },
      "first_execution": 1,
      "last_execution": 1
    }
  },
  { "$sort": { "total_executions": -1 } }
]
