"""
文档处理器 - 处理各种格式的文档并进行智能分块
"""

import re
import os
import tempfile
import shutil
import hashlib
import json
from typing import List, Optional, Tuple, Dict, Any
import logging
from pathlib import Path
from datetime import datetime

from .models import DocumentInfo, ChunkStrategy
from .chunkers import (
    SemanticChunker,
    RecursiveChunker,
    ParagraphChunker,
    HybridChunker,
    FastChunker,
    DocumentChunk
)
from .markitdown_converter import MarkItDownConverter
from .file_cache_manager import FileCacheManager

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文档处理器，支持多种文件格式和分块策略"""
    
    SUPPORTED_EXTENSIONS = {
        # 使用MarkItDown处理的格式（推荐）
        '.pdf': 'markitdown',
        '.pptx': 'markitdown',
        '.ppt': 'markitdown',
        '.docx': 'markitdown',
        '.doc': 'markitdown',
        '.xlsx': 'markitdown',
        '.xls': 'markitdown',
        '.jpg': 'markitdown',
        '.jpeg': 'markitdown',
        '.png': 'markitdown',
        '.gif': 'markitdown',
        '.bmp': 'markitdown',
        '.tiff': 'markitdown',
        '.webp': 'markitdown',
        '.mp3': 'markitdown',
        '.wav': 'markitdown',
        '.m4a': 'markitdown',
        '.flac': 'markitdown',
        '.zip': 'markitdown',
        '.epub': 'markitdown',
        '.xml': 'markitdown',
        '.html': 'markitdown',
        '.htm': 'markitdown',

        # 使用传统方式处理的格式（保持兼容性）
        '.txt': 'text',
        '.md': 'markdown',
        '.csv': 'csv',
        '.json': 'json',
    }
    
    def __init__(self, save_markdown: bool = False, temp_dir: Optional[str] = None,
                 use_magic_pdf: bool = True, enable_cache: bool = True, cache_ttl_hours: int = 24 * 7,
                 cache_dir: Optional[str] = None, processing_mode: Optional[str] = None):
        self.encoding_detectors = ['utf-8', 'gbk', 'gb2312', 'ascii', 'latin-1']

        # 初始化分块器（延迟初始化以避免循环导入）
        self._chunkers = {}

        # 初始化MarkItDown转换器（延迟初始化）
        self._markitdown_converter = None
        self.use_magic_pdf = use_magic_pdf

        # Markdown保存配置
        self.save_markdown = save_markdown
        self.temp_dir = temp_dir or os.path.join(tempfile.gettempdir(), "summeryanyfile_markdown")

        # 文件缓存配置
        self.enable_cache = enable_cache
        self._cache_manager = None
        if enable_cache:
            # 根据use_magic_pdf确定处理模式
            if processing_mode is None:
                processing_mode = "magic_pdf" if use_magic_pdf else "markitdown"
            self._cache_manager = FileCacheManager(
                cache_dir=cache_dir,
                cache_ttl_hours=cache_ttl_hours,
                processing_mode=processing_mode
            )

        # 创建temp目录
        if self.save_markdown:
            os.makedirs(self.temp_dir, exist_ok=True)
            logger.info(f"Markdown文件将保存到: {self.temp_dir}")

        if enable_cache:
            logger.info("文件缓存功能已启用")
    
    def load_document(self, file_path: str, encoding: Optional[str] = None) -> DocumentInfo:
        """
        加载文档

        Args:
            file_path: 文件路径
            encoding: 指定编码，如果为None则自动检测

        Returns:
            文档信息对象

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")

        file_extension = path.suffix.lower()
        if file_extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {file_extension}")

        logger.info(f"开始处理文档: {file_path}")

        # 检查缓存
        if self.enable_cache and self._cache_manager:
            is_cached, md5_hash = self._cache_manager.is_cached(file_path)
            if is_cached and md5_hash:
                logger.info(f"使用缓存的文件处理结果: {md5_hash}")
                cached_content, cached_metadata = self._cache_manager.get_cached_content(md5_hash)

                if cached_content:
                    # 从缓存元数据中恢复信息
                    file_type = cached_metadata.get('processing_metadata', {}).get('file_type') or self.SUPPORTED_EXTENSIONS[file_extension]
                    detected_encoding = cached_metadata.get('processing_metadata', {}).get('detected_encoding', 'utf-8')
                    file_size = cached_metadata.get('original_file_size', path.stat().st_size)

                    # 如果启用了Markdown保存，也保存到temp目录
                    if self.save_markdown and cached_content.strip():
                        self._save_markdown_file(file_path, cached_content)

                    # 提取标题
                    title = self._extract_title(cached_content, path.stem)

                    logger.info(f"成功从缓存恢复文档: {path.name}")
                    return DocumentInfo(
                        title=title,
                        content=cached_content,
                        file_path=str(path.absolute()),
                        file_type=file_type,
                        encoding=detected_encoding,
                        size=file_size,
                    )

        file_type = self.SUPPORTED_EXTENSIONS[file_extension]
        file_size = path.stat().st_size

        # 提取文本内容
        content, detected_encoding = self._extract_text(file_path, file_type, encoding)

        # 保存到缓存
        if self.enable_cache and self._cache_manager and content.strip():
            try:
                processing_metadata = {
                    'file_type': file_type,
                    'detected_encoding': detected_encoding,
                    'processing_method': 'markitdown' if file_extension in ['.pdf', '.docx', '.pptx'] else 'direct'
                }
                md5_hash = self._cache_manager.save_to_cache(file_path, content, processing_metadata)
                logger.info(f"文件处理结果已缓存: {md5_hash}")
            except Exception as e:
                logger.warning(f"保存缓存失败，继续处理: {e}")

        # 如果启用了Markdown保存且内容不为空，保存Markdown文件
        if self.save_markdown and content.strip():
            self._save_markdown_file(file_path, content)

        # 提取标题
        title = self._extract_title(content, path.stem)

        return DocumentInfo(
            title=title,
            content=content,
            file_path=str(path.absolute()),
            file_type=file_type,
            encoding=detected_encoding,
            size=file_size,
        )

    def load_from_url(self, url: str) -> DocumentInfo:
        """
        从URL加载文档（支持YouTube等）

        Args:
            url: URL地址

        Returns:
            文档信息对象

        Raises:
            ValueError: URL处理失败
        """
        logger.info(f"正在从URL加载文档: {url}")

        try:
            converter = self._get_markitdown_converter()
            content, encoding = converter.convert_url(url)

            # 清理和优化内容
            content = converter.clean_markdown_content(content)

            # 从URL提取标题
            title = self._extract_title_from_url(url, content)

            return DocumentInfo(
                title=title,
                content=content,
                file_path=url,
                file_type="url",
                encoding=encoding,
                size=len(content.encode(encoding)),
            )

        except Exception as e:
            logger.error(f"URL文档加载失败: {e}")
            raise ValueError(f"无法从URL加载文档: {e}")

    def _extract_title_from_url(self, url: str, content: str) -> str:
        """从URL和内容中提取标题"""
        # 首先尝试从内容中提取第一个标题
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # 移除Markdown标题标记
                title = re.sub(r'^#+\s*', '', line).strip()
                if title:
                    return title

        # 如果没找到标题，使用URL的一部分
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.netloc:
                return f"来自 {parsed.netloc} 的文档"
            else:
                return "网络文档"
        except Exception:
            return "网络文档"
    
    def _extract_text(self, file_path: str, file_type: str, encoding: Optional[str]) -> Tuple[str, str]:
        """提取文本内容"""

        if file_type in ['text', 'markdown', 'json']:
            return self._extract_text_file(file_path, encoding)
        elif file_type == 'csv':
            return self._extract_csv(file_path, encoding)
        elif file_type == 'markitdown':
            return self._extract_with_markitdown(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
    
    def _extract_text_file(self, file_path: str, encoding: Optional[str]) -> Tuple[str, str]:
        """提取纯文本文件内容"""
        if encoding:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read(), encoding
            except UnicodeDecodeError:
                logger.warning(f"指定编码 {encoding} 失败，尝试自动检测")
        
        # 自动检测编码
        for enc in self.encoding_detectors:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                    return content, enc
            except UnicodeDecodeError:
                continue
        
        # 使用chardet作为最后手段
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                detected_encoding = result['encoding']
                if detected_encoding:
                    content = raw_data.decode(detected_encoding)
                    return content, detected_encoding
        except ImportError:
            logger.warning("chardet未安装，无法进行高级编码检测")
        except Exception as e:
            logger.warning(f"chardet检测失败: {e}")
        
        raise ValueError(f"无法检测文件编码: {file_path}")
    

    def _extract_csv(self, file_path: str, encoding: Optional[str]) -> Tuple[str, str]:
        """提取CSV文件内容"""
        try:
            import pandas as pd
            
            # 尝试不同编码
            encodings_to_try = [encoding] if encoding else self.encoding_detectors
            
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    # 将DataFrame转换为文本描述
                    text = f"数据表包含 {len(df)} 行 {len(df.columns)} 列\n\n"
                    text += f"列名: {', '.join(df.columns)}\n\n"
                    text += "数据预览:\n"
                    text += df.head(10).to_string()
                    
                    return text, enc
                except UnicodeDecodeError:
                    continue
            
            raise ValueError("无法读取CSV文件")
        except ImportError:
            raise ImportError("请安装pandas: pip install pandas")
    


    def _extract_with_markitdown(self, file_path: str) -> Tuple[str, str]:
        """使用MarkItDown提取文件内容，带回退机制"""
        try:
            if self._markitdown_converter is None:
                self._markitdown_converter = MarkItDownConverter(
                    enable_plugins=False,
                    use_magic_pdf=self.use_magic_pdf
                )

            content, encoding = self._markitdown_converter.convert_file(file_path)

            # 清理和优化Markdown内容
            content = self._markitdown_converter.clean_markdown_content(content)

            # 保存Markdown文件到temp目录
            if self.save_markdown:
                self._save_markdown_file(file_path, content)

            # 转换器已经记录了详细的转换日志，这里不再重复记录
            return content, encoding

        except Exception as e:
            logger.warning(f"MarkItDown提取失败，尝试回退方法: {e}")

            # 尝试回退到传统方法
            file_extension = Path(file_path).suffix.lower()

            if file_extension == '.pdf':
                logger.info("回退到pypdf处理PDF文件")
                return self._extract_pdf_fallback(file_path)
            elif file_extension in ['.docx', '.doc']:
                logger.info("回退到python-docx处理Word文件")
                return self._extract_docx_fallback(file_path)
            elif file_extension in ['.html', '.htm']:
                logger.info("回退到BeautifulSoup处理HTML文件")
                return self._extract_html_fallback(file_path)
            else:
                # 对于其他格式，没有回退方法
                logger.error(f"无回退方法可用于文件类型: {file_extension}")
                raise ValueError(f"MarkItDown文件提取失败且无回退方法: {e}")

    def _get_markitdown_converter(self) -> MarkItDownConverter:
        """获取MarkItDown转换器实例"""
        if self._markitdown_converter is None:
            self._markitdown_converter = MarkItDownConverter(
                enable_plugins=False,
                use_magic_pdf=self.use_magic_pdf
            )
        return self._markitdown_converter

    def _extract_pdf_fallback(self, file_path: str) -> Tuple[str, str]:
        """PDF文件回退提取方法"""
        try:
            import pypdf

            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"

                return text.strip(), "utf-8"
        except ImportError:
            raise ImportError("请安装pypdf: pip install pypdf")
        except Exception as e:
            raise ValueError(f"PDF文件读取失败: {e}")

    def _extract_docx_fallback(self, file_path: str) -> Tuple[str, str]:
        """DOCX文件回退提取方法"""
        try:
            from docx import Document

            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            return text.strip(), "utf-8"
        except ImportError:
            raise ImportError("请安装python-docx: pip install python-docx")
        except Exception as e:
            raise ValueError(f"DOCX文件读取失败: {e}")

    def _extract_html_fallback(self, file_path: str, encoding: Optional[str] = None) -> Tuple[str, str]:
        """HTML文件回退提取方法"""
        try:
            from bs4 import BeautifulSoup

            content, detected_encoding = self._extract_text_file(file_path, encoding)
            soup = BeautifulSoup(content, 'html.parser')

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()
            # 清理多余的空白
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text, detected_encoding
        except ImportError:
            raise ImportError("请安装beautifulsoup4: pip install beautifulsoup4")

    def _save_markdown_file(self, original_file_path: str, markdown_content: str) -> str:
        """保存Markdown文件到temp目录"""
        try:
            # 获取原文件名（不含扩展名）
            original_path = Path(original_file_path)
            base_name = original_path.stem

            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 生成Markdown文件名
            markdown_filename = f"{base_name}_{timestamp}.md"
            markdown_path = os.path.join(self.temp_dir, markdown_filename)

            # 保存Markdown文件
            with open(markdown_path, 'w', encoding='utf-8', newline='\n') as f:
                # 添加文件头信息
                f.write(f"# {base_name}\n\n")
                f.write(f"**原文件**: {original_file_path}\n")
                f.write(f"**转换时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**转换工具**: MarkItDown\n\n")
                f.write("---\n\n")
                f.write(markdown_content)

            logger.info(f"Markdown文件已保存: {markdown_path}")
            return markdown_path

        except Exception as e:
            logger.warning(f"保存Markdown文件失败: {e}")
            return ""

    def is_supported_format(self, file_path: str) -> bool:
        """
        检查文件格式是否被支持

        Args:
            file_path: 文件路径

        Returns:
            是否支持该格式
        """
        extension = Path(file_path).suffix.lower()
        return extension in self.SUPPORTED_EXTENSIONS

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        获取所有支持的文件格式

        Returns:
            按类型分组的支持格式字典
        """
        formats = {
            "文档": [".pdf", ".docx", ".doc", ".txt", ".md"],
            "演示文稿": [".pptx", ".ppt"],
            "电子表格": [".xlsx", ".xls", ".csv"],
            "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
            "音频": [".mp3", ".wav", ".m4a", ".flac"],
            "网页": [".html", ".htm"],
            "数据": [".json", ".xml"],
            "压缩包": [".zip"],
            "电子书": [".epub"]
        }
        return formats
    
    def _extract_title(self, content: str, filename: str) -> str:
        """从内容中提取标题"""
        lines = content.split('\n')
        
        # 尝试从Markdown标题提取
        for line in lines[:10]:  # 只检查前10行
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('## '):
                return line[3:].strip()
        
        # 尝试从第一行提取（如果不太长）
        first_line = lines[0].strip() if lines else ""
        if first_line and len(first_line) < 100:
            return first_line
        
        # 使用文件名
        return filename

    def _get_chunker(self, strategy: ChunkStrategy, chunk_size: int, chunk_overlap: int, max_tokens: Optional[int] = None):
        """
        获取分块器实例（延迟初始化）

        Args:
            strategy: 分块策略
            chunk_size: 块大小
            chunk_overlap: 块重叠
            max_tokens: 最大token数（仅用于快速分块器），如果为None则使用环境变量默认值

        Returns:
            对应的分块器实例
        """
        key = (strategy, chunk_size, chunk_overlap, max_tokens)

        if key not in self._chunkers:
            if strategy == ChunkStrategy.SEMANTIC:
                self._chunkers[key] = SemanticChunker(chunk_size, chunk_overlap)
            elif strategy == ChunkStrategy.RECURSIVE:
                self._chunkers[key] = RecursiveChunker(chunk_size, chunk_overlap)
            elif strategy == ChunkStrategy.PARAGRAPH:
                self._chunkers[key] = ParagraphChunker(chunk_size, chunk_overlap)
            elif strategy == ChunkStrategy.HYBRID:
                self._chunkers[key] = HybridChunker(chunk_size, chunk_overlap)
            elif strategy == ChunkStrategy.FAST:
                logger.info(f"🚀 创建快速分块器 (FastChunker): max_tokens={max_tokens}")
                self._chunkers[key] = FastChunker(max_tokens=max_tokens)
            else:
                raise ValueError(f"不支持的分块策略: {strategy}")

        return self._chunkers[key]
    
    def chunk_document(
        self,
        text: str,
        chunk_size: int = 3000,
        chunk_overlap: int = 200,
        strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH,
        max_tokens: Optional[int] = None
    ) -> List[str]:
        """
        智能文档分块

        Args:
            text: 要分块的文本
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            strategy: 分块策略
            max_tokens: 最大token数（仅用于快速分块器），如果为None则使用环境变量默认值

        Returns:
            文本块列表
        """
        if not text.strip():
            return []

        # 使用新的分块器
        logger.info(f"📄 使用分块策略: {strategy}, chunk_size={chunk_size}, max_tokens={max_tokens}")
        chunker = self._get_chunker(strategy, chunk_size, chunk_overlap, max_tokens)
        document_chunks = chunker.chunk_text(text)

        logger.info(f"📊 分块完成: 生成 {len(document_chunks)} 个文档块")
        # 转换为字符串列表以保持向后兼容
        return [chunk.content for chunk in document_chunks]

    def chunk_document_advanced(
        self,
        text: str,
        chunk_size: int = 3000,
        chunk_overlap: int = 200,
        strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH,
        metadata: Optional[dict] = None,
        max_tokens: Optional[int] = None
    ) -> List[DocumentChunk]:
        """
        高级文档分块，返回DocumentChunk对象

        Args:
            text: 要分块的文本
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            strategy: 分块策略
            metadata: 可选的元数据
            max_tokens: 最大token数（仅用于快速分块器），如果为None则使用环境变量默认值

        Returns:
            DocumentChunk对象列表
        """
        if not text.strip():
            return []

        chunker = self._get_chunker(strategy, chunk_size, chunk_overlap, max_tokens)
        return chunker.chunk_text(text, metadata)

    def analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """
        分析文档结构

        Args:
            text: 输入文本

        Returns:
            文档结构分析结果
        """
        # 使用语义分块器分析结构
        semantic_chunker = SemanticChunker()
        structure = semantic_chunker.extract_document_structure(text)

        # 使用混合分块器分析文本特征
        hybrid_chunker = HybridChunker()
        text_analysis = hybrid_chunker.analyze_text_structure(text)

        # 合并结果
        structure.update(text_analysis)
        return structure

    def get_chunking_statistics(
        self,
        text: str,
        chunk_size: int = 3000,
        chunk_overlap: int = 200,
        strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取分块统计信息

        Args:
            text: 输入文本
            chunk_size: 块大小
            chunk_overlap: 块重叠
            strategy: 分块策略
            max_tokens: 最大token数（仅用于快速分块器），如果为None则使用环境变量默认值

        Returns:
            统计信息
        """
        chunker = self._get_chunker(strategy, chunk_size, chunk_overlap, max_tokens)
        chunks = chunker.chunk_text(text)

        if hasattr(chunker, 'get_chunking_statistics'):
            return chunker.get_chunking_statistics(chunks)
        else:
            return chunker.get_chunk_statistics(chunks)
    
    def _chunk_by_paragraph(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """基于段落的分块"""
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前段落加上新段落不超过限制，则添加
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果单个段落太长，需要进一步分割
                if len(para) > chunk_size:
                    sub_chunks = self._split_long_paragraph(para, chunk_size, chunk_overlap)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return self._add_overlap(chunks, chunk_overlap)
    
    def _split_long_paragraph(self, paragraph: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """分割过长的段落"""
        sentences = re.split(r'[.!?。！？]\s*', paragraph)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_by_semantic(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """语义分块（使用新的语义分块器）"""
        chunker = self._get_chunker(ChunkStrategy.SEMANTIC, chunk_size, chunk_overlap, None)
        document_chunks = chunker.chunk_text(text)
        return [chunk.content for chunk in document_chunks]
    
    def _chunk_recursive(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """递归分块"""
        if len(text) <= chunk_size:
            return [text]
        
        # 尝试不同的分割点
        separators = ['\n\n', '\n', '. ', '。', ' ']
        
        for separator in separators:
            if separator in text:
                mid_point = len(text) // 2
                # 寻找最接近中点的分割点
                split_pos = text.find(separator, mid_point)
                if split_pos == -1:
                    split_pos = text.rfind(separator, 0, mid_point)
                
                if split_pos != -1:
                    left_part = text[:split_pos].strip()
                    right_part = text[split_pos + len(separator):].strip()
                    
                    left_chunks = self._chunk_recursive(left_part, chunk_size, chunk_overlap)
                    right_chunks = self._chunk_recursive(right_part, chunk_size, chunk_overlap)
                    
                    return left_chunks + right_chunks
        
        # 如果找不到合适的分割点，强制分割
        mid_point = chunk_size
        return [text[:mid_point], text[mid_point:]]
    
    def _chunk_hybrid(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """混合策略分块"""
        # 首先尝试段落分块
        chunks = self._chunk_by_paragraph(text, chunk_size, chunk_overlap)
        
        # 对过长的块使用递归分块
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > chunk_size * 1.2:  # 允许20%的超出
                sub_chunks = self._chunk_recursive(chunk, chunk_size, chunk_overlap)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _add_overlap(self, chunks: List[str], overlap_size: int) -> List[str]:
        """为块添加重叠"""
        if overlap_size <= 0 or len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]
            
            # 从前一个块的末尾提取重叠内容
            overlap_text = prev_chunk[-overlap_size:] if len(prev_chunk) > overlap_size else prev_chunk
            
            # 添加到当前块的开头
            overlapped_chunk = overlap_text + "\n\n" + current_chunk
            overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks
