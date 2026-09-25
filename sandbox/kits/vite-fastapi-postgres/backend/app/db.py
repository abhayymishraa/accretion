from collections.abc import Iterator

from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Settings(BaseSettings):
    database_url: str


settings = Settings()  # reads DATABASE_URL from the environment
# psycopg 3 driver; DATABASE_URL uses the plain postgresql:// scheme.
engine = create_engine(settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1))


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
