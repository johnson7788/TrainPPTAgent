# 文件名: slide_agent/sub_agents/research_topic/agent.py
import json
import logging
from typing import AsyncGenerator
from pydantic import PrivateAttr
from google.adk.agents.llm_agent import Agent
from google.adk.agents import ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
from typing import Dict, List, Any, AsyncGenerator, Optional, Union
from google.adk.events.event import Event,EventActions
# 导入 ParallelAgent 源码中的内部辅助函数，这是实现并行的关键
from google.adk.agents.parallel_agent import (
    _create_branch_ctx_for_sub_agent,
    _merge_agent_run,
)

# from .load_mcp import load_mcp_tools
from ...config import TOPIC_RESEARCH_AGENT_CONFIG
from ...create_model import create_model
from . import prompt
from .tools import DocumentSearch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载工具和模型配置，这些将作为模板使用
research_model = create_model(model=TOPIC_RESEARCH_AGENT_CONFIG["model"],
                              provider=TOPIC_RESEARCH_AGENT_CONFIG["provider"])

# 定义一个 research_agent 的“模板”。我们不会直接运行它，
# 而是用它来创建多个动态实例。

def research_agent_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    # 1. 检查用户输入
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    print(f"调用了{agent_name} research Agent的callback, 现在Agent共有{history_length}条历史记录")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None


# 自定义我们的动态并行 Agent
class DynamicParallelSearchAgent(ParallelAgent):
    """
    一个可以根据输入动态创建和并行执行子Agent的Agent。
    它期望从上一个Agent接收一个JSON字符串，其中包含一个'topics'列表。
    """
    _agent_template: Agent = PrivateAttr()

    def __init__(self, **kwargs):
        """
        初始化动态并行Agent。

        Args:
            agent_template: 一个Agent实例，用作创建动态子Agent的模板。
            **kwargs: 传递给父类ParallelAgent的参数。
        """
        # sub_agents 初始化为空，因为它们是动态生成的
        super().__init__(sub_agents=[], **kwargs)

    async def _run_async_impl(
            self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        重写核心运行逻辑，以实现动态并行化。
        """
        # 1. 从上下文中获取上一个Agent的输出
        # 通常是历史记录中的最后一个非用户事件
        topics_output = ctx.session.state.get("split_topics", {})
        logger.info(f"DynamicParallelSearchAgent 收到输入: {topics_output}")
        topic_list = []
        try:
            # 清理可能的Markdown代码块
            if isinstance(topics_output, str):
                if topics_output.strip().startswith("```json"):
                    topics_output = topics_output.strip()[7:-3]
                elif topics_output.strip().startswith("```"):
                    topics_output = topics_output.strip()[3:-3]

            topics_data = json.loads(topics_output)
            topic_list = topics_data.get("topics", [])
        except (json.JSONDecodeError, AttributeError) as e:
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=f"错误：解析主题JSON失败 - {e}")]),
                actions=EventActions(escalate=True)
            )
            return

        # 3. 为每个主题动态创建子Agent
        dynamic_sub_agents = []
        # 每个子Agent的输出key的集合，最终存储到state中
        research_output_keys = []
        for topic in topic_list:
            topic_id = topic.get("id", "N/A")
            topic_title = topic.get("title", "Untitled")
            topic_description = topic.get("description", "")

            # 创建一个定制化的指令，将主题信息注入到基础prompt中
            custom_instruction = (
                f"{prompt.RESEARCH_TOPIC_AGENT_PROMPT}\n\n"
                f"Your specific task is to research the following topic:\n"
                f"- **Topic Title**: {topic_title}\n"
                f"- **Description**: {topic_description}\n"
                f"- **Keywords**: {topic.get('keywords', [])}\n"
                f"- **Research Focus**: {topic.get('research_focus', '')}"
            )
            new_research_agent = Agent(
                model=research_model,
                name=f"research_agent_{topic_id}",  # 模板名称
                description="Medical expert for a specific topic.",
                instruction=custom_instruction,
                tools=[DocumentSearch],
                output_key=f"research_agent_{topic_id}",  #输出的内容的key
                before_model_callback=research_agent_before_model_callback
            )
            research_output_keys.append(f"research_agent_{topic_id}")
            # 关键：设置父级Agent，ADK框架需要这个来构建Agent树
            new_research_agent.parent_agent = self
            dynamic_sub_agents.append(new_research_agent)
        ctx.session.state["research_output_keys"] = research_output_keys
        logger.info(f"成功创建了 {len(dynamic_sub_agents)} 个动态 research agents.")

        # 4. 并行运行所有动态创建的Agent
        # 这部分逻辑直接借鉴自 ParallelAgent 的源码
        ctx.session.events = [] # 清空上个Agent的事件
        agent_runs = [
            sub_agent.run_async(
                _create_branch_ctx_for_sub_agent(self, sub_agent, ctx)
            )
            for sub_agent in dynamic_sub_agents
        ]

        # 5. 合并并产生事件流
        async for event in _merge_agent_run(agent_runs):
            yield event


# 实例化我们的新 Agent
parallel_search_agent = DynamicParallelSearchAgent(
    name="parallel_search_agent",
    description="根据拆分的主题，动态创建并行的研究员进行资料搜集",
)