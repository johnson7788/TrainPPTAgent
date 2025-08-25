#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/19 08:49
# @File  : t1.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
import dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from slide_agent.agent import root_agent
dotenv.load_dotenv()


# 5. 初始化 Runner 并执行
runner = Runner(
    app_name="example",
    agent=root_agent,
    session_service=InMemorySessionService()
)

def parse_event(event):
    parsed_output = {}

    if event.content and event.content.parts:
        part = event.content.parts[0]

        # Parse text content
        if part.text:
            parsed_output = {"type": "text", "content": part.text}

        # Parse function call information
        if part.function_call:
            function_call_name = part.function_call.name
            function_call_args = part.function_call.args
            parsed_output = {
                "type": "function call",
                "content": f"function_name: {function_call_name}, function_args: {function_call_args}"
            }

        # Parse function result information
        if part.function_response:
            function_response_name = part.function_response.name # Assuming name is always present for function_response
            function_response_result = None

            if part.function_response.response and 'result' in part.function_response.response:
                result_obj = part.function_response.response['result']
                if hasattr(result_obj, 'content') and result_obj.content:
                    extracted_texts = []
                    for content_part in result_obj.content:
                        if hasattr(content_part, 'text') and content_part.text:
                            extracted_texts.append(content_part.text)
                    function_response_result = "\n".join(extracted_texts)
                else:
                    function_response_result = result_obj # Fallback if 'content' is not found

            if function_response_result is not None:
                parsed_output = {
                    "type": "function result",
                    "content": f"function_name: {function_response_name}, function_result: {function_response_result}"
                }
            else:
                 # Handle cases where function_response has no result or an empty result
                parsed_output = {
                    "type": "function result",
                    "content": f"function_name: {function_response_name}, function_result: No result or empty result found."
                }

    return parsed_output

async def run_workflow(outline: str):
    # 1. 先准备好所有初始状态
    initial_state = {
        'outline': outline,
    }
    print(f"准备初始状态: {initial_state}")
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="user1",
        session_id="session1",
        state=initial_state
    )
    print(f"创建新会话: {session.id}")
    # 验证一下返回的session是否已经包含了state
    print(f"创建后，session.state['outline'] 长度: {len(session.state.get('outline', ''))}")
    message_content = types.Content(parts=[types.Part(text=outline)])
    async for event in runner.run_async(
        user_id="user1",
        session_id="session1",
        new_message=message_content
    ):
        event_out = parse_event(event)
        #打印event的信息
        print(event.author)
        print(event_out.get("type"))
        print(event_out.get("content"))

if __name__ == '__main__':
    # 示例调用
    import asyncio
    outline = """一个大纲"""
    asyncio.run(run_workflow(outline))