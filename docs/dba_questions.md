# Questions for DBA - Connect Product Tables

## Context

We're analyzing product usage for SELF_SERVICE signups (Nov 15, 2025 onwards) and found that:
- **89% of signups never execute a workflow** (Brain Studio)
- **32% start a Connect trial**, but only **2.8% convert to paid**

To understand Connect product engagement, we need data on what users actually do within Connect.

---

## Questions

### 1. Templates Table

**Question:** Is there a `templates` table that tracks template creation/usage?

We want to know:
- Do Connect trial users create templates?
- Which templates do they use?
- How many templates per company?

**Possible table names:**
- `chatbot.templates`
- `billing.templates`
- `chatbot.message_templates`

**Ideal columns:**
```sql
SELECT 
    id,
    company_id,
    name,
    type,
    status,
    created_at,
    updated_at
FROM templates
WHERE created_at >= '2025-11-15'
ORDER BY created_at DESC;
```

---

### 2. Campaigns Table

**Question:** Is there a `campaigns` or `broadcasts` table?

We want to know:
- Do users create campaigns?
- How many campaigns per company?
- Do they send them or just create?

**Possible table names:**
- `chatbot.campaigns`
- `chatbot.broadcasts`
- `chatbot.mass_messages`

**Ideal columns:**
```sql
SELECT 
    id,
    company_id,
    name,
    status,
    recipients_count,
    sent_count,
    created_at,
    sent_at
FROM campaigns
WHERE created_at >= '2025-11-15'
ORDER BY created_at DESC;
```

---

### 3. Operators / Team Members Table

**Question:** Is there a table tracking team member invites?

We want to know:
- Do companies invite team members?
- How many operators per company?
- Are they active?

**Possible table names:**
- `chatbot.operators`
- `chatbot.team_members`
- `chatbot.users` (with company_id)
- `chatbot.company_users`

**Ideal columns:**
```sql
SELECT 
    id,
    company_id,
    user_id,
    role,
    status,
    invited_at,
    last_active_at
FROM operators
WHERE invited_at >= '2025-11-15'
ORDER BY invited_at DESC;
```

---

### 4. UI Event Tracking

**Question:** Is there any table that tracks user clicks/actions in the UI?

We want to know:
- What pages do users visit?
- Where do they click?
- Where do they abandon?

**Possible table names:**
- `analytics.events`
- `chatbot.user_events`
- `analytics.page_views`

This would help us understand the 89% who sign up but never execute a workflow.

---

### 5. Connect Feature Usage

**Question:** What specific features does Connect include, and how are they tracked?

From our understanding, Connect includes:
- Templates
- Campaigns/Broadcasts
- Operators/Team management
- [Others?]

Is there a single table or set of tables that tracks Connect-specific feature usage?

---

## Summary of Data Requests

| Data | Table (if exists) | Priority |
|------|-------------------|----------|
| Template creation/usage | ? | High |
| Campaign creation/sending | ? | High |
| Team member invites | ? | Medium |
| UI event tracking | ? | Medium |
| Connect feature list | Documentation | Low |

---

## Why This Matters

With this data, we can:
1. Build a Connect-specific engagement funnel
2. Understand what trial users actually do
3. Identify why 97% of trials don't convert
4. Make product/onboarding improvements

---

## Contact

If you have questions about this request, please reach out to the product analytics team.

