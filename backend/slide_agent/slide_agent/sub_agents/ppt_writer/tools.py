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
from google.adk.tools.agent_tool import AgentTool
import requests
from urllib.parse import quote


async def SearchImage(query: str, tool_context: ToolContext) -> list[dict]:
    """
    根据关键词搜索对应的图片
    :return:
    """
    # 根据关键词搜索对应的图片， 这里模拟AI的文生图模型
    simulate_images = [
        "https://cdn.pixabay.com/photo/2024/12/18/07/57/aura-9274671_640.jpg",
        "https://cdn.pixabay.com/photo/2024/12/18/15/02/old-9275581_640.jpg",
        "https://cdn.pixabay.com/photo/2022/11/08/11/16/alien-7578281_640.jpg",
        "https://cdn.pixabay.com/photo/2023/01/27/02/28/figure-7747589_640.jpg",
        "https://cdn.pixabay.com/photo/2022/10/29/12/34/fantasy-7555144_640.jpg",
    ]
    one_image = random.choice(simulate_images)
    return one_image


if __name__ == '__main__':
    result = SearchImages("flowers")
    print(result)
