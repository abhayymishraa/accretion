"""Business logic for authentication.

The router validates and routes; every database read, token issue and
email send happens here.
"""

import secrets
from datetime import UTC, datetime
from typing import Literal

from disposable_email_domains import blocklist
from fastapi import BackgroundTasks
from sqlalchemy import ColumnElement, DateTime, delete, exists, func, insert, literal, or_, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from agent.budget.budget import NANOS, allowance, month_spend
from agent.budget.models import SpendEntry
from auth import emails
from auth.exceptions import (
    ApplicantNotFound,
    DemoLinkInvalid,
    DisposableEmail,
    EmailNotVerified,
    EmailNotVerifiedForSignIn,
    EmailTaken,
    EmailTakenConflict,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidRequest,
    InvalidTokenPayload,
    NameRequired,
    UserNotFound,
    VerificationLinkUsed,
    VerificationNotConfigured,
)
from auth.models import AuthIdentity, AuthToken
from auth.schemas import (
    AccountCounts,
    AccountPage,
    AccountRow,
    AccountRun,
    CostAllowance,
    DemoAccount,
    DemoAccountCreate,
    DemoLink,
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
from auth.utils import (
    canonical_email,
    decode_token,
    get_password_hash,
    initial_access,
    issue_tokens,
    verify_password,
)
from auth.verification import (
    email_configured,
    first_link,
    issue_token,
    limit_caller,
    send_approval,
    send_link,
    token_digest,
    token_insert,
)
from db.base import bound
from db.models import Chat, Run, User
from plans import DEMO_PLAN, month_window


async def register_user(
    user: UserRegister, request_ip: str, background: BackgroundTasks, db: AsyncSession
) -> RegisterResponse:
    if not email_configured():
        raise VerificationNotConfigured
    email = canonical_email(str(user.email))
    # Throwaway addresses pass verification, so the blocklist is the only thing
    # standing between a scripted signup and a free monthly build budget. Parent
    # domains are checked too: mailinator and friends hand out every subdomain.
    labels = email.rsplit("@", 1)[-1].split(".")
    if any(".".join(labels[i:]) in blocklist for i in range(len(labels) - 1)):
        raise DisposableEmail
    name = user.name.strip()
    if not name:
        raise NameRequired
    await limit_caller(request_ip)
    # One statement: the account, unless the address is taken (older rows may differ in case), and
    # its link. Column defaults are not applied to an INSERT ... SELECT: every value is given.
    values = bound(
        User,
        email=email,
        hashed_password=get_password_hash(user.password),
        name=name,
        created_at=datetime.now(UTC),
        **initial_access(email),
    )
    taken = select(User.id).where(func.lower(User.email) == email).exists()
    account = (
        insert(User).from_select(list(values), select(*values.values()).where(~taken)).returning(User.id).cte("account")
    )
    statement, token = token_insert(account.c.id, "verify_email", 30, request_ip)
    try:
        created = await db.scalar(statement.returning(AuthToken.user_id))
    except IntegrityError:
        raise EmailTakenConflict from None
    if created is None:
        raise EmailTaken
    # Marked only once the account exists: a refused sign-up leaves the address's resend free.
    await first_link(email)
    background.add_task(send_link, email, name, token)
    return RegisterResponse()


async def login_user(user_data: UserLogin, db: AsyncSession) -> Token:
    """Authenticate user and return jwt"""
    user = await db.scalar(select(User).where(func.lower(User.email) == canonical_email(str(user_data.email))))
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise InvalidCredentials

    if not user.email_verified:
        raise EmailNotVerifiedForSignIn

    return issue_tokens(user)


async def refresh_token(token_data: RefreshTokenRequest, db: AsyncSession) -> Token:
    """refresh access token using refresh token"""

    payload = decode_token(token_data.refresh_token, token_type="refresh")

    if payload is None:
        raise InvalidRefreshToken

    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidTokenPayload

    # A demo session ends with the link it was opened with: revoked or replaced, it renews no more,
    # within the access token's 30 minutes.
    demo_link = payload.get("demo_link")
    live_link = exists().where(
        AuthToken.user_id == User.id, AuthToken.purpose == _DEMO_LINK, AuthToken.digest == demo_link
    )
    user = await db.scalar(select(User).where(User.id == int(user_id), or_(User.plan != DEMO_PLAN, live_link)))
    if user is None or (not user.email_verified):
        raise InvalidRequest

    return issue_tokens(user, demo_link)


async def get_me(user_id: int, db: AsyncSession, changes: dict[str, str] | None = None) -> UserResponse:
    """The account, its sign-in providers and this month's balance, in one query. With `changes`,
    the same statement saves them first and reads the saved row (the update's RETURNING), so a
    profile save is one round trip committed by itself."""
    # One clock read, so the balance and its reset date always describe the same month.
    month = month_window(datetime.now(UTC))
    account = (
        aliased(User, update(User).where(User.id == user_id).values(**changes).returning(User).cte("saved"))
        if changes
        else User
    )
    providers = select(func.array_agg(AuthIdentity.provider)).where(AuthIdentity.user_id == account.id)
    row = (
        await db.execute(
            select(account, providers.scalar_subquery(), month_spend(user_id, *month).scalar_subquery()).where(
                account.id == user_id
            )
        )
    ).first()
    if row is None:
        raise UserNotFound
    user, provider_names, used = row
    if not user.email_verified:
        raise EmailNotVerified
    response = UserResponse.model_validate(user)
    response.providers = provider_names or []
    response.cost_allowance = CostAllowance.model_validate(allowance(user, used, month))
    return response


async def update_me(profile: ProfileUpdate, user_id: int, db: AsyncSession) -> UserResponse:
    if not profile.name.strip():
        raise NameRequired
    return await get_me(user_id, db, {"name": profile.name.strip(), "bio": profile.bio.strip()})


async def request_verification(
    data: EmailRequest, request_ip: str, background: BackgroundTasks, db: AsyncSession
) -> VerificationRequested:
    if not email_configured():
        raise VerificationNotConfigured
    email = canonical_email(str(data.email))
    await limit_caller(request_ip)
    if not await first_link(email):
        return VerificationRequested()
    # One statement: a link for the account at this address, only while it is unverified.
    account = (
        select(User.id, User.email, User.name)
        .where(func.lower(User.email) == email, User.email_verified.is_(False))
        .cte("account")
    )
    statement, token = token_insert(account.c.id, "verify_email", 30, request_ip)
    issued = statement.returning(AuthToken.user_id).cte("issued")
    found = (
        await db.execute(select(account.c.email, account.c.name).join(issued, issued.c.user_id == account.c.id))
    ).first()
    if found:
        background.add_task(send_link, found.email, found.name, token)
    return VerificationRequested()


async def confirm_verification(data: TokenRequest, background: BackgroundTasks, db: AsyncSession) -> Token:
    # One statement: the link consumed, the account's other links retired, the account verified, and
    # whether it was verified before. `now` is an anonymous bind: two SETs of consumed_at share it.
    now = literal(datetime.now(UTC), DateTime(timezone=True))
    digest = token_digest(data.token)
    links = (AuthToken.purpose == "verify_email", AuthToken.consumed_at.is_(None))
    consumed = (
        update(AuthToken)
        .where(AuthToken.digest == digest, AuthToken.expires_at > now, *links)
        .values(consumed_at=now)
        .returning(AuthToken.user_id)
        .cte("consumed")
    )
    retired = (
        update(AuthToken)
        .where(AuthToken.user_id.in_(select(consumed.c.user_id)), AuthToken.digest != digest, *links)
        .values(consumed_at=now)
        .cte("retired")
    )
    before = aliased(User)
    row = (
        await db.execute(
            update(User)
            .where(User.id == before.id, User.id.in_(select(consumed.c.user_id)))
            .values(email_verified=True)
            .returning(User, before.email_verified)
            .add_cte(retired),
            execution_options={"synchronize_session": False},
        )
    ).first()
    if row is None:
        raise VerificationLinkUsed
    user, was_verified = row
    # The admin hears about a signup once its address is proven, not before.
    if user.waitlisted and not was_verified:
        background.add_task(emails.notify_admin, user)
    return issue_tokens(user)


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
    # The totals and the page in one query: one totals row, joined to the page's rows (none on an
    # empty page). Waitlisted first, newest first within each group.
    totals = select(
        func.count().filter(*filters).label("total") if filters else func.count().label("total"),
        func.count().filter(waiting).label("waiting"),
        func.count().filter(approved).label("approved"),
        func.count().filter(waiting, User.email_verified.is_(False)).label("unconfirmed"),
    ).subquery()
    rows = select(User).where(*filters).order_by(approved, User.created_at.desc())
    page_rows = rows.limit(page_size).offset((page - 1) * page_size).subquery()
    listed = aliased(User, page_rows)
    result = (
        await db.execute(
            select(totals, listed)
            .select_from(totals)
            .outerjoin(page_rows, true())
            .order_by(listed.approved_at.is_not(None), listed.created_at.desc())
        )
    ).all()
    counts = result[0]
    return AccountPage(
        items=[AccountRow.model_validate(row[-1]) for row in result if row[-1] is not None],
        total=counts.total,
        page=page,
        page_size=page_size,
        counts=AccountCounts(waiting=counts.waiting, approved=counts.approved, unconfirmed=counts.unconfirmed),
    )


async def approve_user(user_id: int, background: BackgroundTasks, db: AsyncSession) -> AccountRow:
    user = await db.get(User, user_id, with_for_update=True)
    if not user:
        raise ApplicantNotFound
    if user.waitlisted:
        user.approved_at = datetime.now(UTC)
    # A verify_email token doubles as the one-click sign-in: consuming it proves the address and
    # returns a session, so the approval link needs no endpoint of its own. Approving an account
    # again sends a fresh link, for an email that never arrived.
    token = await issue_token(db, user.id, "verify_email", minutes=7 * 24 * 60)
    background.add_task(send_approval, user.email, user.name, token)
    await db.commit()
    return AccountRow.model_validate(user)


# A demo link signs anyone who opens it into its account, as often as they like, until the admin
# revokes or replaces it. Only its digest is stored. ponytail: a far expiry, not a nullable column,
# so the token table and its sweep stay as they are.
_DEMO_LINK = "demo_link"
_DEMO_LINK_MINUTES = 100 * 365 * 24 * 60


async def create_demo_account(data: DemoAccountCreate, db: AsyncSession) -> DemoLink:
    """A verified, approved account on the demo plan, and its link, in one statement. The address
    is reserved (example.com) and the password a random value nobody keeps: the link is the only way in."""
    name = data.name.strip()
    if not name:
        raise NameRequired
    now = datetime.now(UTC)
    values = bound(
        User,
        email=f"demo-{secrets.token_hex(8)}@example.com",
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        name=name,
        created_at=now,
        approved_at=now,
        email_verified=True,
        plan=DEMO_PLAN,
        default_model_choice=data.model_choice,
    )
    account = insert(User).from_select(list(values), select(*values.values())).returning(User.id).cte("account")
    statement, token = token_insert(account.c.id, _DEMO_LINK, _DEMO_LINK_MINUTES)
    user_id = await db.scalar(statement.returning(AuthToken.user_id))
    assert user_id is not None
    return DemoLink(user_id=user_id, token=token)


async def replace_demo_link(user_id: int, db: AsyncSession) -> DemoLink:
    """A new link for a demo account, retiring its old one, in one statement."""
    account = select(User.id).where(User.id == user_id, User.plan == DEMO_PLAN).cte("account")
    old = (
        delete(AuthToken).where(AuthToken.user_id.in_(select(account.c.id)), AuthToken.purpose == _DEMO_LINK).cte("old")
    )
    statement, token = token_insert(account.c.id, _DEMO_LINK, _DEMO_LINK_MINUTES)
    if await db.scalar(statement.add_cte(old).returning(AuthToken.user_id)) is None:
        raise ApplicantNotFound
    return DemoLink(user_id=user_id, token=token)


async def revoke_demo_link(user_id: int, db: AsyncSession) -> None:
    """Idempotent: an account with no link stays without one."""
    await db.execute(delete(AuthToken).where(AuthToken.user_id == user_id, AuthToken.purpose == _DEMO_LINK))


async def redeem_demo_link(data: TokenRequest, db: AsyncSession) -> Token:
    """A session for the demo account the link belongs to, bound to that link. The link is not consumed."""
    digest = token_digest(data.token)
    user = await db.scalar(
        select(User)
        .join(AuthToken, AuthToken.user_id == User.id)
        .where(AuthToken.digest == digest, AuthToken.purpose == _DEMO_LINK, User.plan == DEMO_PLAN)
    )
    if user is None:
        raise DemoLinkInvalid
    return issue_tokens(user, digest)


async def list_demo_accounts(db: AsyncSession) -> list[DemoAccount]:
    """Every demo account, newest first. ponytail: one unpaged list; page it when there are hundreds."""
    link = exists().where(AuthToken.user_id == User.id, AuthToken.purpose == _DEMO_LINK)
    spent = select(func.coalesce(func.sum(SpendEntry.amount_nanos), 0)).where(
        SpendEntry.user_id == User.id, SpendEntry.kind == "model"
    )
    rows = await db.execute(
        select(
            User.id,
            User.name,
            User.created_at,
            User.default_model_choice,
            link.label("link_active"),
            spent.scalar_subquery().label("spent"),
        )
        .where(User.plan == DEMO_PLAN)
        .order_by(User.created_at.desc())
    )
    return [
        DemoAccount(
            id=row.id,
            name=row.name,
            created_at=row.created_at,
            link_active=row.link_active,
            spent_usd=row.spent / NANOS,
            default_model_choice=row.default_model_choice,
        )
        for row in rows
    ]


async def list_demo_runs(user_id: int, db: AsyncSession) -> list[AccountRun]:
    """A demo account's latest builds, read-only, for the admin."""
    rows = await db.execute(
        select(Run, Chat.title)
        .join(Chat, Chat.id == Run.chat_id)
        .join(User, User.id == Chat.user_id)
        .where(Chat.user_id == user_id, User.plan == DEMO_PLAN)
        .order_by(Run.created_at.desc())
        .limit(100)
    )
    return [
        AccountRun(id=run.id, project_title=title, prompt=run.prompt, status=run.status, created_at=run.created_at)
        for run, title in rows
    ]
