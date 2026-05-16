from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, close_redis, engine, init_redis
from app.routes import api

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await engine.dispose()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(title="Core-Auth", version="1.0.0", lifespan=lifespan)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api)

    if FRONTEND.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")

    return app


app = create_app()
