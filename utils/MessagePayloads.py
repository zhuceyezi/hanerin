from typing import Optional, Any
from enum import StrEnum
from typing import TypeVar
from utils.MessageTypes import *
from typing import Literal, Union, Annotated, List
from pydantic import BaseModel, Field, model_validator

T = TypeVar('T')


class MessagePayload(BaseModel):
    message_type: str
    user_id: Optional[int | str] = None
    group_id: Optional[int | str] = None
    message: Message
    auto_escape: Optional[bool] = False

    @model_validator(mode="after")
    def check_user_or_group(self, model):
        if not model.user_id and not model.group_id:
            raise ValueError("'user_id' 或 'group_id' 必须有一个.")
        return model


class FastReplyPayload(BaseModel):
    reply: Message # 回复消息
    auto_escape: Optional[bool] = False # 是否纯文本，不解析CQ
    at_sender: Optional[bool] = True # 回复时是否自动at发送者
    delete: Optional[bool] = False # "撤回消息？
    kick: Optional[bool] = False # "踢出发送者？
    ban: Optional[bool] = False # "禁言？"
    ban_duration: Optional[int] = 3600 # 禁言时长
