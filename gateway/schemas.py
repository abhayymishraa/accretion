"""Request and response bodies for the app services."""

from pydantic import EmailStr, Field

from models import CustomModel


class EmailSent(CustomModel):
    sent: bool = True


class EmailSignIn(CustomModel):
    email: EmailStr
    redirect_uri: str = Field(max_length=2048)


class SignInSession(CustomModel):
    sub: str
    email: str
    name: str | None = None
    picture: str | None = None
    exp: int


class SignInMethods(CustomModel):
    google: bool


class AppServices(CustomModel):
    sign_in: SignInMethods
