import logging
import os

import click
import uvicorn

from adk_agent_executor import ADKAgentExecutor
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from starlette.routing import Route
from google.adk.agents.run_config import RunConfig, StreamingMode
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from starlette.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
from agent import root_agent

# 加载环境变量
load_dotenv()

# 配置日志格式和级别
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host", "host", default="localhost", help="服务器绑定的主机名（默认为 localhost,可以指定具体本机ip）")
@click.option("--port", "port", default=10001, help="服务器监听的端口号（默认为 10001）")
def main(host: str, port: int):
    """
    启动 Outline Agent 服务，支持流式和非流式两种模式。
    """
    logger.info("启动 Outline Agent 服务")
    streaming = os.environ.get("STREAMING") == "true"
    logger.info(f"流式模式: {streaming}")

    agent_card_name = "outline Agent"
    agent_name = "outline_agent"
    # Agent描述必须清晰
    agent_description = "Generate an outline based on the user's requirements"

    # 定义 agent 的技能
    skill = AgentSkill(
        id=agent_name,
        name=agent_card_name,
        description=agent_description,
        tags=["outline"],
        examples=["outline"],
    )

    # 构建 agent 卡片信息
    agent_card = AgentCard(
        name=agent_card_name,
        description=agent_description,
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=streaming),
        skills=[skill],
    )

    # 初始化 Runner，管理 agent 的执行、会话、记忆和产物
    logger.info("初始化Runner...")
    runner = Runner(
        app_name=agent_card.name,
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    # 根据环境变量决定是否启用流式输出
    if streaming:
        logger.info("使用 SSE 流式输出模式")
        run_config = RunConfig(
            streaming_mode=StreamingMode.SSE,
            max_llm_calls=500
        )
    else:
        logger.info("使用普通输出模式")
        run_config = RunConfig(
            streaming_mode=StreamingMode.NONE,
            max_llm_calls=500
        )

    # 初始化 agent 执行器
    agent_executor = ADKAgentExecutor(runner, agent_card, run_config)

    # 请求处理器，管理任务存储和请求分发
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    # 构建 Starlette 应用
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    app = a2a_app.build()
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"服务启动中，监听地址: http://{host}:{port}")
    # 启动 uvicorn 服务器
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
