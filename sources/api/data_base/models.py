# # ------------------------------------------------------------------------
# # Команды для Alembic:
# #   Инициализация Alembic с поддержкой асинхронного взаимодействия с базой данных
# #   alembic init -t async migration
# #
# #   Создаём файл миграции
# #   alembic revision --autogenerate -m "Сообщение"
# #
# #   Применение миграции
# #   alembic upgrade head
# #
# #   Обновить состояние
# #   alembic stamp head
# #
# #   Если надо откатить только одну последнюю миграцию
# #   alembic downgrade -1
# #
# #   Если надо откатить до конкретного ревизионного номера
# #   alembic downgrade НОМЕР РЕВИЗИИ
# # ------------------------------------------------------------------------
# from datetime import datetime
# from enum import Enum
# from uuid import uuid4, UUID
#
# from typing import Optional, List
# import sqlalchemy
# from sqlalchemy import func, Boolean, Integer, Text, ForeignKey, String, DateTime, UniqueConstraint
# from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
# from sqlalchemy.ext.asyncio import AsyncAttrs
# from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
# from sqlalchemy.inspection import inspect
#
# # ------------------------------------------------------------------------
# # Команды для Alembic:
# #   Инициализация Alembic с поддержкой асинхронного взаимодействия с базой данных
# #   alembic init -t async migration
# #
# #   Создаём файл миграции
# #   alembic revision --autogenerate -m "Сообщение"
# #
# #   Применение миграции
# #   alembic upgrade head
# #
# #   Обновить состояние
# #   alembic stamp head
# #
# #   Если надо откатить только одну последнюю миграцию
# #   alembic downgrade -1
# #
# #   Если надо откатить до конкретного ревизионного номера
# #   alembic downgrade НОМЕР РЕВИЗИИ
# # ------------------------------------------------------------------------
#
# class Base(AsyncAttrs, DeclarativeBase):
#     """
#     Класс для создания моделей таблиц, которые автоматически добавляют поля created_at и updated_at
#     для отслеживания времени создания и обновления записей
#     """
#     created_at: Mapped[datetime] = mapped_column(server_default=func.now(), doc="Дата и время создания записи")
#     updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), doc="Дата и время последнего обновления записи")
#
#     def model_to_dict(self) -> dict:
#         """Метод конвертации объекта БД в python dict"""
#         return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
#
# class LLMMode(str, Enum):
#     CHAT = "chat"
#     COMPLETION = "completion"
#     EMBEDDING = "embedding"
#
# class UserRole(str, Enum):
#     ADMIN = "admin"
#     USER = "user"
#
# class TokenStatus(str, Enum):
#     """
#     Статус токена пользователя.
#
#     Возможные значения:
#     - NO_TOKEN — токен ещё не создан для пользователя.
#     - ACTIVE — токен активен и может использоваться.
#     - BLOCKED — токен заблокирован администратором.
#     - EXPIRED — срок действия токена истёк.
#     - DELETED — токен был удалён пользователем или администратором.
#     """
#     NO_TOKEN = "no_token"
#     ACTIVE = "active"
#     BLOCKED = "blocked"
#     EXPIRED = "expired"
#     DELETED = "deleted"
#
# class LLMModelRegistry(Base):
#     """
#     Модель для хранения информации о моделях ИИ в реестре
#
#     UUID(as_uuid=False) - флаг as_uuid=False, запрещает преобразование строки в объект uuid.UUID
#     """
#     __tablename__ = 'llm_model_registry'
#
#     # Обязательные для заполнения поля
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор LLM в реестре")
#     name: Mapped[str] = mapped_column(Text, nullable=False, index=True, doc="Название модели (например, StarCoder-1B)")
#     version: Mapped[str] = mapped_column(Text, nullable=False, doc="Версия модели (v1.1, и т.д.)")
#     vendor: Mapped[str] = mapped_column(Text, nullable=False, doc="Производитель модели (Meta, Google, MistralAI)")
#     source: Mapped[str] = mapped_column(Text, nullable=False, doc="Тип источника (local, huggingface, url)")
#     s3_key: Mapped[str] = mapped_column(Text, nullable=False, doc="Имя файла или путь до него в S3")
#     parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, doc="Параметры модели в формате {ключ: строковое значение}")
#     metrics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, doc="Метрики модели в формате {ключ: числовое значение}")
#     latest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, doc="Флаг, указывающий, является ли версия последней")
#     modes: Mapped[list[LLMMode]] = mapped_column(ARRAY(String(20)), nullable=False, doc="Доступные режимы работы: chat и/или completion, embedding")
#     # Опциональные поля
#     description: Mapped[str | None] = mapped_column(Text, doc="Описание модели")
#     model_format: Mapped[str | None] = mapped_column(Text, doc="Формат модели (GGUF, SafeTensors и т.д.)")
#     model_size: Mapped[str | None] = mapped_column(Text, doc="Размер модели (7B, 8x7B и т.д.)")
#     provider_url: Mapped[str | None] = mapped_column(Text, doc="Расположение источника (URL или путь)")
#     license_name: Mapped[str | None] = mapped_column(Text, doc="Название лицензии (Apache 2.0, MIT)")
#     license_url: Mapped[str | None] = mapped_column(Text, doc="URL текста лицензии")
#     prompt_template: Mapped[str | None] = mapped_column(Text, doc="Шаблон промта по умолчанию")
#     chat_template: Mapped[str | None] = mapped_column(Text, doc="Шаблон чата (Jinja2 format)")
#     context_length: Mapped[int | None] = mapped_column(Integer, doc="Максимальная длина контекста модели")
#
#     # Связь с кластером
#     cluster_id: Mapped[int | None] = mapped_column(Integer, doc="ID кластера из GPUStack")
#     cluster: Mapped["Cluster | None"] = relationship("Cluster", foreign_keys="[LLMModelRegistry.cluster_id]",
#                                                      primaryjoin="Cluster.cluster_id == LLMModelRegistry.cluster_id",
#                                                      back_populates="llm_models",
#                                                      doc="Кластер, к которому принадлежит модель")
#
#     # Связь с моделью LLMModelInstanceRegistry, отношение один-кo-многим
#     instances: Mapped[list["LLMModelInstanceRegistry"]] = relationship("LLMModelInstanceRegistry", back_populates="llm_model", cascade="all, delete-orphan")
#
# class WorkerModelRegistry(Base):
#     """Модель рабочего узла выполнения ИИ-моделей"""
#     __tablename__ = 'worker_model_registry'
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор")
#     name: Mapped[str] = mapped_column(Text, nullable=False, doc="Название рабочего узла")
#     url: Mapped[str] = mapped_column(Text, nullable=False, doc="API endpoint узла")
#     dashboard_url: Mapped[str] = mapped_column(Text, nullable=False, doc="URL панели узла")
#     hostname: Mapped[str | None] = mapped_column(Text, doc="Имя хоста воркера")
#     ip: Mapped[str | None] = mapped_column(Text, doc="IP адрес воркера")
#     port: Mapped[int | None] = mapped_column(Integer, doc="Порт воркера")
#     metrics_port: Mapped[int | None] = mapped_column(Integer, doc="Порт метрик воркера")
#     state: Mapped[str | None] = mapped_column(String(50), doc="Состояние воркера")
#     gpustack_worker_id: Mapped[int | None] = mapped_column(Integer, doc="ID воркера в GPUStack")
#     gpu_data: Mapped[list[dict] | None] = mapped_column(JSONB, default=list, doc="Список GPU устройств воркера")
#
#     # Связь с кластером
#     cluster_id: Mapped[int | None] = mapped_column(Integer, doc="ID кластера из GPUStack")
#     cluster: Mapped["Cluster | None"] = relationship("Cluster", foreign_keys="[WorkerModelRegistry.cluster_id]",
#                                                      primaryjoin="Cluster.cluster_id == WorkerModelRegistry.cluster_id",
#                                                      back_populates="workers",
#                                                      doc="Кластер, к которому принадлежит воркер")
#
# class LLMModelInstanceRegistry(Base):
#     """Модель инстансов запущенных моделей на рабочих узлах"""
#     __tablename__ = 'llm_model_instance_registry'
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор")
#     mode: Mapped[LLMMode] = mapped_column(String(20), nullable=False, doc="Активный режим работы: chat, completion или embedding")
#     dashboard_url: Mapped[str] = mapped_column(Text, nullable=False, doc="URL мониторинга инстанса")
#     worker_node_ids: Mapped[list[UUID | str] | None] = mapped_column(JSONB, default=None, nullable=True, doc="Список рабочих узлов Erebus, задействованных инстансом")
#     gpu_data_list: Mapped[list[str] | None] = mapped_column(JSONB, default=None, nullable=True, doc="Список выбранных GPU идентификаторов")
#
#     # Связи
#     llm_model_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("llm_model_registry.id"), doc="Внешний ключ к модели LLM")
#     llm_model: Mapped["LLMModelRegistry"] = relationship("LLMModelRegistry", back_populates="instances", lazy="selectin", doc="Связанная языковая модель")
#
#     # Связь с кластером
#     cluster_id: Mapped[int | None] = mapped_column(Integer, doc="ID кластера из GPUStack")
#     cluster: Mapped["Cluster | None"] = relationship("Cluster", foreign_keys="[LLMModelInstanceRegistry.cluster_id]",
#                                                      primaryjoin="Cluster.cluster_id == LLMModelInstanceRegistry.cluster_id",
#                                                      back_populates="llm_instances",
#                                                      doc="Кластер, к которому принадлежит инстанс")
#
#     gpustack_id: Mapped[int] = mapped_column(Integer, doc="ID инстанса модели в GPUStack")
#     # Опциональное поле, для режима "embedding" модель не добавляется в LiteLLM
#     litellm_id: Mapped[str | None] = mapped_column(Text, doc="ID инстанса модели в LiteLLM")
#
#     # Имена из GPUStack
#     replica_name: Mapped[str | None] = mapped_column(Text, doc="Имя реплики инстанса в GPUStack (с суффиксом, соответствует name)")
#     instance_name: Mapped[str | None] = mapped_column(Text, doc="Имя инстанса модели в GPUStack (без суффикса реплики, соответствует model_name)")
#
#
# class PluginModelRegistry(Base):
#     """Модель для хранения информации о плагинах IDE в реестре"""
#     __tablename__ = 'plugin_model_registry'
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор плагина")
#     editor: Mapped[str] = mapped_column(Text, nullable=False, doc="Среда разработки (IDE) плагина: VSCode, IntelliJ")
#     version: Mapped[str] = mapped_column(Text, nullable=False, doc="Версия плагина (v1.1 и т.д.)")
#     latest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, doc="Флаг, указывающий, является ли версия последней")
#     upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, doc="Дата загрузки плагина в формате ISO 8601 (пример 2025-05-14T12:09:56)")
#     s3_key: Mapped[str] = mapped_column(Text, nullable=False, doc="Имя файла или путь до него в S3")
#
# #==================== #
# #  МОДЕЛЬ КЛАСТЕРОВ
# #==================== #
#
# class Cluster(Base):
#     """
#     Модель кластера для управления вычислительными ресурсами
#     """
#     __tablename__ = 'clusters'
#
#     # Обязательные поля
#     id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()), doc="Уникальный идентификатор кластера")
#     cluster_id: Mapped[int] = mapped_column(Integer, doc="ID кластера из GPUStack")
#     name: Mapped[str] = mapped_column(String(255), nullable=False, doc="Название кластера")
#     provider: Mapped[str] = mapped_column(String(50), nullable=False, doc="Провайдер облачных услуг")
#     state: Mapped[str] = mapped_column(String(50), nullable=False, doc="Текущее состояние кластера")
#     # Опциональные поля
#     description: Mapped[str | None] = mapped_column(Text, doc="Описание кластера")
#     credential_id: Mapped[int | None] = mapped_column(Integer, doc="ID учетных данных для доступа к облаку")
#     region: Mapped[str | None] = mapped_column(String(255), doc="Регион размещения кластера")
#     state_message: Mapped[str | None] = mapped_column(Text, doc="Сообщение о состоянии кластера")
#     hashed_suffix: Mapped[str] = mapped_column(String(12), nullable=True, default="not defined", doc="Хешированный суффикс для уникальности")
#     registration_token: Mapped[str] = mapped_column(String(58), nullable=True, default="not defined", doc="Токен регистрации для подключения к кластеру")
#     deleted_at: Mapped[datetime | None] = mapped_column(DateTime, doc="Дата и время удаления (soft delete)")
#     last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, doc="Дата и время последней синхронизации с GPUStack")
#     workers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, doc="Количество воркеров в кластере")
#     ready_workers: Mapped[int] = mapped_column(Integer, nullable=False, default=0, doc="Количество готовых воркеров в кластере")
#     gpus: Mapped[int] = mapped_column(Integer, nullable=False, default=0, doc="Количество GPU в кластере")
#     models: Mapped[int] = mapped_column(Integer, nullable=False, default=0, doc="Количество моделей в кластере")
#
#     # Связи с другими моделями (по cluster_id)
#     llm_models: Mapped[list["LLMModelRegistry"]] = relationship("LLMModelRegistry",
#                                                                 foreign_keys="[LLMModelRegistry.cluster_id]",
#                                                                 primaryjoin="Cluster.cluster_id == LLMModelRegistry.cluster_id",
#                                                                 back_populates="cluster", cascade="all, delete-orphan")
#     llm_instances: Mapped[list["LLMModelInstanceRegistry"]] = relationship("LLMModelInstanceRegistry",
#                                                                            foreign_keys="[LLMModelInstanceRegistry.cluster_id]",
#                                                                            primaryjoin="Cluster.cluster_id == LLMModelInstanceRegistry.cluster_id",
#                                                                            back_populates="cluster",
#                                                                            cascade="all, delete-orphan")
#     workers: Mapped[list["WorkerModelRegistry"]] = relationship("WorkerModelRegistry",
#                                                                 foreign_keys="[WorkerModelRegistry.cluster_id]",
#                                                                 primaryjoin="Cluster.cluster_id == WorkerModelRegistry.cluster_id",
#                                                                 back_populates="cluster", cascade="all, delete-orphan")
#
#
# #==================================================#
# #  МОДЕЛИ ПОЛЬЗОВАТЕЛЕЙ, ГРУПП, ИСТОЧНИКОВ ДАННЫХ
# #==================================================#
#
# class UserModelRegistry(Base):
#     __tablename__ = "user_model_registry"
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4, doc="Уникальный идентификатор пользователя")
#     full_name: Mapped[str] = mapped_column(String(255), nullable=False, doc="Полное имя пользователя для отображения в интерфейсе")
#     email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True, doc="Электронная почта пользователя, используется для уведомлений и восстановления пароля")
#     role: Mapped[str] = mapped_column(String(20), nullable=False)
#     litellm_token: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True, doc="LiteLLM токен")
#     hashed_litellm_token: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True, doc="Хэш LiteLLM токена")
#     litellm_token_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, doc="Дата и время создания записи")
#     litellm_user_id: Mapped[str] = mapped_column(Text, nullable=False, doc="ID пользователя в LiteLLM")
#     group: Mapped[str | None] = mapped_column(Text, doc="Группа")
#     user_limits: Mapped[dict | None] = mapped_column(JSONB, nullable=True, doc="Лимиты пользователя")
#     models: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True, doc="Список доступных моделей пользователю, по умолчанию доступны все")
#     token_status: Mapped[TokenStatus] = mapped_column(String(20), nullable=False, default=TokenStatus.NO_TOKEN.value, doc="Статус токена пользователя")
#
#     memberships: Mapped[List["UserGroupMembership"]] = relationship(
#         "UserGroupMembership",
#         back_populates="user",
#         cascade="all, delete-orphan",
#         overlaps="user_groups"
#     )
#     user_groups: Mapped[List["UserGroup"]] = relationship(
#         "UserGroup",
#         secondary="user_group_memberships",
#         back_populates="user_model_registry",
#         lazy="selectin",
#         viewonly=True,
#         overlaps="memberships,user"
#     )
#
# class UserGroup(Base):
#     __tablename__ = "groups"
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
#     tabby_group_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True, doc="Индивидуальный ID в Tabby")
#     description: Mapped[Optional[str]] = mapped_column(String)
#     is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Флаг системной группы - нельзя удалить через интерфейс")
#     created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
#     updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#
#     memberships: Mapped[List["UserGroupMembership"]] = relationship(
#         "UserGroupMembership",
#         back_populates="group",
#         cascade="all, delete-orphan",
#         passive_deletes=True,
#         overlaps="user_groups"
#     )
#     user_model_registry: Mapped[List["UserModelRegistry"]] = relationship(
#         "UserModelRegistry",
#         secondary="user_group_memberships",
#         back_populates="user_groups",
#         lazy="selectin",
#         viewonly=True,
#         overlaps="memberships,group"
#     )
#     policies: Mapped[List["AccessPolicy"]] = relationship(
#         "AccessPolicy",
#         secondary="policy_groups",
#         back_populates="groups",
#         lazy="selectin",
#         passive_deletes=True,
#     )
#
# class UserGroupMembership(Base):
#     __tablename__ = "user_group_memberships"
#     __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_model_registry.id", ondelete="CASCADE"))
#     group_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"))
#     role_in_group: Mapped[str] = mapped_column(String(20), nullable=False, default="member", doc="Роль в группе (member|owner|admin)")
#     added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
#     user: Mapped["UserModelRegistry"] = relationship("UserModelRegistry", back_populates="memberships", overlaps="user_groups")
#     group: Mapped["UserGroup"] = relationship("UserGroup", back_populates="memberships", overlaps="user_groups")
#
#     @property
#     def is_group_admin(self) -> bool:
#         return self.role_in_group in ("admin", "owner")
#
# class AccessPolicy(Base):
#     __tablename__ = "access_policies"
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
#     description: Mapped[Optional[str]] = mapped_column(String)
#     created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
#     updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#
#     groups: Mapped[List["UserGroup"]] = relationship(
#         "UserGroup",
#         secondary="policy_groups",
#         back_populates="policies",
#         lazy="selectin",
#         passive_deletes = True
#     )
#
#     sources: Mapped[List["Source"]] = relationship(
#         "Source",
#         secondary="policy_sources",
#         back_populates="policies",
#         lazy="selectin",
#         passive_deletes = True
#     )
#
# class PolicyGroup(Base):
#     __tablename__ = "policy_groups"
#     __table_args__ = (UniqueConstraint("policy_id", "group_id", name="uq_policy_group"),)
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     policy_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("access_policies.id", ondelete="CASCADE"))
#     group_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"))
#     assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
#
# class Source(Base):
#     __tablename__ = "sources"
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     name: Mapped[str] = mapped_column(String(255), nullable=False)
#     type: Mapped[str] = mapped_column(String(50), nullable=False, doc="Тип источника данных: git, doc")
#     description: Mapped[Optional[str]] = mapped_column(String)
#     is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
#     proxy_url: Mapped[str | None] = mapped_column(Text, doc="URL для прокси")
#
#     created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
#     updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#
#     policies: Mapped[List["AccessPolicy"]] = relationship(
#         "AccessPolicy",
#         secondary="policy_sources",
#         back_populates="sources",
#         lazy="selectin",
#         passive_deletes=True
#     )
#     __table_args__ = (UniqueConstraint("name", "type", name="uq_sources_name_type"),)
#
#
# class PolicySource(Base):
#     __tablename__ = "policy_sources"
#     __table_args__ = (UniqueConstraint("policy_id", "source_id", name="uq_policy_source"),)
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     policy_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("access_policies.id", ondelete="CASCADE"))
#     source_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"))
#     can_read: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
#     can_write: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
#     can_manage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
#     row_filter: Mapped[Optional[str]] = mapped_column(String)
#     column_mask: Mapped[Optional[str]] = mapped_column(String)
#
# # ======================================#
# #   ДЕТАЛЬНЫЕ МОДЕЛИ ИСТОЧНИКОВ ДАННЫХ
# # ======================================#
#
# class SourceGit(Base):
#     """Параметры подключения к Git-репозиториям (SOURCE_GIT)"""
#     __tablename__ = 'source_git'
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True,
#                                      doc="Ссылка на запись в SOURCES")
#     git_url: Mapped[str] = mapped_column(String(1000), nullable=False, doc="URL Git-репозитория")
#     branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main", doc="Ветка для индексации")
#     access_token: Mapped[str | None] = mapped_column(String(500),
#                                                      doc="Токен доступа для приватных репозиториев (должен быть зашифрован)")
#     ssh_key: Mapped[str | None] = mapped_column(Text, doc="SSH-ключ для доступа к репозиторию (альтернатива токену)")
#     http_headers: Mapped[dict | None] = mapped_column(JSONB,
#                                                       doc="HTTP-заголовки для запросов в формате JSON (например, авторизация)")
#     options: Mapped[dict | None] = mapped_column(JSONB, doc="Дополнительные параметры в формате JSON")
#     proxy_url: Mapped[str | None] = mapped_column(Text, doc="URL для прокси")
#
#
# class SourceDoc(Base):
#     """Параметры для документов по URL (SOURCE_DOC)"""
#     __tablename__ = 'source_doc'
#
#     id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True,
#                                      doc="Ссылка на запись в SOURCES")
#     url: Mapped[str] = mapped_column(String(1000), nullable=False, doc="URL документа для индексации")
#     doc_metadata: Mapped[dict | None] = mapped_column(JSONB,
#                                                       doc="Метаданные документа в формате JSON (тип файла, размер, дата последнего изменения)")
#     http_headers: Mapped[dict | None] = mapped_column(JSONB,
#                                                       doc="HTTP-заголовки для запросов в формате JSON (например, авторизация)")
#     options: Mapped[dict | None] = mapped_column(JSONB, doc="Дополнительные параметры в формате JSON")
#     proxy_url: Mapped[str | None] = mapped_column(Text, doc="URL для прокси")


