import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from . import config
from .database import Base, engine, SessionLocal
from .routers import public, auth, staff
from . import services


async def _scheduler():
    while True:
        await asyncio.sleep(config.ESCALATION_CHECK_SECONDS)
        with SessionLocal() as db:
            services.run_escalation_checks(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    task = asyncio.create_task(_scheduler())
    yield
    task.cancel()


app = FastAPI(title="Saagi SyncCampus API", version="0.1.0", lifespan=lifespan)
if config.FRONTEND_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.FRONTEND_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(staff.router)

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
@app.get("/health")
def health():
    return {"status": "ok"}


if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")
