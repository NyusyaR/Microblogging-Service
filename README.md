## **Microblogging Service**

Корпоративный сервис микроблогов, реализованный на FastAPI + SQLAlchemy (async).

Проект полностью dockerized, покрыт тестами и включает OpenAPI-документацию.

## **Стек технологий**

\- FastAPI
\- SQLAlchemy 2.0 (async)
\- PostgreSQL
\- Alembic
\- Docker / Docker Compose
\- Pytest
\- Nginx
\- GitHub Actions (CI)

## **Быстрый старт**

Клонировать репозиторий

\`\`\`bash
git clone https://github.com/NyusyaR/Microblogging-Service.git
cd microblogging_service

## **Создать .env файл**

\`\`\`bash
cp .env.template .env

## **Запустить контейнеры**

\`\`\`bash
docker compose up –build

## **Документация API**

Swagger:
http://127.0.0.1:8080/docs

Redoc:
http://127.0.0.1:8080/redoc

## **Авторизация**

Все эндпоинты требуют заголовок:
api-key: &lt;your_api_key&gt;
В Swagger можно использовать кнопку **Authorize**.

## **Запуск тестов**

pytest

## **Работа с миграциями**

Создание новой миграции:
\`\`\`bash
alembic revision --autogenerate -m "описание"

Применение:
\`\`\`bash
alembic upgrade head

## **Основные эндпоинты**

| **Метод** | **Endpoint** | **Описание** |
| --- | --- | --- |
| POST | /api/tweets | Создать твит |
| POST | /api/medias | Загрузка медиа |
| DELETE | /api/tweets/{id} | Удалить твит |
| POST | /api/tweets/{id}/likes | Поставить лайк |
| DELETE | /api/tweets/{id}/likes | Убрать лайк |
| POST | /api/users/{id}/follow | Подписаться |
| DELETE | /api/users/{id}/follow | Отписаться |
| GET | /api/tweets | Лента |
| GET | /api/users/me | Мой профиль |
| GET | /api/users/{id} | Профиль пользователя |

## **Архитектура**

- app — FastAPI
- db — PostgreSQL
- nginx — reverse proxy + static
- frontend — SPA

## **Структура проекта**

alembic/
docker/
nginx/
service_app/
  config.py
  database.py
  dependencies.py
  main.py
  repository.py  
  router.py  
  schemas.py  
  security.py
tests/
.env
.env.template
.gitignore
alembic.ini  
docker-compose.yml  
Dockerfile.backend
Dockerfile.nginx
pytest.ini  
README.md
requirements.txt
