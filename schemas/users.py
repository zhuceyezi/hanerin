from typing import Optional, Any
from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    qq: int = Field(..., primary_key=True)
    mai_userid: Optional[bytes] = Field(default=None, nullable=True)
    divingfish_user_email: Optional[bytes] = Field(default=None, nullable=True)

