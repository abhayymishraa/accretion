from dataclasses import dataclass

from pydantic import BaseModel, EmailStr, Field

from models import CustomModel, UtcDatetime


@dataclass(frozen=True)
class TokenUser:
    """The caller as their access token states it, read without a database query. Waitlist,
    role and removal changes reach it when the token is renewed, within its 30 minutes."""

    id: int
    role: str
    approved: bool


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(CustomModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CostAllowance(CustomModel):
    """This month's model budget. Resets on the first of the month, UTC."""

    unlimited: bool
    limit_usd: float
    remaining_usd: float
    resets_at: UtcDatetime


class UserResponse(CustomModel):
    id: int
    email: EmailStr
    name: str
    bio: str = ""
    email_verified: bool = False
    providers: list[str] = Field(default_factory=list)
    created_at: UtcDatetime
    cost_allowance: CostAllowance | None = None
    default_model_choice: str = "auto"
    waitlisted: bool = True


class AccountRow(CustomModel):
    """One account as the admin's waitlist page lists it."""

    id: int
    email: EmailStr
    name: str
    email_verified: bool
    created_at: UtcDatetime
    approved_at: UtcDatetime | None


class AccountCounts(CustomModel):
    waiting: int
    approved: int
    unconfirmed: int


class AccountPage(CustomModel):
    """One page of the admin's account list, with totals across every account."""

    items: list[AccountRow]
    total: int
    page: int
    page_size: int
    counts: AccountCounts


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterResponse(CustomModel):
    verification_required: bool = True
    message: str = "You're on the waitlist. Check your email to confirm your spot."


class VerificationRequested(CustomModel):
    message: str = "If this account needs verification, an email is on its way. Check your inbox and spam folder."


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str = Field(default="", max_length=280)


class EmailRequest(BaseModel):
    email: EmailStr


class AuthOptions(CustomModel):
    providers: dict[str, bool]
    email_verification: bool


class ProviderLink(CustomModel):
    url: str


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
