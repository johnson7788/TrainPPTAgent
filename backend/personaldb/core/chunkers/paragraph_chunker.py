"""
段落分块器 - 基于段落边界的分块策略
"""

import re
import logging
from typing import List, Dict, Any, Optional

from .base_chunker import BaseChunker, DocumentChunk

logger = logging.getLogger(__name__)


class ParagraphChunker(BaseChunker):
    """
    段落分块器，基于段落边界分割文本
    
    这个分块器尝试保持段落的完整性，只在段落边界处分割
    """
    
    def __init__(
        self, 
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        paragraph_separator: str = r'\n\s*\n'
    ) -> None:
        """
        初始化段落分块器
        
        Args:
            chunk_size: 每个块的最大大小
            chunk_overlap: 块之间的重叠
            paragraph_separator: 段落分隔符的正则表达式
        """
        super().__init__(chunk_size, chunk_overlap)
        self.paragraph_separator = paragraph_separator
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        基于段落分块文本
        
        Args:
            text: 输入文本
            metadata: 可选的元数据
            
        Returns:
            DocumentChunk对象列表
        """
        if metadata is None:
            metadata = {}
        
        # 按段落分割
        paragraphs = re.split(self.paragraph_separator, text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return []
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            # 检查添加此段落是否会超过块大小
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # 保存当前块
                if current_chunk:
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": chunk_index,
                        "chunking_strategy": "paragraph"
                    })
                    chunks.append(self._create_chunk(current_chunk, chunk_metadata))
                    chunk_index += 1
                
                # 如果单个段落太长，需要进一步分割
                if len(paragraph) > self.chunk_size:
                    sub_chunks = self._split_long_paragraph(paragraph, metadata, chunk_index)
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk:
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": chunk_index,
                "chunking_strategy": "paragraph"
            })
            chunks.append(self._create_chunk(current_chunk, chunk_metadata))
        
        # 添加重叠
        if self.chunk_overlap > 0:
            chunks = self._add_overlap_to_chunks(chunks)
        
        logger.info(f"创建了 {len(chunks)} 个段落块")
        return chunks
    
    def _split_long_paragraph(self, paragraph: str, metadata: Dict[str, Any], start_index: int) -> List[DocumentChunk]:
        """
        分割过长的段落
        
        Args:
            paragraph: 要分割的段落
            metadata: 基础元数据
            start_index: 起始索引
            
        Returns:
            DocumentChunk对象列表
        """
        # 尝试按句子分割
        sentences = re.split(r'[.!?。！？]\s*', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            # 如果没有句子，强制分割
            chunks = []
            for i in range(0, len(paragraph), self.chunk_size):
                chunk_text = paragraph[i:i + self.chunk_size]
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": start_index + i // self.chunk_size,
                    "chunking_strategy": "paragraph_forced",
                    "is_split_paragraph": True
                })
                chunks.append(self._create_chunk(chunk_text, chunk_metadata))
            return chunks
        
        chunks = []
        current_chunk = ""
        chunk_index = start_index
        
        for sentence in sentences:
            # 检查添加此句子是否会超过限制
            potential_chunk = current_chunk + ". " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # 保存当前块
                if current_chunk:
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": chunk_index,
                        "chunking_strategy": "paragraph_sentence",
                        "is_split_paragraph": True
                    })
                    chunks.append(self._create_chunk(current_chunk, chunk_metadata))
                    chunk_index += 1
                
                # 如果单个句子太长，强制分割
                if len(sentence) > self.chunk_size:
                    for i in range(0, len(sentence), self.chunk_size):
                        chunk_text = sentence[i:i + self.chunk_size]
                        chunk_metadata = metadata.copy()
                        chunk_metadata.update({
                            "chunk_index": chunk_index,
                            "chunking_strategy": "paragraph_forced",
                            "is_split_paragraph": True,
                            "is_split_sentence": True
                        })
                        chunks.append(self._create_chunk(chunk_text, chunk_metadata))
                        chunk_index += 1
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": chunk_index,
                "chunking_strategy": "paragraph_sentence",
                "is_split_paragraph": True
            })
            chunks.append(self._create_chunk(current_chunk, chunk_metadata))
        
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
