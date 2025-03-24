# modules/auth/api/models.py

from pydantic import BaseModel

class User(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
