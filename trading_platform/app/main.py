from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
from app.api.v1.router import router as v1_router
from app.core.database import engine, Base
from app.services.order_processor import start_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start background worker
    asyncio.create_task(start_worker())
    yield

app = FastAPI(title="Trading Platform API", lifespan=lifespan)
app.include_router(v1_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}