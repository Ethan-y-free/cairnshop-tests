from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class User(ApiModel):
    id: int
    email: str = ""
    phone: str = ""
    display_name: str = ""
    role: str


class Category(ApiModel):
    id: int
    name: str
    slug: str


class Product(ApiModel):
    id: int
    category_id: int
    sku: str
    name: str
    description: str = ""
    image_url: str = ""
    detail: str = ""
    price_cents: int
    original_price_cents: int = 0
    stock: int
    status: str


class CartItem(ApiModel):
    product_id: int
    sku: str
    name: str
    image_url: str = ""
    price_cents: int
    original_price_cents: int = 0
    stock: int
    status: str
    quantity: int


class Cart(ApiModel):
    items: list[CartItem]
    subtotal_cents: int


class OrderItem(ApiModel):
    product_id: int
    product_name: str
    unit_price_cents: int
    quantity: int


class Order(ApiModel):
    id: int
    order_no: str
    user_id: int
    status: str
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    config_version: int
    created_at: str
    promo: dict = Field(default_factory=dict)
    items: list[OrderItem]


class ErrorDetail(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    error: ErrorDetail
