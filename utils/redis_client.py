import redis

r = redis.Redis(host="localhost", port=6379, db=0)

ACTIVE_INGEST_KEY = "rag:active_ingest:{user_name}"


def set_active_ingest(user_name: str, ingest_id: str) -> None:
    r.set(ACTIVE_INGEST_KEY.format(user_name=user_name), ingest_id)


def get_active_ingest_id(user_name: str) -> str | None:
    raw = r.get(ACTIVE_INGEST_KEY.format(user_name=user_name))
    if raw is None:
        return None
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
