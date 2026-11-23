"""GET /api/summary: monthly dashboard figures and budget status."""

import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.clock import get_today
from app.db.connection import get_connection
from app.schemas.summary import SummaryOut
from app.services import summary_service

router = APIRouter(prefix="/api")

Connection = Annotated[sqlite3.Connection, Depends(get_connection)]
Today = Annotated[date, Depends(get_today)]


@router.get("/summary", response_model=SummaryOut)
def read_summary(conn: Connection, today: Today, month: str | None = None) -> SummaryOut:
    return summary_service.summarize(conn, month, today)
