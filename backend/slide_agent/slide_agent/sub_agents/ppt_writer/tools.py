#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/20 10:02
# @File  : tools.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 搜索图片，用于PPT的配图

import re
import os
import time
from datetime import datetime
import random
import hashlib
from pathlib import Path
from google.adk.tools import ToolContext
import requests
from urllib.parse import quote
import json
from typing import List, Dict, Any


async def SearchImage(query: str, count: int = 1, tool_context: ToolContext = None) -> List[Dict[str, Any]]:
    """
    根据关键词搜索对应的图片，使用Pexels API
    :param query: 搜索关键词
    :param count: 返回图片数量，默认1张
    :param tool_context: 工具上下文
    :return: 图片信息列表
    """
    try:
        # 从环境变量获取Pexels API密钥
        pexels_api_key = os.getenv("PEXELS_API_KEY")
        if not pexels_api_key:
            # 如果没有API密钥，使用模拟数据
            return _get_simulate_images(query, count)
        
        # 构建Pexels API请求
        headers = {
            "Authorization": pexels_api_key
        }
        
        # 对查询词进行URL编码
        encoded_query = quote(query)
        url = f"https://api.pexels.com/v1/search?query={encoded_query}&per_page={min(count, 80)}&orientation=landscape"
        
        print(f"正在搜索图片，关键词: {query}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        photos = data.get("photos", [])
        
        if not photos:
            print(f"未找到关键词 '{query}' 相关的图片，使用模拟数据")
            return _get_simulate_images(query, count)
        
        # 转换为前端需要的格式
        image_results = []
        for photo in photos[:count]:
            image_info = {
                "id": photo.get("id", random.randint(100000, 999999)),
                "src": photo.get("src", {}).get("large2x", photo.get("src", {}).get("large", "")),
                "width": photo.get("width", 1920),
                "height": photo.get("height", 1080),
                "alt": photo.get("alt", query),
                "photographer": photo.get("photographer", "Unknown"),
                "url": photo.get("url", "")
            }
            image_results.append(image_info)
        
        print(f"成功搜索到 {len(image_results)} 张图片")
        return image_results
        
    except requests.exceptions.RequestException as e:
        print(f"Pexels API请求失败: {e}")
        return _get_simulate_images(query, count)
    except Exception as e:
        print(f"图片搜索出错: {e}")
        return _get_simulate_images(query, count)


def _get_simulate_images(query: str, count: int) -> List[Dict[str, Any]]:
    """
    获取模拟图片数据（当API不可用时使用）
    """
    # 根据查询词选择不同的模拟图片
    query_lower = query.lower()
    
    # 预设的图片池，按主题分类
    image_pools = {
        "technology": [
            "https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg",
            "https://images.pexels.com/photos/3861967/pexels-photo-3861967.jpeg",
            "https://images.pexels.com/photos/3861966/pexels-photo-3861966.jpeg",
            "https://images.pexels.com/photos/3861965/pexels-photo-3861965.jpeg",
            "https://images.pexels.com/photos/3861964/pexels-photo-3861964.jpeg",
        ],
        "business": [
            "https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg",
            "https://images.pexels.com/photos/3183153/pexels-photo-3183153.jpeg",
            "https://images.pexels.com/photos/3183154/pexels-photo-3183154.jpeg",
            "https://images.pexels.com/photos/3183155/pexels-photo-3183155.jpeg",
            "https://images.pexels.com/photos/3183156/pexels-photo-3183156.jpeg",
        ],
        "nature": [
            "https://images.pexels.com/photos/3225517/pexels-photo-3225517.jpeg",
            "https://images.pexels.com/photos/3225518/pexels-photo-3225518.jpeg",
            "https://images.pexels.com/photos/3225519/pexels-photo-3225519.jpeg",
            "https://images.pexels.com/photos/3225520/pexels-photo-3225520.jpeg",
            "https://images.pexels.com/photos/3225521/pexels-photo-3225521.jpeg",
        ],
        "abstract": [
            "https://images.pexels.com/photos/3255761/pexels-photo-3255761.jpeg",
            "https://images.pexels.com/photos/3255762/pexels-photo-3255762.jpeg",
            "https://images.pexels.com/photos/3255763/pexels-photo-3255763.jpeg",
            "https://images.pexels.com/photos/3255764/pexels-photo-3255764.jpeg",
            "https://images.pexels.com/photos/3255765/pexels-photo-3255765.jpeg",
        ]
    }
    
    # 根据查询词选择最匹配的图片池
    selected_pool = "abstract"  # 默认
    for keyword, pool in image_pools.items():
        if keyword in query_lower:
            selected_pool = keyword
            break
    
    # 从选中的池中随机选择图片
    pool_images = image_pools[selected_pool]
    selected_images = random.sample(pool_images, min(count, len(pool_images)))
    
    # 如果需要的数量超过池中的图片，重复选择
    while len(selected_images) < count:
        selected_images.extend(random.sample(pool_images, min(count - len(selected_images), len(pool_images))))
    
    # 转换为标准格式
    image_results = []
    for i, src in enumerate(selected_images[:count]):
        image_info = {
            "id": random.randint(100000, 999999) + i,
            "src": src,
            "width": 1920,
            "height": 1080,
            "alt": f"{query} image {i+1}",
            "photographer": "Pexels",
            "url": src
        }
        image_results.append(image_info)
    
    return image_results


if __name__ == '__main__':
    import asyncio
    
    async def test():
        # 测试搜索功能
        result = await SearchImage("technology", 3)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())
