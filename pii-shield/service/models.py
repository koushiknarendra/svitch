from pydantic import BaseModel
from typing import Literal


class DetectRequest(BaseModel):
    text: str
    locale: Literal["in", "global", "all"] = "all"


class EntityResponse(BaseModel):
    type: str
    value: str
    start: int
    end: int


class DetectResponse(BaseModel):
    entities: list[EntityResponse]
    count: int


class RedactRequest(BaseModel):
    text: str
    locale: Literal["in", "global", "all"] = "all"
    replacement: Literal["token", "mask"] = "token"


class RedactResponse(BaseModel):
    text: str
    original_text: str
    entities: list[EntityResponse]
    count: int


class WrapRequest(BaseModel):
    messages: list[dict]
    locale: Literal["in", "global", "all"] = "all"
    replacement: Literal["token", "mask"] = "token"


class WrapResponse(BaseModel):
    messages: list[dict]
    redacted_count: int
    entities_by_message: list[list[EntityResponse]]
