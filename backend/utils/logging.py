import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logging(log_dir: str = ".logs", log_level: int = logging.INFO, max_bytes: int = 10485760, backup_count: int = 5) -> None:
    """配置日志系统

    Args:
        log_dir: 日志文件目录
        log_level: 日志级别
        max_bytes: 单个日志文件最大字节数
        backup_count: 日志文件备份数量
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(log_level)

    # 文件处理器
    log_file = os.path.join(log_dir, "code_analyzer.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(log_level)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 禁止某些第三方库的日志
    logging.getLogger('git').setLevel(logging.WARNING)
    logging.getLogger('tree_sitter').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

    logging.info(f"Logging system initialized. Log file: {log_file}")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志器

    Args:
        name: 日志器名称

    Returns:
        配置好的日志器实例
    """
    return logging.getLogger(name)