"""Script to manually trigger digest email generation and sending."""

import asyncio

from app.demand.digest import generate_and_send_digest


async def main():
    """Trigger digest email."""
    print("Generating and sending digest email...")
    success = await generate_and_send_digest()

    if success:
        print("✅ Digest email sent successfully!")
    else:
        print("❌ Failed to send digest email.")


if __name__ == "__main__":
    asyncio.run(main())
