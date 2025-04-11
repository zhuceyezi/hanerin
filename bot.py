import os
import botpy
from fastapi import FastAPI
from fastapi import APIRouter
from fastapi import Request
from h11 import Response
from numpy.random import random
from pydantic import BaseModel
import json
import binascii
import random
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from botpy.ext.cog_yaml import read
from classes.Hanerin import Hanerin
from classes.Payloads import *
import shlex

test_config = read(os.path.join(os.path.dirname(__file__), "configs/secrets.yaml"))

print(test_config)

hanerin = Hanerin()
bot = FastAPI()
route = APIRouter(prefix="/qq")

def parse_command(msg: str):
    try:
        tokens = shlex.split(msg.strip().lstrip('/'))
        if not tokens:
            return None, []
        return tokens[0], tokens[1:]
    except ValueError:
        return None, []

def get_message_private_or_group(body: RequestPayload):
    return "groups"

def get_openid(body: RequestPayload):
    data = body.d
    type = get_message_private_or_group(body)
    if type == "groups":
        return data["group_openid"]
    elif type == "users":
        return data["user_openid"]
    else:
        raise Exception("Unknown type")
@route.api_route("/", methods=["GET","POST"])
async def routing(request: Request):
    body = await request.body()
    body = RequestPayload(**json.loads(body))
    data = body.d
    com, args = parse_command(data["content"])
    command = f"/{com}"
    func = hanerin.get_function(command)
    if func is None:
        return
    await func(request)
    return

async def hello_world(request: Request):
    body = await request.body()
    body = RequestPayload(**json.loads(body))
    data = body.d
    _, args = parse_command(data["content"])
    payload = SendMessagePayload(
        msg_type=MessageType.TEXT,
        content="Hello, world!",
        msg_id=data["id"],
        msg_seq=body.s
    )
    param = ParameterPayload(
        payload=payload,
        openid=get_openid(body),
        type=get_message_private_or_group(body)
    )
    print(f"调用命令/hello")
    await hanerin.send_message(param)
hanerin.add_command("/hello", hello_world)

async def d100(request: Request):
    body = await request.body()
    body = RequestPayload(**json.loads(body))
    data = body.d
    _, args = parse_command(data["content"])
    random_number = random.randint(0,99)
    response_content = f"D100随机数结果：{random_number}"
    payload = SendMessagePayload(
        msg_type=MessageType.TEXT,
        msg_id=data["id"],
        content= response_content,
        msg_seq=body.s
    )
    param = ParameterPayload(
        payload=payload,
        type=get_message_private_or_group(body),
        openid=get_openid(body),
    )
    print("调用命令/d100")
    await hanerin.send_message(param)
hanerin.add_command("/d100", d100)


bot.include_router(route)
