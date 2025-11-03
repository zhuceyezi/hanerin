
import os
import sys
import logging
from loguru import logger

# 确保 logs 目录存在
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ========== 清理默认 handler ==========
logger.remove()

# ========== 控制台输出（带颜色）==========
logger.add(
    sink=sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
    enqueue=True,  # 异步安全（FastAPI/多线程推荐）
)

# ========== 文件输出（每天轮转 + 压缩 + 保留7天）==========
logger.add(
    sink=os.path.join(LOG_DIR, "Hanerin_{time:YYYY-MM-DD}.log"),
    rotation="00:00",        # 每天午夜分割
    retention="7 days",      # 保留最近7天
    compression="gz",        # 旧日志自动压缩为 .gz
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    encoding="utf-8",
    enqueue=True,            # 异步安全
)

# ========== 关键：桥接标准 logging 到 loguru ==========
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取日志级别（兼容 loguru）
        level = logger.level(record.levelname).no if record.levelname in logger._core.levels else record.levelno
        # 转发日志（depth=6 能正确显示原始调用位置）
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

# 将 SQLAlchemy 的日志重定向到 loguru
sqlalchemy_logger = logging.getLogger("sqlalchemy")
sqlalchemy_logger.setLevel(logging.INFO)
sqlalchemy_logger.addHandler(InterceptHandler())
sqlalchemy_logger.propagate = False  # 避免重复输出

# 可选：如果你只想看 SQL 语句，可以只监听 engine
# logging.getLogger("sqlalchemy.engine").addHandler(InterceptHandler())

# ========== 导出 logger 供其他模块使用 ==========
__all__ = ["logger"]