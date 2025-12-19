---
applies_to: demand
---

# Jobs Feature (Demand Side)

**Paraform Scraper - Role Discovery & Scoring**

---

## Overview

Automated demand-side pipeline for identifying, enriching, and scoring live recruitment roles from Paraform.

**Runs:** Twice daily (6am, 6pm UK time)
**Output:** Scored roles + email digest
**Storage:** PostgreSQL (shared with recruiting pipeline)

---

## Scoring System (0.00-1.00 Scale)

### Engineer Attractiveness
- Compensation (30%)
- Tech Stack (25%)
- Company Prestige (25%)
- Impact Potential (20%)

### Recruiter Attractiveness  
- Commission Value (40%)
- Company Reputation (20%)
- Role Urgency (20%)
- Exclusivity (20%)

### Combined Score & Tiers
```
combined_score = (engineer_score + recruiter_score) / 2

>= 0.80  HOT
0.60-0.79  WARM
0.40-0.59  LUKEWARM
< 0.40  COLD
```

---

## Structure

```
app/jobs/
├── models.py        # Role, RoleScrapeRun, RoleChange
├── schemas.py       # Pydantic models
├── routes.py        # API endpoints
├── service.py       # Business logic
├── scraper/
│   ├── auth.py      # Paraform session management
│   ├── extractors.py # Page scraping logic
│   └── orchestrator.py # Scrape coordination
└── scoring/
    └── engine.py    # Score calculation
```

---

## Integration Points

- **Shared Company Model:** `app/shared/models.py` (both recruiting + jobs enrich)
- **LLM Client:** `app/core/llm.py` (reuse OpenRouter)
- **Scheduling:** APScheduler (6am/6pm UK time)

---

**Status:** Structure created, ready for models + scraper implementation
