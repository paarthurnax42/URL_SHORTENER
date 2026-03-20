# URL Shortener

Сокращатель ссылок на FastAPI + PostgreSQL + Redis


Основная идея — пользователь вводит длинный URL, а ваш сервис генерирует для него короткую ссылку, которую можно использовать для быстрого доступа.

## Как это работает:

- Пользователь отправляет запрос (POST /links/shorten) с длинной ссылкой.

- Сервис генерирует уникальный короткий код и возвращает его пользователю.

- При открытии короткой ссылки (GET-запрос к /{short_code}) сервис ищет в базе данных соответствующий оригинальный URL и перенаправляет пользователя (Redirect).


## Быстрый старт

```bash
# Клонировать репозиторий
git clone <repository-url>
cd another_one_url_shortener

# Создать .env
cp .env.example .env
# Отредактировать .env (изменить SECRET_KEY, DB_PASS)

# Запустить всё
docker-compose up -d

```

### Сервисы:

| Сервис | URL | Описание |
|--------|-----|----------|
| Приложение | http://localhost:8000 | FastAPI API |
| Swagger API Docs | http://localhost:8000/docs | Документация API |

---

## Переменные окружения

```bash
# DB settings
DB_USER=postgres
DB_PASS=your_secure_password_here
DB_NAME=links

# App settings
LINK_LENGHT=6
DEFAULT_EXPIRATION_MINUTES=60

# JWT settings
SECRET_KEY=your_super_secret_key_min_32_characters_long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS settings
CORS_ORIGINS=http://localhost:80

# Docker settings
APP_PORT=8000
WORKERS=4
```

---

## Структура проекта

```
.
├── app/                      # Бэкенд (FastAPI)
│   ├── api/v1/              # API роуты
│   ├── core/                # Конфигурация, безопасность
│   ├── crud/                # CRUD операции
│   ├── db/                  # БД сессии, модели
│   ├── models/              # SQLAlchemy модели
│   ├── schemas/             # Pydantic схемы
│   └── main.py              # Точка входа
├── alembic/                  # Миграции БД
├── docker-compose.yaml       # Docker Compose
├── nginx.conf                # Nginx конфигурация
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## API Документация

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | Вход |
| GET | `/api/v1/auth/me` | Информация о пользователе |
| POST | `/api/v1/links/shorten` | Создает короткую ссылку, возможна передача custom_alias |
| GET | `/links/{short_code}` | Перенаправляет на оригинальный URL. |
| PUT | `/api/v1/links/{code}` | Обновляет URL, к короткой ссылке привязывается новая длинная |
| DELETE | `/api/v1/links/{short_code}` | Удаляет связь |
| GET | `/api/v1/links/my` | Мои ссылки |
| GET | `/api/v1/links/{code}/stats` | Статистика |

---

##  Дополнительные функции
- Создание коротких ссылок для незарегистрированных пользователей.
- Автоудаление истекших ссылок


## Технологии

- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Alembic (миграции)
- Pydantic
- JWT (PyJWT)

---

## Тестирование

Все тесты запускаются в изолированном Docker-окружении (PostgreSQL + Redis).

### Быстрый старт

```bash
# Запустить все тесты (контейнеры поднимутся автоматически)
make tests

# Запустить конкретные тесты
make tests TESTS_TO_RUN=tests/func/test_auth.py
make tests TESTS_TO_RUN=tests/unit/

# Нагрузочное тестирование (Locust UI)
make load

# Остановить тестовые контейнеры
make docker-down
```

> **Примечание:** Для нагрузочного тестирования требуется установленный `locust` локально:

### Структура тестов

```
tests/
├── unit/                    # Unit-тесты
│   ├── test_security.py     # Пароли, JWT
│   ├── test_cache.py        # Redis cache
│   ├── test_*_crud.py       # CRUD операции
│   └── ...
├── func/                    # Функциональные тесты
│   ├── test_auth.py         # Авторизация
│   ├── test_links.py        # API ссылок
│   ├── test_tags.py         # API тегов
│   └── test_redirect.py     # Редиректы
└── load/                    # Нагрузочные тесты
    └── locustfile.py        # Locust сценарии
```

### Конфигурация

Тестовые контейнеры используют отдельные порты:
- **PostgreSQL**: 5433 (хост) → 5432 (контейнер)
- **Redis**: 6380 (хост) → 6379 (контейнер)

Настройки в файле `tests/.env`.

### Команды

| Команда | Описание |
|---------|----------|
| `make tests` | Запустить все тесты с покрытием |
| `make tests TESTS_TO_RUN=tests/func/` | Запустить тесты из папки |
| `make tests TESTS_TO_RUN=tests/func/test_auth.py::TestAuth::test_login` | Конкретный тест |
| `make coverage` | Запустить тесты и открыть отчёт о покрытии |
| `make load` | Нагрузочное тестирование (Locust UI) |
| `make docker-up` | Поднять тестовые контейнеры |
| `make docker-down` | Остановить тестовые контейнеры |
| `make docker-clean` | Остановить и удалить тома |
| `make clean` | Очистить кэш и отчёты (htmlcov, .coverage, __pycache__) |
# Updated
