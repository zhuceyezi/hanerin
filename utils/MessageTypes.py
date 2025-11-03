from typing import Optional, Any
from enum import StrEnum
from typing import TypeVar
from polars import Field
from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated, List

class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    AT = "at"

class BaseMessageSegment(BaseModel):
    type: Literal[MessageType.TEXT, MessageType.IMAGE]
    data: dict

class TextMessageSegmentData(BaseModel):
    text: str

class TextMessageSegment(BaseMessageSegment):
    type: Literal[MessageType.TEXT]
    data: TextMessageSegmentData

class AtMessageSegmentData(BaseModel):
    qq: int | Literal["all"]

class AtMessageSegment(BaseMessageSegment):
    type: Literal[MessageType.AT]
    data: AtMessageSegmentData

MessageSegment = Annotated[
    TextMessageSegment | AtMessageSegment,
    Field(discriminator='type')
]

type Message = List[MessageSegment] | str


class BaseEvent(BaseModel):
    time: int            # 事件发生时间戳
    self_id: int         # 接收事件的机器人QQ号
    post_type: Literal["message", "notice", "request", "meta_event"]  # 事件类型

class Sender(BaseModel):
    user_id: Optional[int] = None
    nickname: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[int] = None

class MessageEvent(BaseEvent):
    post_type: Literal['message']
    message_type: Literal['private', 'group']
    sub_type: Literal['normal', 'anonymous','notice']
    message_id: int
    user_id: int
    group_id: Optional[int] = None
    anonymous: Optional[dict] = None
    message: Message
    raw_message: str
    font: int
    sender: Sender

class NoticeEvent(BaseEvent):
    post_type: Literal["notice"]
    notice_type: str  # 通知子类型
    user_id: int
    group_id: int = None  # 如果是群通知
    # 根据需要添加其他字段

class RequestEvent(BaseEvent):
    post_type: Literal["request"]
    request_type: str  # 请求子类型
    user_id: int
    comment: str = None
    flag: str
    # 根据需要添加其他字段

class MetaEvent(BaseEvent):
    post_type: Literal["meta_event"]
    meta_event_type: str
    sub_type: str = None
    # 根据需要添加其他字段

Event: type[MessageEvent | NoticeEvent | RequestEvent | MetaEvent] = Annotated[
    MessageEvent | NoticeEvent | RequestEvent | MetaEvent,
    Field(discriminator='post_type')
]


