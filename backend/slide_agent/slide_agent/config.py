#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/19 11:16
# @File  : config.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :  项目的基本配置

# 对所有的上面的研究员Agent的研究结果写PPT
PPT_WRITER_AGENT_CONFIG = {
    # "provider": "openai",
    # "provider": "local_openai",
    # "model": "gpt-4.1",
    # "provider": "google",
    # "model": "gemini-2.0-flash",
    # "provider": "claude",
    # "model": "claude-sonnet-4-20250514",
    # "provider": "deepseek",
    # "model": "deepseek-chat",
    # "model": "gpt-4o-2024-08-06",
    "provider": "ali",
    "model": "qwen-turbo-latest",
}
# 检查每一页的PPT是否符合要求，不符合要求的会被重写
PPT_CHECKER_AGENT_CONFIG = {
    # "provider": "openai",
    # "provider": "local_openai",
    # "model": "gpt-4.1",
    # "provider": "google",
    # "model": "gemini-2.0-flash",
    # "provider": "claude",
    # "model": "claude-sonnet-4-20250514",
    # "provider": "local_deepseek",
    # "model": "deepseek-chat",
    # "model": "gpt-4o-2024-08-06",
    "provider": "ali",
    "model": "qwen-turbo-latest",
    # "provider": "deepseek",
    # "model": "deepseek-chat",
}