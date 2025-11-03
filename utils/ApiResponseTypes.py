from typing import List, Optional

from pydantic.v1 import BaseModel


class BaseResponse(BaseModel):
    code: int
    msg: str
    data: object


class LoginResponseData(BaseModel):
    token: str
    refreshToken: str


class LoginResponse(BaseResponse):
    code: int
    msg: str
    data: LoginResponseData | None

class UserInfo(BaseModel):
    buttons: List[str]
    roles: List[str]
    userId: int
    userName: str
    email: str
    avatar: Optional[str] = None

class UserInfoResponse(BaseResponse):
    data: UserInfo | None

