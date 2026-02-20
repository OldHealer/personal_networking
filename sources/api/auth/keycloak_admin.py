"""
Административные операции с Keycloak:
- получение admin токена
- создание пользователя
"""
import httpx

from fastapi import HTTPException, status

from settings import config


async def _get_admin_access_token() -> str:
    """
    Получаем admin access token через Client Credentials.

    Требования к Keycloak:
    - создан confidential client (например, rockfile-admin-cli)
    - включены Service Accounts
    - назначены роли realm-management (например, manage-users)
    """
    data = {
        "grant_type": "client_credentials",
        "client_id": config.keycloak_admin.client_id,
        "client_secret": config.keycloak_admin.client_secret,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(config.keycloak_admin.token_url, data=data, timeout=10)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Keycloak token error: {response.text}",
            )
        payload = response.json()
        return payload.get("access_token", "")


async def create_keycloak_user(user_payload: dict) -> str:
    """
    Создаём пользователя в Keycloak и возвращаем его ID.

    Keycloak возвращает Location заголовок с URL созданного пользователя.
    """
    token = await _get_admin_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            config.keycloak_admin.admin_users_url,
            json=user_payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code not in (201, 204):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Keycloak create user error: {response.text}",
            )

        location = response.headers.get("Location", "")
        if not location:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Keycloak did not return Location header",
            )

        # Обычно URL заканчивается на .../users/<id>
        user_id = location.rstrip("/").split("/")[-1]
        return user_id
