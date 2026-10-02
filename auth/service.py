"""Business logic for authentication.

The router validates and routes; every database read, token issue and
email send happens here.
"""

from datetime import UTC, datetime
from typing import Literal

from disposable_email_domains import blocklist
from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.budget.budget import allowance
from auth import emails
from auth.exceptions import (
    AccountUnavailable,
    ApplicantNotFound,
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
    AccountCounts,
    AccountPage,
    AccountRow,
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
    initial_access,
    verify_password,
)
from .verification import (
    consume_token,
    email_configured,
    frontend_url,
    issue_token,
    send_verification,
    token_digest,
)


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
        **initial_access(email),
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
    # The admin hears about a signup once its address is proven, not before.
    newly_waiting = user.waitlisted and not user.email_verified
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
    if newly_waiting:
        await emails.notify_admin(user)
    return Token(
        access_token=create_access_token({"sub": str(user_id)}),
        refresh_token=create_refresh_token({"sub": str(user_id)}),
    )


async def list_users(
    status: Literal["waiting", "approved", "all"], search: str, page: int, db: AsyncSession
) -> AccountPage:
    page_size = 25
    waiting, approved = User.approved_at.is_(None), User.approved_at.is_not(None)
    filters: list[ColumnElement[bool]] = []
    if status == "waiting":
        filters.append(waiting)
    elif status == "approved":
        filters.append(approved)
    term = search.strip()
    if term:
        filters.append(or_(User.name.icontains(term, autoescape=True), User.email.icontains(term, autoescape=True)))
    total = await db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    # Waitlisted first, newest first within each group.
    users = await db.scalars(
        select(User)
        .where(*filters)
        .order_by(approved, User.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    counts = (
        await db.execute(
            select(
                func.count().filter(waiting),
                func.count().filter(approved),
                func.count().filter(waiting, User.email_verified.is_(False)),
            )
        )
    ).one()
    return AccountPage(
        items=[AccountRow.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        counts=AccountCounts(waiting=counts[0], approved=counts[1], unconfirmed=counts[2]),
    )


async def approve_user(user_id: int, db: AsyncSession) -> AccountRow:
    user = await db.get(User, user_id, with_for_update=True)
    if not user:
        raise ApplicantNotFound
    if user.waitlisted:
        user.approved_at = datetime.now(UTC)
        # A verify_email token doubles as the one-click sign-in: consuming it proves the
        # address and returns a session, so the approval link needs no endpoint of its own.
        token = await issue_token(db, user.id, "verify_email", minutes=7 * 24 * 60)
        link = f"{frontend_url()}/verify-email#token={token}"
        await emails.send(
            user.email,
            *emails.approved(user.name, link),
            f"approved-{token_digest(token)}",
        )
    await db.commit()
    return AccountRow.model_validate(user)
