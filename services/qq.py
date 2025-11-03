from fastapi import APIRouter, Response
from logger import logger
from bot.Hanerin import hanerin
from utils.MessagePayloads import FastReplyPayload
from utils.MessageTypes import Event, MessageEvent, TextMessageSegment, MessageType, TextMessageSegmentData
from utils.utils import parse_command, parse_no_backslash_command, handle_command_as_arg_commands, bind_args

route = APIRouter(prefix="/qq")


@route.post("/")
async def routing(event: Event) -> Response:
    if not isinstance(event, MessageEvent):
        return Response("必须为消息", status_code=404)

    if event.sub_type != "normal":
        return Response("必须为消息", status_code=404)
    content = event.message
    logger.info(f"收到消息 『{event.raw_message}』")
    if not hanerin.is_group_message(event.message):
        return Response("不是群聊消息或者没at机器人", status_code=404)

    command, arg_list = parse_command(content)
    func = hanerin.get_function(command)[0]
    command_name = command

    if func is None:
        logger.info(f"该请求试图使用不存在的命令{command}, 尝试匹配非指令对答")
        command, arg_list = parse_no_backslash_command(content)
        func, _, command_name = hanerin.get_function(command)
        arg_list = handle_command_as_arg_commands(command_name, command, arg_list)
        if func is None:
            return Response("找不到命令", status_code=404)
    try:
        if not hanerin.has_access(command_name, event.user_id, event.group_id):
            reply = FastReplyPayload(
                reply=[TextMessageSegment(
                    type=MessageType.TEXT,
                    data=TextMessageSegmentData(
                        text=f" 没有权限进行此操作"
                    )
                )]
            )
            return reply
        args = bind_args(func, arg_list)
        args["event"] = event
        return await func(**args)
    except Exception as e:
        logger.exception(f"发生错误: {e}")
        reply = FastReplyPayload(
            reply=[TextMessageSegment(
                type=MessageType.TEXT,
                data=TextMessageSegmentData(
                    text=f" 发生了错误，可能是指令格式不正确，或者指令执行中发生了异常。请检查格式。如果你确信指令正确，则机器人发生了异常，请联系开发者。"
                )
            )]
        )
        return reply


@route.get("/{qq}/userid")
def get_userid(qq):
    return hanerin.route.get_mai_userid(qq)
