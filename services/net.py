import os

from dotenv import load_dotenv
from passlib.hash import bcrypt
from fastapi import APIRouter, Form, Depends, Query, Body, Cookie
import hashlib
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from mai_apis.SDGB.main.Config import music_data
from mai_apis.SDGB.main.MaiUserData import MaiUserData
from DAO.userDAO import UserDAO
from db.database import get_db, AsyncSessionLocal
from schemas.users import User
from utils.ApiResponseTypes import LoginResponse, LoginResponseData, UserInfo, UserInfoResponse, PreviewResponse, \
    BaseResponse, PreviewResponseData, GameCharge, GameChargeResponse, GameChargeResponseData, UserChargeResponseData, \
    UserChargeResponse
from datetime import datetime, timedelta
import jwt
from fastapi import Header, HTTPException, status
from typing import Optional

# JWT配置
load_dotenv()

ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")  # 应从环境变量获取
REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET")  # 应从环境变量获取
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7天

# 生成JWT token
def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "type": "access"
    }
    encoded_jwt = jwt.encode(payload, ACCESS_TOKEN_SECRET, algorithm="HS256")
    return encoded_jwt

def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(payload, REFRESH_TOKEN_SECRET, algorithm="HS256")
    return encoded_jwt

def verify_access_token(token: str) -> Optional[str]:
    """验证access token并返回用户ID"""
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "access":
            return None

        return user_id
    except jwt.ExpiredSignatureError:
        # Token已过期
        return None
    except jwt.PyJWTError:
        # Token无效
        return None

