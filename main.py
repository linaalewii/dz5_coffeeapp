"""Сервис учёта заказов кофейни (домашнее задание к уроку 5)."""

from datetime import datetime
from enum import Enum
from functools import lru_cache
from itertools import count
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Значения по умолчанию действуют, если в .env ничего не задано."""

    app_name: str = "Учёт заказов кофейни"
    default_page_size: int = 10
    max_page_size: int = 50

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Зависимость: читает настройки один раз и переиспользует."""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


class DrinkSize(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


class OrderStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    completed = "completed"


class SortBy(str, Enum):
    created_at = "created_at"
    drink = "drink"



class OrderCreate(BaseModel):
    """Что присылает клиент при создании заказа."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    drink: str = Field(
        min_length=1,
        max_length=100,
        description="Название напитка из меню",
        examples=["Латте"],
    )
    size: DrinkSize = Field(description="Размер напитка", examples=["medium"])
    quantity: int = Field(gt=0, description="Количество порций", examples=[2])
    customer_name: str | None = Field(
        default=None,
        max_length=100,
        description="Имя клиента (необязательно)",
        examples=["Ирина"],
    )


class OrderUpdate(BaseModel):
    """Частичное обновление: все поля необязательные."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    drink: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Название напитка из меню",
        examples=["Капучино"],
    )
    size: DrinkSize | None = Field(
        default=None, description="Размер напитка", examples=["large"]
    )
    quantity: int | None = Field(
        default=None, gt=0, description="Количество порций", examples=[3]
    )
    customer_name: str | None = Field(
        default=None,
        max_length=100,
        description="Имя клиента",
        examples=["Анна"],
    )
    status: OrderStatus | None = Field(
        default=None, description="Статус заказа", examples=["ready"]
    )


class Order(BaseModel):
    """Заказ в ответе сервера (с id, статусом и временем создания)."""

    id: int = Field(description="Идентификатор заказа", examples=[1])
    drink: str = Field(description="Название напитка из меню", examples=["Латте"])
    size: DrinkSize = Field(description="Размер напитка", examples=["medium"])
    quantity: int = Field(description="Количество порций", examples=[2])
    customer_name: str | None = Field(
        default=None, description="Имя клиента", examples=["Ирина"]
    )
    status: OrderStatus = Field(
        default=OrderStatus.pending, description="Статус заказа", examples=["pending"]
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Время создания заказа (ставит сервер)",
        examples=["2026-07-10T09:15:00"],
    )


orders: dict[int, Order] = {}

_id_counter = count(1)

TAG_ORDERS = "Заказы"
TAG_SERVICE = "Сервис"

app = FastAPI(
    title="Учёт заказов кофейни",
    description=(
        "Маленький сервис для бариста: создать заказ, посмотреть список, "
        "отметить готовым или выполненным и отменить.\n\n"
        "Данные хранятся в памяти и пропадают при перезапуске сервера."
    ),
    version="1.0.0",
)


def get_order_or_404(order_id: int) -> Order:
    """Возвращает заказ или отвечает клиенту статусом 404."""
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заказ с id={order_id} не найден",
        )
    return order

@app.get("/", tags=[TAG_SERVICE], summary="Приветствие сервиса")
def read_root():
    return {"message": "Сервис учёта заказов кофейни на связи"}


@app.get("/info", tags=[TAG_SERVICE], summary="Информация о сервисе")
def get_info(settings: SettingsDep):
    return {"app_name": settings.app_name, "orders_count": len(orders)}


@app.post(
    "/orders",
    response_model=Order,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_ORDERS],
    summary="Создать заказ",
)
def create_order(data: OrderCreate):
    order = Order(
        id=next(_id_counter),
        status=OrderStatus.pending,
        **data.model_dump(),
    ) 
    orders[order.id] = order
    return order


@app.get(
    "/orders",
    response_model=list[Order],
    tags=[TAG_ORDERS],
    summary="Список заказов",
)
def list_orders(
    settings: SettingsDep,
    order_status: Annotated[
        OrderStatus | None,
        Query(alias="status", description="Фильтр по статусу заказа"),
    ] = None,
    limit: Annotated[
        int | None,
        Query(
            ge=1,
            description=(
                "Сколько заказов вернуть. Если не указано — значение из настроек; "
                "больше максимума из настроек не отдаётся."
            ),
        ),
    ] = None,
    offset: Annotated[
        int, Query(ge=0, description="Сколько заказов пропустить с начала")
    ] = 0,
    sort_by: Annotated[
        SortBy | None,
        Query(description="Сортировка: по времени создания или по названию напитка"),
    ] = None,
):
    result = list(orders.values())

    if order_status is not None:
        result = [o for o in result if o.status == order_status]

    if sort_by == SortBy.created_at:
        result.sort(key=lambda o: o.created_at)
    elif sort_by == SortBy.drink:
        result.sort(key=lambda o: o.drink.lower())

    page_size = limit if limit is not None else settings.default_page_size
    page_size = min(page_size, settings.max_page_size)
    return result[offset : offset + page_size]


@app.get(
    "/orders/{order_id}",
    response_model=Order,
    tags=[TAG_ORDERS],
    summary="Получить заказ по id",
)
def get_order(order_id: int):
    return get_order_or_404(order_id)


@app.patch(
    "/orders/{order_id}",
    response_model=Order,
    tags=[TAG_ORDERS],
    summary="Частично обновить заказ",
)
def update_order(order_id: int, data: OrderUpdate):
    order = get_order_or_404(order_id)

    changes = {
        key: value
        for key, value in data.model_dump(exclude_unset=True).items()
        if value is not None
    }
    updated = order.model_copy(update=changes)  
    orders[order_id] = updated
    return updated


@app.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[TAG_ORDERS],
    summary="Отменить (удалить) заказ",
)
def delete_order(order_id: int):
    get_order_or_404(order_id)
    del orders[order_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)