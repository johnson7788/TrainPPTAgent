import asyncio
import logging

from collections.abc import AsyncGenerator,AsyncIterable
from google.adk import Runner

from google.adk.events import Event
from google.genai import types
from typing import Any, Dict, List, Literal, Optional, Union
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    Artifact,
    FilePart,
    FileWithBytes,
    FileWithUri,
    GetTaskRequest,
    GetTaskSuccessResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendMessageSuccessResponse,
    Task,
    TaskQueryParams,
    TaskState,
    TaskStatus,
    TextPart,
    DataPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from a2a.utils.message import new_agent_text_message
from google.adk.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def extract_agent_names(agent: BaseAgent, names=None):
    """
    递归遍历 agent 树，收集所有 agent 的 name 属性。
    """
    if names is None:
        names = set()
    names.add(agent.name)
    for sub in getattr(agent, "sub_agents", []) or []:
        extract_agent_names(sub, names)
    return names

class ADKAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an ADK-based Agent."""

    def __init__(self, runner: Runner, card: AgentCard, run_config, show_agent):
        self.runner = runner
        self._card = card

        self._running_sessions = {}
        self.run_config = run_config
        # show_agent代表和前端联动，显示xml的ppt的结果
        self.show_agent = show_agent

    def _run_agent(
        self, session_id, new_message: types.Content
    ) -> AsyncGenerator[Event, None]:
        return self.runner.run_async(
            session_id=session_id, user_id="self", new_message=new_message,
            run_config=self.run_config
        )

    async def _process_request(
        self,
        new_message: types.Content,
        session_id: str,
        task_updater: TaskUpdater,
        metadata: dict | None = None
    ) -> None:
        # The call to self._upsert_session was returning a coroutine object,
        # leading to an AttributeError when trying to access .id on it directly.
        # We need to await the coroutine to get the actual session object.
        # metadata用户传入的原数据
        if metadata is None:
            # 没有传入元数据，创建一个空字典
            metadata = {}
        session_obj = await self._upsert_session(
            session_id,metadata
        )
        logger.debug(f"收到请求信息: {new_message}")
        # Update session_id with the ID from the resolved session object
        # to be used in self._run_agent.
        session_id = session_obj.id
        # 汇集所有的 agent 名称
        logger.info(f"收到请求信息: {new_message}")
        agent_names = extract_agent_names(self.runner.agent)
        agent_names = list(agent_names)
        async for event in self._run_agent(session_id, new_message):
            agent_author = event.author
            if agent_author in self.show_agent:
                logger.info(f"[adk executor] {agent_author}完成")
                if event.content and event.content.parts:
                    final_session = await self.runner.session_service.get_session(
                        app_name=self.runner.app_name, user_id="self", session_id=session_id
                    )
                    print("最终的session中的结果final_session中的state: ", final_session.state)
                    references = final_session.state.get("references", [])
                    # 最后一个agent的输出了，输出成status
                    await task_updater.update_status(
                        TaskState.working,
                        message=task_updater.new_agent_message(
                            convert_genai_parts_to_a2a(event.content.parts), metadata={"author": agent_author, "show": True, "references": references}
                        ),
                    )
                    print(f"final_session中的parts: {event.content.parts}")
                    # await task_updater.complete()  # 这个会关掉event的Queue
                    # break
                else:
                    print(f"event.content没有结果，跳过, Agent是: {agent_author}, event是: {event}")
                    continue
            elif not event.content or not event.content.parts:
                print(f"event.content没有结果，跳过, Agent是: {agent_author}, event是: {event}")
                continue
            elif event.is_final_response():
                final_session = await self.runner.session_service.get_session(
                    app_name=self.runner.app_name, user_id="self", session_id=session_id
                )
                print("最终的session中的结果final_session中的state: ", final_session.state)
                final_metadata = final_session.state.get("metadata")
                references = final_session.state.get("references",[])
                agent_author = event.author
                if agent_author in agent_names:
                    logger.info(f"[adk executor] {agent_author}完成")
                    agent_names.remove(agent_author)
                parts = convert_genai_parts_to_a2a(event.content.parts)
                logger.info("返回最终的结果: %s", parts)
                await task_updater.add_artifact(parts=parts,metadata={"author": agent_author, "references": references})
                if not agent_names:
                    # 说明任务整体完成了，没有要进行其它任务的Agent了，所有Agent都完成了自己的任务
                    await task_updater.complete()  # 这个会关掉event的Queue
                    break
            elif event.get_function_calls():
                logger.info(f"触发了工具调用。。。返回DataPart数据, {event}")
                await task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts),metadata={"author": agent_author}
                    ),
                )
            elif event.get_function_responses():
                logger.info(f"工具返回了结果。。。返回DataPart数据, {event}")
                await task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts), metadata={"author": agent_author}
                    ),
                )
            else:
                logger.info(f"其它的事件,例如数据的流事件 {event}")
                await task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts),metadata={"author": agent_author}
                    ),
                )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        # Run the agent until either complete or the task is suspended.
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        # Immediately notify that the task is submitted.
        if not context.current_task:
            await updater.submit()
        await updater.start_work()
        await self._process_request(
            types.UserContent(
                parts=convert_a2a_parts_to_genai(context.message.parts),
            ),
            context.context_id,
            updater,
            metadata=context.message.metadata
        )
        logger.info("[adk executor] Agent执行完成退出")

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Ideally: kill any ongoing tasks.
        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str, metadata={}):
        """
        Retrieves a session if it exists, otherwise creates a new one.
        Ensures that async session service methods are properly awaited.
        """
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id="self", session_id=session_id
        )
        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name, user_id="self", session_id=session_id, state={"metadata":metadata}
            )
        # According to ADK InMemorySessionService, create_session should always return a Session object.
        if session is None:
            logger.error(
                f"Critical error: Session is None even after create_session for session_id: {session_id}"
            )
            raise RuntimeError(f"Failed to get or create session: {session_id}")
        return session


def convert_a2a_parts_to_genai(parts: list[Part]) -> list[types.Part]:
    """Convert a list of A2A Part types into a list of Google Gen AI Part types."""
    return [convert_a2a_part_to_genai(part) for part in parts]


def convert_a2a_part_to_genai(part: Part) -> types.Part:
    """Convert a single A2A Part type into a Google Gen AI Part type."""
    part = part.root
    if isinstance(part, TextPart):
        return types.Part(text=part.text)
    if isinstance(part, FilePart):
        if isinstance(part.file, FileWithUri):
            return types.Part(
                file_data=types.FileData(
                    file_uri=part.file.uri, mime_type=part.file.mime_type
                )
            )
        if isinstance(part.file, FileWithBytes):
            return types.Part(
                inline_data=types.Blob(
                    data=part.file.bytes, mime_type=part.file.mime_type
                )
            )
        raise ValueError(f"Unsupported file type: {type(part.file)}")
    raise ValueError(f"Unsupported part type: {type(part)}")


def convert_genai_parts_to_a2a(parts: list[types.Part]) -> list[Part]:
    """提取Event的结果信息，函数的call和response等信息"""
    return [
        convert_genai_part_to_a2a(part)
        for part in parts
        if (part.text or part.file_data or part.inline_data or part.function_call or part.function_response)
    ]


def convert_genai_part_to_a2a(part: types.Part) -> Part:
    """Convert a single Google Gen AI Part type into an A2A Part type."""
    if part.text:
        return TextPart(text=part.text)
    if part.file_data:
        return FilePart(
            file=FileWithUri(
                uri=part.file_data.file_uri,
                mime_type=part.file_data.mime_type,
            )
        )
    if part.inline_data:
        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                )
            )
        )
    if part.function_call:
        # print(f"function_call , {part}")
        function_data = extract_function_info_to_datapart(part)
        return DataPart(data=function_data)
    if part.function_response:
        # print(f"function_response, {part}")
        function_data = extract_function_info_to_datapart(part)
        return DataPart(data=function_data)
    raise ValueError(f"Unsupported part type: {part}")


def extract_function_info_to_datapart(part: Part) -> DataPart:
    """
    从一系列Part对象中提取function_call或function_response信息，
    并将其封装为DataPart对象。

    Args:
        part: 包含Part对象
    Returns:
        DataPart对象。
    """
    extracted_data = {}

    if part.function_call:
        # 提取 function_call 信息
        extracted_data = {
            "type": "function_call",
            "id": part.function_call.id,
            "name": part.function_call.name,
            "args": part.function_call.args
        }
    elif part.function_response:
        # 提取 function_response 信息
        extracted_data = {
            "type": "function_response",
            "id": part.function_response.id,
            "name": part.function_response.name,
            "response": part.function_response.response
        }
    return extracted_data