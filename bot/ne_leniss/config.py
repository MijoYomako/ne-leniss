import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

DEFAULT_TZ = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_url: str
    port: int
    webapp_url: str
    debug_bypass_auth: bool


def load_settings() -> Settings:
    return Settings(
        bot_token=os.environ["BOT_TOKEN"],
        db_url=os.environ.get("DB_URL", "sqlite+aiosqlite:///data/state.sqlite"),
        port=int(os.environ.get("PORT", "8000")),
        webapp_url=os.environ.get("WEBAPP_URL", "http://localhost:5173"),
        debug_bypass_auth=os.environ.get("DEBUG_BYPASS_AUTH", "0") == "1",
    )
