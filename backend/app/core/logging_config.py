"""
日志配置模块
提供统一的日志配置和格式化
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(app_name: str = "InnerPath", log_level: str = "INFO", log_dir: str = "logs"):
    """
    设置日志配置

    Args:
        app_name: 应用名称
        log_level: 日志级别
        log_dir: 日志目录
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有的处理器
    root_logger.handlers.clear()

    # 日志格式
    detailed_format = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_format = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # 1. 控制台处理器（彩色输出）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_format)
    root_logger.addHandler(console_handler)

    # 2. 文件处理器 - 所有日志
    all_log_file = log_path / f"{app_name.lower()}_all.log"
    file_handler = RotatingFileHandler(
        all_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_format)
    root_logger.addHandler(file_handler)

    # 3. 文件处理器 - 错误日志
    error_log_file = log_path / f"{app_name.lower()}_error.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_format)
    root_logger.addHandler(error_handler)

    # 4. 文件处理器 - API 调用日志
    api_log_file = log_path / f"{app_name.lower()}_api.log"
    api_handler = RotatingFileHandler(
        api_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(detailed_format)

    # 为 API 日志创建专门的 logger
    api_logger = logging.getLogger('api')
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)

    # 禁用第三方库的详细日志
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    logging.info(f"日志系统初始化完成 | 级别: {log_level} | 目录: {log_path.absolute()}")


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称（通常使用 __name__）

    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)


# API 调用日志装饰器
def log_api_call(func):
    """装饰器：记录 API 调用"""
    import functools
    import time

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger('api')
        func_name = func.__name__

        # 记录开始
        logger.info(f"API 调用开始: {func_name}")
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"API 调用成功: {func_name} | 耗时: {elapsed:.2f}ms")
            return result
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"API 调用失败: {func_name} | 耗时: {elapsed:.2f}ms | 错误: {str(e)}")
            raise

    return wrapper


# 外部 API 调用日志装饰器
def log_external_api(api_name: str):
    """装饰器：记录外部 API 调用（如 DeepSeek）"""
    import functools
    import time

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger('api.external')

            # 记录开始
            logger.info(f"外部 API 调用开始: {api_name}")
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"外部 API 调用成功: {api_name} | 耗时: {elapsed:.2f}ms")
                return result
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                logger.error(f"外部 API 调用失败: {api_name} | 耗时: {elapsed:.2f}ms | 错误: {str(e)}")
                raise

        return wrapper
    return decorator
