"""
日志工具 - 配置和管理应用日志
"""

import logging
import sys
from typing import Optional
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rich_logging: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        rich_logging: 是否使用Rich格式化
        format_string: 自定义格式字符串
        
    Returns:
        配置好的logger
    """
    # 清除现有的handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 设置日志级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # 默认格式
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = []
    
    # 控制台处理器
    if rich_logging:
        try:
            console = Console(stderr=True)
            console_handler = RichHandler(
                console=console,
                show_time=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True
            )
            console_handler.setLevel(numeric_level)
        except ImportError:
            # 如果Rich不可用，使用标准处理器
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(numeric_level)
            formatter = logging.Formatter(format_string)
            console_handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(numeric_level)
        formatter = logging.Formatter(format_string)
        console_handler.setFormatter(formatter)
    
    handlers.append(console_handler)
    
    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(format_string)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # 添加处理器
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger
    
    Args:
        name: logger名称
        
    Returns:
        logger实例
    """
    return logging.getLogger(name)


class ProgressLogger:
    """进度日志记录器"""
    
    def __init__(self, logger: logging.Logger, total_steps: int):
        self.logger = logger
        self.total_steps = total_steps
        self.current_step = 0
    
    def update(self, step_name: str, increment: int = 1):
        """更新进度"""
        self.current_step += increment
        progress = (self.current_step / self.total_steps) * 100
        self.logger.info(f"[{progress:.1f}%] {step_name}")
    
    def set_step(self, step: int, step_name: str):
        """设置当前步骤"""
        self.current_step = step
        progress = (self.current_step / self.total_steps) * 100
        self.logger.info(f"[{progress:.1f}%] {step_name}")
    
    def complete(self, message: str = "处理完成"):
        """标记完成"""
        self.current_step = self.total_steps
        self.logger.info(f"[100.0%] {message}")


class LoggerMixin:
    """日志混入类"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取logger"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
