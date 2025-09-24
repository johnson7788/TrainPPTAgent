#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/12
# @Desc  : 使用FastAPI实现API，接收JSON或RabbitMQ消息，下载七牛云文件，读取内容并生成embedding向量

import os
import json
import requests
import uvicorn
import logging
import pika
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
class RabbitMessage(BaseModel):
    id: Optional[int] = None  # 允许 id 为 None，用于 removeById
    userId: int
    fileType: Optional[str] = None  # 允许 fileType 为 None
    url: Optional[str] = None  # 允许 url 为 None
    folderId: Optional[int] = None  # 允许 folderId 为 None
    ids: Optional[List[int]] = None  # ids 字段，用于 removeById


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
        logger.info("搜索成功")
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

def rabbitmq_callback(ch, method, properties, body):
    """
    RabbitMQ消息回调函数 - 使用同步处理
    """
    try:
        logger.info(f"接收到RabbitMQ消息: {body}")
        print(f"接收到RabbitMQ消息: {body}")
        body_str = body.decode('utf-8')
        if body_str.startswith('"') and body_str.endswith('"'):
            body_str = body_str[1:-1]
            body_str = body_str.replace('\\"', '"')
        message = json.loads(body_str)
        logger.info(f"解析后的消息: {message}")

        msg_content = message.get("message", {})
        msg_type = message.get("type")
        file_type = msg_content.get('fileType')
        file_name = msg_content.get('name', 'unknown')

        if msg_type == "updateOrSave" and file_type != "image":
            print(f"收到了updateOrSave的消息，开始进行处理")
            try:
                rabbit_msg = RabbitMessage(
                    id=msg_content.get("id"),
                    userId=msg_content.get("userId"),
                    fileType=msg_content.get("fileType"),
                    url=msg_content.get("url"),
                    folderId=msg_content.get("folderId")
                )
                process_file_sync(
                    file_name = file_name,
                    id=rabbit_msg.id,
                    user_id=rabbit_msg.userId,
                    file_type=rabbit_msg.fileType,
                    url=rabbit_msg.url,
                    folder_id=rabbit_msg.folderId
                )
                print(f"文件进行embedding处理完成")
            except ValidationError as e:
                logger.error(f"消息格式不符合RabbitMessage模型: {str(e)}", exc_info=True)
        elif msg_type == "removeById" and file_type != "image":
            print(f"收到了removeById的消息，开始进行处理")
            try:
                rabbit_msg = RabbitMessage(
                    userId=msg_content.get("userId"),
                    fileType=msg_content.get("fileType"),
                    url=msg_content.get("url"),
                    folderId=msg_content.get("folderId"),
                    ids=msg_content.get("ids")
                )
                if not rabbit_msg.ids:
                    logger.error("removeById 消息中 ids 字段为空或缺失")
                    raise ValueError("ids 字段不能为空")
                embedder = embedding_utils.EmbeddingModel()
                chroma = embedding_utils.ChromaDB(embedder)
                for file_id in rabbit_msg.ids:
                    result = chroma.delete_file_vectors(
                        user_id=rabbit_msg.userId,
                        file_id=file_id
                    )
                    if result == "success":
                        print(f"成功删除文件 ID {file_id} 的向量")
                        logger.info(f"成功删除文件 ID {file_id} 的向量")
                    else:
                        print(f"删除文件 ID {file_id} 的向量失败")
                        logger.error(f"删除文件 ID {file_id} 的向量失败")
            except ValidationError as e:
                logger.error(f"消息格式不符合RabbitMessage模型: {str(e)}", exc_info=True)
            except ValueError as e:
                logger.error(f"处理失败: {str(e)}", exc_info=True)
        else:
            logger.info(f"忽略非updateOrSave或removeById类型的消息: {msg_type}  文件类型是{file_type}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"RabbitMQ消息处理失败: {str(e)}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_rabbitmq_consumer():
    """
    启动RabbitMQ消费者
    """
    print(f"RABBITMQ_URL={os.getenv('RABBITMQ_URL')}")
    print(f"QUEUE_NAME_QUESTION={os.getenv('QUEUE_NAME_QUESTION')}")
    connection_params = pika.URLParameters(os.getenv("RABBITMQ_URL"))
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    channel.queue_declare(queue=os.getenv("QUEUE_NAME_QUESTION"), durable=True)
    channel.basic_consume(queue=os.getenv("QUEUE_NAME_QUESTION"), on_message_callback=rabbitmq_callback)
    print("开始监听RabbitMQ消息...")
    channel.start_consuming()

if __name__ == "__main__":
    """
    主函数入口：启动FastAPI服务和RabbitMQ消费者
    """
    print("启动FastAPI服务...")
    import threading
    rabbit_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    rabbit_thread.start()
    uvicorn.run(app, host="0.0.0.0", port=9900)