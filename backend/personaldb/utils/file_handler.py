"""
文件处理工具 - 处理文件下载、URL解析等
"""

import os
import requests
from typing import Optional, Tuple
from pathlib import Path
import tempfile
import logging
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FileHandler:
    """文件处理器，支持本地文件和网络URL"""
    
    def __init__(self, timeout: int = 30, max_size: int = 100 * 1024 * 1024):  # 100MB
        self.timeout = timeout
        self.max_size = max_size
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SummeryAnyFile/1.0 (Document Processing Tool)'
        })
    
    def handle_input(self, input_path: str, temp_dir: Optional[str] = None) -> Tuple[str, bool]:
        """
        处理输入路径，支持本地文件和URL
        
        Args:
            input_path: 输入路径（文件路径或URL）
            temp_dir: 临时目录
            
        Returns:
            (本地文件路径, 是否为临时文件)
            
        Raises:
            ValueError: 输入无效
            FileNotFoundError: 文件不存在
            requests.RequestException: 网络请求失败
        """
        if self._is_url(input_path):
            return self._download_from_url(input_path, temp_dir), True
        else:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"文件不存在: {input_path}")
            return input_path, False
    
    def _is_url(self, path: str) -> bool:
        """判断是否为URL"""
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _download_from_url(self, url: str, temp_dir: Optional[str] = None) -> str:
        """
        从URL下载文件
        
        Args:
            url: 文件URL
            temp_dir: 临时目录
            
        Returns:
            下载的本地文件路径
        """
        logger.info(f"正在下载: {url}")
        
        try:
            # 发送HEAD请求检查文件信息
            head_response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            head_response.raise_for_status()
            
            # 检查文件大小
            content_length = head_response.headers.get('content-length')
            if content_length and int(content_length) > self.max_size:
                raise ValueError(f"文件太大: {content_length} bytes (最大: {self.max_size} bytes)")
            
            # 获取文件名
            filename = self._extract_filename_from_url(url, head_response.headers)
            
            # 创建临时文件
            if temp_dir:
                temp_path = Path(temp_dir)
                temp_path.mkdir(parents=True, exist_ok=True)
                file_path = temp_path / filename
            else:
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=Path(filename).suffix,
                    prefix="summeryanyfile_"
                )
                file_path = Path(temp_file.name)
                temp_file.close()
            
            # 下载文件
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 检查下载大小
                        if downloaded_size > self.max_size:
                            f.close()
                            file_path.unlink()  # 删除部分下载的文件
                            raise ValueError(f"下载文件太大: {downloaded_size} bytes")
            
            logger.info(f"下载完成: {file_path} ({downloaded_size} bytes)")
            return str(file_path)
            
        except requests.RequestException as e:
            logger.error(f"下载失败: {e}")
            raise
        except Exception as e:
            logger.error(f"处理URL时出错: {e}")
            raise
    
    def _extract_filename_from_url(self, url: str, headers: dict) -> str:
        """从URL和响应头中提取文件名"""
        # 尝试从Content-Disposition头获取
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                if filename:
                    return filename
            except Exception:
                pass
        
        # 从URL路径获取
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path:
            filename = os.path.basename(path)
            if filename and '.' in filename:
                return filename
        
        # 默认文件名
        return "downloaded_file.txt"
    
    def extract_text_from_webpage(self, url: str) -> str:
        """
        从网页提取文本内容
        
        Args:
            url: 网页URL
            
        Returns:
            提取的文本内容
        """
        logger.info(f"正在提取网页内容: {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 检测编码
            response.encoding = response.apparent_encoding or 'utf-8'
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # 提取主要内容
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            if main_content:
                text = main_content.get_text()
            else:
                text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            logger.info(f"网页内容提取完成，长度: {len(text)} 字符")
            return text
            
        except Exception as e:
            logger.error(f"网页内容提取失败: {e}")
            raise
    
    def cleanup_temp_file(self, file_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"临时文件已删除: {file_path}")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {e}")
    
    def get_file_info(self, file_path: str) -> dict:
        """获取文件信息"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        stat = path.stat()
        return {
            "path": str(path.absolute()),
            "name": path.name,
            "size": stat.st_size,
            "extension": path.suffix.lower(),
            "modified_time": stat.st_mtime,
        }
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'session'):
            self.session.close()
