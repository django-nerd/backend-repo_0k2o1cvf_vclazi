import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Smiley Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Helpers -----

def serialize_doc(doc: dict) -> dict:
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert any nested ObjectIds if present
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d

# ----- Models -----

class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    images: List[str] = []
    sizes: List[str] = ["S", "M", "L", "XL"]
    in_stock: bool = True

class CartItem(BaseModel):
    product_id: str
    size: str
    quantity: int = Field(..., ge=1, le=10)

class CustomerInfo(BaseModel):
    name: str
    email: str
    address: str

class OrderCreate(BaseModel):
    items: List[CartItem]
    customer: CustomerInfo

# ----- Seed Data -----

SEED_PRODUCTS = [
    {
        "title": "Smiley Classic Hoodie",
        "description": "Cozy fleece hoodie with the iconic Smiley front print.",
        "price": 59.0,
        "category": "hoodies",
        "images": [
            "https://images.unsplash.com/photo-1548883354-7622d03acae1?q=80&w=1600&auto=format&fit=crop",
        ],
        "sizes": ["S", "M", "L", "XL"],
        "in_stock": True,
    },
    {
        "title": "Smiley Minimal Tee",
        "description": "Soft cotton t‑shirt with a subtle embroidered smile.",
        "price": 24.0,
        "category": "t-shirts",
        "images": [
            "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?q=80&w=1600&auto=format&fit=crop",
        ],
        "sizes": ["S", "M", "L", "XL"],
        "in_stock": True,
    },
    {
        "title": "Smiley Oversized Hoodie",
        "description": "Premium heavyweight hoodie, oversized fit.",
        "price": 72.0,
        "category": "hoodies",
        "images": [
            "https://images.unsplash.com/photo-1544441893-675973e31985?q=80&w=1600&auto=format&fit=crop",
        ],
        "sizes": ["S", "M", "L", "XL"],
        "in_stock": True,
    },
    {
        "title": "Smiley Retro Tee",
        "description": "90s inspired graphic tee with retro smile.",
        "price": 29.0,
        "category": "t-shirts",
        "images": [
            "https://images.unsplash.com/photo-1503342217505-b0a15cf70489?q=80&w=1600&auto=format&fit=crop",
        ],
        "sizes": ["S", "M", "L", "XL"],
        "in_stock": True,
    },
]

async def ensure_seed_products():
    try:
        count = db["product"].count_documents({}) if db else 0
        if count == 0:
            db["product"].insert_many(SEED_PRODUCTS)
    except Exception:
        pass

# ----- Routes -----

@app.get("/")
def read_root():
    return {"message": "Smiley Store Backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", None) or "❌ Not Set"
            collections = db.list_collection_names()
            response["collections"] = collections[:10]
            response["database"] = "✅ Connected & Working"
            response["connection_status"] = "Connected"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

@app.get("/api/products")
async def list_products(category: Optional[str] = None):
    await ensure_seed_products()
    query = {"category": category} if category else {}
    products = get_documents("product", query)
    return [serialize_doc(p) for p in products]

@app.post("/api/products")
async def create_product(p: ProductCreate):
    inserted_id = create_document("product", p.model_dump())
    doc = db["product"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)

@app.post("/api/order")
async def create_order(order: OrderCreate):
    # Basic validation: ensure product exists for each item
    total = 0.0
    items_serialized = []
    for item in order.items:
        try:
            prod = db["product"].find_one({"_id": ObjectId(item.product_id)})
        except Exception:
            prod = None
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
        price = float(prod.get("price", 0))
        line_total = price * item.quantity
        total += line_total
        items_serialized.append({
            "product_id": item.product_id,
            "title": prod.get("title"),
            "size": item.size,
            "quantity": item.quantity,
            "unit_price": price,
            "line_total": line_total,
        })

    order_doc = {
        "items": items_serialized,
        "customer": order.customer.model_dump(),
        "total": round(total, 2),
        "status": "received",
    }
    order_id = create_document("order", order_doc)
    saved = db["order"].find_one({"_id": ObjectId(order_id)})
    return serialize_doc(saved)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
