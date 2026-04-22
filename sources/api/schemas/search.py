"""Схемы ответа для полнотекстового поиска."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SearchContactHit(BaseModel):
    """Найденный контакт."""

    id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    relationship_type: str | None = None
    rank: float = Field(..., description="Релевантность (ts_rank_cd)")
    snippet: str | None = Field(None, description="Подсвеченный фрагмент (ts_headline)")


class SearchInteractionHit(BaseModel):
    """Найденное взаимодействие."""

    id: UUID
    contact_id: UUID
    contact_full_name: str
    occurred_at: datetime
    channel: str | None = None
    rank: float = Field(..., description="Релевантность (ts_rank_cd)")
    snippet: str | None = Field(None, description="Подсвеченный фрагмент (ts_headline)")


class SearchResponse(BaseModel):
    """Ответ полнотекстового поиска."""

    query: str
    total: int
    contacts: list[SearchContactHit] = Field(default_factory=list)
    interactions: list[SearchInteractionHit] = Field(default_factory=list)
