"""Failures callers can see when using GitHub."""

from exceptions import BadRequest, Conflict, NotFound, PermissionDenied, ServiceUnavailable, UnprocessableEntity


class GithubNotConfigured(ServiceUnavailable):
    DETAIL = "GitHub isn't set up on this server yet."


class GithubNotConnected(BadRequest):
    DETAIL = "Connect GitHub first."


class GithubReconnect(BadRequest):
    DETAIL = "Reconnect GitHub to keep saving."


class GithubUnavailable(ServiceUnavailable):
    DETAIL = "Couldn't reach GitHub. Try again in a moment."


class SignInExpired(BadRequest):
    DETAIL = "This sign-in expired or was already used. Connect again."


class SignInUnavailable(ServiceUnavailable):
    DETAIL = "Sign-in is unavailable right now. Try again in a moment."


class RepoNotLinked(NotFound):
    DETAIL = "This project isn't saved to GitHub."


class RepoAlreadyLinked(Conflict):
    DETAIL = "This project is already saved to GitHub."


class RepoNotFound(NotFound):
    DETAIL = "GitHub can't find this repository. Check that Accretion can reach it."


class RepoEmpty(UnprocessableEntity):
    DETAIL = "This repository has no files yet."


class RepoNotSupported(UnprocessableEntity):
    DETAIL = (
        "This repository's setup can't be run here yet. Accretion runs Next.js, Vite + Express or Vite + FastAPI apps."
    )


class RepoTooBig(UnprocessableEntity):
    DETAIL = "This repository is too big to open here: at most 600 files and 64 MB."


class ProjectHasNoFiles(BadRequest):
    DETAIL = "Build the app once before saving it to GitHub."


class BranchNameInvalid(BadRequest):
    DETAIL = "Use letters, numbers, dots, dashes, underscores and slashes for the branch name."


class BranchExists(Conflict):
    DETAIL = "A branch with this name already exists."


class NothingToApprove(BadRequest):
    DETAIL = "No workflow file is waiting for approval."


class WebhookSignatureInvalid(PermissionDenied):
    DETAIL = "Invalid signature"


class BranchNotFound(NotFound):
    DETAIL = "GitHub can't find this branch."


class SameBranch(BadRequest):
    DETAIL = "This project already saves to the main branch."


class NothingToMerge(BadRequest):
    DETAIL = "This branch has no changes the main branch lacks."
