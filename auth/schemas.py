from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from plans import DEFAULT_PLAN, plan_credits


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CostWindow(BaseModel):
    limit_usd: float
    used_or_reserved_usd: float
    remaining_usd: float
    resets_at: datetime


class CostAllowance(BaseModel):
    unlimited: bool
    currency: str = "USD"
    reset_timezone: str = "UTC"
    daily: CostWindow
    monthly: CostWindow


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    bio: str = ""
    email_verified: bool = False
    providers: list[str] = Field(default_factory=list)
    created_at: datetime
    last_query_at: datetime | None = None
    tokens_remaining: int = plan_credits(DEFAULT_PLAN)
    credits_limit: int = plan_credits(DEFAULT_PLAN)
    credits_unlimited: bool = False
    tokens_reset_at: datetime | None = None
    cost_allowance: CostAllowance | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    verification_required: bool = True
    message: str = "Check your email to verify your account."


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str = Field(default="", max_length=280)


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
