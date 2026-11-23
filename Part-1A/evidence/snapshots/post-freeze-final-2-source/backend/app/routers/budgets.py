"""PUT /api/budgets/{month}: create or replace the budget for one month."""

import sqlite3
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from app.db.connection import get_connection
from app.schemas.budget import BudgetIn, BudgetOut
from app.services import budget_service

router = APIRouter(prefix="/api/budgets")

Connection = Annotated[sqlite3.Connection, Depends(get_connection)]


@router.put("/{month}", response_model=BudgetOut)
def put_budget(month: str, payload: BudgetIn, conn: Connection) -> BudgetOut:
    return BudgetOut(**asdict(budget_service.save_budget(conn, month, payload)))
