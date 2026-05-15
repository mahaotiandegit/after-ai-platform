from fastapi import APIRouter

from app.db.redis_client import check_redis
from app.db.session import check_database

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
def system_health():
    database = check_database()
    redis = check_redis()

    overall_status = "ok"
    if database["status"] != "ok" or redis["status"] != "ok":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "services": {
            "database": database,
            "redis": redis,
        },
    }
