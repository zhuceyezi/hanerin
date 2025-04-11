from pydantic import BaseModel
from typing import Any, Optional
from typing import Generic, TypeVar
from enum import IntEnum

T = TypeVar("T")


class MessageType(IntEnum):
    TEXT = 0
    IMAGE = 1
    MARKDOWN = 2
    ARK = 3
    EMBED = 4


class ValidationData(BaseModel):
    plain_token: str
    event_ts: str


class CallbackPayload(BaseModel):
    op: int
    d: ValidationData


class RequestPayload(BaseModel, Generic[T]):
    op: int
    d: T
    t: Optional[str] = None
    s: Optional[int] = None
    id: Optional[str] = None

class ParameterPayload(BaseModel):
    payload: Any
    type: str
    openid: str


class SendMessagePayload(BaseModel):
    msg_type: MessageType
    content: Optional[str] = None
    # 以下字段根据 msg_type 决定是否使用
    markdown: Optional[dict] = None
    keyboard: Optional[dict] = None
    ark: Optional[dict] = None
    media: Optional[dict] = None
    msg_id: str
    msg_seq: Optional[int] = None


class SendResponsePayload(BaseModel):
    id: str  # 消息唯一ID
    timestamp: int  # 发送时间
