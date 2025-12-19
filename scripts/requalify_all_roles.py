#!/usr/bin/env python3
"""Re-qualify all active roles with current qualification logic.

Use this after changing qualification rules (e.g., location filtering, salary thresholds).
Updates qualification_tier and disqualification_reasons for all ACTIVE roles.
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.demand.models import Role
from app.demand.qualification import qualify_role

logger = get_logger(__name__)


async def requalify_all_roles() -> None:
    """Re-qualify all active roles with current logic."""
    logger.info("requalify.started")

    async with AsyncSessionLocal() as db:
        # Fetch all active roles
        stmt = select(Role).where(Role.lifecycle_status == "ACTIVE")
        result = await db.execute(stmt)
        roles = result.scalars().all()

        logger.info("requalify.roles_found", count=len(roles))

        updated = 0
        disqualified = 0

        for role in roles:
            # Run current qualification logic
            qual_result = qualify_role(role.raw_response)

            # Track if status changed
            old_tier = role.qualification_tier
            new_tier = qual_result.tier

            # Update role
            role.qualification_tier = new_tier
            role.qualification_reasons = qual_result.reasons
            role.disqualification_reasons = qual_result.disqualifications
            role.updated_at = datetime.now(UTC)

            if old_tier != new_tier:
                updated += 1
                if new_tier == "SKIP" and old_tier in ("QUALIFIED", "MAYBE"):
                    disqualified += 1
                    logger.info(
                        "requalify.role_disqualified",
                        paraform_id=role.paraform_id,
                        company=role.company_name,
                        old_tier=old_tier,
                        new_tier=new_tier,
                        reasons=qual_result.disqualifications,
                    )

        # Commit all updates
        await db.commit()

        logger.info(
            "requalify.completed",
            total_roles=len(roles),
            updated=updated,
            disqualified=disqualified,
        )

        print("\n✅ Requalification complete!")
        print(f"   Total roles: {len(roles)}")
        print(f"   Updated: {updated}")
        print(f"   Newly disqualified: {disqualified}")


if __name__ == "__main__":
    asyncio.run(requalify_all_roles())
