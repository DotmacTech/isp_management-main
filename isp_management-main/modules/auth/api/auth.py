# modules/auth/api/auth.py
from .models import User

def get_current_active_user(token: str) -> User:
    # Replace with your logic for fetching the active user based on the token
    return User(id=1, username="admin", email="admin@example.com", is_admin=True)
