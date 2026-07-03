import asyncio
import logging
from pathlib import Path

import asyncpg

from .postgres import _dsn

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations() -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = path.read_text()
            await conn.execute(sql)
            logger.info("Applied migration %s", path.name)
    finally:
        await conn.close()


def main() -> None:
    asyncio.run(run_migrations())


if __name__ == "__main__":
    main()
