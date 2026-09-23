from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from db.models import User, AuthIdentity, AuthToken
from db.base import get_db
from agent.budget.budget import allowance
from .schemas import (
    UserLogin,
    UserResponse,
    UserRegister,
    Token,
    RefreshTokenRequest,
    RegisterResponse,
    ProfileUpdate,
    EmailRequest,
    TokenRequest,
    CostAllowance,
)

from .utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from .dependencies import get_current_user
from .verification import email_configured, send_verification, consume_token
from datetime import datetime, timezone

from disposable_email_domains import blocklist
from plans import month_window

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user: UserRegister, request: Request, db: AsyncSession = Depends(get_db)
):
    if not email_configured():
        raise HTTPException(
            503, "Email verification is not configured yet. Please try again later."
        )
    email = str(user.email).lower()
    # Throwaway addresses pass verification, so the blocklist is the only thing
    # standing between a scripted signup and a free monthly credit grant. Parent
    # domains are checked too: mailinator and friends hand out every subdomain.
    labels = email.rsplit("@", 1)[-1].split(".")
    if any(".".join(labels[i:]) in blocklist for i in range(len(labels) - 1)):
        raise HTTPException(
            422, "Disposable email addresses are not accepted. Use a permanent address."
        )
    existing = await db.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise HTTPException(
            400, "Email already registered. Sign in or request a verification email."
        )
    if not user.name.strip():
        raise HTTPException(422, "Enter your name.")
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
        raise HTTPException(409, "Email already registered.") from None
    await send_verification(
        db, new_user, request.client.host if request.client else "unknown"
    )
    await db.commit()
    return RegisterResponse()


@router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return jwt"""

    result = await db.execute(
        select(User).where(func.lower(User.email) == str(user_data.email).lower())
    )

    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="incorrect email or pass"
        )

    if not user.email_verified:
        raise HTTPException(403, "Verify your email before signing in.")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """refresh access token using refresh token"""

    payload = decode_token(token_data.refresh_token, token_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inavalid refresh token"
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))

    user = result.scalar_one_or_none()
    if user is None or (not user.email_verified):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid request"
        )

    acccess_token = create_access_token(data={"sub": str(user.id)})

    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(access_token=acccess_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    response = UserResponse.model_validate(current_user)
    # Reflect the available allowance without starting a new window on a profile read.
    if not response.credits_unlimited and (
        response.tokens_reset_at is None
        or response.tokens_reset_at <= datetime.now(timezone.utc)
    ):
        response.tokens_remaining = current_user.credits_limit
        response.tokens_reset_at = month_window(datetime.now(timezone.utc))[1]
    response.providers = list(
        await db.scalars(
            select(AuthIdentity.provider).where(AuthIdentity.user_id == current_user.id)
        )
    )
    response.cost_allowance = CostAllowance.model_validate(await allowance(db, current_user))
    return response


@router.patch("/me", response_model=UserResponse)
async def update_me(
    profile: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not profile.name.strip():
        raise HTTPException(422, "Enter your name.")
    current_user.name = profile.name.strip()
    current_user.bio = profile.bio.strip()
    await db.commit()
    return await get_me(current_user, db)


@router.post("/verification/request", status_code=202)
async def request_verification(
    data: EmailRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    if not email_configured():
        raise HTTPException(
            503, "Email verification is not configured yet. Please try again later."
        )
    user = await db.scalar(
        select(User).where(func.lower(User.email) == str(data.email).lower())
    )
    if user and not user.email_verified:
        await send_verification(
            db, user, request.client.host if request.client else "unknown"
        )
        await db.commit()
    return {
        "message": "If this account needs verification, an email is on its way. Check your inbox and spam folder."
    }


@router.post("/verification/confirm", response_model=Token)
async def confirm_verification(data: TokenRequest, db: AsyncSession = Depends(get_db)):
    user_id = await consume_token(db, data.token, "verify_email")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(400, "This account is no longer available.")
    user.email_verified = True
    await db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user_id,
            AuthToken.purpose == "verify_email",
            AuthToken.consumed_at.is_(None),
        )
        .values(consumed_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return Token(
        access_token=create_access_token({"sub": str(user_id)}),
        refresh_token=create_refresh_token({"sub": str(user_id)}),
    )
