from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.data_base.models import RelationshipType


class ContactCardBase(BaseModel):
    """Общие поля карточки контакта."""

    full_name: str = Field(..., max_length=255, description="Полное имя")
    address: str | None = Field(None, description="Адрес")
    phone: str | None = Field(None, max_length=50, description="Телефон")
    email: str | None = Field(None, max_length=255, description="Email")
    # Используем строку вместо enum, чтобы не падать на старых/нестандартных значениях.
    # На уровне БД по-прежнему храним строку с ожидаемыми значениями.
    relationship_type: str | None = Field(None, max_length=20, description="Тип отношений (business/personal/other или произвольная строка)")

    hobbies: list | None = Field(default_factory=list, description="Хобби (список)")
    interests: list | None = Field(default_factory=list, description="Интересы (список)")

    family_status: str | None = Field(None, max_length=100, description="Семейное положение")
    birthday: date | None = Field(None, description="День рождения")

    promises: list | None = Field(default_factory=list, description="Обещания и упоминания (список агрегированных обещаний по всем взаимодействиям)")
    goals: list | None = Field(default_factory=list, description="Цели и амбиции (список)")
    ambitions: str | None = Field(None, description="Амбиции и планы")


class ContactCardCreate(ContactCardBase):
    """Запрос на создание карточки контакта."""


class ContactCardUpdate(BaseModel):
    """Запрос на обновление карточки контакта."""

    full_name: str | None = Field(None, max_length=255, description="Полное имя")
    address: str | None = Field(None, description="Адрес")
    phone: str | None = Field(None, max_length=50, description="Телефон")
    email: str | None = Field(None, max_length=255, description="Email")

    # Для частичного обновления также принимаем произвольную строку/None без enum-валидации
    relationship_type: str | None = Field(None, max_length=20, description="Тип отношений (business/personal/other или произвольная строка)")

    hobbies: list | None = Field(None, description="Хобби (список)")
    interests: list | None = Field(None, description="Интересы (список)")

    family_status: str | None = Field(None, max_length=100, description="Семейное положение")
    birthday: date | None = Field(None, description="День рождения")

    promises: list | None = Field(None, description="Обещания и упоминания (список агрегированных обещаний по всем взаимодействиям)")
    goals: list | None = Field(None, description="Цели и амбиции (список)")
    ambitions: str | None = Field(None, description="Амбиции и планы")


def _ensure_list(value):  # noqa: ANN001
    """Нормализует значение из БД (None, строка и т.д.) в list для полей-списков."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            import json
            return json.loads(value) if value.strip() else []
        except Exception:
            return []
    return list(value) if hasattr(value, "__iter__") else []


class ContactCardResponse(ContactCardBase):
    """Ответ с карточкой контакта."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    last_interaction_at: datetime | None = Field(None, description="Дата последнего взаимодействия")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("hobbies", "interests", "promises", "goals", mode="before")
    @classmethod
    def coerce_list(cls, v):
        return _ensure_list(v)


class ContactCardListResponse(BaseModel):
    """Список карточек с пагинацией."""

    items: list[ContactCardResponse]
    total: int
    page: int
    per_page: int


class ContactLinkBase(BaseModel):
    """Базовые поля связи между контактами."""

    relationship_type: str = Field(..., max_length=50, description="Тип связи: spouse/friend/colleague/parent/child/other")
    context: str | None = Field(None, description="Контекст связи")
    is_directed: bool = Field(False, description="Флаг направления (True — направленная, False — симметричная)")


class ContactLinkCreate(ContactLinkBase):
    """Создание связи: в path передаётся contact_id_a, в теле — contact_id_b."""

    contact_id_b: UUID = Field(..., description="ID второго контакта")


class ContactLinkUpdate(BaseModel):
    """Частичное обновление связи."""

    relationship_type: str | None = Field(None, max_length=50, description="Тип связи")
    context: str | None = Field(None, description="Контекст связи")
    is_directed: bool | None = Field(None, description="Флаг направления")


class ContactLinkResponse(ContactLinkBase):
    """Ответ по связи между контактами."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    contact_id_a: UUID
    contact_id_b: UUID


class ContactInteractionBase(BaseModel):
    """Базовые поля взаимодействия."""

    occurred_at: datetime = Field(..., description="Дата и время взаимодействия")
    channel: str | None = Field(None, max_length=50, description="Канал общения (встреча/звонок/сообщение)")
    notes: str | None = Field(None, description="Заметки о встрече")
    promises: list | None = Field(default_factory=list, description="Обещания/упоминания (сырые данные по взаимодействию)")
    mentions: list | None = Field(default_factory=list, description="Темы и упоминания (список)")


class ContactInteractionCreate(ContactInteractionBase):
    """Создание взаимодействия: contact_id берётся из path."""


class ContactInteractionUpdate(BaseModel):
    """Частичное обновление взаимодействия."""

    occurred_at: datetime | None = Field(None, description="Дата и время взаимодействия")
    channel: str | None = Field(None, max_length=50, description="Канал общения (встреча/звонок/сообщение)")
    notes: str | None = Field(None, description="Заметки о встрече")
    promises: list | None = Field(None, description="Обновлённый список обещаний")
    mentions: list | None = Field(None, description="Обновлённый список упоминаний")


class PromiseUpdate(BaseModel):
    """Частичное обновление отдельного обещания."""

    text: str | None = Field(None, description="Новый текст обещания")
    direction: str | None = Field(None, description="Направление: mine | theirs")


class ContactInteractionResponse(ContactInteractionBase):
    """Ответ по взаимодействию."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
