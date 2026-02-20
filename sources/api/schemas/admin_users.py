from pydantic import BaseModel, EmailStr, Field


class AdminCreateUserRequest(BaseModel):
    """Запрос на создание пользователя админом."""

    username: str = Field(..., description="Имя пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль пользователя")
    tenant_name: str = Field(..., description="Название арендатора")


class AdminCreateUserResponse(BaseModel):
    """Ответ после создания пользователя."""

    keycloak_user_id: str
    app_user_id: str
    tenant_id: str
