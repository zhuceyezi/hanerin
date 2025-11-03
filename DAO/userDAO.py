from DAO.base.baseDAO import BaseDAO
from schemas.users import User


class UserDAO(BaseDAO[User]):
    def __init__(self):
        super().__init__(User)
