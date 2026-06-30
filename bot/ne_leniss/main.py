import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from ne_leniss.config import load_settings
from ne_leniss.db import create_async_engine_from_url, init_db, sessionmaker_from_engine
from ne_leniss.repository import Repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("ne_leniss")


async def main() -> None:
    settings = load_settings()
    engine = create_async_engine_from_url(settings.db_url)
    await init_db(engine)
    log.info("DB initialised: %s", settings.db_url)
    # Repository is wired but bot/api startup lives in later tasks.
    _ = Repository(sessionmaker_from_engine(engine))


if __name__ == "__main__":
    asyncio.run(main())
