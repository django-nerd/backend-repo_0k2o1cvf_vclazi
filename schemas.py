"""
Database Schemas for Smiley Store

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category (hoodies | t-shirts)")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    sizes: List[str] = Field(default_factory=lambda: ["S","M","L","XL"], description="Available sizes")
    in_stock: bool = Field(True, description="Whether product is in stock")

class Order(BaseModel):
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer email")
    customer_address: str = Field(..., description="Shipping address")
    total: float = Field(..., ge=0, description="Order total")
