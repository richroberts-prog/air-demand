#!/usr/bin/env python3
"""Force rescore all roles with updated scoring algorithm.

This script rescores ALL roles regardless of whether they have existing scores.
Use this after making changes to the scoring algorithm.
"""

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.demand.models import JobCompany, Role
from app.demand.service import classify_and_score_role

logger = get_logger(__name__)


async def rescore_all_roles(limit: int | None = None) -> tuple[int, int]:
    """Rescore all roles.

    Args:
        limit: Optional limit for testing.

    Returns:
        Tuple of (scored_count, error_count).
    """
    scored_count = 0
    error_count = 0

    async with AsyncSessionLocal() as db:
        # Get all roles (not just unscored)
        stmt = select(Role)
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        roles = result.scalars().all()
        total = len(roles)

        logger.info(
            "rescore.started",
            total_roles=total,
            limit=limit,
        )

        for idx, role in enumerate(roles, start=1):
            try:
                # Get company
                company_stmt = select(JobCompany).where(JobCompany.id == role.company_id)
                company_result = await db.execute(company_stmt)
                company = company_result.scalar_one()

                # Classify and score
                await classify_and_score_role(db, role, company)
                await db.commit()
                scored_count += 1

                if idx % 50 == 0:
                    logger.info(
                        "rescore.progress",
                        scored=scored_count,
                        errors=error_count,
                        total=total,
                        pct=round(idx / total * 100, 1),
                    )

            except Exception as e:
                error_count += 1
                logger.error(
                    "rescore.role_failed",
                    role_id=role.id,
                    role_title=role.title,
                    error=str(e),
                    exc_info=True,
                )
                await db.rollback()
                continue

        logger.info(
            "rescore.completed",
            scored=scored_count,
            errors=error_count,
            total=total,
        )

    return scored_count, error_count


async def main() -> None:
    """Main entry point."""
    import sys

    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        print(f"Rescoring up to {limit} roles...")
    else:
        print("Rescoring ALL roles...")

    scored, errors = await rescore_all_roles(limit=limit)

    print("\n✅ Rescore complete!")
    print(f"   Scored: {scored}")
    print(f"   Errors: {errors}")

    if errors > 0:
        print(f"\n⚠️  {errors} roles failed to score. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
