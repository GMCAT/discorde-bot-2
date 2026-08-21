from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ServiceRequest:
    bot_id: str
    chat_id: str
    user_id: str | None
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceResponse:
    success: bool
    service: str
    message: str | list[str]
    error_code: str | None = None

