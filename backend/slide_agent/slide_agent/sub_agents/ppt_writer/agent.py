import json
import logging
from typing import Dict, List, Any, AsyncGenerator, Optional
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents import LoopAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from .tools import SearchImage, DocumentSearch,KnowledgeBaseSearch
from ...config import PPT_WRITER_AGENT_CONFIG  # 保留导入，检查器不需要模型
from ...create_model import create_model
from . import prompt
from .utils import validate_slide

logger = logging.getLogger(__name__)

# ========== 通用回调（与原文件一致） ==========
def my_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    logger.info(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None

def my_after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    # 1. 检查用户输入，注意如果是llm的stream模式，那么response_data的结果是一个token的结果，还有可能是工具的调用
    agent_name = callback_context.agent_name
    response_parts = llm_response.content.parts
    part_texts = []
    for one_part in response_parts:
        part_text = one_part.text
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    logger.info(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    return None

# ========== 生成前/后回调 ==========
def my_writer_before_agent_callback(callback_context: CallbackContext) -> None:
    # 这里可根据需要读取 state 做前置处理
    current_slide_index: int = callback_context.state.get("current_slide_index", 0)  # Default to 0
    slides_plan_num = callback_context.state.get("slides_plan_num")
    # 返回 None，继续调用 LLM
    return None

def my_after_agent_callback(callback_context: CallbackContext) -> None:
    """
    在LLM生成内容后，将其原始文本缓存到 state['last_written_raw']，
    供 CheckerAgent 进行 JSON 校验；不在此处推进页码。
    """
    model_last_output_content = callback_context._invocation_context.session.events[-1]
    response_parts = model_last_output_content.content.parts
    part_texts = []
    for one_part in response_parts:
        part_text = one_part.text
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)

    # 保存本轮生成的原始文本，等待校验
    callback_context.state["last_written_raw"] = part_text_content
    print(f"--- 本页生成的原始内容已写入 state['last_written_raw'] ---")

# ========== Writer（生成） ==========
class PPTWriterSubAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="PPTWriterSubAgent",
            model=create_model(model=PPT_WRITER_AGENT_CONFIG["model"], provider=PPT_WRITER_AGENT_CONFIG["provider"]),
            description="根据每一页的幻灯片slide的json结构，丰富幻灯片的slide的内容",
            instruction=self._get_dynamic_instruction,
            before_agent_callback=my_writer_before_agent_callback,
            after_agent_callback=my_after_agent_callback,
            before_model_callback=my_before_model_callback,
            after_model_callback=my_after_model_callback,
            # tools=[DocumentSearch,KnowledgeBaseSearch,SearchImage],
            tools=[KnowledgeBaseSearch,SearchImage],
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        slides_plan_num: int = ctx.session.state.get("slides_plan_num")
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)

        # 根据上一次Checker校验结果决定是否清空 / 追加内消息 == =
        st = ctx.session.state
        last_passed = st.get("last_validation_passed")  # 可能为 None / True / False
        feedback_text = st.get("last_validation_feedback")

        # 首轮（index==0 且还未校验）视为需要清空；若上次通过，也清空；若上次失败，则不清空并注入反馈。
        should_clear = (current_slide_index == 0 and last_passed is None) or (last_passed is True)

        if should_clear:
            # 只有在“通过校验”或“首轮未校验”时才清空
            ctx.session.events = []
            # 使用一次后复位，避免“旧的通过”状态影响后续判断
            st["last_validation_passed"] = None
        else:
            # 上次未通过：不清空，并把错误反馈加入上下文，帮助模型修正
            # if feedback_text:
            #     ctx.session.events.append(
            #         Event(
            #             author="CheckerAgent",
            #             content=types.Content(parts=[types.Part(text=feedback_text)])
            #         )
            #     )
            logger.info(f"=====>>>6. 当前正在进行对: 第{current_slide_index}个块重新生成")
            del_history = ctx.session.events.pop()
            logger.info(f"=============>>>删除了最后1个内容块：\n{del_history}")
            del_history = ctx.session.events.pop()
            logger.info(f"=============>>>删除了倒数第2个内容块：\n{del_history}")
            logger.info(f"=============>>>删除后的历史记录为：\n{ctx.session.events}")
        if current_slide_index == 0:
            print(f"正在生成第{current_slide_index}页幻灯片...")

        async for event in super()._run_async_impl(ctx):
            print(f"{self.name} 收到事件：{event}")
            logger.info(f"{self.name} 收到事件：{event}")
            yield event

    def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
        """动态整合所有研究发现并生成指令"""
        # 当前正在生成第几页的ppt
        current_slide_index: int = ctx.state.get("current_slide_index", 0)
        # 获取大纲
        outline_json: list = ctx.state.get("outline_json")
        # 获取要生成的ppt的这一页的schema大纲
        current_slide_schema = outline_json[current_slide_index]
        metadata = ctx.state.get("metadata", {})
        # 默认支持所有的搜索工具
        search_engine = metadata.get("search_engine", [])
        # 如果是None，那么没问题，走默认PREFIX_PAGE_PROMPT，如果是空列表，那么使用所有工具
        if search_engine == []:
            search_engine = ["KnowledgeBaseSearch","DocumentSearch","SearchImage"]
        user_id = metadata.get("user_id", "")
        language = metadata.get("language", "chinese")  # 默认中文
        if not user_id and search_engine and "KnowledgeBaseSearch" in search_engine:
            print("当前用户未指定知识库的用户id，无法使用KnowledgeBaseSearch进行搜索，必须去除知识库搜索工具")
            search_engine.remove("KnowledgeBaseSearch")
        # 根据不同的搜索工具，使用不同的prefix的prompt, search_engine为False的时候
        if not search_engine:
            prefix_prompt = prompt.PREFIX_PAGE_PROMPT.format(language=language)
        elif search_engine == ["SearchImage"]:
            prefix_prompt = prompt.PREFIX_PAGE_PROMPT_WITH_IMAGE.format(language=language)
        else:
            prefix_prompt = prompt.PREFIX_PAGE_PROMPT_WITH_SEARCH.format(tool_names=search_engine,language=language)
        # 这页ppt的类型
        current_slide_type = current_slide_schema.get("type")
        print(f"当前要生成第{current_slide_index}页的ppt， 类型为：{current_slide_type}， 具体内容为：{current_slide_schema}")
        # 根据不同的类型，形成不同的prompt
        slide_prompt = prompt.prompt_mapper[current_slide_type]
        current_slide_schema_json = json.dumps(current_slide_schema, ensure_ascii=False)
        prompt_instruction = prefix_prompt + slide_prompt.format(input_slide_data=current_slide_schema_json, language=language)
        print(f"第{current_slide_index}页的prompt是：{prompt_instruction}")
        return prompt_instruction

