#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/12
# @Desc  : 使用FastAPI实现API，接收JSON或RabbitMQ消息，下载七牛云文件，读取内容并生成embedding向量

import os
import json
import requests
import uvicorn
import logging
import asyncio
import uuid
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import embedding_utils
import read_all_files
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 请求体
class RequestBody(BaseModel):
    userId: int
    qiniuUrl: str

# RabbitMQ消息处理类
class RabbitMessage(BaseModel):
    id: int
    userId: int
    fileType: str
    url: str
    folderId: int

# 创建临时下载目录
TEMP_DIR = "temp_download"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# RabbitMQ消息处理类

class SearchQuery(BaseModel):
    userId: int | str
    query: str
    keyword: Optional[str] = ""
    topk: Optional[int] = 3

@app.post("/search")
def search_personal_knowledge_base(query: SearchQuery):
    """
    搜索个人知识库
    """
    try:
        logger.info(f"收到搜索请求: {query}")
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)
        collection_name = f"user_{query.userId}"

        result = chroma.query2collection(
            collection=collection_name,
            query_documents=[query.query],
            keyword=query.keyword,
            topk=query.topk
        )
        logger.info(f"搜索成功: {result}")
        return result
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

def process_and_vectorize_local_file(file_name: str, temp_file_path: str, id: int, user_id: int, file_type: str, url: str, folder_id: int):
    """
    从本地文件路径处理文件、进行向量化并存储
    """
    # 步骤2: 使用read_all_files读取文件内容
    logger.info(f"开始读取文件内容: {temp_file_path}")
    content: List[str] = read_all_files.read_file_content(temp_file_path)
    if not content or all(not line.strip() for line in content):
        logger.error(f"文件内容为空或无效: {temp_file_path}")
        raise ValueError("文件内容为空或无效")
    logger.info(f"文件内容读取成功，长度: {len(content)}")

    # 步骤3: 检查环境变量
    if not os.getenv("ALI_API_KEY"):
        logger.error("ALI_API_KEY环境变量未设置")
        raise ValueError("ALI_API_KEY环境变量未设置")

    # 步骤4: 使用embedding_utils插入向量
    logger.info("初始化embedding模型")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)
    logger.info(f"开始插入文件 {id} 的向量")
    embedding_result = chroma.insert_file_vectors(
        file_name=file_name,
        user_id=user_id,
        file_id=id,
        file_type=file_type or "unknown",
        url=url or "",
        folder_id=folder_id or 0,
        documents=content
    )
    logger.info("向量插入成功")

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id,
        "fileType": file_type,
        "url": url,
        "folderId": folder_id,
        "embedding_result": embedding_result
    }
    logger.info(f"处理OK。。。")
    return result


