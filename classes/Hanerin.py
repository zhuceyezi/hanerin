import time
from datetime import datetime
import requests
from botpy.ext.cog_yaml import read
from botpy import logging

from classes.Payloads import ParameterPayload

_log = logging.get_logger()

test_config = read("/home/aleafy/PycharmProjects/Hanerin/configs/secrets.yaml")
class Hanerin:
    def renew_access_token(self):
        url = "https://bots.qq.com/app/getAppAccessToken"
        payload = {
            "appId": test_config["appid"],
            "clientSecret": test_config["secret"]
        }
        res = requests.post(url, json=payload)
        data = res.json()
        token = data["access_token"]
        self.token_expire_time = time.time() + int(data["expires_in"])
        self.access_token = token
        print(f"Token已经更新，下次过期时间{datetime.fromtimestamp(self.token_expire_time).strftime('%Y-%m-%d %H:%M:%S')}")
        return token

    def __init__(self):
        self.endpoint = "https://sandbox.api.sgroup.qq.com"
        self.command_mapping = {}
        self.token_expire_time = None
        self.access_token = None
        self.renew_access_token()

    def get_headers(self):
        now = time.time()
        if now > self.token_expire_time:
            print("Token已经过期，正在更新")
            self.renew_access_token()
        return {
            "Authorization": f"QQBot {self.access_token}"
        }

    def add_command(self, key, value):
        self.command_mapping[key] = value

    def get_function(self,key):
        return self.command_mapping.get(key, None)

    async def send_message(self, data: ParameterPayload):
        openid = data.openid
        payload = data.payload
        mode = data.type
        url = self.endpoint + f"/v2/{mode}/{openid}/messages"
        res = requests.post(url, data=payload.model_dump(), headers=self.get_headers())
        print(res)

