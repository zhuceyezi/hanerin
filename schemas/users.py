# models.py
from sqlalchemy import Integer, LargeBinary, Column, String, BigInteger, JSON
from typing import Optional, List
from db.database import Base
from utils.ApiResponseTypes import UserInfo


class User(Base):
    __tablename__ = "hanerin_users"
    user_id: int = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username: str = Column(String(10), unique=True, nullable=False)
    qq: int = Column(BigInteger, nullable=True, default=None)
    wahlap_user_id: Optional[str] = Column(String(8), nullable=True, default=None)
    df_token: Optional[str] = Column(String(50), nullable=True, default=None)
    hashed_password: str = Column(String(60), nullable=False)
    email: str = Column(String(50), nullable=True, default=None)
    avatar: Optional[str] = Column(String(200), nullable=True, default=None)
    buttons: str = Column(String(50), nullable=True)
    roles: str = Column(String(20), nullable=True)

    def get_info(self):
        return UserInfo(userId=self.user_id, userName=self.username,roles=self.roles.split(","),
                        buttons=self.buttons.split(","),
                        email=self.email)