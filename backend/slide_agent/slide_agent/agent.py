from google.adk.agents.llm_agent import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from .sub_agents.ppt_writer.agent import ppt_generator_loop_agent
from google.adk.agents.callback_context import CallbackContext
from dotenv import load_dotenv
# 在模块顶部加载环境变量
load_dotenv('.env')

def before_agent_callback(callback_context: CallbackContext) -> None:
    """
    在调用LLM之前，从会话状态中获取当前幻灯片计划，并格式化LLM输入。把传入的markdown大纲变成json格式
    """
    metadata = callback_context.state.get("metadata", {})
    print(f"传入的metadata信息如下: {metadata}")
    language = metadata.get("language","EN-US")
    # 设置幻灯片数量和语言
    callback_context.state["language"] = language
    # 返回 None，继续调用 LLM
    return None

root_agent = SequentialAgent(
    name="WritingSystemAgent",
    description="多Agent写作系统的总协调器",
    sub_agents=[
        ppt_generator_loop_agent
    ],
    before_agent_callback=before_agent_callback
)
