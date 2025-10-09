"""
递归分块器 - 使用递归字符分割策略
"""

import logging
from typing import List, Dict, Any, Optional

from .base_chunker import BaseChunker, DocumentChunk

logger = logging.getLogger(__name__)


class RecursiveChunker(BaseChunker):
    """
    递归分块器，使用分层分隔符递归分割文本
    
    这个分块器尝试在自然断点处分割文本，如段落、句子等
    """
    
    def __init__(
        self, 
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ) -> None:
        """
        初始化递归分块器
        
        Args:
            chunk_size: 每个块的最大大小
            chunk_overlap: 块之间的重叠
            separators: 分隔符列表，按优先级排序
        """
        super().__init__(chunk_size, chunk_overlap)
        
        if separators is None:
            self.separators = [
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
                " ",     # 空格
                ""       # 字符级分割（最后手段）
            ]
        else:
            self.separators = separators
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        使用递归策略分块文本
        
        Args:
            text: 输入文本
            metadata: 可选的元数据
            
        Returns:
            DocumentChunk对象列表
        """
        if metadata is None:
            metadata = {}
        
        # 递归分割文本
        text_chunks = self._split_text_recursive(text)
        
        # 转换为DocumentChunk对象
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "chunking_strategy": "recursive"
            })
            chunks.append(self._create_chunk(chunk_text, chunk_metadata))
        
        # 添加重叠
        if self.chunk_overlap > 0:
            chunks = self._add_overlap_to_chunks(chunks)
        
        logger.info(f"创建了 {len(chunks)} 个递归块")
        return chunks
    
    def _split_text_recursive(self, text: str) -> List[str]:
        """
        递归分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            文本块列表
        """
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        # 尝试每个分隔符
        for separator in self.separators:
            if separator in text:
                return self._split_by_separator(text, separator)
        
        # 如果没有找到分隔符，强制分割
        logger.warning("未找到合适的分隔符，强制分割文本")
        return [text[:self.chunk_size], text[self.chunk_size:]]
    
    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """
        使用指定分隔符分割文本
        
        Args:
            text: 要分割的文本
            separator: 分隔符
            
        Returns:
            文本块列表
        """
        if separator == "":
            # 字符级分割
            mid_point = self.chunk_size
            left_part = text[:mid_point]
            right_part = text[mid_point:]
            
            left_chunks = self._split_text_recursive(left_part)
            right_chunks = self._split_text_recursive(right_part)
            
            return left_chunks + right_chunks
        
        # 分割文本
        parts = text.split(separator)
        
        # 重新组合块
        chunks = []
        current_chunk = ""
        
        for part in parts:
            # 检查添加这部分是否会超过限制
            potential_chunk = current_chunk + separator + part if current_chunk else part
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果单个部分太大，递归分割
                if len(part) > self.chunk_size:
                    sub_chunks = self._split_text_recursive(part)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _add_overlap_to_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        为块添加重叠
        
        Args:
            chunks: 原始块列表
            
        Returns:
            带重叠的块列表
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]
            
            # 从前一个块的末尾提取重叠内容
            prev_content = prev_chunk.content
            overlap_text = prev_content[-self.chunk_overlap:] if len(prev_content) > self.chunk_overlap else prev_content
            
            # 创建新的块内容
            new_content = overlap_text + "\n\n" + current_chunk.content
            
            # 更新块内容
            new_metadata = current_chunk.metadata.copy()
            new_metadata["has_overlap"] = True
            new_metadata["overlap_size"] = len(overlap_text)
            
            overlapped_chunk = self._create_chunk(new_content, new_metadata)
            overlapped_chunk.chunk_id = current_chunk.chunk_id  # 保持原始ID
            
            overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks
