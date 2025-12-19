"""Re-qualify existing roles after qualification logic changes.

Use when:
- Changing qualification gates (e.g., removing hiring_count check)
- Adjusting thresholds (salary, commission)
- Fixing qualification bugs

Does NOT:
- Fetch new roles from Paraform
- Call detail API
- Run LLM enrichment
- Update raw_response

Usage:
    uv run python -m app.jobs.scripts.requalify_roles [--tier SKIP] [--limit 100]
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import get_db
from app.demand.models import Role
from app.demand.qualification import qualify_role


async def requalify_roles(tier_filter: str | None = None, limit: int | None = None) -> None:
    """Re-qualify existing roles without scraping/enrichment.

    Args:
        tier_filter: Optional qualification tier to filter by (SKIP, MAYBE, QUALIFIED)
        limit: Optional limit on number of roles to process
    """
    async for db in get_db():
        # Build query
        stmt = select(Role).where(Role.lifecycle_status == "ACTIVE")
        if tier_filter:
            stmt = stmt.where(Role.qualification_tier == tier_filter)
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        roles = result.scalars().all()

        print(f"Requalifying {len(roles)} roles...")

        changed_count = 0
        for idx, role in enumerate(roles, 1):
            # Re-run qualification on existing raw_response
            qualification = qualify_role(role.raw_response)

            old_tier = role.qualification_tier
            role.is_qualified = qualification.is_qualified
            role.qualification_tier = qualification.tier
            role.qualification_reasons = qualification.reasons
            role.disqualification_reasons = qualification.disqualifications

            if old_tier != qualification.tier:
                changed_count += 1
                print(f"  {role.title}: {old_tier} → {qualification.tier}")

            if idx % 100 == 0:
                print(f"  Progress: {idx}/{len(roles)}")

        await db.commit()
        print(f"✓ Requalified {len(roles)} roles, {changed_count} changed tier")
        break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", help="Filter by qualification tier (SKIP, MAYBE, QUALIFIED)")
    parser.add_argument("--limit", type=int, help="Limit number of roles to process")
    args = parser.parse_args()

    asyncio.run(requalify_roles(args.tier, args.limit))
