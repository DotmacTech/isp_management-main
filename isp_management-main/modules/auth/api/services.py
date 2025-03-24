from .schemas import LoginRequest, LoginResponse, UserCreate, UserUpdate, UserResponse
from fastapi import HTTPException

class AuthService:
    @staticmethod
    def login(login_request: LoginRequest) -> LoginResponse:
        # Logic for user authentication (this is just an example)
        if login_request.email == "admin@example.com" and login_request.password == "password":
            return LoginResponse(access_token="fake-access-token", token_type="bearer")
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    @staticmethod
    def register(user_create: UserCreate) -> UserResponse:
        # Logic to create a new user (example)
        return UserResponse(
            id=1, 
            email=user_create.email, 
            first_name=user_create.first_name, 
            last_name=user_create.last_name, 
            is_active=True
        )

    @staticmethod
    def update_user(user_update: UserUpdate, user_id: int) -> UserResponse:
        # Logic to update a user (example)
        return UserResponse(
            id=user_id, 
            email=user_update.email or "existing@example.com", 
            first_name=user_update.first_name or "John", 
            last_name=user_update.last_name or "Doe", 
            is_active=user_update.is_active if user_update.is_active is not None else True
        )
