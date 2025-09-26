"""
基础分块器抽象类
"""

import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """文档块数据类"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """后处理初始化"""
        if not self.chunk_id:
            self.chunk_id = str(uuid.uuid4())
    
    @property
    def size(self) -> int:
        """获取块大小（字符数）"""
        return len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "chunk_id": self.chunk_id,
            "size": self.size
        }


class BaseChunker(ABC):
    """
    基础分块器抽象类
    
    所有分块器都应该继承这个类并实现chunk_text方法
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        """
        初始化分块器
        
        Args:
            chunk_size: 块大小限制
            chunk_overlap: 块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        分块文本的抽象方法
        
        Args:
            text: 要分块的文本
            metadata: 可选的元数据
            
        Returns:
            DocumentChunk对象列表
        """
        pass
    
    def validate_chunk_size(self, chunk: DocumentChunk) -> bool:
        """
        验证块大小是否符合要求
        
        Args:
            chunk: 要验证的块
            
        Returns:
            是否符合大小要求
        """
        return chunk.size <= self.chunk_size
    
    def _create_chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentChunk:
        """
        创建文档块
        
        Args:
            content: 块内容
            metadata: 块元数据
            
        Returns:
            DocumentChunk对象
        """
        if metadata is None:
            metadata = {}
        
        return DocumentChunk(
            content=content.strip(),
            metadata=metadata
        )
    
    def get_chunk_statistics(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        获取分块统计信息
        
        Args:
            chunks: 块列表
            
        Returns:
            统计信息字典
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "total_size": 0,
                "avg_size": 0,
                "min_size": 0,
                "max_size": 0
            }
        
        sizes = [chunk.size for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_size": sum(sizes),
            "avg_size": sum(sizes) / len(sizes),
            "min_size": min(sizes),
            "max_size": max(sizes)
        }
