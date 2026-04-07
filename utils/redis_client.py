import redis

r = redis.Redis(host="localhost", port=6379, db=0)

ACTIVE_INGEST_KEY = "rag:active_ingest:{user_name}"
DEFAULT_USER_NAME = "default"


def set_active_ingest(user_name: str | None, ingest_id: str) -> None:
    user_key = user_name or DEFAULT_USER_NAME
    r.set(ACTIVE_INGEST_KEY.format(user_name=user_key), ingest_id)


def get_active_ingest_id(user_name: str | None) -> str | None:
    user_key = user_name or DEFAULT_USER_NAME
    raw = r.get(ACTIVE_INGEST_KEY.format(user_name=user_key))
    if raw is None:
        return None
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
