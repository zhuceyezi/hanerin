from passlib.hash import bcrypt
from fastapi import APIRouter, Request, Response, Form, Depends, Query, Body, Header
import hashlib
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from DAO.userDAO import UserDAO
from bot.Hanerin import hanerin
from db.database import get_db, AsyncSessionLocal
from schemas.users import User
from utils.ApiResponseTypes import LoginResponse, LoginResponseData, UserInfo, UserInfoResponse

route = APIRouter(prefix="/net/api")
userDAO = UserDAO()
def hash_password(password: str) -> str:
    pre_hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return bcrypt.hash(pre_hashed)

def verify_password(plain_password: str, hashed: str) -> bool:
    pre_hashed = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return bcrypt.verify(pre_hashed, hashed)

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
    db_password = user.hashed_password
    if verify_password(password, db_password):
        return LoginResponse(code=200, msg="登录成功", data=LoginResponseData(token="1", refreshToken="2"))
    else:
        return LoginResponse(code=401, msg="登录失败", data=None)

@route.get("/user/info")
async def user_info(db: AsyncSession = Depends(get_db)):
    user_data = await userDAO.get(db, username='aleafy')
    return UserInfoResponse(code=200, msg="请求成功", data=user_data.get_info())
