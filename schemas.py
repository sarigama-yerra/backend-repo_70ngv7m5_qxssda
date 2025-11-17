"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Add your own schemas here:
# --------------------------------------------------

class Qr(BaseModel):
    """QR code generation history schema
    Collection name: "qr" (lowercase of class name)
    """
    content: str = Field(..., description="Text or URL encoded in the QR code")
    fill_color: str = Field('#111827', description="QR code color")
    back_color: str = Field('#ffffff', description="Background color")
    box_size: int = Field(10, ge=1, le=50, description="Pixel size of each QR box")
    border: int = Field(4, ge=0, le=20, description="Border size (modules)")
    error_correction: str = Field('M', description="Error correction level: L, M, Q, H")
    logo_url: Optional[HttpUrl] = Field(None, description="Optional logo URL to embed in center")
