from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Запрос на самостоятельную регистрацию пользователя."""

    username: str = Field(..., description="Имя пользователя")
    email: EmailStr = Field(..., description="Email пользователя (уникальный)")
    password: str = Field(..., min_length=6, description="Пароль пользователя")
    tenant_name: str | None = Field(None, description="Название арендатора (опционально)")


class RegisterResponse(BaseModel):
    """Ответ после регистрации пользователя."""

    keycloak_user_id: str
    app_user_id: str
    tenant_id: str
