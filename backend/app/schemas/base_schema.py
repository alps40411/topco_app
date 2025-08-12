# backend/app/schemas/base_schema.py
from pydantic import BaseModel

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True # SQLAlchemy 2.0 orm_mode is deprecated