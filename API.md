# API Документация URL Shortener

## 📋 Быстрый старт

### 1. Регистрация пользователя

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

**Ответ (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjc5ODc2NTQzfQ.abc123",
  "token_type": "bearer"
}
```

---

### 2. Вход

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

**Ответ (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123",
  "token_type": "bearer"
}
```

---

### 3. Создать ссылку

```bash
TOKEN="your-token-here"

curl -X POST http://localhost:8000/api/v1/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"original": "https://www.google.com"}'
```

**Ответ (201 Created):**
```json
{
  "id": 1,
  "original": "https://www.google.com",
  "short": "prklVe",
  "alias": null,
  "created_at": "2026-03-15T16:30:00Z",
  "expired_at": null,
  "last_used_at": null,
  "clicks_count": 0,
  "is_active": true
}
```

---

### 4. Создать ссылку с алиасом

```bash
curl -X POST http://localhost:8000/api/v1/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"original": "https://example.com", "alias": "mylink"}'
```

**Ответ (201 Created):**
```json
{
  "id": 2,
  "original": "https://example.com",
  "short": "abc123",
  "alias": "mylink",
  "created_at": "2026-03-15T16:35:00Z",
  "expired_at": null,
  "last_used_at": null,
  "clicks_count": 0,
  "is_active": true
}
```

---

### 5. Создать ссылку со временем жизни

```bash
curl -X POST http://localhost:8000/api/v1/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"original": "https://temp.com", "expired_at": 60}'
```

**Ответ (201 Created):**
```json
{
  "id": 3,
  "original": "https://temp.com",
  "short": "xyz789",
  "alias": null,
  "created_at": "2026-03-15T16:40:00Z",
  "expired_at": "2026-03-15T17:40:00Z",
  "last_used_at": null,
  "clicks_count": 0,
  "is_active": true
}
```

---

### 6. Редирект по короткой ссылке

```bash
curl -v http://localhost:8000/links/prklVe
```

**Ответ (307 Temporary Redirect):**
```
HTTP/1.1 307 Temporary Redirect
location: https://www.google.com
```

---

### 7. Редирект с автоматическим переходом

```bash
curl -L http://localhost:8000/links/prklVe
```

**Ответ:** Перенаправит на `https://www.google.com`

---

### 8. Информация о ссылке

```bash
curl http://localhost:8000/api/v1/links/prklVe/info
```

**Ответ (200 OK):**
```json
{
  "id": 1,
  "original": "https://www.google.com",
  "short": "prklVe",
  "alias": null,
  "created_at": "2026-03-15T16:30:00Z",
  "expired_at": null,
  "last_used_at": null,
  "clicks_count": 0,
  "is_active": true
}
```

---

### 9. Статистика ссылки

```bash
curl http://localhost:8000/api/v1/links/prklVe/stats
```

**Ответ (200 OK):**
```json
{
  "id": 1,
  "short": "prklVe",
  "original": "https://www.google.com",
  "alias": null,
  "clicks_count": 5,
  "created_at": "2026-03-15T16:30:00Z",
  "expired_at": null,
  "last_used_at": "2026-03-15T16:45:00Z",
  "is_active": true
}
```

---

### 10. Мои ссылки

```bash
curl http://localhost:8000/api/v1/links/my \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "original": "https://www.google.com",
    "short": "prklVe",
    "alias": null,
    "created_at": "2026-03-15T16:30:00Z",
    "expired_at": null,
    "last_used_at": "2026-03-15T16:45:00Z",
    "clicks_count": 5,
    "is_active": true
  },
  {
    "id": 2,
    "original": "https://example.com",
    "short": "abc123",
    "alias": "mylink",
    "created_at": "2026-03-15T16:35:00Z",
    "expired_at": null,
    "last_used_at": null,
    "clicks_count": 0,
    "is_active": true
  }
]
```

---

### 11. Обновить ссылку

```bash
curl -X PUT http://localhost:8000/api/v1/links/prklVe \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"original": "https://new-url.com"}'
```

**Ответ (200 OK):**
```json
{
  "id": 1,
  "original": "https://new-url.com",
  "short": "prklVe",
  "alias": null,
  "created_at": "2026-03-15T16:30:00Z",
  "expired_at": null,
  "last_used_at": "2026-03-15T16:45:00Z",
  "clicks_count": 5,
  "is_active": true
}
```

---

### 12. Удалить ссылку

