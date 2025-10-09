"""
快速分块器 - 基于 max_tokens 的简单快速分块策略
"""

import logging
import os
from typing import List, Dict, Any, Optional

from .base_chunker import BaseChunker, DocumentChunk

logger = logging.getLogger(__name__)


def _get_default_max_tokens() -> int:
    """
    从环境变量获取默认的 max_tokens 值

    Returns:
        默认的 max_tokens 值
    """
    try:
        # 尝试从环境变量读取
        env_value = os.getenv("MAX_TOKENS")
        if env_value:
            return int(env_value)
    except (ValueError, TypeError):
        logger.warning(f"无效的 MAX_TOKENS 环境变量值: {env_value}")

    # 如果环境变量不存在或无效，返回默认值
    return 4000


class FastChunker(BaseChunker):
    """
    快速分块器，基于 max_tokens 的简单分块策略
    
    - 块大小：max_tokens 的 1/3
    - 重叠大小：max_tokens 的 1/10
    - 优化速度，适合大文档的快速处理
    """
    
    def __init__(
        self,
        max_tokens: Optional[int] = None,
        chars_per_token: float = 4.0
    ) -> None:
        """
        初始化快速分块器

        Args:
            max_tokens: 最大 token 数量，如果为 None 则从环境变量读取
            chars_per_token: 每个 token 的平均字符数（用于估算）
        """
        # 如果没有提供 max_tokens，从环境变量获取默认值
        if max_tokens is None:
            max_tokens = _get_default_max_tokens()

        # 计算块大小和重叠大小（以 token 为单位）
        self.chunk_size_tokens = max_tokens // 3
        self.chunk_overlap_tokens = max_tokens // 10

        # 为了与 BaseChunker 兼容，我们使用 token 数量作为"字符"数量
        # 实际的字符长度控制在 _split_text_fast 方法中处理
        chunk_size = self.chunk_size_tokens
        chunk_overlap = self.chunk_overlap_tokens

        super().__init__(chunk_size, chunk_overlap)

        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token

        logger.info(f"快速分块器初始化: max_tokens={max_tokens}, "
                   f"chunk_size={self.chunk_size_tokens}, chunk_overlap={self.chunk_overlap_tokens}")
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        使用快速策略分块文本
        
        Args:
            text: 输入文本
            metadata: 可选的元数据
            
        Returns:
            DocumentChunk对象列表
        """
        if metadata is None:
            metadata = {}
        
        # 快速分割文本
        text_chunks = self._split_text_fast(text)
        
        # 转换为DocumentChunk对象
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "chunking_strategy": "fast",
                "estimated_tokens": len(chunk_text) / self.chars_per_token
            })
            chunks.append(self._create_chunk(chunk_text, chunk_metadata))
        
        logger.info(f"创建了 {len(chunks)} 个快速块")
        return chunks
    
    def _split_text_fast(self, text: str) -> List[str]:
        """
        快速分割文本，基于 token 数量进行分割

        Args:
            text: 要分割的文本

        Returns:
            文本块列表
        """
        # 估算文本的 token 数量
        estimated_tokens = self.get_token_estimate(text)

        if estimated_tokens <= self.chunk_size_tokens:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            # 计算当前块的字符长度（基于 token 限制）
            max_chars = int(self.chunk_size_tokens * self.chars_per_token)
            end = min(start + max_chars, len(text))

            if end >= len(text):
                # 最后一个块
                remaining_text = text[start:]
                if remaining_text.strip():
                    chunks.append(remaining_text)
                break

            # 尝试在自然断点处分割
            chunk_text = text[start:end]
            split_point = self._find_split_point(chunk_text)

            if split_point > 0:
                # 在自然断点处分割
                actual_end = start + split_point
                chunk_content = text[start:actual_end]
                chunks.append(chunk_content)

                # 下一个块的开始位置考虑重叠
                overlap_chars = int(self.chunk_overlap_tokens * self.chars_per_token)
                start = actual_end - overlap_chars
            else:
                # 没有找到自然断点，强制分割
                chunks.append(chunk_text)
                overlap_chars = int(self.chunk_overlap_tokens * self.chars_per_token)
                start = end - overlap_chars

            # 确保不会无限循环
            if start < 0:
                start = 0

        return [chunk for chunk in chunks if chunk.strip()]
    
    def _find_split_point(self, text: str) -> int:
        """
        在文本中找到最佳分割点
        
        Args:
            text: 要分析的文本
            
        Returns:
            分割点位置，如果没有找到返回0
        """
        # 优先级分隔符列表（从后往前查找）
        separators = [
            "\n\n",  # 段落分隔符
            "\n",    # 行分隔符
            ". ",    # 英文句子分隔符
            "。",    # 中文句子分隔符
            "! ",    # 英文感叹句
            "！",    # 中文感叹句
            "? ",    # 英文疑问句
            "？",    # 中文疑问句
            "; ",    # 分号
            "；",    # 中文分号
            ", ",    # 逗号
            "，",    # 中文逗号
            " "      # 空格
        ]
        
        # 从文本末尾向前查找最佳分割点
        for separator in separators:
            # 在文本的后半部分查找分隔符
            search_start = len(text) // 2
            pos = text.rfind(separator, search_start)
            if pos != -1:
                return pos + len(separator)
        
        return 0
    
    def get_token_estimate(self, text: str) -> int:
        """
        估算文本的 token 数量
        
        Args:
            text: 要估算的文本
            
        Returns:
            估算的 token 数量
        """
        return int(len(text) / self.chars_per_token)
    
    def adjust_for_token_limit(self, chunks: List[DocumentChunk], token_limit: int) -> List[DocumentChunk]:
        """
        根据 token 限制调整块
        
        Args:
            chunks: 原始块列表
            token_limit: token 限制
            
        Returns:
            调整后的块列表
        """
        adjusted_chunks = []
        
        for chunk in chunks:
            estimated_tokens = self.get_token_estimate(chunk.content)
            
            if estimated_tokens <= token_limit:
                adjusted_chunks.append(chunk)
            else:
                # 如果块太大，进一步分割
                sub_chunks = self._split_large_chunk(chunk, token_limit)
                adjusted_chunks.extend(sub_chunks)
        
        return adjusted_chunks
    
    def _split_large_chunk(self, chunk: DocumentChunk, token_limit: int) -> List[DocumentChunk]:
        """
        分割过大的块
        
        Args:
            chunk: 要分割的块
            token_limit: token 限制
            
        Returns:
            分割后的块列表
        """
        max_chars = int(token_limit * self.chars_per_token)
        
        if len(chunk.content) <= max_chars:
            return [chunk]
        
        # 创建临时分块器
        temp_chunker = FastChunker(
            max_tokens=token_limit,
            chars_per_token=self.chars_per_token
        )
        
        # 分割内容
        sub_chunks = temp_chunker.chunk_text(chunk.content, chunk.metadata)
        
        # 更新元数据
        for i, sub_chunk in enumerate(sub_chunks):
            sub_chunk.metadata.update({
                "parent_chunk_id": chunk.chunk_id,
                "sub_chunk_index": i,
                "is_sub_chunk": True
            })
        
        return sub_chunks
