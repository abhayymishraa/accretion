"""Business logic for authentication.

The router validates and routes; every database read, token issue and
email send happens here.
"""

from datetime import UTC, datetime

from disposable_email_domains import blocklist
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.budget.budget import allowance
from auth.exceptions import (
    AccountUnavailable,
    DisposableEmail,
    EmailNotVerifiedForSignIn,
    EmailTaken,
    EmailTakenConflict,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidRequest,
    InvalidTokenPayload,
    NameRequired,
    VerificationNotConfigured,
)
from auth.models import AuthIdentity, AuthToken
from db.models import User

from .schemas import (
    CostAllowance,
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
from .utils import (
    canonical_email,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from .verification import consume_token, email_configured, send_verification


async def register_user(user: UserRegister, request_ip: str, db: AsyncSession) -> RegisterResponse:
    if not email_configured():
        raise VerificationNotConfigured
    email = canonical_email(str(user.email))
    # Throwaway addresses pass verification, so the blocklist is the only thing
    # standing between a scripted signup and a free monthly build budget. Parent
    # domains are checked too: mailinator and friends hand out every subdomain.
    labels = email.rsplit("@", 1)[-1].split(".")
    if any(".".join(labels[i:]) in blocklist for i in range(len(labels) - 1)):
        raise DisposableEmail
    existing = await db.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise EmailTaken
    if not user.name.strip():
        raise NameRequired
    new_user = User(
        email=email,
        hashed_password=get_password_hash(user.password),
        name=user.name.strip(),
    )
    db.add(new_user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise EmailTakenConflict from None
    await send_verification(db, new_user, request_ip)
    await db.commit()
    return RegisterResponse()


async def login_user(user_data: UserLogin, db: AsyncSession) -> Token:
    """Authenticate user and return jwt"""

    result = await db.execute(select(User).where(func.lower(User.email) == canonical_email(str(user_data.email))))

    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise InvalidCredentials

    if not user.email_verified:
        raise EmailNotVerifiedForSignIn

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(access_token=access_token, refresh_token=refresh_token)


async def refresh_token(token_data: RefreshTokenRequest, db: AsyncSession) -> Token:
    """refresh access token using refresh token"""

    payload = decode_token(token_data.refresh_token, token_type="refresh")

    if payload is None:
        raise InvalidRefreshToken

    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidTokenPayload

    result = await db.execute(select(User).where(User.id == int(user_id)))

    user = result.scalar_one_or_none()
    if user is None or (not user.email_verified):
        raise InvalidRequest

    acccess_token = create_access_token(data={"sub": str(user.id)})

    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(access_token=acccess_token, refresh_token=new_refresh_token)


async def get_me(current_user: User, db: AsyncSession) -> UserResponse:
    response = UserResponse.model_validate(current_user)
    response.providers = list(
        await db.scalars(select(AuthIdentity.provider).where(AuthIdentity.user_id == current_user.id))
    )
    response.cost_allowance = CostAllowance.model_validate(await allowance(db, current_user))
    return response


async def update_me(
    profile: ProfileUpdate,
    current_user: User,
    db: AsyncSession,
) -> UserResponse:
    if not profile.name.strip():
        raise NameRequired
    current_user.name = profile.name.strip()
    current_user.bio = profile.bio.strip()
    await db.commit()
    return await get_me(current_user, db)


async def request_verification(data: EmailRequest, request_ip: str, db: AsyncSession) -> VerificationRequested:
    if not email_configured():
        raise VerificationNotConfigured
    user = await db.scalar(select(User).where(func.lower(User.email) == canonical_email(str(data.email))))
    if user and not user.email_verified:
        await send_verification(db, user, request_ip)
        await db.commit()
    return VerificationRequested()


async def confirm_verification(data: TokenRequest, db: AsyncSession) -> Token:
    user_id = await consume_token(db, data.token, "verify_email")
    user = await db.get(User, user_id)
    if not user:
        raise AccountUnavailable
    user.email_verified = True
    await db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user_id,
            AuthToken.purpose == "verify_email",
            AuthToken.consumed_at.is_(None),
        )
        .values(consumed_at=datetime.now(UTC))
    )
    await db.commit()
    return Token(
        access_token=create_access_token({"sub": str(user_id)}),
        refresh_token=create_refresh_token({"sub": str(user_id)}),
    )
