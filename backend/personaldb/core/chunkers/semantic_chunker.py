"""
语义分块器 - 基于Markdown头部结构的智能分块
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from .base_chunker import BaseChunker, DocumentChunk

logger = logging.getLogger(__name__)


class SemanticChunker(BaseChunker):
    """
    语义分块器，使用Markdown头部结构创建有意义的块
    
    这是主要推荐的分块策略，因为它保留了文档结构和语义边界
    """
    
    def __init__(
        self, 
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        headers_to_split_on: Optional[List[Tuple[str, str]]] = None
    ) -> None:
        """
        初始化语义分块器
        
        Args:
            chunk_size: 每个块的最大大小
            chunk_overlap: 块之间的重叠
            headers_to_split_on: (头部模式, 头部名称) 元组列表
        """
        super().__init__(chunk_size, chunk_overlap)
        
        if headers_to_split_on is None:
            self.headers_to_split_on = [
                ("#", "Chapter"),
                ("##", "Section"),
                ("###", "Subsection"),
                ("####", "Subsubsection"),
            ]
        else:
            self.headers_to_split_on = headers_to_split_on
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        使用Markdown头部结构和自定义模式分块文本

        Args:
            text: 输入文本（最好是Markdown格式）
            metadata: 可选的元数据

        Returns:
            DocumentChunk对象列表
        """
        if metadata is None:
            metadata = {}

        try:
            # 首先尝试标准Markdown头部
            chunks = self._chunk_by_markdown_headers(text, metadata)

            # 如果只得到一个块，尝试自定义模式
            if len(chunks) <= 1:
                logger.info("未找到标准Markdown头部，尝试自定义模式")
                return self._chunk_with_custom_patterns(text, metadata)

            # 验证块大小并在必要时分割
            final_chunks = []
            for i, chunk in enumerate(chunks):
                if not self.validate_chunk_size(chunk):
                    logger.warning(f"块 {i} 超过大小限制，应用递归分割")
                    sub_chunks = self._split_large_chunk(chunk)
                    final_chunks.extend(sub_chunks)
                else:
                    final_chunks.append(chunk)

            logger.info(f"创建了 {len(final_chunks)} 个语义块")
            return final_chunks

        except Exception as e:
            logger.error(f"语义分块错误: {e}")
            # 回退到简单段落分割
            return self._fallback_chunking(text, metadata)
    
    def _chunk_by_markdown_headers(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        基于Markdown头部分块
        
        Args:
            text: 输入文本
            metadata: 基础元数据
            
        Returns:
            DocumentChunk对象列表
        """
        lines = text.split('\n')
        chunks = []
        current_chunk_lines = []
        current_headers = {}
        chunk_index = 0
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # 检查是否是头部
            header_info = self._detect_header(line_stripped)
            
            if header_info:
                # 保存当前块（如果有内容）
                if current_chunk_lines:
                    chunk_content = '\n'.join(current_chunk_lines).strip()
                    if chunk_content:
                        chunk_metadata = metadata.copy()
                        chunk_metadata.update({
                            "chunk_index": chunk_index,
                            "chunking_strategy": "semantic",
                            "headers": current_headers.copy(),
                            "start_line": line_num - len(current_chunk_lines),
                            "end_line": line_num - 1
                        })
                        chunks.append(self._create_chunk(chunk_content, chunk_metadata))
                        chunk_index += 1
                
                # 更新当前头部信息
                header_level, header_name = header_info
                current_headers[header_name] = line_stripped[header_level:].strip()
                
                # 清除更深层级的头部
                levels_to_remove = []
                for existing_level, existing_name in self.headers_to_split_on:
                    if len(existing_level) > header_level:
                        levels_to_remove.append(existing_name)
                
                for level_name in levels_to_remove:
                    current_headers.pop(level_name, None)
                
                # 开始新块
                current_chunk_lines = [line]
            else:
                current_chunk_lines.append(line)
        
        # 添加最后一个块
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines).strip()
            if chunk_content:
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": chunk_index,
                    "chunking_strategy": "semantic",
                    "headers": current_headers.copy(),
                    "start_line": len(lines) - len(current_chunk_lines) + 1,
                    "end_line": len(lines)
                })
                chunks.append(self._create_chunk(chunk_content, chunk_metadata))
        
        return chunks
    
    def _detect_header(self, line: str) -> Optional[Tuple[int, str]]:
        """
        检测是否为头部行
        
        Args:
            line: 要检测的行
            
        Returns:
            (头部级别, 头部名称) 或 None
        """
        for header_pattern, header_name in self.headers_to_split_on:
            if line.startswith(header_pattern + ' '):
                return len(header_pattern), header_name
        return None

    def _split_large_chunk(self, chunk: DocumentChunk) -> List[DocumentChunk]:
        """
        分割大块使用递归字符分割

        Args:
            chunk: 要分割的大块

        Returns:
            较小块的列表
        """
        # 导入递归分块器作为回退
        from .recursive_chunker import RecursiveChunker

        recursive_chunker = RecursiveChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        sub_chunks = recursive_chunker.chunk_text(chunk.content, chunk.metadata)

        # 更新元数据以表明这是从语义块分割的
        for i, sub_chunk in enumerate(sub_chunks):
            sub_chunk.metadata["parent_chunk_id"] = chunk.chunk_id
            sub_chunk.metadata["sub_chunk_index"] = i
            sub_chunk.metadata["chunking_strategy"] = "semantic_recursive"

        return sub_chunks

    def _chunk_with_custom_patterns(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        当未找到标准Markdown头部时使用自定义模式分块文本

        Args:
            text: 输入文本
            metadata: 基础元数据

        Returns:
            DocumentChunk对象列表
        """
        logger.info("使用基于自定义模式的分块")

        # 尝试查找可能表示结构的自定义模式
        custom_patterns = [
            r'^[A-Z][^.!?]*[.!?]\s*$',  # 可能是标题的句子
            r'^\d+\.\s+',  # 编号列表
            r'^[A-Z\s]+:',  # 带冒号的全大写标签
            r'^[*-]\s+',   # 项目符号
            r'^\w+\s*\([^)]*\)',  # 带括号的文本
        ]

        lines = text.split('\n')
        potential_breaks = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检查行是否匹配任何自定义模式
            for pattern in custom_patterns:
                if re.match(pattern, line):
                    potential_breaks.append(i)
                    break

        # 如果找到潜在断点，使用它们
        if potential_breaks:
            return self._chunk_by_breaks(text, potential_breaks, metadata)
        else:
            # 回退到基于段落的分块
            return self._fallback_chunking(text, metadata)

    def _chunk_by_breaks(self, text: str, break_points: List[int], metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        使用识别的断点分块文本

        Args:
            text: 输入文本
            break_points: 应该发生断点的行号
            metadata: 基础元数据

        Returns:
            DocumentChunk对象列表
        """
        lines = text.split('\n')
        chunks = []
        current_chunk_lines = []
        chunk_index = 0

        for i, line in enumerate(lines):
            current_chunk_lines.append(line)

            # 检查这是否是断点且我们有内容
            if i in break_points and len(current_chunk_lines) > 1:
                # 从累积的行创建块（排除当前行）
                chunk_content = '\n'.join(current_chunk_lines[:-1]).strip()
                if chunk_content:
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": chunk_index,
                        "chunking_strategy": "custom_pattern"
                    })
                    chunks.append(self._create_chunk(chunk_content, chunk_metadata))
                    chunk_index += 1

                # 用当前行开始新块
                current_chunk_lines = [line]

        # 如果有剩余内容，添加最后一个块
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines).strip()
            if chunk_content:
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": chunk_index,
                    "chunking_strategy": "custom_pattern"
                })
                chunks.append(self._create_chunk(chunk_content, chunk_metadata))

        return chunks

    def _fallback_chunking(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        当Markdown解析失败时的回退分块方法

        Args:
            text: 输入文本
            metadata: 基础元数据

        Returns:
            DocumentChunk对象列表
        """
        logger.warning("使用基于段落的回退分块")

        # 按双换行符分割（段落）
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        chunk_index = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # 检查添加此段落是否会超过块大小
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph

            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # 如果有内容，保存当前块
                if current_chunk:
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": chunk_index,
                        "chunking_strategy": "fallback_paragraph"
                    })
                    chunks.append(self._create_chunk(current_chunk, chunk_metadata))
                    chunk_index += 1

                # 用当前段落开始新块
                current_chunk = paragraph

        # 添加最后一个块
        if current_chunk:
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": chunk_index,
                "chunking_strategy": "fallback_paragraph"
            })
            chunks.append(self._create_chunk(current_chunk, chunk_metadata))

        return chunks

    def extract_document_structure(self, text: str) -> Dict[str, Any]:
        """
        提取文档结构信息

        Args:
            text: 输入文本

        Returns:
            包含结构信息的字典
        """
        structure = {
            "headers": [],
            "total_sections": 0,
            "max_depth": 0
        }

        lines = text.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            for header_pattern, header_name in self.headers_to_split_on:
                if line.startswith(header_pattern + ' '):
                    header_text = line[len(header_pattern):].strip()
                    depth = len(header_pattern)

                    structure["headers"].append({
                        "text": header_text,
                        "level": header_name,
                        "depth": depth,
                        "line_number": line_num
                    })

                    structure["max_depth"] = max(structure["max_depth"], depth)
                    break

        structure["total_sections"] = len(structure["headers"])
        return structure