def process_file_sync(file_name:str, id: int, user_id: int, file_type: str, url: str, folder_id: int):
    """
    处理文件下载、读取和生成embedding的同步版本
    """
    if not url:
        logger.error("url为空")
        raise ValueError("url不能为空")

    # 验证URL格式
    if not url.startswith(("http://", "https://")):
        logger.error(f"无效的URL格式: {url}")
        raise ValueError("url必须以http://或https://开头")

    parsed_url = urlparse(url)
    logger.info(f"解析后的URL: {parsed_url.geturl()}")
    temp_file_path = None
    try:
        # 步骤1: 下载文件
        local_file_name = os.path.basename(parsed_url.path) or f"downloaded_file_{user_id}"
        temp_file_path = os.path.join(TEMP_DIR, local_file_name)
        logger.info(f"开始下载文件: {url}")
        response = requests.get(url, timeout=60, proxies=None)
        response.raise_for_status()
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"文件下载成功: {temp_file_path}")

        return process_and_vectorize_local_file(file_name, temp_file_path, id, user_id, file_type, url, folder_id)

    except requests.exceptions.Timeout as e:
        logger.error(f"下载文件超时: {str(e)}", exc_info=True)
        raise ValueError(f"下载文件超时: {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"下载文件失败: {str(e)}", exc_info=True)
        raise ValueError(f"下载文件失败: {str(e)}")
    except ValueError as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"未知错误: {str(e)}", exc_info=True)
        raise ValueError(f"未知错误: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"临时文件已删除: {temp_file_path}")


@app.post("/upload/")
async def upload_and_vectorize_endpoint(
    userId: int = Form(...),
    fileId: int = Form(...),
    folderId: int = Form(0),
    fileType: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    上传文件或通过URL进行向量化
    """
    if not url and not file:
        raise HTTPException(status_code=400, detail="必须提供 'url' 或 'file'")
    if url and file:
        raise HTTPException(status_code=400, detail="只能提供 'url' 或 'file' 中的一个")

    temp_file_path = None
    try:
        if file:
            if not fileType:
                fileType = file.filename.split('.')[-1] if '.' in file.filename else 'unknown'
            
            temp_file_name = f"{uuid.uuid4()}_{file.filename}"
            temp_file_path = os.path.join(TEMP_DIR, temp_file_name)
            
            with open(temp_file_path, "wb") as buffer:
                buffer.write(await file.read())
            logger.info(f"文件上传成功: {temp_file_path}")
            
            return process_and_vectorize_local_file(
                file_name=file.filename,
                temp_file_path=temp_file_path,
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url="",  # 直接上传的文件没有URL
                folder_id=folderId
            )
        elif url:
            return process_file_sync(
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url=url,
                folder_id=folderId
            )
    except Exception as e:
        logger.error(f"上传和向量化失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"临时文件已删除: {temp_file_path}")


class TextVectorizeBody(BaseModel):
    """
    纯文本向量化请求体。
    仅必需字段：content, fileId, fileName
    其余参数均为可选，默认空/0。
    """
    content: str
    fileId: int
    fileName: str
    userId: Optional[int] = 0
    fileType: Optional[str] = None
    url: Optional[str] = ""
    folderId: Optional[int] = 0


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    """
    简单切分：先按段落，再对超长段落做定长切分。
    这样可避免单块文本过长导致的向量化超限。
    """
    text = (text or "").strip()
    if not text:
        return []

    # 先按空行分段
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    if not blocks:
        blocks = [text]

    chunks: List[str] = []
    for b in blocks:
        if len(b) <= max_chars:
            chunks.append(b)
        else:
            start = 0
            while start < len(b):
                end = min(start + max_chars, len(b))
                chunks.append(b[start:end])
                if end == len(b):
                    break
                start = max(0, end - overlap)  # 轻微重叠，提升召回
    return chunks


def process_text_content(
    file_name: str,
    text: str,
    id: int,
    user_id: int = 0,
    file_type: Optional[str] = None,
    folder_id: int = 0,
    url: str = ""
):
    """
    直接对纯文本进行向量化并落库（Chroma）。
    其余参数默认空/0，以满足“无需额外参数”的需求。
    """
    logger.info("开始处理纯文本向量化")
    if not text or not text.strip():
        raise ValueError("content 不能为空")

    # 与现有流程保持一致的环境变量校验
    if not os.getenv("ALI_API_KEY"):
        logger.error("ALI_API_KEY环境变量未设置")
        raise ValueError("ALI_API_KEY环境变量未设置")

    documents = _chunk_text(text)
    if not documents:
        raise ValueError("content 无有效文本")

    logger.info("初始化 embedding 模型与 Chroma")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)

    logger.info(f"插入文本向量：fileId={id}, userId={user_id}")
    embedding_result = chroma.insert_file_vectors(
        file_name=file_name,
        user_id=user_id or 0,
        file_id=id,
        file_type=file_type or "unknown",
        url=url or "",
        folder_id=folder_id or 0,
        documents=documents
    )

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id or 0,
        "fileType": file_type or "unknown",
        "url": url or "",
        "folderId": folder_id or 0,
        "embedding_result": embedding_result
    }
    logger.info("纯文本向量化完成")
    return result


# ===== 纯文本向量化接口 =====
@app.post("/vectorize/text")
def vectorize_text_endpoint(body: TextVectorizeBody):
    """
    纯文本向量化：
    - 必填：content, fileId, fileName
    - 可选：userId(默认0), fileType(None), url(""), folderId(0)
    """
    try:
        logger.info(
            f"收到文本向量化请求: fileId={body.fileId}, fileName={body.fileName}, userId={body.userId}"
        )
        return process_text_content(
            file_name=body.fileName,
            text=body.content,
            id=body.fileId,
            user_id=body.userId or 0,
            file_type=body.fileType,
            folder_id=body.folderId or 0,
            url=body.url or ""
        )
    except Exception as e:
        logger.error(f"文本向量化失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文本向量化失败: {str(e)}")


if __name__ == "__main__":
    """
    主函数入口：启动FastAPI服务
    """
    print("启动FastAPI服务...")
    uvicorn.run(app, host="127.0.0.1", port=9900)