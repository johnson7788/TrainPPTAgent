"""
文件缓存管理器 - 基于MD5哈希值缓存文件处理结果
"""

import os
import json
import hashlib
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FileCacheManager:
    """文件缓存管理器，用于缓存文件处理结果"""
    
    def __init__(self, cache_dir: Optional[str] = None, cache_ttl_hours: int = 24 * 7, processing_mode: Optional[str] = None):
        """
        初始化文件缓存管理器

        Args:
            cache_dir: 缓存目录，默认为系统临时目录下的summeryanyfile_cache
            cache_ttl_hours: 缓存过期时间（小时），默认7天
            processing_mode: 处理模式（如markitdown、magic_pdf等），用于分离不同模式的缓存
        """
        self.cache_ttl_hours = cache_ttl_hours
        self.processing_mode = processing_mode or "default"

        # 设置缓存目录
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "summeryanyfile_cache"

        # 如果指定了处理模式，在缓存目录下创建模式子目录
        if self.processing_mode != "default":
            self.cache_dir = self.cache_dir / self.processing_mode

        # 创建缓存目录结构
        self.files_cache_dir = self.cache_dir / "files"
        self.markdown_cache_dir = self.cache_dir / "markdown"
        self.metadata_cache_dir = self.cache_dir / "metadata"

        # 确保目录存在
        for dir_path in [self.files_cache_dir, self.markdown_cache_dir, self.metadata_cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"文件缓存管理器初始化完成，缓存目录: {self.cache_dir}，处理模式: {self.processing_mode}")
    
    def calculate_file_md5(self, file_path: str) -> str:
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            MD5哈希值字符串
        """
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                # 分块读取文件以处理大文件
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            md5_hash = hash_md5.hexdigest()
            logger.debug(f"文件 {file_path} 的MD5: {md5_hash}")
            return md5_hash
            
        except Exception as e:
            logger.error(f"计算文件MD5失败 {file_path}: {e}")
            raise
    
    def is_cached(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        检查文件是否已缓存且未过期
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否已缓存, MD5哈希值)
        """
        try:
            md5_hash = self.calculate_file_md5(file_path)
            
            # 检查元数据文件是否存在
            metadata_file = self.metadata_cache_dir / f"{md5_hash}.json"
            if not metadata_file.exists():
                return False, md5_hash
            
            # 检查缓存是否过期
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                cached_time = datetime.fromisoformat(metadata.get('cached_time', ''))
                expiry_time = cached_time + timedelta(hours=self.cache_ttl_hours)
                
                if datetime.now() > expiry_time:
                    logger.info(f"缓存已过期: {md5_hash}")
                    self._remove_cache_entry(md5_hash)
                    return False, md5_hash
                
                # 检查markdown文件是否存在
                markdown_file = self.markdown_cache_dir / f"{md5_hash}.md"
                if not markdown_file.exists():
                    logger.warning(f"缓存元数据存在但markdown文件缺失: {md5_hash}")
                    self._remove_cache_entry(md5_hash)
                    return False, md5_hash
                
                logger.info(f"找到有效缓存: {md5_hash}")
                return True, md5_hash
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"缓存元数据文件损坏: {metadata_file}, 错误: {e}")
                self._remove_cache_entry(md5_hash)
                return False, md5_hash
                
        except Exception as e:
            logger.error(f"检查缓存状态失败: {e}")
            return False, None
    
    def get_cached_content(self, md5_hash: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        获取缓存的内容和元数据
        
        Args:
            md5_hash: 文件MD5哈希值
            
        Returns:
            (markdown内容, 元数据)
        """
        try:
            # 读取markdown内容
            markdown_file = self.markdown_cache_dir / f"{md5_hash}.md"
            if not markdown_file.exists():
                return None, None
            
            with open(markdown_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # 读取元数据
            metadata_file = self.metadata_cache_dir / f"{md5_hash}.json"
            if not metadata_file.exists():
                return markdown_content, {}
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"成功读取缓存内容: {md5_hash}")
            return markdown_content, metadata
            
        except Exception as e:
            logger.error(f"读取缓存内容失败 {md5_hash}: {e}")
            return None, None
    
    def save_to_cache(self, file_path: str, markdown_content: str, 
                     processing_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        保存文件处理结果到缓存
        
        Args:
            file_path: 原始文件路径
            markdown_content: 处理后的markdown内容
            processing_metadata: 处理过程的元数据
            
        Returns:
            MD5哈希值
        """
        try:
            md5_hash = self.calculate_file_md5(file_path)
            
            # 保存markdown内容
            markdown_file = self.markdown_cache_dir / f"{md5_hash}.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # 准备元数据
            file_info = Path(file_path)
            metadata = {
                'md5_hash': md5_hash,
                'original_file_path': str(file_info.absolute()),
                'original_file_name': file_info.name,
                'original_file_size': file_info.stat().st_size,
                'original_file_extension': file_info.suffix.lower(),
                'cached_time': datetime.now().isoformat(),
                'markdown_length': len(markdown_content),
                'processing_metadata': processing_metadata or {}
            }
            
            # 保存元数据
            metadata_file = self.metadata_cache_dir / f"{md5_hash}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 可选：保存原始文件副本（用于调试或备份）
            if self._should_backup_file(file_path):
                self._backup_original_file(file_path, md5_hash)
            
            logger.info(f"成功缓存文件处理结果: {md5_hash} ({file_info.name})")
            return md5_hash
            
        except Exception as e:
            logger.error(f"保存缓存失败 {file_path}: {e}")
            raise
    
    def _should_backup_file(self, file_path: str) -> bool:
        """
        判断是否应该备份原始文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该备份
        """
        # 对于小文件（<10MB）进行备份
        try:
            file_size = Path(file_path).stat().st_size
            return file_size < 10 * 1024 * 1024  # 10MB
        except:
            return False
    
    def _backup_original_file(self, file_path: str, md5_hash: str):
        """
        备份原始文件
        
        Args:
            file_path: 原始文件路径
            md5_hash: MD5哈希值
        """
        try:
            file_info = Path(file_path)
            backup_file = self.files_cache_dir / f"{md5_hash}{file_info.suffix}"
            
            shutil.copy2(file_path, backup_file)
            logger.debug(f"已备份原始文件: {backup_file}")
            
        except Exception as e:
            logger.warning(f"备份原始文件失败: {e}")
    
    def _remove_cache_entry(self, md5_hash: str):
        """
        删除缓存条目
        
        Args:
            md5_hash: MD5哈希值
        """
        try:
            # 删除markdown文件
            markdown_file = self.markdown_cache_dir / f"{md5_hash}.md"
            if markdown_file.exists():
                markdown_file.unlink()
            
            # 删除元数据文件
            metadata_file = self.metadata_cache_dir / f"{md5_hash}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            # 删除备份文件（如果存在）
            for backup_file in self.files_cache_dir.glob(f"{md5_hash}.*"):
                backup_file.unlink()
            
            logger.debug(f"已删除缓存条目: {md5_hash}")
            
        except Exception as e:
            logger.warning(f"删除缓存条目失败 {md5_hash}: {e}")
    
    def cleanup_expired_cache(self):
        """清理过期的缓存条目"""
        try:
            cleaned_count = 0
            
            for metadata_file in self.metadata_cache_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    cached_time = datetime.fromisoformat(metadata.get('cached_time', ''))
                    expiry_time = cached_time + timedelta(hours=self.cache_ttl_hours)
                    
                    if datetime.now() > expiry_time:
                        md5_hash = metadata_file.stem
                        self._remove_cache_entry(md5_hash)
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"清理缓存条目失败 {metadata_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 个过期缓存条目")
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        try:
            metadata_files = list(self.metadata_cache_dir.glob("*.json"))
            markdown_files = list(self.markdown_cache_dir.glob("*.md"))
            backup_files = list(self.files_cache_dir.glob("*"))
            
            total_size = 0
            for file_path in [*metadata_files, *markdown_files, *backup_files]:
                try:
                    total_size += file_path.stat().st_size
                except:
                    pass
            
            return {
                'cache_dir': str(self.cache_dir),
                'total_entries': len(metadata_files),
                'markdown_files': len(markdown_files),
                'backup_files': len(backup_files),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_ttl_hours': self.cache_ttl_hours
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计信息失败: {e}")
            return {}
