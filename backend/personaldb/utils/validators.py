"""
验证工具 - 验证输入参数和配置
"""

import os
import re
from typing import Optional, List, Dict, Any
from pathlib import Path
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def validate_file_path(file_path: str, check_exists: bool = True) -> bool:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        check_exists: 是否检查文件存在
        
    Returns:
        是否有效
    """
    if not file_path or not isinstance(file_path, str):
        return False
    
    try:
        path = Path(file_path)
        
        # 检查路径格式
        if not path.is_absolute() and not path.exists():
            # 尝试相对路径
            path = Path.cwd() / path
        
        if check_exists:
            return path.exists() and path.is_file()
        else:
            # 检查父目录是否存在（用于输出文件）
            return path.parent.exists() or path.parent == Path.cwd()
    
    except Exception as e:
        logger.debug(f"文件路径验证失败: {e}")
        return False


def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: URL字符串
        
    Returns:
        是否为有效URL
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url)
        return all([
            result.scheme in ['http', 'https'],
            result.netloc,
            len(url) < 2048  # URL长度限制
        ])
    except Exception:
        return False


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    验证配置参数
    
    Args:
        config: 配置字典
        
    Returns:
        错误信息列表，空列表表示验证通过
    """
    errors = []
    
    # 验证LLM配置
    llm_model = config.get('llm_model')
    if not llm_model or not isinstance(llm_model, str):
        errors.append("llm_model 必须是非空字符串")
    
    llm_provider = config.get('llm_provider')
    valid_providers = ['openai', 'anthropic', 'azure']
    if llm_provider not in valid_providers:
        errors.append(f"llm_provider 必须是以下之一: {valid_providers}")
    
    # 验证数值参数
    numeric_params = {
        'max_slides': (1, 100),
        'chunk_size': (100, 9999999),
        'chunk_overlap': (0, 1000),
        'max_tokens': (100, 9999999),
    }
    
    for param, (min_val, max_val) in numeric_params.items():
        value = config.get(param)
        if value is not None:
            if not isinstance(value, (int, float)):
                errors.append(f"{param} 必须是数字")
            elif not (min_val <= value <= max_val):
                errors.append(f"{param} 必须在 {min_val} 到 {max_val} 之间")
    
    # 验证温度参数
    temperature = config.get('temperature')
    if temperature is not None:
        if not isinstance(temperature, (int, float)):
            errors.append("temperature 必须是数字")
        elif not (0.0 <= temperature <= 2.0):
            errors.append("temperature 必须在 0.0 到 2.0 之间")

    # 验证base_url
    base_url = config.get('openai_base_url')
    if base_url and not validate_url(base_url):
        errors.append("openai_base_url 必须是有效的URL")
    
    # 验证分块策略
    chunk_strategy = config.get('chunk_strategy')
    valid_strategies = ['paragraph', 'semantic', 'recursive', 'hybrid', 'fast']
    if chunk_strategy and chunk_strategy not in valid_strategies:
        errors.append(f"chunk_strategy 必须是以下之一: {valid_strategies}")
    
    # 验证日志级别
    log_level = config.get('log_level')
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level and log_level.upper() not in valid_levels:
        errors.append(f"log_level 必须是以下之一: {valid_levels}")
    
    return errors


def validate_api_key(api_key: str, provider: str) -> bool:
    """
    验证API密钥格式
    
    Args:
        api_key: API密钥
        provider: 提供商名称
        
    Returns:
        是否有效
    """
    if not api_key or not isinstance(api_key, str):
        return False
    
    # 基本长度检查
    if len(api_key) < 10:
        return False
    
    # 提供商特定的验证
    if provider == 'openai':
        # OpenAI API密钥通常以sk-开头
        return api_key.startswith('sk-') and len(api_key) > 40
    elif provider == 'anthropic':
        # Anthropic API密钥通常以sk-ant-开头
        return api_key.startswith('sk-ant-') and len(api_key) > 50
    elif provider == 'azure':
        # Azure密钥格式较为灵活
        return len(api_key) >= 32
    
    return True  # 其他提供商的基本验证


