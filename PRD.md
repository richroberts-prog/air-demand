---
document_type: product_requirements
purpose: Define what Air Demand does, who it serves, and what success looks like
status: draft
version: 1.0
last_updated: 2025-12-19
owner: product
related:
  - .claude/tasks/IMPLEMENTATION_PLAN.md
  - docs/architecture/
---

# Product Requirements Document: Air Demand

## Overview

Continuously discover, evaluate, and surface high-quality recruiting opportunities from Paraform marketplace. Deliver curated intelligence to headhunters via daily digest.

---

## Problem

**Challenge**: Headhunters waste time scanning hundreds of roles to find the few worth pursuing.

**Without Air Demand:**
- Manual screening of 300+ roles daily
- Manual company research (investors, funding, credibility)
- Manual profitability calculation
- Miss opportunities due to information overload

**With Air Demand:**
- Daily digest of 20-50 qualified roles
- Pre-researched company intelligence
- Pre-calculated scores (profitability, appeal, momentum)
- Trending signals (🔥 surging, ⚠️ stalled)

---

## User

**Elite Headhunter** - Experienced recruiter focused on high-salary engineering placements

**Needs:**
- Pre-qualified opportunities (location, salary, commission filters applied)
- Company intelligence (investors, funding, team pedigree)
- Profitability signals (salary × commission ÷ competition)
- Trend indicators (interview activity)

**Doesn't Need:**
- Roles outside NYC/London/US Remote
- Roles <$200K salary or <14% commission
- Non-engineering roles
- Every role on marketplace (signal vs noise)

---

## Core Capabilities

### 1. Continuous Discovery
- Monitor Paraform marketplace 2x daily
- Capture new roles within hours of posting
- Detect changes (salary, commission, hiring activity)
- Track lifecycle (active → filled → removed)

### 2. Intelligent Qualification

**Hard Filters** (must pass all):
- Geography: NYC, London, or US Remote
- Salary: ≥$200K
- Commission: ≥14%
- Role type: Core engineering (backend, full-stack, embedded, infrastructure)
- Status: Active and accepting recruiters

**Quality Signals** (3+ for QUALIFIED):
- Tier-1 investor backing
- Well-funded (recent raises)
- Company stage/size sweet spot
- Manager/team quality indicators

### 3. Multi-Dimensional Scoring

**Engineer Score**: What top 1% engineers want
- Tier-1 investors, hot company, modern tech stack, impactful work, strong team

**Headhunter Score**: Profitability
- High salary × commission ÷ competition

**Excitement Score**: Company momentum
- Recent funding, team pedigree (ex-FAANG), mission/market timing

**Combined Score**: Weighted average for ranking

### 4. Context Enrichment

**LLM-Extracted Intelligence**:
- Investor/angel identification
- Funding signals (raises, total raised, valuation)
- Team pedigree (ex-FAANG, notable founders)
- Technology stack and product details

**Comprehensive Briefings** (for top-scored roles):
- Problem context (what they're building, why)
- Credibility signals (why engineers should care)
- Day-to-day expectations
- Requirements and qualifications
- Interview process details

### 5. Temporal Intelligence

**Track Over Time**:
- When posted, salary/commission changes
- Interview activity (interviewing, hired)
- Competition changes

**Trend Indicators**:
- 🔥 **Surging**: Interview activity increasing (hot opportunity)
- ⚠️ **Stalled**: No recent progress (red flag)
- ✅ **Hired**: Recent placements (reduced urgency)

### 6. Daily Intelligence Delivery

**Email Digest** (weekday mornings):
- Top qualified roles (sorted by score)
- New roles since last digest
- Material changes (salary increases, hiring surges)
- Hot roles (trending up)

**Dashboard**:
- Browse all qualified roles
- Filter by score, location, company
- View detailed briefings
- Track changes over time

---

## Success Criteria

**Feature Parity**: Replicate all current functionality
- Scrapes Paraform 2x daily
- Qualifies roles (hard filters + quality signals)
- Scores roles (engineer, headhunter, excitement)
- Enriches with LLM intelligence
- Generates briefings for top roles
- Tracks changes over time
- Delivers daily digest
- Provides dashboard

**Data Accuracy**:
- Qualification matches expert judgment (>95%)
- Enrichment extracts correct information
- Change detection identifies all material updates
- Briefings are accurate and relevant

**Operational Reliability**:
- Scrapes succeed >99% of the time
- Daily digest delivers on schedule
- No data loss or corruption
- Graceful handling of external service failures

**User Value**:
- Saves 2+ hours daily on manual screening
- Increases placement rate (better opportunities)
- Faster response time on high-value roles

---

## Priorities

**P0 - Must Have**:
- Discovery (continuous Paraform monitoring)
- Qualification (hard filters)
- Scoring (multi-dimensional)
- Delivery (daily digest email)
- Reliability (automated scraping/digest)

**P1 - Should Have**:
- Enrichment (LLM intelligence)
- Briefings (comprehensive profiles)
- Temporal tracking (change detection, trends)
- Dashboard (web interface)

**P2 - Nice to Have**:
- Advanced analytics
- Personalization (per-user preferences)
- Real-time notifications
- CRM integration/API

---

## Out of Scope

- Supply-side integration (candidate matching)
- CRM functionality (deal tracking, pipeline)
- Candidate outreach (email templates, messaging)
- Placement tracking (offers, commissions)
- Multi-marketplace (beyond Paraform)
