import hashlib

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from redis import Redis

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.security import create_access_token
from shared.security import create_refresh_token
from shared.security import decode_token

from .database import get_db
from .models import User
from .schemas import LoginRequest
from .schemas import RefreshRequest
from .schemas import RegisterRequest
from .schemas import TokenResponse
from .schemas import UserResponse
from .security import hash_password
from .security import verify_password

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


redis_client = Redis.from_url(
    "redis://redis:6379/0",
    decode_responses=True,
)


def token_key(token: str) -> str:

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    return f"revoked_token:{token_hash}"


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):

    existing_user = db.scalar(select(User).where(User.email == request.email))

    if existing_user:

        raise HTTPException(
            status_code=409,
            detail="User already exists",
        )

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        role="user",
    )

    db.add(user)

    db.commit()

    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    user = db.scalar(select(User).where(User.email == request.email))

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(
        request.password,
        user.password_hash,
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not user.is_active:

        raise HTTPException(
            status_code=403,
            detail="User is inactive",
        )

    roles = [user.role]

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        roles=roles,
    )

    refresh_token = create_refresh_token(
        user_id=user.id,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(
    request: RefreshRequest,
):

    try:

        payload = decode_token(request.refresh_token)

    except ValueError:

        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":

        raise HTTPException(
            status_code=401,
            detail="Invalid token type",
        )

    if redis_client.exists(token_key(request.refresh_token)):

        raise HTTPException(
            status_code=401,
            detail="Refresh token revoked",
        )

    user_id = int(payload["sub"])

    access_token = create_access_token(
        user_id=user_id,
        email="",
        roles=["user"],
    )

    new_refresh_token = create_refresh_token(
        user_id=user_id,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
def logout(
    request: RefreshRequest,
):

    try:

        payload = decode_token(request.refresh_token)

    except ValueError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    exp = payload.get("exp")

    if exp:

        import time

        ttl = max(
            int(exp - time.time()),
            1,
        )

        redis_client.setex(
            token_key(request.refresh_token),
            ttl,
            "1",
        )

    return {"message": "Successfully logged out"}
