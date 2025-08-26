import asyncio
import json
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
        if chunk_data["type"] == "text":
            yield chunk_data["text"]

async def get_agent_response(prompt: str):
    """Gets a complete response from the agent."""
    timeout = httpx.Timeout(300.0)
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        try:
            client = await A2AClient.get_client_from_agent_card_url(
                httpx_client, 'http://localhost:10001'
            )
        except Exception as e:
            print(f"Error connecting to agent: {e}")
            return f"Error connecting to agent: {e}"

        request_id = uuid.uuid4().hex
        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [{'type': 'text', 'text': prompt}],
                'messageId': request_id,
            }
        }

        request = SendMessageRequest(
            id=request_id,
            params=MessageSendParams(**send_message_payload)
        )

        try:
            response = await client.send_message(request)
            if response.message and response.message.parts:
                text_part = response.message.parts[0]
                if hasattr(text_part, 'text'):
                    return text_part.text
            return ""
        except Exception as e:
            print(f"Error getting response: {e}")
            return f"Error getting response: {e}"


@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    if request.stream:
        return StreamingResponse(stream_agent_response(request.content), media_type="text/plain")
    else:
        response_text = await get_agent_response(request.content)
        return {"text": response_text}

class AipptContentRequest(BaseModel):
    content: str

async def stream_content_response(prompt: str):
    """A generator that yields parts of the agent response."""
    # PPT的正文内容
    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)
    async for chunk_data in content_wrapper.generate(prompt):
        if chunk_data["type"] == "text":
            yield chunk_data["text"]

async def aippt_content_streamer(markdown_content: str):
    """Parses markdown and streams slide data as JSON objects."""
    return StreamingResponse(stream_content_response(markdown_content), media_type="text/plain")

@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    return StreamingResponse(aippt_content_streamer(request.content), media_type="application/json; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=6800)