# ========== Checker（规则校验 JSON，不调用大模型） ==========
class CheckerAgent(BaseAgent):
    """
    仅用规则判断 Writer 的输出是否为 JSON：
    - 截取首个 '{' 到最后一个 '}' 的子串尝试 json.loads
    - 成功：state['is_valid_json']=True，state['last_slide_json']=obj
    - 失败：state['is_valid_json']=False
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="CheckerAgent",
            description="规则校验 Writer 输出是否为 JSON（不调用大模型）",
            **kwargs
        )

    def _try_parse_json(self, text: str) -> Optional[dict]:
        if not text:
            return None
        s = text.strip()
        if s.startswith("```json"):
            s = s[len("```json"):].strip()
        if s.startswith("```"):
            s = s[len("```"):].strip()
        if s.endswith("```"):
            s = s[: -len("```")].strip()
        try:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                s = s[start:end+1]
            return json.loads(s)
        except Exception:
            return None

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        raw = ctx.session.state.get("last_written_raw")  # Writer 存入
        data = self._try_parse_json(raw)
        if data is None:
            ctx.session.state["is_valid_json"] = False
            ctx.session.state["last_slide_json"] = None
            fail_msg = "校验结果：❌ 非 JSON。将触发重试或跳过策略。"
            ctx.session.state["last_validation_passed"] = False
            ctx.session.state["last_validation_feedback"] = fail_msg
            # yield Event(
            #     author=self.name,
            #     content=types.Content(parts=[types.Part(text="校验结果：❌ 非 JSON。将触发重试或跳过策略。")])
            # )
            return
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)
        outline_json: list = ctx.session.state.get("outline_json")
        current_slide_schema = outline_json[current_slide_index]
        is_valid, error_messages = validate_slide(data, current_slide_schema)
        if not is_valid:
            ctx.session.state["is_valid_json"] = False
            ctx.session.state["last_slide_json"] = None
            # === ：记录“未通过校验”的状态与错误信息 ===
            fail_msg = f"校验结果：❌ JSON。将触发重试或跳过策略。缺少了部分字段: {error_messages}"
            ctx.session.state["last_validation_passed"] = False
            ctx.session.state["last_validation_feedback"] = fail_msg
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=f"校验结果：❌ JSON。将触发重试或跳过策略。缺少了部分字段: {error_messages}")])
            )
            return
        ctx.session.state["is_valid_json"] = True
        ctx.session.state["last_slide_json"] = data
        # === 记录“通过校验”的状态，并清空反馈文本 ===
        ctx.session.state["last_validation_passed"] = True
        # ctx.session.state["last_validation_feedback"] = None
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="校验结果：✅ 有效 JSON。")])
        )
        return

# ========== Controller（推进/终止） ==========
class ControllerAgent(BaseAgent):
    """
    决策：
    - 若校验通过：把 JSON 存入 accumulated 列表，推进 current_slide_index
    - 若校验失败：针对当前页重试，重试次数超过阈值则跳过此页并推进
    - 若已到最后一页：汇总输出并 escalate 终止
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="ControllerAgent",
            description="根据校验结果推进或终止",
            **kwargs
        )

    def _get_retry_map(self, st: Dict[str, Any]) -> Dict[int, int]:
        # 避免 setdefault：若不存在则赋空 dict
        m = st.get("retry_count_map")
        if m is None:
            m = {}
            st["retry_count_map"] = m
        return m

    def _append_accumulated(self, st: Dict[str, Any], item: dict) -> None:
        acc = st.get("generated_slides_content")
        if acc is None:
            acc = []
            st["generated_slides_content"] = acc
        acc.append(item)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        max_retries: int = 3
        st = ctx.session.state
        slides_plan_num: int = int(st.get("slides_plan_num", 0))
        current_slide_index: int = int(st.get("current_slide_index", 0))
        is_valid: bool = bool(st.get("is_valid_json", False))
        retry_map = self._get_retry_map(st)
        current_retries = int(retry_map.get(current_slide_index, 0))

        if is_valid:
            data = st.get("last_slide_json")
            # 累计保存
            self._append_accumulated(st, data if data is not None else st.get("last_written_raw"))
            # 清理本页中间态
            last_written_raw = st.get("last_written_raw")
            last_slide_json = st.get("last_slide_json")
            if last_slide_json:
                return_slide_json = json.dumps(last_slide_json, ensure_ascii=False)
            else:
                return_slide_json = last_written_raw
            st["last_written_raw"] = None
            st["last_slide_json"] = None
            st["is_valid_json"] = False
            retry_map[current_slide_index] = 0

            # 推进页码
            st["current_slide_index"] = current_slide_index + 1
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=return_slide_json)])
            )
            print(f"第 {current_slide_index} 页已通过校验，进入下一页。")
        else:
            # 失败：尝试重试或跳过
            current_retries += 1
            retry_map[current_slide_index] = current_retries
            if current_retries <= max_retries:
                print(f"第 {current_slide_index} 页非 JSON，准备第 {current_retries} 次重试。")
                # 不推进页码，由 LoopAgent 触发下一轮 Writer
                return
            else:
                # 超过重试阈值，选择跳过此页，推进
                print(f"第 {current_slide_index} 页重试超过 {max_retries} 次，跳过并进入下一页。")
                st["current_slide_index"] = current_slide_index + 1
                last_written_raw = st.get("last_written_raw")
                last_slide_json = st.get("last_slide_json")
                if last_slide_json:
                    return_slide_json = json.dumps(last_slide_json, ensure_ascii=False)
                else:
                    return_slide_json = last_written_raw
                # 清理中间态
                st["last_written_raw"] = None
                st["last_slide_json"] = None
                st["is_valid_json"] = False
                retry_map[current_slide_index] = 0
                # 即使失败，也返回last_written_raw
                yield Event(
                    author=self.name,
                    content=types.Content(parts=[types.Part(text=return_slide_json)])
                )

        # 终止判断：到达最后一页后输出汇总并 escalate
        new_index = int(st.get("current_slide_index", 0))
        if slides_plan_num > 0 and new_index >= slides_plan_num:
            # 汇总输出
            accumulated = st.get("generated_slides_content") or []
            try:
                pretty = json.dumps(accumulated, ensure_ascii=False, indent=2)
            except Exception:
                pretty = str(accumulated)
            print(f"全部页处理完成。汇总如下：\n\n{pretty}")
            # 结束循环
            yield Event(author=self.name, actions=EventActions(escalate=True))

        return

# ========== Loop 入口 ==========
def my_super_before_agent_callback(callback_context: CallbackContext):
    """
    Loop 启动前的初始化（仅一次）
    """
    st = callback_context.state
    # 初始化重试计数 map、累计结果
    if st.get("retry_count_map") is None:
        st["retry_count_map"] = {}
    if st.get("generated_slides_content") is None:
        st["generated_slides_content"] = []
    # attempts 不是必须，这里不做。
    return None

# --- 4. PPTGeneratorLoopAgent ---
ppt_generator_loop_agent = LoopAgent(
    name="PPTGeneratorLoopAgent",
    max_iterations=200,  # 给足够大，依赖 Controller 决定终止
    sub_agents=[
        PPTWriterSubAgent(),  # 1) 生成
        CheckerAgent(),       # 2) 规则校验 JSON（不调用大模型）
        ControllerAgent(),    # 3) 控制推进 / 终止
    ],
    before_agent_callback=my_super_before_agent_callback,
)