def verify_refresh_token(token: str) -> Optional[str]:
    """验证refresh token并返回用户ID"""
    if token is None:
        return None
    try:
        payload = jwt.decode(token, REFRESH_TOKEN_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "refresh":
            return None

        return user_id
    except jwt.ExpiredSignatureError:
        # Token已过期
        return None
    except jwt.InvalidTokenError:
        # Token无效（包括DecodeError, InvalidSignatureError等）
        return None

route = APIRouter(prefix="/net/api")
userDAO = UserDAO()
def hash_password(password: str) -> str:
    pre_hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return bcrypt.hash(pre_hashed)

def verify_password(plain_password: str, hashed: str) -> bool:
    pre_hashed = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return bcrypt.verify(pre_hashed, hashed)

def mask_user_id(user_id, keep_prefix=2, keep_suffix=2, mask_char='*'):
    """
    对用户ID进行脱敏处理。

    参数:
        user_id (str or int): 用户ID
        keep_prefix (int): 保留前缀字符数，默认2
        keep_suffix (int): 保留后缀字符数，默认2
        mask_char (str): 用于遮蔽的字符，默认'*'

    返回:
        str: 脱敏后的用户ID

    示例:
        mask_user_id(10239920)        -> '10******20'
        mask_user_id("10239920", 1, 1) -> '1******0'
    """
    uid_str = str(user_id)
    total_len = len(uid_str)

    if total_len <= keep_prefix + keep_suffix:
        # 如果总长度不够保留前后部分，则全部遮蔽或按策略处理
        return mask_char * total_len

    masked_middle = mask_char * (total_len - keep_prefix - keep_suffix)
    return uid_str[:keep_prefix] + masked_middle + uid_str[-keep_suffix:]

@route.post("/register")
async def register(username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    password_hash = hash_password(password)
    new_user = User(username=username, hashed_password=password_hash)
    result = await userDAO.insert(db, new_user)
    return result

@route.get("/verify-password")
async def verify(username: str = Query(...), password: str = Query(...), db: AsyncSession = Depends(get_db)):
    user = await userDAO.get(db, username=username)
    db_password = user.hashed_password
    return verify_password(password, db_password)

@route.post("/auth/login")
async def login(userName: str = Body(...), password: str = Body(...), db: AsyncSession = Depends(get_db)):
    user = await userDAO.get(db, username=userName)
    if not user:
        return LoginResponse(code=401, msg="登录失败", data=None)

    db_password = user.hashed_password
    if verify_password(password, db_password):
        # 生成access token (短期有效)
        access_token = create_access_token(
            user_id=str(user.user_id),
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 生成refresh token (长期有效)
        refresh_token = create_refresh_token(
            user_id=str(user.user_id),
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )

        # 设置 HttpOnly Cookie
        response = JSONResponse(content={
            "code": 200,
            "msg": "登录成功",
            "data": {
                "token": access_token,
                "refreshToken": refresh_token  # 仅返回 access token
            }
        })

        # 设置 HttpOnly Cookie（仅用于 refresh token）
        response.set_cookie(
            key="refreshToken",
            value=refresh_token,
            httponly=True,      # JS 无法访问
            secure=False,        # 仅 HTTPS
            path="/",
            samesite="lax",  # 防 CSRF
            max_age=7 * 24 * 60 * 60  # 7天（秒）
        )

        return response
    else:
        return LoginResponse(code=401, msg="登录失败", data=None)

@route.get("/user/info")
async def user_info(
        authorization: str = Header(...),
        refresh_token: str = Cookie(None, alias="refreshToken"),
        db: AsyncSession = Depends(get_db)
):
    # 从Authorization header中提取token (格式: "Bearer <token>")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'Bearer '"
        )

    token = authorization[7:]  # 移除 "Bearer " 前缀

    # 验证token
    user_id = verify_access_token(token)
    refreshed = False
    if user_id is None:
        user_id = verify_refresh_token(refresh_token)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        else:
            token = create_access_token(user_id)
            refreshed = True

    # 根据user_id获取用户信息
    user_data = await userDAO.get(db, int(user_id))
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    data = user_data.get_info().dict()

    if refreshed:
        data["token"] = token

    response = JSONResponse(content={
        "code": 200,
        "msg": "登录成功",
        "data": data
    })

    # 返回用户信息
    return response

@route.get("/user/mai2/preview")
async def get_preview(userId: str = Query(...), db: AsyncSession = Depends(get_db)):
    user = await userDAO.get(db, userId)
    maiUserData = MaiUserData(user_id=user.wahlap_user_id)
    try:
        response = PreviewResponseData.model_validate(maiUserData.preview())
        response.userId = mask_user_id(response.userId)
        return PreviewResponse(code=200, msg="请求成功", data=response)
    except Exception as e:
        return BaseResponse(code=500, msg="请求出错")

@route.get("/user/mai2/getActiveTicket")
async def get_active_ticket(userId: str = Query(...), db: AsyncSession = Depends(get_db)):
    user = await userDAO.get(db, userId)
    maiUserData = MaiUserData(user_id=user.wahlap_user_id)
    try:
        response = UserChargeResponseData.model_validate(maiUserData.get_active_ticket())
        return UserChargeResponse(code=200, msg="请求成功", data=response)
    except Exception as e:
        return BaseResponse(code=500, msg="请求出错")

@route.post("/user/mai2/postClearTicket")
async def clear_ticket(userId: int = Body(..., embed=True), db: AsyncSession = Depends(get_db)):
    user = await userDAO.get(db, userId)
    maiUserData = MaiUserData(user_id=user.wahlap_user_id, music_data=music_data)
    try:
        response = maiUserData.login().commit()
        return BaseResponse(code=200, msg="成功", data={"error_no":0, "error_msg": ""})
    except Exception as e:
        return BaseResponse(code=500, msg=f"清除功能票出错: {e}", data={"error_no": 1, "error_msg": str(e)})

@route.post("/user/mai2/postTicket")
async def post_ticket(userId: int = Body(..., embed=True), ticketId: int = Body(...), db: AsyncSession = Depends(get_db)):
    user = await userDAO.get(db, userId)
    maiUserData = MaiUserData(user_id=user.wahlap_user_id)
    try:
        maiUserData.login(load_full_data=False).ticket(ticketId=ticketId).logout()
        return BaseResponse(msg=f"上传成功")
    except Exception as e:
        return BaseResponse(code=500, msg=f"发送功能票出错: {e}")