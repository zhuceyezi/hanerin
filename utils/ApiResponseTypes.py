from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BaseResponse(BaseModel):
    code: Optional[int] = 200
    msg: str
    data: Optional[object] = {}


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

class PreviewResponseData(BaseModel):
    userId: int | str
    userName: str
    isLogin: bool
    lastGameId: Optional[int] = None
    lastRomVersion: str
    lastDataVersion: str
    lastLoginDate: datetime
    lastPlayDate: datetime
    playerRating: int
    nameplateId: int
    iconId: int
    trophyId: int
    isNetMember: bool  # 可考虑改为 bool，但原始数据为 1/0
    isInherit: bool
    totalAwake: int
    dispRate: int
    dailyBonusDate: datetime
    headPhoneVolume: Optional[int] = None
    banState: int

class PreviewResponse(BaseResponse):
    code: int
    msg: str
    data: PreviewResponseData | None

class GameCharge(BaseModel):
    orderId: int
    chargeId: int
    price: int
    startDate: datetime
    endDate: datetime

class GameChargeResponseData(BaseModel):
    length: int
    gameChargeList: List[GameCharge]

class GameChargeResponse(BaseResponse):
    data: GameChargeResponseData | None

class UserCharge(BaseModel):
    chargeId: int
    stock: int
    purchaseDate: datetime
    validDate: datetime
    extNum1: int

class UserChargeResponseData(BaseModel):
    userId: int
    length: int
    userChargeList: List[UserCharge]

class UserChargeResponse(BaseResponse):
    data: Optional[UserChargeResponseData] = None