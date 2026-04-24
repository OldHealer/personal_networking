# ------------------------------------------------------------------------
# Команды для Alembic:
#   Инициализация Alembic с поддержкой асинхронного взаимодействия с базой данных
#   alembic init -t async migration
#
#   Создаём файл миграции
#   alembic revision --autogenerate -m "Сообщение"
#
#   Применение миграции
#   alembic upgrade head
#
#   Обновить состояние
#   alembic stamp head
#
#   Если надо откатить только одну последнюю миграцию
#   alembic downgrade -1
#
#   Если надо откатить до конкретного ревизионного номера
#   alembic downgrade НОМЕР РЕВИЗИИ
# ------------------------------------------------------------------------

from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import JSON
from sqlalchemy.inspection import inspect


class Base(AsyncAttrs, DeclarativeBase):
    """Базовая модель с техническими полями времени"""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), doc="Дата и время создания записи")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), doc="Дата и время последнего обновления записи")

    def model_to_dict(self) -> dict:
        """Конвертирует ORM-объект в словарь"""
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class RelationshipType(str, Enum):
    BUSINESS = "business"
    PERSONAL = "personal"
    OTHER = "other"


class Tenant(Base):
    """Арендатор (мультитенантность)."""

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Идентификатор арендатора",)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True, doc="Название арендатора",)

    users: Mapped[list["AppUser"]] = relationship("AppUser", back_populates="tenant", cascade="all, delete-orphan", lazy="selectin",)
    contacts: Mapped[list["ContactCard"]] = relationship("ContactCard", back_populates="tenant", cascade="all, delete-orphan", lazy="selectin",)


class AppUser(Base):
    """Пользователь приложения, связанный с Keycloak."""

    __tablename__ = "app_users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Внутренний идентификатор пользователя",)
    keycloak_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False, doc="Subject (sub) из токена Keycloak",)
    username: Mapped[str | None] = mapped_column(String(255), index=True, doc="Имя пользователя (preferred_username)",)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, doc="Email пользователя (уникальный)",)
    tenant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), index=True, doc="ID арендатора (для мультитенантности, опционально)",)
    tenant: Mapped["Tenant | None"] = relationship("Tenant", back_populates="users", primaryjoin="AppUser.tenant_id == Tenant.id",)

class ContactCard(Base):
    """Карточка контакта (основная сущность)."""

    __tablename__ = "contact_cards"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор контакта",)
    tenant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), index=True, doc="ID арендатора",)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, doc="Полное имя",)
    address: Mapped[str | None] = mapped_column(Text, doc="Адрес")
    phone: Mapped[str | None] = mapped_column(String(50), index=True, doc="Телефон")
    email: Mapped[str | None] = mapped_column(String(255), index=True, doc="Email")
    relationship_type: Mapped[str | None] = mapped_column(String(20), doc="Тип отношений: business/personal/other",)

    hobbies: Mapped[list | None] = mapped_column(JSON, default=list, doc="Хобби (список)",)
    interests: Mapped[list | None] = mapped_column(JSON, default=list, doc="Интересы (список)",    )

    family_status: Mapped[str | None] = mapped_column(String(100), doc="Семейное положение",)
    birthday: Mapped[date | None] = mapped_column( Date, doc="День рождения",)

    promises: Mapped[list | None] = mapped_column(JSON, default=list, doc="Обещания и упоминания (список)", )
    goals: Mapped[list | None] = mapped_column(JSON, default=list, doc="Цели и амбиции (список)",)
    ambitions: Mapped[str | None] = mapped_column(Text, doc="Амбиции и планы",)

    family_members: Mapped[list["ContactFamilyMember"]] = relationship("ContactFamilyMember", back_populates="contact", cascade="all, delete-orphan", lazy="selectin",)
    interactions: Mapped[list["ContactInteraction"]] = relationship("ContactInteraction", back_populates="contact", cascade="all, delete-orphan", lazy="selectin",)
    tenant: Mapped["Tenant | None"] = relationship("Tenant", back_populates="contacts", primaryjoin="ContactCard.tenant_id == Tenant.id",)
    links_from: Mapped[list["ContactLink"]] = relationship(
            "ContactLink",
            foreign_keys="ContactLink.contact_id_a",
            back_populates="contact_a",
            cascade="all, delete-orphan",
            lazy="selectin",
        )
    links_to: Mapped[list["ContactLink"]] = relationship(
        "ContactLink",
        foreign_keys="ContactLink.contact_id_b",
        back_populates="contact_b",
        cascade="all, delete-orphan",
        lazy="selectin",
    )



class ContactFamilyMember(Base):
    """Член семьи/близкий человек контакта."""

    __tablename__ = "contact_family_members"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор записи",)
    contact_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("contact_cards.id", ondelete="CASCADE"), index=True, doc="Ссылка на контакт",)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, doc="Имя члена семьи",)
    relation: Mapped[str | None] = mapped_column(String(100), doc="Степень родства")
    birthday: Mapped[date | None] = mapped_column(Date, doc="День рождения")
    notes: Mapped[str | None] = mapped_column(Text, doc="Заметки")

    contact: Mapped["ContactCard"] = relationship("ContactCard", back_populates="family_members", primaryjoin="ContactFamilyMember.contact_id == ContactCard.id",)


class ContactLink(Base):
    """Связь между двумя контактами (граф отношений)."""

    __tablename__ = "contact_links"
    # Запрещаем дубль связи одного типа между одной и той же парой контактов.
    # Для симметричных (is_directed=False) порядок пары нормализуется в сервисе
    # (contact_id_a < contact_id_b как строки), чтобы constraint ловил и обратную сторону.
    __table_args__ = (
        UniqueConstraint("contact_id_a", "contact_id_b", "relationship_type",
                         name="uq_contact_links_pair_type"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Идентификатор связи", )
    tenant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), index=True, doc="ID арендатора", )
    contact_id_a: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("contact_cards.id", ondelete="CASCADE"), index=True, doc="ID первой карточки", )
    contact_id_b: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True),  ForeignKey("contact_cards.id", ondelete="CASCADE"), index=True, doc="ID второй карточки", )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, doc="Тип связи: spouse/friend/colleague/parent/child/other", )
    context: Mapped[str | None] = mapped_column(Text, doc="Контекст связи")
    is_directed: Mapped[bool] = mapped_column(Integer, default=0, doc="Флаг направления (1 — направленная, 0 — симметричная)", )

    contact_a: Mapped["ContactCard"] = relationship("ContactCard", foreign_keys=[contact_id_a], back_populates="links_from", )
    contact_b: Mapped["ContactCard"] = relationship("ContactCard", foreign_keys=[contact_id_b], back_populates="links_to", )


class ContactInteraction(Base):
    """Взаимодействие с контактом (встреча/звонок/сообщение)."""

    __tablename__ = "contact_interactions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор взаимодействия",)
    contact_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("contact_cards.id", ondelete="CASCADE"), index=True, doc="Ссылка на контакт", )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, doc="Дата и время взаимодействия",)
    channel: Mapped[str | None] = mapped_column(String(50), doc="Канал общения (встреча/звонок/сообщение)",)
    notes: Mapped[str | None] = mapped_column(Text, doc="Заметки о встрече")
    promises: Mapped[list | None] = mapped_column(JSON, default=list, doc="Обещания/упоминания (список)",)
    mentions: Mapped[list | None] = mapped_column(JSON, default=list, doc="Темы и упоминания (список)",)

    contact: Mapped["ContactCard"] = relationship("ContactCard", back_populates="interactions", primaryjoin="ContactInteraction.contact_id == ContactCard.id",)
