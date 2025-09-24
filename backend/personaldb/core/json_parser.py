"""
JSON解析工具 - 处理LLM返回的JSON响应
"""

import json
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class JSONParser:
    """JSON解析器，用于处理LLM返回的各种格式的JSON响应"""
    
    @staticmethod
    def extract_json_from_response(response: str) -> Dict[str, Any]:
        """
        从LLM响应中提取JSON
        
        Args:
            response: LLM的原始响应文本
            
        Returns:
            解析后的JSON字典，如果解析失败则返回默认结构
        """
        if not response or not response.strip():
            logger.warning("收到空响应，返回默认JSON结构")
            return JSONParser._get_default_structure()
        
        # 尝试方法1：直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            logger.debug("直接JSON解析失败，尝试其他方法")
        
        # 尝试方法2：提取JSON代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if json_match:
            try:
                json_content = json_match.group(1).strip()
                return json.loads(json_content)
            except json.JSONDecodeError:
                logger.debug("JSON代码块解析失败")
        
        # 尝试方法3：提取普通代码块
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            try:
                code_content = code_match.group(1).strip()
                return json.loads(code_content)
            except json.JSONDecodeError:
                logger.debug("代码块解析失败")
        
        # 尝试方法4：寻找JSON结构
        json_patterns = [
            r'\{.*\}',  # 匹配大括号包围的内容
            r'\[.*\]',  # 匹配方括号包围的内容
        ]
        
        for pattern in json_patterns:
            json_match = re.search(pattern, response, re.DOTALL)
            if json_match:
                try:
                    json_content = json_match.group(0)
                    return json.loads(json_content)
                except json.JSONDecodeError:
                    continue
        
        # 尝试方法5：清理并重试
        cleaned_response = JSONParser._clean_response(response)
        if cleaned_response:
            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                logger.debug("清理后的响应解析失败")
        
        logger.warning(f"所有JSON解析方法都失败，响应内容: {response[:200]}...")
        return JSONParser._get_default_structure()
    
    @staticmethod
    def _clean_response(response: str) -> Optional[str]:
        """
        清理响应文本，尝试提取可能的JSON内容
        
        Args:
            response: 原始响应文本
            
        Returns:
            清理后的文本，如果无法清理则返回None
        """
        # 移除常见的非JSON前缀和后缀
        prefixes_to_remove = [
            "Here's the JSON:",
            "Here is the JSON:",
            "JSON:",
            "Result:",
            "Output:",
            "Response:",
        ]
        
        cleaned = response.strip()
        
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
        
        # 移除可能的Markdown格式
        cleaned = re.sub(r'^```.*?\n', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\n```$', '', cleaned, flags=re.MULTILINE)
        
        # 查找第一个 { 和最后一个 }
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            return cleaned[first_brace:last_brace + 1]
        
        return None
    
    @staticmethod
    def _get_default_structure() -> Dict[str, Any]:
        """
        返回默认的JSON结构
        
        Returns:
            默认的PPT大纲结构
        """
        return {
            "title": "PPT大纲",
            "total_pages": 10,
            "page_count_mode": "estimated",
            "slides": [
                {
                    "page_number": 1,
                    "title": "标题页",
                    "content_points": ["演示标题", "演示者信息", "日期"],
                    "slide_type": "title",
                    "description": "PPT的开场标题页"
                }
            ]
        }
    
    @staticmethod
    def validate_ppt_structure(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并修复PPT结构
        
        Args:
            data: 待验证的PPT数据
            
        Returns:
            验证并修复后的PPT数据
        """
        # 确保必需字段存在
        if "title" not in data:
            data["title"] = "PPT大纲"
        
        if "slides" not in data or not isinstance(data["slides"], list):
            data["slides"] = []
        
        if "total_pages" not in data:
            data["total_pages"] = len(data["slides"])
        
        if "page_count_mode" not in data:
            data["page_count_mode"] = "final"
        
        # 验证和修复每个幻灯片
        valid_slides = []
        for i, slide in enumerate(data["slides"]):
            if not isinstance(slide, dict):
                continue
            
            # 确保幻灯片必需字段
            slide.setdefault("page_number", i + 1)
            slide.setdefault("title", f"幻灯片 {i + 1}")
            slide.setdefault("content_points", [])
            slide.setdefault("slide_type", "content")
            slide.setdefault("description", "")
            
            # 验证slide_type
            if slide["slide_type"] not in ["title", "content", "conclusion"]:
                slide["slide_type"] = "content"
            
            # 确保content_points是列表
            if not isinstance(slide["content_points"], list):
                slide["content_points"] = []
            
            valid_slides.append(slide)
        
        data["slides"] = valid_slides
        data["total_pages"] = len(valid_slides)
        
        return data
