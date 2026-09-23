"""Probe responses."""

from models import CustomModel


class Liveness(CustomModel):
    message: str
    status: str


class Readiness(CustomModel):
    status: str
