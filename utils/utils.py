import inspect
from typing import Callable, Any
import shlex
from typing import Tuple, Optional
from utils.Types import *

def parse_command(message: Message) -> Tuple[Optional[str], list[str]]:
    try:
        for segment in message:
            if not isinstance(segment, TextMessageSegment):
                continue

            raw = segment.data.text.strip().lstrip('/')
            if not raw:
                continue

            tokens = shlex.split(raw)
            if not tokens:
                return None, []
            return f"/{tokens[0]}", tokens[1:]

        return None, []
    except ValueError:
        # shlex.split 抛异常的情况（引号未闭合等）
        return None, []


class CommandArgError(ValueError):
    """参数绑定失败时抛出的异常"""
    pass

class TooManyArgsError(CommandArgError):
    """参数绑定失败时抛出的异常"""
    pass

class InvalidArgsValueError(CommandArgError):
    """参数绑定失败时抛出的异常"""
    pass

class MissingArgsError(CommandArgError):
    """参数绑定失败时抛出的异常"""
    pass

class CommandExcuteException(Exception):
    pass

def bind_args(func: Callable, arg_list: list[str]) -> dict[str, Any]:
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Ignore *args and **kwargs for binding positional args
    positional_params = [p for p in params if p.kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD
    )]

    if len(arg_list) > len(positional_params):
        raise TooManyArgsError("Too many arguments")

    args = {}

    for i, arg in enumerate(arg_list):
        param = positional_params[i]
        name = param.name
        ann = param.annotation

        try:
            value = arg if ann is inspect.Parameter.empty else ann(arg)
        except Exception:
            raise InvalidArgsValueError(f"Invalid value for `{name}`: {arg}")

        args[name] = value

    # Fill in defaults for remaining positional parameters
    for param in positional_params[len(arg_list):]:
        if param.default is inspect.Parameter.empty:
            raise MissingArgsError(f"Missing argument: `{param.name}`")
        args[param.name] = param.default

    return args


