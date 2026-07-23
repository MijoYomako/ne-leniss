import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

DEFAULT_TZ = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_url: str
    host: str
    port: int
    webapp_url: str
    debug_bypass_auth: bool
    enable_debug_commands: bool


def load_settings() -> Settings:
    return Settings(
        bot_token=os.environ["BOT_TOKEN"],
        db_url=os.environ.get("DB_URL", "sqlite+aiosqlite:///data/state.sqlite"),
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        webapp_url=os.environ.get("WEBAPP_URL", "http://localhost:5173"),
        debug_bypass_auth=os.environ.get("DEBUG_BYPASS_AUTH", "0") == "1",
        # /seed, /reset_onboarding, /trigger_morning wipe or fabricate user
        # data — off by default so a real user can't nuke their history.
        enable_debug_commands=os.environ.get("ENABLE_DEBUG_COMMANDS", "0") == "1",
    )
