import os
from fastapi import FastAPI
from fastapi import APIRouter
from fastapi import Request
from pydantic import BaseModel
from nacl.signing import SigningKey
import json
import hashlib
import nacl.encoding
import binascii
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import hashlib

from botpy.ext.cog_yaml import read
from botpy import logging
router = APIRouter()
app = FastAPI()

test_config = read(os.path.join(os.path.dirname(__file__), "configs/secrets.yaml"))



@router.api_route("/qq", methods=["POST","GET"])
async def handle_validation(request: Request):
    class ValidationData(BaseModel):
        plain_token: str
        event_ts: str

    class CallbackPayload(BaseModel):
        op: int
        d: ValidationData

    body = await request.body()
    payload = CallbackPayload(**json.loads(body))

    data = payload.d
    bot_secret = test_config["secret"]

    # 重复到超过32位，再取前32位
    seed = (bot_secret * ((32 // len(bot_secret)) + 1)).encode("utf-8")[:32]

    # 使用 Ed25519 私钥构造
    private_key = Ed25519PrivateKey.from_private_bytes(seed)

    # 拼接签名消息
    message = (data.event_ts + data.plain_token).encode("utf-8")
    signature = private_key.sign(message)

    return {
        "plain_token": data.plain_token,
        "signature": binascii.hexlify(signature).decode("utf-8")
    }
app.include_router(router)
print(app.routes)