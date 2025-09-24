"""
核心模块 - 包含数据模型、文档处理、LLM管理等核心功能
"""

from .models import SlideInfo, PPTState, ChunkStrategy
from .document_processor import DocumentProcessor
from .llm_manager import LLMManager
from .json_parser import JSONParser
from .file_cache_manager import FileCacheManager

__all__ = [
    "SlideInfo",
    "PPTState",
    "ChunkStrategy",
    "DocumentProcessor",
    "LLMManager",
    "JSONParser",
    "FileCacheManager",
]
