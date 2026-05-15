import redis

from app.core.config import get_settings

settings = get_settings()


def get_redis_client() -> redis.Redis:
    return redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


def check_redis() -> dict:
    try:
        client = get_redis_client()
        pong = client.ping()
        return {
            "status": "ok",
            "detail": f"redis connected, ping={pong}",
        }
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
        }
