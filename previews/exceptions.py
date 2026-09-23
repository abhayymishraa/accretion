"""Failures callers can see when opening or inspecting a preview."""

from exceptions import ServiceUnavailable


class PreviewUnavailable(ServiceUnavailable):
    DETAIL = "Preview could not start. Saved files are still available; retry opening the preview."
