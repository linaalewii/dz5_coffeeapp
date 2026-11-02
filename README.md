# Учёт заказов кофейни

Домашнее задание к уроку 5: маленький сервис на FastAPI для бариста. Хранение данных в памяти, без базы данных.

## Что умеет

| Метод и путь | Что делает |
|---|---|
| `POST /orders` | создать заказ (статус `pending`, время создания ставит сервер), ответ 201 |
| `GET /orders` | список заказов: фильтр `status`, `limit`, `offset`, сортировка `sort_by` |
| `GET /orders/{order_id}` | один заказ, 404 если не найден |
| `PATCH /orders/{order_id}` | частично обновить заказ (например, статус `ready`) |
| `DELETE /orders/{order_id}` | отменить заказ, ответ 204 без тела |
| `GET /` | приветствие |
| `GET /info` | название сервиса и число заказов в памяти |

Размер напитка: `small`, `medium`, `large`. Статус заказа: `pending`, `ready`, `completed`.

## Запуск

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
pip install "fastapi[standard]" pydantic-settings
copy .env.example .env            # Windows (на macOS/Linux: cp .env.example .env)
fastapi dev main.py
```

Документация и проверка запросов: http://127.0.0.1:8000/docs

## Настройки

Задаются в `.env` (образец — `.env.example`):

| Переменная | Значение по умолчанию | Смысл |
|---|---|---|
| `APP_NAME` | Учёт заказов кофейни | название сервиса для `/info` |
| `DEFAULT_PAGE_SIZE` | 10 | сколько заказов отдаётся, если `limit` не указан |
| `MAX_PAGE_SIZE` | 50 | максимум заказов на странице |

Файл `.env` в репозиторий не попадает (он в `.gitignore`).

## Пример

```http
POST /orders

{"drink": "Латте", "size": "medium", "quantity": 2, "customer_name": "Ирина"}
```

Ответ 201: заказ с `id`, статусом `pending` и `created_at`.
