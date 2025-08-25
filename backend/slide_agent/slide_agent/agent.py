from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types  # 用于在回调里短路并给用户返回消息
from dotenv import load_dotenv
from .sub_agents.ppt_writer.agent import ppt_generator_loop_agent
from .utils import parse_markdown_to_slides  # 复用你已有的解析函数

# 在模块顶部加载环境变量
load_dotenv('.env')

def _get_markdown_from_context(callback_context: CallbackContext) -> str | None:
    """
    尝试从当前这次调用的上下文中拿到用户刚发来的 Markdown 文本。
    1) 优先读取回调上下文可能暴露的 user_content（不同版本可能命名略异，做了 getattr 兼容）
    2) 其次尝试从 state 及 metadata 的若干常见键里兜底（如果客户端自行塞了）。
    """
    # 1) 通过回调上下文的 user_content（如果该属性存在）
    user_content = getattr(callback_context, "user_content", None)
    if user_content and getattr(user_content, "parts", None):
        for part in user_content.parts:
            text = getattr(part, "text", None)
            if text:
                return text
    return None


def _is_valid_outline(md: str) -> bool:
    """
    做个轻量合法性校验：
    - 必须存在一级标题 '# '
    - 至少存在二级 '## ' 或三级 '### ' 或条目 '- '
    （你的 parse_markdown_to_slides 很宽松，这里加一道门槛，失败就判不合法）
    """
    lines = [ln.strip() for ln in md.splitlines()]
    has_h1 = any(ln.startswith("# ") for ln in lines)
    has_section = any(ln.startswith("## ") for ln in lines)
    has_sub_or_item = any(ln.startswith("### ") or ln.startswith("- ") for ln in lines)
    return has_h1 and (has_section or has_sub_or_item)


def before_agent_callback(callback_context: CallbackContext):
    """
    在调用 LLM/子 Agent 之前：
    1) 读取用户刚发的 Markdown 大纲
    2) 校验 + 解析为 JSON（slides 结构）
    3) 成功：写入 state['metadata']['outline_json']，继续执行
       失败：直接返回错误信息，短路后续 Agent 执行
    """
    state = callback_context.state
    metadata = state.get("metadata") or {}

    # 兼容你原来的语言设置
    language = metadata.get("language", "EN-US")
    state["language"] = language

    md_content = _get_markdown_from_context(callback_context)
    if not md_content or not _is_valid_outline(md_content):
        # 解析前的快速校验失败：直接告诉用户不合法并短路
        return types.Content(
            role="model",
            parts=[types.Part(text="markdown不合法：请提供包含 # / ## / ### 标题与条目的大纲")]
        )

    try:
        slides = parse_markdown_to_slides(md_content)
    except Exception:
        # 真解析出异常：直接告诉用户不合法并短路
        return types.Content(
            role="model",
            parts=[types.Part(text="markdown不合法")]
        )

    # 成功：把 JSON(可序列化的 list/dict) 放到 metadata 里供后续 Agent 使用
    state["outline_json"] = slides
    state["slides_plan_num"] = len(slides)
    state["makrdown"] = md_content
    # 返回 None 继续执行后续 Agent: ppt_generator_loop_agent
    return None


root_agent = SequentialAgent(
    name="WritingSystemAgent",
    description="多Agent写作系统的总协调器",
    sub_agents=[ppt_generator_loop_agent],
    before_agent_callback=before_agent_callback
)
