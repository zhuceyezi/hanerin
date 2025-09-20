from sqlmodel import SQLModel, Session, create_engine, select
from utils.Payloads import *
from schemas.users import User
from utils.Types import *
from apis.SDGB.API_AimeDB import implGetUID
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from apis.SDGB.update_sy import get_user_music
import requests

def _bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder="big")


def _int_to_bytes(n: int) -> bytes:
    length = (n.bit_length() + 7) // 8 or 1
    return n.to_bytes(length, byteorder="big")


class Hanerin:
    def __init__(self, qq):
        self.url = "http://127.0.0.1:30001"
        self.command_map = {} # 0: command, 1: access list
        self.qq = qq
        self.engine = create_engine('sqlite:///cloud/hanerin.sqlite')
        self.df = self.Divingfish()
        self.mai2 = self.Mai2(self.engine)
        return

    def has_access(self, command, user_id=None, group_id=None):
        access = self.command_map[command][1]
        if access['all']:
            return True
        assert (user_id or group_id)
        in_groups = access["groups"] == "all" or group_id in access["groups"] if group_id else False
        in_users = access["users"] == "all" or user_id in access["users"] if user_id else False
        if user_id and group_id:
            return in_users or in_groups
        elif group_id:
            return in_groups
        else:
            return in_users


    def add_command(self, key, value, access):
        self.command_map[key] = [value, access]

    def get_function(self, key):
        return self.command_map.get(key, [None, None])

    def command(self, keys: str | list[str], users: list[int] | str = [], groups: list[int] | str = []):
        def decorator(func):
            access = {
                "users": users,
                "groups": groups,
                "all": users == 'all' and groups == 'all'
            }
            key_list = [keys] if isinstance(keys, str) else keys
            for key in key_list:
                self.add_command(key, func, access)
            return func

        return decorator

    def is_group_message(self, msg: Message) -> bool:
        first = msg[0]
        if isinstance(first, AtMessageSegment) and first.data.qq == self.qq:
            return True
        return False

    class Mai2:

        def __init__(self, db_engine):
            self.engine = db_engine
            with open("cloud/aes.key", "rb") as f:
                self.aes_key = f.read()
            with open("cloud/nonce", "rb") as f:
                self.nonce = f.read()
            return

        def _encrypt_aes_gcm(self, nums: int):
            """
            加密整数，用来存储userid. Userid为敏感数据，若被截取可对账号造成不可逆的损害。
            :param nums: 华立userid
            :return: 加密后的字符Bytes
            """
            bytes = _int_to_bytes(nums)
            aesgcm = AESGCM(self.aes_key)
            ciphertext = aesgcm.encrypt(self.nonce, bytes, associated_data=None)
            return ciphertext

        def _decrypt_aes_gcm(self, ciphertext: bytes):
            """
            解码字符bytes
            :param ciphertext: 加密字符字节
            :return: 解密后的userid
            """
            aesgcm = AESGCM(self.aes_key)
            bytes = aesgcm.decrypt(self.nonce, ciphertext, associated_data=None)
            return _bytes_to_int(bytes)

        def get_mai_userid(self, qq):
            with Session(self.engine) as session:
                query = select(User).where(User.qq == qq)
                user = session.exec(query).first()
                return self._decrypt_aes_gcm(user.mai_userid)

        def bind_mai_account(self, qq: int, qr_code_content: str) -> bool:
            """
            绑定华立舞萌账号
            :param qq: QQ号
            :param qr_code_content: 二维码解码出的字符串，如：SGWCMAID2504190427XXXXX
            :return:
            """
            response = implGetUID(qr_code_content)
            if response["errorID"] != 0:
                return False
            user_id = response["userID"]
            user_id = self._encrypt_aes_gcm(user_id)
            with Session(self.engine) as session:
                query = select(User).where(User.qq == qq)
                existing_user = session.exec(query).first()
                if existing_user and existing_user.mai_userid == user_id:
                    return True
                elif existing_user:
                    existing_user.mai_userid = user_id
                    session.add(existing_user)
                    session.commit()
                    return True
                else:
                    new_user = User(qq=qq, mai_userid=user_id)
                    SQLModel.metadata.create_all(self.engine)
                    session.add(new_user)
                    session.commit()
                    return True

        def get_user_music_info(self, qq):
            return get_user_music(self.get_mai_userid(qq))


        def b50(self, qq):
            # 如果绑定了华立，选取华立
            # 如果没有绑定华立, 选取水鱼
            # 如果都没绑定，返回报错信息

            # 生成b50内容
            
            return




    class Divingfish:
        def __init__(self):
            return

        def refresh_music_database(self):
            url = "https://www.diving-fish.com/api/maimaidxprober/music_data"
            payload = {}
            headers = {}
            response = requests.get(url, headers=headers, data=payload)
            data = response.json()
            data_by_id = {entry["id"]: entry for entry in data}
            return data_by_id