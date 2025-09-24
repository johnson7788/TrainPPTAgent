"""
混合分块器 - 结合多种分块策略的智能分块器
"""

import logging
from typing import List, Dict, Any, Optional

from .base_chunker import BaseChunker, DocumentChunk
from .semantic_chunker import SemanticChunker
from .paragraph_chunker import ParagraphChunker
from .recursive_chunker import RecursiveChunker

logger = logging.getLogger(__name__)


class HybridChunker(BaseChunker):
    """
    混合分块器，智能选择和组合多种分块策略
    
    这个分块器首先尝试语义分块，然后对过大的块使用段落分块，
    最后对仍然过大的块使用递归分块
    """
    
    def __init__(
        self, 
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        size_tolerance: float = 1.2
    ) -> None:
        """
        初始化混合分块器
        
        Args:
            chunk_size: 每个块的最大大小
            chunk_overlap: 块之间的重叠
            size_tolerance: 大小容忍度（超过此倍数的块将被进一步分割）
        """
        super().__init__(chunk_size, chunk_overlap)
        self.size_tolerance = size_tolerance
        
        # 初始化子分块器
        self.semantic_chunker = SemanticChunker(chunk_size, chunk_overlap)
        self.paragraph_chunker = ParagraphChunker(chunk_size, chunk_overlap)
        self.recursive_chunker = RecursiveChunker(chunk_size, chunk_overlap)
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        使用混合策略分块文本
        
        Args:
            text: 输入文本
            metadata: 可选的元数据
            
        Returns:
            DocumentChunk对象列表
        """
        if metadata is None:
            metadata = {}
        
        logger.info("开始混合分块策略")
        
        # 第一步：尝试语义分块
        try:
            chunks = self.semantic_chunker.chunk_text(text, metadata)
            logger.info(f"语义分块产生了 {len(chunks)} 个块")
            
            # 检查是否有过大的块需要进一步处理
            final_chunks = []
            for chunk in chunks:
                if self._is_chunk_too_large(chunk):
                    logger.info(f"块 {chunk.chunk_id} 过大，应用段落分块")
                    sub_chunks = self._apply_paragraph_chunking(chunk)
                    final_chunks.extend(sub_chunks)
                else:
                    final_chunks.append(chunk)
            
            # 第三步：对仍然过大的块应用递归分块
            ultra_final_chunks = []
            for chunk in final_chunks:
                if self._is_chunk_too_large(chunk):
                    logger.info(f"块 {chunk.chunk_id} 仍然过大，应用递归分块")
                    sub_chunks = self._apply_recursive_chunking(chunk)
                    ultra_final_chunks.extend(sub_chunks)
                else:
                    ultra_final_chunks.append(chunk)
            
            # 更新元数据
            for i, chunk in enumerate(ultra_final_chunks):
                chunk.metadata["final_chunk_index"] = i
                chunk.metadata["chunking_strategy"] = "hybrid"
            
            logger.info(f"混合分块完成，最终产生了 {len(ultra_final_chunks)} 个块")
            return ultra_final_chunks
            
        except Exception as e:
            logger.error(f"混合分块失败，回退到段落分块: {e}")
            return self.paragraph_chunker.chunk_text(text, metadata)
    
    def _is_chunk_too_large(self, chunk: DocumentChunk) -> bool:
        """
        检查块是否过大
        
        Args:
            chunk: 要检查的块
            
        Returns:
            是否过大
        """
        return chunk.size > self.chunk_size * self.size_tolerance
    
    def _apply_paragraph_chunking(self, chunk: DocumentChunk) -> List[DocumentChunk]:
        """
        对单个块应用段落分块
        
        Args:
            chunk: 要分块的块
            
        Returns:
            分块后的块列表
        """
        # 创建新的元数据，保留原始信息
        new_metadata = chunk.metadata.copy()
        new_metadata["parent_chunk_id"] = chunk.chunk_id
        new_metadata["parent_strategy"] = chunk.metadata.get("chunking_strategy", "unknown")
        
        # 应用段落分块
        sub_chunks = self.paragraph_chunker.chunk_text(chunk.content, new_metadata)
        
        # 更新元数据
        for i, sub_chunk in enumerate(sub_chunks):
            sub_chunk.metadata["sub_chunk_index"] = i
            sub_chunk.metadata["chunking_strategy"] = "hybrid_paragraph"
        
        return sub_chunks
    
    def _apply_recursive_chunking(self, chunk: DocumentChunk) -> List[DocumentChunk]:
        """
        对单个块应用递归分块
        
        Args:
            chunk: 要分块的块
            
        Returns:
            分块后的块列表
        """
        # 创建新的元数据，保留原始信息
        new_metadata = chunk.metadata.copy()
        new_metadata["parent_chunk_id"] = chunk.chunk_id
        new_metadata["parent_strategy"] = chunk.metadata.get("chunking_strategy", "unknown")
        
        # 应用递归分块
        sub_chunks = self.recursive_chunker.chunk_text(chunk.content, new_metadata)
        
        # 更新元数据
        for i, sub_chunk in enumerate(sub_chunks):
            sub_chunk.metadata["sub_chunk_index"] = i
            sub_chunk.metadata["chunking_strategy"] = "hybrid_recursive"
        
        return sub_chunks
    
    def analyze_text_structure(self, text: str) -> Dict[str, Any]:
        """
        分析文本结构以选择最佳分块策略
        
        Args:
            text: 输入文本
            
        Returns:
            结构分析结果
        """
        analysis = {
            "text_length": len(text),
            "line_count": len(text.split('\n')),
            "paragraph_count": len([p for p in text.split('\n\n') if p.strip()]),
            "has_markdown_headers": False,
            "header_count": 0,
            "recommended_strategy": "paragraph"
        }
        
        # 检查Markdown头部
        lines = text.split('\n')
        header_count = 0
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                header_count += 1
        
        analysis["header_count"] = header_count
        analysis["has_markdown_headers"] = header_count > 0
        
        # 推荐策略
        if header_count >= 3:
            analysis["recommended_strategy"] = "semantic"
        elif analysis["paragraph_count"] >= 5:
            analysis["recommended_strategy"] = "paragraph"
        else:
            analysis["recommended_strategy"] = "recursive"
        
        return analysis
    
    def get_chunking_statistics(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        获取分块统计信息
        
        Args:
            chunks: 块列表
            
        Returns:
            统计信息
        """
        if not chunks:
            return {"total_chunks": 0}
        
        # 基础统计
        base_stats = self.get_chunk_statistics(chunks)
        
        # 策略统计
        strategy_counts = {}
        for chunk in chunks:
            strategy = chunk.metadata.get("chunking_strategy", "unknown")
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        # 大小分布
        sizes = [chunk.size for chunk in chunks]
        oversized_count = sum(1 for size in sizes if size > self.chunk_size)
        
        base_stats.update({
            "strategy_distribution": strategy_counts,
            "oversized_chunks": oversized_count,
            "oversized_percentage": (oversized_count / len(chunks)) * 100 if chunks else 0,
            "size_tolerance": self.size_tolerance
        })
        
        return base_stats
