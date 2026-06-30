import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

log = logging.getLogger("ne_leniss.auth")

MAX_AUTH_AGE_SECONDS = 24 * 60 * 60  # 24h


def verify_init_data(init_data: str, bot_token: str) -> int | None:
    """Verify Telegram WebApp initData HMAC and return user.id or None.

    Per https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data:
        return None
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True)
    except Exception:
        return None
    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if received_hash is None:
        return None

    auth_date_raw = data.get("auth_date")
    if auth_date_raw is not None:
        try:
            auth_date = int(auth_date_raw)
            if abs(time.time() - auth_date) > MAX_AUTH_AGE_SECONDS:
                return None
        except ValueError:
            return None

    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        return None

    user_raw = data.get("user")
    if not user_raw:
        return None
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        return None
    user_id = user.get("id")
    if not isinstance(user_id, int):
        return None
    return user_id
