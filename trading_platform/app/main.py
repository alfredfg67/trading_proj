from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
import logging
from app.api.v1.router import router as v1_router
from app.core.database import engine, Base
from app.services.order_processor import start_worker
from app.dal.base import DatabaseError
from app.services.mt5_sync import run_mt5_sync_periodically

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(start_worker())
    logger.info("Application startup complete")
    yield

app = FastAPI(title="Trading Platform API", lifespan=lifespan)
app.include_router(v1_router, prefix="/api/v1")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )

@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error", "message": str(exc)}
    )
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing code ...
    asyncio.create_task(run_mt5_sync_periodically(interval_hours=24))
    yield

@app.get("/health")
async def health():
    return {"status": "ok"}