from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
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
    socials: Mapped[dict | None] = mapped_column(JSON, default=dict, doc="Социальные сети и контакты в формате JSON",)

    first_met_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), doc="Дата и время знакомства",)
    first_met_place: Mapped[str | None] = mapped_column(String(255), doc="Место знакомства",)
    first_met_context: Mapped[str | None] = mapped_column(Text, doc="Обстоятельства знакомства",)

    relationship_type: Mapped[str | None] = mapped_column(String(20), doc="Тип отношений: business/personal/other",)
    projects_notes: Mapped[str | None] = mapped_column(Text, doc="Проекты и договоренности",)

    hobbies: Mapped[list | None] = mapped_column(JSON, default=list, doc="Хобби (список)",)
    interests: Mapped[list | None] = mapped_column(JSON, default=list, doc="Интересы (список)",    )

    family_status: Mapped[str | None] = mapped_column(String(100), doc="Семейное положение",)
    birthday: Mapped[date | None] = mapped_column( Date, doc="День рождения",)

    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), doc="Дата последнего контакта", )
    last_contact_summary: Mapped[str | None] = mapped_column(Text, doc="Краткая заметка о последнем контакте",)

    promises: Mapped[list | None] = mapped_column(JSON, default=list, doc="Обещания и упоминания (список)", )
    recommendations: Mapped[str | None] = mapped_column(Text, doc="Рекомендации и мнения",)
    competence_rating: Mapped[int | None] = mapped_column(Integer, doc="Оценка компетенций (1-5)",    )
    competence_notes: Mapped[str | None] = mapped_column(Text, doc="Комментарий к оценке компетенций",    )

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
