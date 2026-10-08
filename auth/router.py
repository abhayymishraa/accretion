"""Authentication endpoints: registration, sessions, tokens and verification."""

from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status

from auth import service, social
from auth.dependencies import AdminUser, ClientIp, SignedInUser, get_token_user
from auth.schemas import (
    AccountPage,
    AccountRow,
    AuthOptions,
    EmailRequest,
    ProfileUpdate,
    ProviderLink,
    RefreshTokenRequest,
    RegisterResponse,
    Token,
    TokenRequest,
    TokenUser,
    UserLogin,
    UserRegister,
    UserResponse,
    VerificationRequested,
)
from db.base import Autocommit, DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[Autocommit])
async def register_user(
    user: UserRegister, request_ip: ClientIp, background: BackgroundTasks, db: DbSession
) -> RegisterResponse:
    return await service.register_user(user=user, request_ip=request_ip, background=background, db=db)


@router.post("/login", dependencies=[Autocommit])
async def login_user(user_data: UserLogin, db: DbSession) -> Token:
    """Authenticate user and return jwt"""
    return await service.login_user(user_data=user_data, db=db)


@router.post("/refresh", dependencies=[Autocommit])
async def refresh_token(token_data: RefreshTokenRequest, db: DbSession) -> Token:
    """refresh access token using refresh token"""
    return await service.refresh_token(token_data=token_data, db=db)


@router.get("/me", dependencies=[Autocommit])
async def get_me(current_user: Annotated[TokenUser, Depends(get_token_user)], db: DbSession) -> UserResponse:
    return await service.get_me(current_user.id, db)


@router.patch("/me", dependencies=[Autocommit])
async def update_me(
    profile: ProfileUpdate,
    current_user: Annotated[TokenUser, Depends(get_token_user)],
    db: DbSession,
) -> UserResponse:
    return await service.update_me(profile, current_user.id, db)


@router.post("/verification/request", status_code=202, dependencies=[Autocommit])
async def request_verification(
    data: EmailRequest, request_ip: ClientIp, background: BackgroundTasks, db: DbSession
) -> VerificationRequested:
    return await service.request_verification(data=data, request_ip=request_ip, background=background, db=db)


@router.post("/verification/confirm", dependencies=[Autocommit])
async def confirm_verification(data: TokenRequest, background: BackgroundTasks, db: DbSession) -> Token:
    return await service.confirm_verification(data=data, background=background, db=db)


@router.get("/options")
async def auth_options() -> AuthOptions:
    return social.auth_options()


@router.post("/oauth/{provider}/link")
async def link_provider(provider: str, user: SignedInUser, db: DbSession) -> ProviderLink:
    return await social.link_provider(provider, user.id, db)


@router.get("/oauth/{provider}")
async def start_oauth(provider: str, request: Request, ticket: str | None = None, *, db: DbSession):
    return await social.start_oauth(provider, request, ticket, db)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, background: BackgroundTasks, db: DbSession):
    return await social.oauth_callback(provider, request, background, db)


@router.post("/oauth/exchange")
async def exchange_oauth(data: TokenRequest, db: DbSession) -> Token:
    return await social.exchange_oauth(data, db)


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("", dependencies=[Autocommit])
async def list_users(
    *,
    _: AdminUser,
    db: DbSession,
    status: Literal["waiting", "approved", "all"] = "waiting",
    search: Annotated[str, Query(max_length=100)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
) -> AccountPage:
    return await service.list_users(status=status, search=search, page=page, db=db)


@users_router.post("/{user_id}/approval")
async def approve_user(user_id: int, _: AdminUser, background: BackgroundTasks, db: DbSession) -> AccountRow:
    return await service.approve_user(user_id=user_id, background=background, db=db)
