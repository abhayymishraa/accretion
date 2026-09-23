"""Readiness failures."""

from exceptions import ServiceUnavailable


class DatabaseUnavailable(ServiceUnavailable):
    DETAIL = "Database unavailable"
