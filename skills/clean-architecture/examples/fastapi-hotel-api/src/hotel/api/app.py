"""API adapter layer: the FastAPI app factory and the module-level app for uvicorn."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from hotel.api.errors import register_error_handlers
from hotel.api.routers import bookings, rooms
from hotel.infrastructure.db import create_db_engine, create_tables
from hotel.infrastructure.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_db_engine(settings.database_url)
        create_tables(app.state.engine)
        yield
        app.state.engine.dispose()

    app = FastAPI(title="Hotel API", lifespan=lifespan)
    app.include_router(rooms.router)
    app.include_router(bookings.router)
    register_error_handlers(app)
    return app


app = create_app()
