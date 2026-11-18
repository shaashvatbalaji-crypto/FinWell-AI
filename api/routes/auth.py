
import re
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from config.settings import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from mysql_pipeline.user_storage import create_user, get_user_by_email
from services.security import hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("username", "email")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value.lower()


class LoginRequest(BaseModel):
    email: str
    password: str


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    password_hash = hash_password(request.password)

    result = create_user(
        username=request.username,
        email=request.email,
        password_hash=password_hash,
    )

    if not result.get("success"):
        if result.get("message") == "Username or email already exists.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result["message"],
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to create account. Please try again.",
        )

    return {
        "success": True,
        "message": "Account created successfully.",
        "user": {
            "user_id": result["user_id"],
            "username": result["username"],
            "email": result["email"],
        },
    }


@router.post("/login")
def login(request: LoginRequest):
    user = get_user_by_email(request.email.strip().lower())

    if (
        user is None
        or not user.get("password_hash")
        or not verify_password(request.password, user["password_hash"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token = create_access_token(user["user_id"])

    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
        },
    }
