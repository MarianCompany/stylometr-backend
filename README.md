# Stylometr Backend

Серверная часть веб-ориентированной системы атрибуции авторства русскоязычных текстов на основе методов стилометрического анализа.



## Назначение

Backend-компонент обеспечивает:

- аутентификацию и авторизацию пользователей с использованием JWT-токенов;
- управление профилями авторов и связанными с ними текстами;
- автоматическое извлечение стилометрических признаков из текстов;
- агрегацию метрик для профилей авторов;
- сравнение проверяемого текста с эталонным профилем автора;
- расчёт дельты Бёрроуза, косинусного сходства и вероятности авторства;
- административные функции:
  - управление пользователями;
  - модерацию профилей;
  - просмотр журналов действий.



## Технологический стек

| Компонент | Назначение |
|---|---|
| Python 3.13 | Основной язык разработки |
| FastAPI | Веб-фреймворк |
| SQLAlchemy | ORM |
| Alembic | Миграции базы данных |
| Pydantic | Валидация данных |
| PostgreSQL | Основная база данных |
| Redis | Кеширование |
| JWT | Аутентификация |
| Docker | Контейнеризация |



## Требования к окружению

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- `pip`



# Установка и запуск

## Локальный запуск (режим разработки)

### 1. Клонирование репозитория

```bash
cd stylometr-backend
```

### 2. Создание виртуального окружения

```bash
python -m venv .venv
```

### 3. Активация виртуального окружения

#### Linux / macOS

```bash
source .venv/bin/activate
```

#### Windows

```bash
.venv\Scripts\activate
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Создание файла `.env`

Создайте файл `.env` на основе `.env.example`:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/stylometry
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_DAYS=7
DEBUG=true
CORS_ORIGINS=http://localhost:3000
```

### 6. Выполнение миграций базы данных

```bash
alembic upgrade head
```

### 7. Заполнение начальными данными

```bash
python -m db.seed.seed
```

### 8. Запуск сервера разработки

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```



## Запуск через Docker

```bash
docker compose up -d --build
```



## Проверка работоспособности

```bash
curl http://localhost:8000/health
```

### Ожидаемый ответ

```json
{
  "status": "ok",
  "database": "ok"
}
```



## Структура проекта

```text
stylometr-backend/
├── main.py                 # Точка входа приложения
├── requirements.txt        # Зависимости Python
├── .env.example            # Пример конфигурации окружения
├── alembic/                # Миграции базы данных
├── alembic.ini             # Конфигурация Alembic
├── db/                     # Модели и CRUD-операции
│   ├── models.py           
│   ├── crud.py             
│   ├── session.py          
│   └── seed/               
├── routers/                # API-маршруты
│   ├── auth.py             
│   ├── profiles.py         
│   └── users.py            
├── admin/                  # Адми-панель
├── services/               # Бизнес-логика
│   ├── auth.py             
│   ├── profile_metrics.py  
│   └── comparisons.py      
├── analytics/              # Лингвистическая обработка
│   ├── features.py         
│   ├── preprocessing.py    
│   └── morph.py           
├── schemas/                # Pydantic-схемы
└── core/                   # Конфигурация
    └── config.py           
```



## API-эндпоинты

### Пользовательские эндпоинты

| Метод | Эндпоинт | Назначение |
|---|---|---|
| POST | `/auth/register` | Регистрация пользователя |
| POST | `/auth/login` | Вход и получение токенов |
| POST | `/auth/refresh` | Обновление access-токена |
| POST | `/auth/logout` | Выход |
| GET | `/auth/me` | Получение текущего пользователя |
| GET | `/profiles` | Список профилей текущего пользователя |
| POST | `/profiles` | Создание профиля автора |
| GET | `/profiles/{profile_id}` | Получение профиля |
| PATCH | `/profiles/{profile_id}` | Изменение профиля |
| DELETE | `/profiles/{profile_id}` | Удаление профиля |
| GET | `/profiles/{profile_id}/metrics` | Метрики профиля |
| POST | `/profiles/{profile_id}/texts` | Добавление текста |
| GET | `/profiles/{profile_id}/texts` | Список текстов профиля |
| GET | `/profiles/{profile_id}/texts/{text_id}` | Просмотр текста |
| DELETE | `/profiles/{profile_id}/texts/{text_id}` | Удаление текста |
| POST | `/profiles/{profile_id}/compare` | Сравнение текста с профилем |



### Административные эндпоинты

| Метод | Эндпоинт | Назначение |
|---|---|---|
| GET | `/admin/users` | Список пользователей |
| GET | `/admin/users/{user_id}` | Карточка пользователя |
| PATCH | `/admin/users/{user_id}/role` | Смена роли |
| POST | `/admin/users/{user_id}/ban` | Блокировка пользователя |
| GET | `/admin/users/{user_id}/profiles` | Профили пользователя |
| GET | `/admin/users/{user_id}/texts` | Тексты пользователя |
| GET | `/admin/moderation/profiles/pending` | Очередь модерации |
| POST | `/admin/moderation/profiles/{profile_id}/approve` | Одобрение профиля |
| POST | `/admin/moderation/profiles/{profile_id}/reject` | Отклонение профиля |



## Переменные окружения

| Переменная | Описание | Обязательная |
|---|---|---|
| `DATABASE_URL` | Строка подключения к PostgreSQL | Да |
| `SECRET_KEY` | Секретный ключ для JWT | Да |
| `ALGORITHM` | Алгоритм подписи JWT (`HS256`) | Нет |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни access-токена (минуты) | Нет |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Время жизни refresh-токена (дни) | Нет |
| `DEBUG` | Режим отладки (`true/false`) | Нет |
| `CORS_ORIGINS` | Разрешённые источники для CORS | Нет |

## Миграции базы данных

### Создание новой миграции

```bash
alembic revision --autogenerate -m "описание изменений"
```

### Применение миграций

```bash
alembic upgrade head
```

### Откат последней миграции

```bash
alembic downgrade -1
```


## API-документация

После запуска сервиса документация будет доступна по адресам:

```text
http://localhost:8000/docs
http://localhost:8000/redoc
```

- `/docs` — Swagger UI
- `/redoc` — ReDoc

### Ответ

```json
{
  "status": "ok",
  "database": "ok"
}
```
