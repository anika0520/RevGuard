"""Copilot endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Body

from ..ai.copilot import SUGGESTIONS, answer
from .common import ok

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


@router.post("/ask")
def ask(question: str = Body(..., embed=True)):
    return ok(answer(question))


@router.get("/suggestions")
def suggestions():
    return ok(SUGGESTIONS)