```bash
curl -X DELETE http://localhost:8000/api/v1/links/prklVe \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (204 No Content):**
```
(пустое тело)
```

---

### 13. Поиск ссылок по URL

```bash
curl "http://localhost:8000/api/v1/links/search?original_url=google" \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "original": "https://www.google.com",
    "short": "prklVe",
    "alias": null,
    "created_at": "2026-03-15T16:30:00Z",
    "expired_at": null,
    "last_used_at": "2026-03-15T16:45:00Z",
    "clicks_count": 5,
    "is_active": true
  }
]
```

---

### 14. История истекших ссылок

```bash
curl http://localhost:8000/api/v1/links/expired/history \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (200 OK):**
```json
[
  {
    "id": 3,
    "original": "https://temp.com",
    "short": "xyz789",
    "alias": null,
    "created_at": "2026-03-15T16:40:00Z",
    "expired_at": "2026-03-15T17:40:00Z",
    "last_used_at": null,
    "clicks_count": 0,
    "is_active": false
  }
]
```

---

### 15. Удалить неиспользуемые ссылки

```bash
curl -X POST http://localhost:8000/api/v1/links/cleanup/unused \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"days": 30}'
```

**Ответ (200 OK):**
```json
{
  "deleted_count": 5,
  "days_threshold": 30
}
```

---

## 🏷️ Теги

### Создать тег

```bash
curl -X POST http://localhost:8000/api/v1/tags \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "project1"}'
```

**Ответ (201 Created):**
```json
{
  "id": 1,
  "name": "project1",
  "created_at": "2026-03-15T17:00:00Z",
  "owner_id": 1
}
```

---

### Мои теги

```bash
curl http://localhost:8000/api/v1/tags \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "name": "project1",
    "created_at": "2026-03-15T17:00:00Z",
    "owner_id": 1
  },
  {
    "id": 2,
    "name": "social-media",
    "created_at": "2026-03-15T17:05:00Z",
    "owner_id": 1
  }
]
```

---

### Добавить тег к ссылке

```bash
curl -X POST http://localhost:8000/api/v1/links/prklVe/tags/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (201 Created):**
```json
{
  "message": "Tag added successfully"
}
```

---

### Удалить тег у ссылки

```bash
curl -X DELETE http://localhost:8000/api/v1/links/prklVe/tags/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (204 No Content):**
```
(пустое тело)
```

---

### Ссылки с тегом

```bash
curl http://localhost:8000/api/v1/tags/1/links \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "short": "prklVe",
    "original": "https://www.google.com",
    "alias": null,
    "clicks_count": 5
  }
]
```

---

### Удалить тег

```bash
curl -X DELETE http://localhost:8000/api/v1/tags/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ (204 No Content):**
```
(пустое тело)
```

---

## ❌ Ошибки

### 400 Bad Request
```json
{
  "detail": "Alias 'mylink' already exists"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions to delete this link"
}
```

### 404 Not Found
```json
{
  "detail": "Link with short code 'abc123' not found"
}
```

### 410 Gone (истекла)
```json
{
  "detail": "Link has expired"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Too many requests",
  "message": "Rate limit exceeded. Please try again later."
}
```

---

## 📊 Сводная таблица endpoints

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| POST | `/api/v1/auth/register` | ❌ | Регистрация |
| POST | `/api/v1/auth/login` | ❌ | Вход |
| GET | `/api/v1/auth/me` | ✅ | Инфо о пользователе |
| POST | `/api/v1/links/shorten` | ❌ | Создать ссылку |
| GET | `/api/v1/links/my` | ✅ | Мои ссылки |
| GET | `/api/v1/links/search` | ✅ | Поиск по URL |
| PUT | `/api/v1/links/{code}` | ✅ | Обновить ссылку |
| DELETE | `/api/v1/links/{code}` | ✅ | Удалить ссылку |
| GET | `/api/v1/links/{code}/info` | ❌ | Инфо о ссылке |
| GET | `/api/v1/links/{code}/stats` | ❌ | Статистика |
| GET | `/api/v1/links/expired/history` | ✅ | История истекших |
| POST | `/api/v1/links/cleanup/unused` | ✅ | Удалить неиспользуемые |
| POST | `/api/v1/links/{code}/tags/{tag}` | ✅ | Добавить тег |
| DELETE | `/api/v1/links/{code}/tags/{tag}` | ✅ | Удалить тег |
| POST | `/api/v1/tags` | ✅ | Создать тег |
| GET | `/api/v1/tags` | ✅ | Мои теги |
| DELETE | `/api/v1/tags/{id}` | ✅ | Удалить тег |
| GET | `/api/v1/tags/{id}/links` | ✅ | Ссылки с тегом |
| GET | `/links/{code}` | ❌ | Редирект |

---

## 🔧 Переменные окружения

```bash
# Для тестов на локальной машине
export TOKEN="your-token-here"

# Для тестов на сервере
export API_URL="http://91.105.197.101:8000"
```
