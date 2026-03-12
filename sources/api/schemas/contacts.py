from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.data_base.models import RelationshipType


class ContactCardBase(BaseModel):
    """Общие поля карточки контакта."""

    full_name: str = Field(..., description="Полное имя")
    address: str | None = Field(None, description="Адрес")
    phone: str | None = Field(None, description="Телефон")
    email: str | None = Field(None, description="Email")
    socials: dict | None = Field(default_factory=dict, description="Социальные сети и контакты (JSON)")

    first_met_at: datetime | None = Field(None, description="Дата и время знакомства")
    first_met_place: str | None = Field(None, description="Место знакомства")
    first_met_context: str | None = Field(None, description="Обстоятельства знакомства")

    relationship_type: RelationshipType | None = Field(None, description="Тип отношений")
    projects_notes: str | None = Field(None, description="Проекты и договоренности")

    hobbies: list | None = Field(default_factory=list, description="Хобби (список)")
    interests: list | None = Field(default_factory=list, description="Интересы (список)")

    family_status: str | None = Field(None, description="Семейное положение")
    birthday: date | None = Field(None, description="День рождения")

    last_contact_at: datetime | None = Field(None, description="Дата последнего контакта")
    last_contact_summary: str | None = Field(None, description="Заметка о последнем контакте")

    promises: list | None = Field(default_factory=list, description="Обещания и упоминания (список)")
    recommendations: str | None = Field(None, description="Рекомендации и мнения")
    competence_rating: int | None = Field(None, description="Оценка компетенций (1-5)")
    competence_notes: str | None = Field(None, description="Комментарий к оценке компетенций")

    goals: list | None = Field(default_factory=list, description="Цели и амбиции (список)")
    ambitions: str | None = Field(None, description="Амбиции и планы")


class ContactCardCreate(ContactCardBase):
    """Запрос на создание карточки контакта."""


class ContactCardUpdate(BaseModel):
    """Запрос на обновление карточки контакта."""

    full_name: str | None = Field(None, description="Полное имя")
    address: str | None = Field(None, description="Адрес")
    phone: str | None = Field(None, description="Телефон")
    email: str | None = Field(None, description="Email")
    socials: dict | None = Field(None, description="Социальные сети и контакты (JSON)")

    first_met_at: datetime | None = Field(None, description="Дата и время знакомства")
    first_met_place: str | None = Field(None, description="Место знакомства")
    first_met_context: str | None = Field(None, description="Обстоятельства знакомства")

    relationship_type: RelationshipType | None = Field(None, description="Тип отношений")
    projects_notes: str | None = Field(None, description="Проекты и договоренности")

    hobbies: list | None = Field(None, description="Хобби (список)")
    interests: list | None = Field(None, description="Интересы (список)")

    family_status: str | None = Field(None, description="Семейное положение")
    birthday: date | None = Field(None, description="День рождения")

    last_contact_at: datetime | None = Field(None, description="Дата последнего контакта")
    last_contact_summary: str | None = Field(None, description="Заметка о последнем контакте")

    promises: list | None = Field(None, description="Обещания и упоминания (список)")
    recommendations: str | None = Field(None, description="Рекомендации и мнения")
    competence_rating: int | None = Field(None, description="Оценка компетенций (1-5)")
    competence_notes: str | None = Field(None, description="Комментарий к оценке компетенций")

    goals: list | None = Field(None, description="Цели и амбиции (список)")
    ambitions: str | None = Field(None, description="Амбиции и планы")


class ContactCardResponse(ContactCardBase):
    """Ответ с карточкой контакта."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ContactCardListResponse(BaseModel):
    """Список карточек с пагинацией."""

    items: list[ContactCardResponse]
    total: int
    page: int
    per_page: int
