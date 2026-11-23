"""Expense endpoints: parse the request, call one service function, shape the response."""

import sqlite3
from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.clock import get_today
from app.db.connection import get_connection
from app.schemas.expense import ExpenseIn, ExpenseOut
from app.services import expense_service

router = APIRouter(prefix="/api/expenses")

Connection = Annotated[sqlite3.Connection, Depends(get_connection)]
Today = Annotated[date, Depends(get_today)]


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    conn: Connection, month: str | None = None, category: str | None = None
) -> list[ExpenseOut]:
    records = expense_service.list_expenses(conn, month, category)
    return [ExpenseOut(**asdict(r)) for r in records]


@router.post("", response_model=ExpenseOut, status_code=201)
def create_expense(payload: ExpenseIn, conn: Connection, today: Today) -> ExpenseOut:
    return ExpenseOut(**asdict(expense_service.create(conn, payload, today)))


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int, payload: ExpenseIn, conn: Connection, today: Today
) -> ExpenseOut:
    return ExpenseOut(**asdict(expense_service.update(conn, expense_id, payload, today)))


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int, conn: Connection) -> Response:
    expense_service.delete(conn, expense_id)
    return Response(status_code=204)
