from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Запрос на самостоятельную регистрацию пользователя."""
    username: str = Field(..., description="Имя пользователя")
    email: EmailStr = Field(..., description="Email пользователя (уникальный)")
    password: str = Field(..., min_length=6, description="Пароль пользователя")
    first_name: str | None = Field(None, description="Имя")
    last_name: str | None = Field(None, description="Фамилия")
    tenant_name: str | None = Field(None, description="Название арендатора (опционально)")

class RegisterResponse(BaseModel):
    """Ответ после регистрации пользователя."""
    keycloak_user_id: str
    app_user_id: str
    tenant_id: str

class LoginRequest(BaseModel):
    """Запрос на авторизацию."""
    username: str = Field(..., description="Логин или email пользователя")
    password: str = Field(..., min_length=6, description="Пароль пользователя")

class LoginResponse(BaseModel):
    """Ответ с токенами Keycloak."""
    access_token: str
    refresh_token: str | None = None
    token_type: str
    expires_in: int