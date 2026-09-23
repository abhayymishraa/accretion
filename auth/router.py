"""Authentication endpoints: registration, sessions, tokens and verification."""

from fastapi import APIRouter, status

from auth import service
from db.base import DbSession

from .dependencies import ClientIp, CurrentUser
from .schemas import (
    EmailRequest,
    ProfileUpdate,
    RefreshTokenRequest,
    RegisterResponse,
    Token,
    TokenRequest,
    UserLogin,
    UserRegister,
    UserResponse,
    VerificationRequested,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserRegister, request_ip: ClientIp, db: DbSession) -> RegisterResponse:
    return await service.register_user(user=user, request_ip=request_ip, db=db)


@router.post("/login")
async def login_user(user_data: UserLogin, db: DbSession) -> Token:
    """Authenticate user and return jwt"""
    return await service.login_user(user_data=user_data, db=db)


@router.post("/refresh")
async def refresh_token(token_data: RefreshTokenRequest, db: DbSession) -> Token:
    """refresh access token using refresh token"""
    return await service.refresh_token(token_data=token_data, db=db)


@router.get("/me")
async def get_me(current_user: CurrentUser, db: DbSession) -> UserResponse:
    return await service.get_me(current_user=current_user, db=db)


@router.patch("/me")
async def update_me(
    profile: ProfileUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    return await service.update_me(profile=profile, current_user=current_user, db=db)


@router.post("/verification/request", status_code=202)
async def request_verification(data: EmailRequest, request_ip: ClientIp, db: DbSession) -> VerificationRequested:
    return await service.request_verification(data=data, request_ip=request_ip, db=db)


@router.post("/verification/confirm")
async def confirm_verification(data: TokenRequest, db: DbSession) -> Token:
    return await service.confirm_verification(data=data, db=db)
