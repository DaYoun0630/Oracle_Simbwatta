from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import db
from .routers import health, auth, doctor, patient, family, notifications

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 DB 연결
    await db.init_db()
    yield
    # 종료 시 DB 연결 해제
    await db.close_db()

app = FastAPI(title=settings.app_name, lifespan=lifespan)

# CORS 설정 (프론트엔드 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중에는 모든 출처 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(doctor.router)
app.include_router(patient.router)
app.include_router(family.router)
app.include_router(notifications.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "mci-api"}
