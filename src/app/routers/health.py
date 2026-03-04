from fastapi import APIRouter, HTTPException
from .. import db
from ..storage import storage
from ..config import settings
import redis.asyncio as redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Basic health check"""
    return {"status": "ok"}


@router.get("/health/db")
async def health_db():
    """Check database connectivity"""
    try:
        result = await db.fetchrow("SELECT 1 as test")
        if result and result["test"] == 1:
            return {"status": "ok", "database": "connected"}
        return {"status": "error", "database": "unexpected_result"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@router.get("/health/minio")
async def health_minio():
    """Check MinIO connectivity"""
    try:
        # List buckets to verify connection
        buckets = storage.client.list_buckets()
        bucket_names = [b.name for b in buckets]
        return {
            "status": "ok",
            "minio": "connected",
            "buckets": bucket_names
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MinIO error: {str(e)}")


@router.get("/health/redis")
async def health_redis():
    """Check Redis connectivity"""
    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis error: {str(e)}")
