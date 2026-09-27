"""Model registry: price, window, image input and a plain-language card per model.

Loaded and validated once at import, so a bad entry fails at boot rather than
mid-run. Prices stay dollar strings; agent/budget converts them to nanos.
"""

import tomllib
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent import PACKAGE_ROOT

Dollars = Annotated[str, Field(pattern=r"^\d+(\.\d+)?$")]


class Rates(BaseModel):
    """USD per million tokens."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input: Dollars
    output: Dollars
    cache_read: Dollars
    cache_write: Dollars


class LongContext(Rates):
    """Rates for the whole request once its input exceeds `above` tokens."""

    above: int = Field(gt=0)


class Card(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    what: str
    not_for: str
    speed: Literal["fast", "medium", "slow"]
    cost: Literal["free", "cheap", "moderate", "expensive"]


class ModelEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    provider: Literal["openai", "gemini", "openrouter"]
    context_window: int = Field(gt=0)
    attachment: bool
    auto: bool
    cost: Rates
    long_context: LongContext | None = None
    card: Card


def _load() -> tuple[dict[str, ModelEntry], str, Rates]:
    raw = tomllib.loads((PACKAGE_ROOT / "routing" / "models.toml").read_text())
    entries = [ModelEntry.model_validate(item) for item in raw["models"]]
    models = {entry.id: entry for entry in entries}
    if len(models) != len(entries):
        raise ValueError("models.toml lists a model id more than once")
    return models, raw["router"]["model"], Rates.model_validate(raw["router"]["cost"])


MODELS, JEV_MODEL, JEV_COST = _load()
