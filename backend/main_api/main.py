import asyncio
import json
import re
import os
import dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import httpx
from a2a.client import A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest
)
from outline_client import A2AOutlineClientWrapper
from content_client import A2AContentClientWrapper
dotenv.load_dotenv()

OUTLINE_API = os.environ["OUTLINE_API"]
CONTENT_API = os.environ["CONTENT_API"]
app = FastAPI()

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool

async def stream_agent_response(prompt: str):
    """A generator that yields parts of the agent response."""
    outline_wrapper = A2AOutlineClientWrapper(session_id=uuid.uuid4().hex, agent_url=OUTLINE_API)
    async for chunk_data in outline_wrapper.generate(prompt):
        print(f"生成大纲输出的chunk_data: {chunk_data}")
        if chunk_data["type"] == "text":
            yield chunk_data["text"]


@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    assert request.stream, "只支持流式的返回大纲"
    return StreamingResponse(stream_agent_response(request.content), media_type="text/plain")

class AipptContentRequest(BaseModel):
    content: str

async def stream_content_response(markdown_content: str):
    """  # PPT的正文内容生成"""
    # 用正则找到第一个一级标题及之后的内容
    match = re.search(r"(# .*)", markdown_content, flags=re.DOTALL)

    if match:
        result = markdown_content[match.start():]
    else:
        result = markdown_content
    print(f"用户输入的markdown大纲是：{result}")
    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)
    async for chunk_data in content_wrapper.generate(result):
        if chunk_data["type"] == "text":
            yield chunk_data["text"]
@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    markdown_content = request.content
    return StreamingResponse(stream_content_response(markdown_content), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=6800)