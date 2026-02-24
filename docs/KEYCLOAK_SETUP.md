# Инструкция по настройке Keycloak (prod-ready)

Ниже — пошаговая, интуитивная инструкция для настройки Keycloak при выкате на прод.
Примерные имена соответствуют проекту Rockfile.

---

## 1) Развертывание Keycloak

### 1.1 Контейнер + отдельная БД (рекомендуется)
- Keycloak **не должен** использовать БД проекта.
- Для прод окружения используйте отдельную БД PostgreSQL.

**Пример базовой команды (DEV):**
```bash
docker run -d --name rockfile-keycloak -p 8081:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=owner \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=owner \
  quay.io/keycloak/keycloak:latest start-dev
```

**Для prod** рекомендуется:
- включить HTTPS
- задать `KC_HOSTNAME`
- использовать полноценный конфиг БД (не H2)

---

## 2) Создание Realm

1. Открой `http://<keycloak-host>`
2. Войти админом
3. В левом верхнем углу выбрать `Master` → `Create realm`
4. Имя: `rockfile`

---

## 3) Настройки Realm (Login/Email/User Profile)

### 3.1 Login
`Realm settings` → `Login`
- **User registration**: ON (самостоятельная регистрация)
- **Email as username**: ON
- **Duplicate emails**: OFF
- **Verify email**: ON (prod) / OFF (dev)
- **Login with email**: ON (если хотите вход по email)

### 3.2 User profile (важно!)
`Realm settings` → `User profile` → `Attributes`
- Проверьте обязательные поля.
- Если `First name` и `Last name` обязательны — наш бек уже отправляет их.

### 3.3 Required actions (отключить дефолты, если не нужны)
`Realm settings` → `Authentication` → `Required actions`
- `Verify Email`: ON только если есть SMTP
- `Update Password`: OFF
- `Update Profile`: OFF (если не хотите блокировать вход)

---

## 4) Клиент приложения (rockfile-api)

### 4.1 Создать клиента
`Clients` → `Create client`
- Client type: **OpenID Connect**
- Client ID: `rockfile-api`
- `Save`

### 4.2 Настройки клиента
`Clients` → `rockfile-api` → `Settings`

**Основное:**
- **Client authentication**:  
  - ON (confidential) — если используете `client_secret`
  - OFF (public) — если не хотите хранить secret
- **Standard flow**: ON (для авторизации через браузер)
- **Direct access grants**: ON (если используете login по паролю)

**Redirect/Origins:**
- `Root URL`: `https://app.example.com`
- `Home URL`: `https://app.example.com`
- `Valid redirect URIs`: `https://app.example.com/*`
- `Valid post logout redirect URIs`: `https://app.example.com/*`
- `Web origins`: `https://app.example.com`

> Для локалки указывайте `http://localhost:8100` и `http://localhost:3000`

---

## 5) Audience Mapper (важно)

Чтобы в токене был `aud = rockfile-api`, добавьте Audience Mapper.

**Вариант А (через Client scopes):**
1. `Client scopes` → `rockfile-api-dedicated`
2. `Mappers` → `Create mapper`
3. Type: **Audience**
4. `Included Client Audience`: `rockfile-api`
5. `Add to access token`: ON

**Вариант Б (прямо в client):**
1. `Clients` → `rockfile-api`
2. Вкладка `Mappers` → `Add mapper` → `By configuration`
3. Type: **Audience**
4. `Included Client Audience`: `rockfile-api`
5. `Add to access token`: ON

---

## 6) Роли

Создайте роли:
- `superadmin`
- `admin`
- `user`

`Realm roles` → `Create role`

Назначить роли пользователю:
`Users` → пользователь → `Role mapping`

---

## 7) Админ‑клиент для создания пользователей (rockfile-admin-cli)

### 7.1 Создать клиента
`Clients` → `Create client`
- Client type: **OpenID Connect**
- Client ID: `rockfile-admin-cli`
- **Client authentication**: ON
- **Service accounts**: ON

### 7.2 Выдать роли сервисному аккаунту
`Clients` → `rockfile-admin-cli` → `Service account roles`
В `realm-management` добавить:
- `manage-users`
- (опционально) `view-users`

### 7.3 Client Secret
`Clients` → `rockfile-admin-cli` → `Credentials`
Скопируйте `Client secret`

---

## 8) SMTP (для подтверждения email)

Если включено **Verify Email**:
`Realm settings` → `Email`
- Настроить SMTP (host, port, user, password)
- Проверить `Test connection`

---

## 9) Токены и сроки жизни

`Realm settings` → `Tokens`
- **Access Token Lifespan**: 15–60 минут
- **SSO Session Idle**: 1–4 часа
- **SSO Session Max**: 1 день и более

---

## 10) Переменные окружения для приложения

```env
KEYCLOAK__ISSUER=https://auth.example.com/realms/rockfile
KEYCLOAK__JWKS_URL=https://auth.example.com/realms/rockfile/protocol/openid-connect/certs
KEYCLOAK__TOKEN_URL=https://auth.example.com/realms/rockfile/protocol/openid-connect/token
KEYCLOAK__CLIENT_ID=rockfile-api
KEYCLOAK__CLIENT_SECRET=... # если client confidential

KEYCLOAK_ADMIN__BASE_URL=https://auth.example.com
KEYCLOAK_ADMIN__REALM=rockfile
KEYCLOAK_ADMIN__CLIENT_ID=rockfile-admin-cli
KEYCLOAK_ADMIN__CLIENT_SECRET=...
```

---

## 11) Проверка

### 11.1 OIDC конфиг
`/.well-known/openid-configuration`
```
https://auth.example.com/realms/rockfile/.well-known/openid-configuration
```

### 11.2 JWT
Проверь, что в токене:
- `iss` = `https://auth.example.com/realms/rockfile`
- `aud` содержит `rockfile-api`
- `realm_access.roles` содержит нужные роли

---

Если нужно — дополню инструкцию для reverse proxy (Nginx), HTTPS и backup Keycloak DB.
