from pydantic import BaseModel, EmailStr, Field

from models import CustomModel, UtcDatetime


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


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterResponse(CustomModel):
    verification_required: bool = True
    message: str = "Check your email to verify your account."


class VerificationRequested(CustomModel):
    message: str = "If this account needs verification, an email is on its way. Check your inbox and spam folder."


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str = Field(default="", max_length=280)


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