def validate_slide_data(slide_data: Dict[str, Any]) -> List[str]:
    """
    验证幻灯片数据
    
    Args:
        slide_data: 幻灯片数据字典
        
    Returns:
        错误信息列表
    """
    errors = []
    
    # 必需字段
    required_fields = ['page_number', 'title', 'content_points', 'slide_type']
    for field in required_fields:
        if field not in slide_data:
            errors.append(f"缺少必需字段: {field}")
    
    # 验证页码
    page_number = slide_data.get('page_number')
    if page_number is not None:
        if not isinstance(page_number, int) or page_number < 1:
            errors.append("page_number 必须是正整数")
    
    # 验证标题
    title = slide_data.get('title')
    if title is not None:
        if not isinstance(title, str) or not title.strip():
            errors.append("title 必须是非空字符串")
        elif len(title) > 200:
            errors.append("title 长度不能超过200字符")
    
    # 验证内容要点
    content_points = slide_data.get('content_points')
    if content_points is not None:
        if not isinstance(content_points, list):
            errors.append("content_points 必须是列表")
        else:
            for i, point in enumerate(content_points):
                if not isinstance(point, str):
                    errors.append(f"content_points[{i}] 必须是字符串")
                elif len(point) > 500:
                    errors.append(f"content_points[{i}] 长度不能超过500字符")
    
    # 验证幻灯片类型
    slide_type = slide_data.get('slide_type')
    valid_types = ['title', 'content', 'conclusion']
    if slide_type and slide_type not in valid_types:
        errors.append(f"slide_type 必须是以下之一: {valid_types}")
    
    return errors


def validate_ppt_outline(outline_data: Dict[str, Any]) -> List[str]:
    """
    验证PPT大纲数据
    
    Args:
        outline_data: PPT大纲数据
        
    Returns:
        错误信息列表
    """
    errors = []
    
    # 验证基本字段
    if 'title' not in outline_data:
        errors.append("缺少PPT标题")
    elif not isinstance(outline_data['title'], str) or not outline_data['title'].strip():
        errors.append("PPT标题必须是非空字符串")
    
    if 'slides' not in outline_data:
        errors.append("缺少幻灯片列表")
    elif not isinstance(outline_data['slides'], list):
        errors.append("slides 必须是列表")
    else:
        # 验证每个幻灯片
        slides = outline_data['slides']
        if not slides:
            errors.append("幻灯片列表不能为空")
        
        page_numbers = set()
        for i, slide in enumerate(slides):
            slide_errors = validate_slide_data(slide)
            for error in slide_errors:
                errors.append(f"幻灯片 {i+1}: {error}")
            
            # 检查页码重复
            page_num = slide.get('page_number')
            if page_num in page_numbers:
                errors.append(f"页码重复: {page_num}")
            else:
                page_numbers.add(page_num)
    
    # 验证总页数
    total_pages = outline_data.get('total_pages')
    if total_pages is not None:
        if not isinstance(total_pages, int) or total_pages < 1:
            errors.append("total_pages 必须是正整数")
        elif 'slides' in outline_data and len(outline_data['slides']) != total_pages:
            errors.append("total_pages 与实际幻灯片数量不匹配")
    
    return errors


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除或替换非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(illegal_chars, '_', filename)
    
    # 移除多余的空格和点
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    sanitized = sanitized.strip('.')
    
    # 确保不为空
    if not sanitized:
        sanitized = "untitled"
    
    # 限制长度
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized


def validate_encoding(encoding: str) -> bool:
    """
    验证编码名称
    
    Args:
        encoding: 编码名称
        
    Returns:
        是否为有效编码
    """
    try:
        import codecs
        codecs.lookup(encoding)
        return True
    except (LookupError, TypeError):
        return False
