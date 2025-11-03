import time

from exceptiongroup import catch
from fastapi.middleware.cors import CORSMiddleware
from logger import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi import Response
from bot.Hanerin import hanerin
from db.database import init_db, get_db, AsyncSessionLocal
from mai_apis.SDGB.API_AimeDB import implGetUID
from io import BytesIO
from utils.MessagePayloads import FastReplyPayload
import json
from mai_apis.mcsmanager import McsManager
from dotenv import load_dotenv
from services import qq,df,mai2,net
from utils.MessageTypes import TextMessageSegment, MessageType, TextMessageSegmentData, MessageEvent
from utils.maimai_best_50 import generate50
import os

load_dotenv()
mcs_api = os.getenv("mcs_api_key")
mcs = McsManager(api_key=mcs_api)


@asynccontextmanager
async def lifespan(app: FastAPI):
    t1 = time.time()
    logger.info("正在初始化数据库实例...")
    await init_db()
    t2 = time.time()
    elapsed_time = t2 - t1
    logger.info(f"数据库实例初始化完成，耗时：{int(round(elapsed_time * 1000, 0))}ms.")
    yield

bot = FastAPI(lifespan=lifespan)

bot.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（前端域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET, POST, PUT, DELETE 等）
    allow_headers=["*"],  # 允许所有请求头
)

bot.include_router(qq.route)
bot.include_router(df.route)
bot.include_router(mai2.route)
bot.include_router(net.route)


@hanerin.command("/hello", users=[840042638])
async def say_hello(name: str = "", **kwargs):
    reply = FastReplyPayload(
        reply=[TextMessageSegment(
            type=MessageType.TEXT,
            data=TextMessageSegmentData(
                text= f" Hello {name}"
            )
        )]
    )
    return reply

@hanerin.command("/mc", users=[840042638], groups=[343331682])
async def mc(command: str, content: str = "", **kwargs):
    res = Response()
    data = {}
    if command in ["start","启动"]:
        res = mcs.start_instance()
        data = res.json()

    elif command in ["理赔","创哥理赔","lp"]:
        res = mcs.execute_command(content)
        data = res.json()

    elif command in ["restart", "重启"]:
        res = mcs.restart_instance()
        data = res.json()

    else:
        reply = FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=f" 未知的服务器操作"
                )
            )]
        )
        return reply

    if res.status_code == 200:
        reply = FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=f" 操作成功"
                )
            )]
        )
        return reply
    elif res.status_code == 500 and data['data'] in mcs.ERROR_LIST:
        reply = FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=f" 错误：{data['data']}"
                )
            )]
        )
        return reply

    else:
        reply = FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=f" 有错误发生，启动失败"
                )
            )]
        )
        return reply

@hanerin.command("/help")
async def help(page=0, **kwargs):
    reply = FastReplyPayload(
        reply=[TextMessageSegment(
            type=MessageType.TEXT,
            data=TextMessageSegmentData(
                text=f" 帮助列表:\n"
                     f"/mc: mc相关指令，包括:\n"
                     f"/mc start: 启动服务器\n"
                     f"/mc restart: 重启服务器\n"
                     f"/mc lp/理赔/创哥理赔 '<命令>': 向服务器执行命令，记得用引号包裹命令\n"
                     f"/hello <文本>: 向你打招呼！\n"
                     f"/mai bindhl <二维码扫描出的字符串>: 绑定华立账号, 请确保二维码处于有效期间内"
            )
        )]
    )
    return reply

@hanerin.command("/qrcode", users=[840042638], groups=[220666756])
async def qrcode(qr_code_content=None, **kwargs):
    response_text = ""
    if qr_code_content is None or qr_code_content == "":
        response_text = f" 请输入二维码扫描出来的完整字符串"
    result = implGetUID(qr_code_content)
    if result["errorID"] in [1,2]:
        response_text= f" 二维码已过期"
    elif result["errorID"] == 60001:
        response_text = f" 二维码内容明显无效"
    elif result["errorID"] == 60002:
        response_text = f" 无法解码 Response 的内容"
    else:
        response_text = f" {result["userID"]}"
    return FastReplyPayload(
        reply=[TextMessageSegment(
            type=MessageType.TEXT,
            data=TextMessageSegmentData(
                text=response_text
            )
        )],
        delete=True
    )

@hanerin.command("/mai", users=[840042638], groups=[220666756])
async def mai(command, qr_code_content=None, **kwargs):
    event = kwargs.get("event")
    if command in ["bindhl", "绑定华立","绑定官服"]:
        if qr_code_content is None:
            return FastReplyPayload(
                reply=[TextMessageSegment(
                    type=MessageType.TEXT,
                    data=TextMessageSegmentData(
                        text=f" 请输入二维码扫描出来的完整字符串"
                    )
                )]
            )
        ok = hanerin.bind_mai_account(event.user_id, qr_code_content)
        if not ok:
            return FastReplyPayload(
                reply=[TextMessageSegment(
                    type=MessageType.TEXT,
                    data=TextMessageSegmentData(
                        text=f" 发生错误，操作失败"
                    )
                )]
            )
        return FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=f" 绑定成功"
                )
            )],
            delete=True
        )
    else:
        return FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=f" 无效的操作"
                )
            )],
        )

@hanerin.command("/register", users=[840042638], groups=[220666756])
async def register(username, password, **kwargs,):
    response_text = ""
    async with AsyncSessionLocal() as db:
        try:
            registered_user = await net.register(username, password, db)
            if registered_user is None:
                response_text = " 注册发生异常: 新用户为空"
            else:
                response_text = f" 注册成功, 用户名: {registered_user.username}"
        except Exception:
            response_text = " 注册失败"
        return FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=response_text
                )
            )],
        )