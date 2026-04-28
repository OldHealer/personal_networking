from pydantic import BaseModel, EmailStr, Field


class AdminCreateUserRequest(BaseModel):
    """Запрос на создание пользователя админом."""

    username: str = Field(..., max_length=255, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, max_length=128, description="Пароль пользователя")
    first_name: str | None = Field(None, max_length=255, description="Имя")
    last_name: str | None = Field(None, max_length=255, description="Фамилия")
    tenant_name: str = Field(..., max_length=255, description="Название арендатора")


class AdminCreateUserResponse(BaseModel):
    """Ответ после создания пользователя."""

    keycloak_user_id: str
    app_user_id: str
    tenant_id: str
