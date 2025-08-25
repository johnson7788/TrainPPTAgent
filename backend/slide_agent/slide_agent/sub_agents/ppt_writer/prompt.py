#promt的前缀
PREFIX_PAGE_PROMPT = """
你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。

保持原有结构与键名完全不变：不得新增/删除字段；数组长度不变；只改写字符串内容。

统一输出为中文；专有名词可带英文小写缩写。

文风：简洁、商务演示友好，避免夸张或无法证实的数字。

严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。
"""


# input_slide_data代表slide的json的模版
COVER_PAGE_PROMPT="""
封面页（type: "cover"）
你是PPT封面文案优化器。保持 title 原样，不改；重写 data.text 为 18～32 字的中文副标题，强调主题价值与适用场景，避免标点堆叠与口号化。
满足“通用约束”。
{input_slide_data}
"""

CONTENTS_PAGE_PROMPT = """
目录页（type: "contents"）
你是PPT目录优化器。仅在需要时对 data.items[*] 的短语做轻微润色（可名词化或动宾化，使其更像目录条目），不得改变顺序与数量；每项不超过14个字；不添加或删除项目。
满足“通用约束”。
{input_slide_data}
"""

TRANSITION_PAGE_PROMPT = """
过渡页（type: "transition"）
你是章节过渡文案撰写者。保持 data.title 原样不改；重写 data.text 为2～3句过渡语，每句12～24字，说明本章为何重要、将回答什么问题、读者可获得的收获。避免夸张或口号化表达。
满足“通用约束”。
{input_slide_data}
"""

CONTENT_PAGE_PROMPT = """
内容页（type: "content"）
你是技术与产业结合的内容扩写器。保持 data.title 与各 items[*].title 原样不改；对 items[*].text 逐项扩写为2～3句、合计60～120字，采用“是什么→为何重要→如何落地/示例”的逻辑；不得新增/删减 items；避免编造精确数据或过度承诺。
满足“通用约束”。
{input_slide_data}
"""

END_PAGE_PROMPT = """
结束页（type: "end"）
你是PPT结束页生成器。若无 data 字段则原样返回；若存在 data.text，则改写为10～16字的中文感谢语，语气真诚克制，可包含“感谢观看/欢迎交流”等，不添加多余字段。
满足“通用约束”。
{input_slide_data}
"""
# 不同的类型的页面对应的prompt
prompt_mapper = {
    "cover": COVER_PAGE_PROMPT,
    "contents": CONTENTS_PAGE_PROMPT,
    "transition": TRANSITION_PAGE_PROMPT,
    "content": CONTENT_PAGE_PROMPT,
    "end": END_PAGE_PROMPT,
}