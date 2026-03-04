from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import db
from .routers import health, auth, doctor, patient, family, notifications

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(doctor.router)
app.include_router(patient.router)
app.include_router(family.router)
app.include_router(notifications.router)


@app.on_event("startup")
async def startup():
    await db.init_db()


@app.on_event("shutdown")
async def shutdown():
    await db.close_db()
