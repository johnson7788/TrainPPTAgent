import asyncio
import json
import re
import os
import docx
import dotenv
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

# 加载统一环境配置
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)
else:
    dotenv.load_dotenv()

OUTLINE_API = os.environ.get("OUTLINE_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('OUTLINE_API_PORT', '10001')}")
CONTENT_API = os.environ.get("CONTENT_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('CONTENT_API_PORT', '10011')}")
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

@app.post("/tools/aippt_outline_from_word")
async def aippt_outline_from_word(file: UploadFile = File(...)):
    document = docx.Document(file.file)
    content = "".join([para.text for para in document.paragraphs])
    return StreamingResponse(stream_agent_response(content), media_type="text/plain")

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
        print(f"生成正文输出的chunk_data: {chunk_data}")
        if chunk_data["type"] == "text":
            yield chunk_data["text"]
@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    markdown_content = request.content
    return StreamingResponse(stream_content_response(markdown_content), media_type="text/plain")

@app.get("/data/{filename}")
async def get_data(filename: str):
    file_path = os.path.join("./template", filename)
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("MAIN_API_PORT", "6800"))
    uvicorn.run(app, host=host, port=port)