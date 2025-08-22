#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/20 10:02
# @File  : tools.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from weixin_search import sogou_weixin_search,get_real_url,get_article_content
import time
from datetime import datetime
import random

async def DocumentSearch(
    keyword: str, number: int,
    tool_context: ToolContext,
):
    """
    根据关键词搜索文档
    :param keyword: str, 搜索的相关文档的关键词
    :return: 返回每篇文档数据
    """
    agent_name = tool_context.agent_name
    print(f"Agent{agent_name}正在调用工具：DocumentSearch: " + keyword)
    metadata = tool_context.state.get("metadata", {})
    if metadata is None:
        metadata = {}
    print(f"调用工具：DocumentSearch时传入的metadata: {metadata}")
    print("文档检索: " + keyword)
    start_time = time.time()
    results = sogou_weixin_search(keyword)
    if not results:
        return f"没有搜索到{keyword}相关的文章"
    articles = []
    results = results[:number]
    for every_result in results:
        sougou_link = every_result["link"]
        real_url = get_real_url(sougou_link)
        # referer：请求来源
        content = get_article_content(real_url, referer=sougou_link)
        article = {
            "title": every_result["title"],
            "publish_time": every_result["publish_time"],
            "real_url": real_url,
            "content": content
        }
        articles.append(article)
    end_time = time.time()
    print(f"关键词{keyword}相关的文章已经获取完毕，获取到{len(articles)}篇, 耗时{end_time - start_time}秒")
    metadata["tool_document_ids"] = articles
    tool_context.state["metadata"] = metadata
    return articles

if __name__ == '__main__':
    result = DocumentSearch(keyword="电动汽车")
    print(result)