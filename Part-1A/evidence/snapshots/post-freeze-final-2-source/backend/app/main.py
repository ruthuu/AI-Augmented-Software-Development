"""Application factory. Importing this module builds `app` but touches no database or folder."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.clock import get_today
from app.core.config import Settings
from app.core.errors import register_error_handlers
from app.db.migrate import initialize_database
from app.routers import budgets, expenses, meta, summary


def create_app(db_path: Path | None = None, today_override: date | None = None) -> FastAPI:
    settings = Settings.from_env()
    database = db_path or settings.db_path

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        initialize_database(database)
        yield

    application = FastAPI(title="SpendWise", lifespan=lifespan)
    application.state.db_path = database
    if today_override is not None:
        application.dependency_overrides[get_today] = lambda: today_override
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(application)
    application.include_router(meta.router)
    application.include_router(expenses.router)
    application.include_router(budgets.router)
    application.include_router(summary.router)
    return application


app = create_app()
