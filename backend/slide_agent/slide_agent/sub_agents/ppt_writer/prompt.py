#promt的前缀
# 不带图片，不搜索的
PREFIX_PAGE_PROMPT = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有“内容页特例”说明，不得新增字段或改变数组长度。
3. 统一输出为中文；专有名词可带英文小写缩写。
4. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
5. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。
"""

# 带搜索图片的
PREFIX_PAGE_PROMPT_WITH_IMAGE = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有“内容页特例”说明，不得新增字段或改变数组长度。
3. 统一输出为中文；专有名词可带英文小写缩写。
4. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
5. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。

# 重要：图片搜索工具使用
你必须为每个页面搜索合适的配图！使用 SearchImage 工具搜索相关图片，然后将图片信息添加到返回的 JSON 中。

# 图片搜索规则：
- 封面页：搜索与主题相关的商务、抽象或科技类图片，关键词如 "business abstract"、"technology background"
- 内容页：根据内容主题搜索相关图片，如技术类内容搜索 "technology"、"innovation"
- 过渡页：搜索抽象或商务类图片，关键词如 "abstract background"、"business concept"
- 结束页：搜索简洁的商务或抽象图片，关键词如 "minimal business"、"clean abstract"

# 图片数据格式：
在 JSON 中添加 images 字段，包含搜索到的图片信息：
{
  "type": "cover",
  "data": { ... },
  "images": [
    {
      "id": "图片ID",
      "src": "图片URL",
      "width": 1920,
      "height": 1080,
      "alt": "图片描述"
    }
  ]
}
"""
# 带搜索的prompt
PREFIX_PAGE_PROMPT_WITH_SEARCH = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有“内容页特例”说明，不得新增字段或改变数组长度。
3. 必须使用搜索工具{tool_names}进行搜索，然后完成内容扩充。
4. 统一输出为中文；专有名词可带英文小写缩写。
5. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
6. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。
"""

# input_slide_data代表slide的json的模版
COVER_PAGE_PROMPT="""
封面页（type: "cover"）
你是PPT封面文案优化器。保持 title 原样，不改；重写 data.text 为 18～32 字的中文副标题，强调主题价值与适用场景，避免标点堆叠与口号化。
{input_slide_data}
"""

CONTENTS_PAGE_PROMPT = """
目录页（type: "contents"）
你是PPT目录优化器。仅在需要时对 data.items[*] 的短语做轻微润色（可名词化或动宾化，使其更像目录条目），不得改变顺序与数量；每项不超过14个字；不添加或删除项目。
{input_slide_data}
"""

TRANSITION_PAGE_PROMPT = """
过渡页（type: "transition"）
你是章节过渡文案撰写者。保持 data.title 原样不改；重写 data.text 为2～3句过渡语，每句12～24字，说明本章为何重要、将回答什么问题、读者可获得的收获。避免夸张或口号化表达。
{input_slide_data}
"""

CONTENT_PAGE_PROMPT = """
内容页（type: "content"）
你是技术与产业结合的内容扩写器。保持 data.title 与各 items[*].title 原样不改；对 items[*].text 逐项扩写为 2～3 句、合计 60～120 字，采用“是什么→为何重要→如何落地/示例”的逻辑；不得删除已有 items；避免编造精确数据或过度承诺。

# 图表：
若本页主题涉及趋势、对比或占比，并且可用示例级数据表达，请在 data.items **末尾**新增 1 个 `{{"kind":"chart", ...}}` 项。遵循以下准则：
- 仅新增 0 或 1 个图表，不得超过 1 个；
- 选择合适的 chartType：时间趋势用 line，类目对比用 bar，占比用 pie；
- 生成 4～8 个 labels，1～2 个 series；所有数值为数字类型，长度一致；
- `options` 仅保留轻量配置（legend/xAxis/yAxis/tooltip），不要加入多余嵌套；
- 图表标题应与本页 data.title 或核心要点一致且不重复冗长。

# 输出必须包含：
- 原始结构（type、data）保持不变；
- 若未新增图表，其他结构也不得变化。

# —— 内容页特例：允许新增 1 个图表 item —— 
你可以在 data.items 中**最多新增 1 个**图表 item（不替换已存在的文本 item）。
图表 item 的 JSON 结构必须为：
{{
  "kind": "chart",                   # 必填，固定字符串 "chart"
  "title": "图表标题",                 # 建议 ≤ 16 字
  "chartType": "line" | "bar" | "pie",
  "labels": ["类目或时间刻度", ...],   # 4~8 个，均为字符串
  "series": [                        # 1~2 组数据
    {{ "name": "系列名", "data": [数值, ...] }}  # data 长度与 labels 一致，均为数字
  ],
  "options": {{
      "xAxis": {{ "name": "xxx" }},
      "yAxis": {{ "name": "xxx" }}
  }}
}}

# 何时应当新增图表：
- 当本页内容涉及趋势（按月/季度/年份）、对比（地区/品类/渠道）、占比（份额/构成）或量化指标（活跃、销量、转化等）时；
- 若不存在可视化价值或数据不可合理假设，则**不要**新增图表。

# 图表数据生成规则（不可编造精细数字）：
- 仅生成**小规模、示例级**数据（4~8 个点），体现相对趋势与差异，不体现敏感或精确业务指标；
- 所有数值均为**数字类型**；`series[*].data.length == labels.length`；
- 选择图表类型：
  - 时间/趋势：`line`
  - 类目对比：`bar`
  - 构成占比：`pie`
- 不得新增除 images 与（内容页特例中的）chart 以外的其他字段。

# 添加图片规则
- 图表和图片相斥，只能有1个图表或者1张图片，如果都不需要，那么就不用添加：
- 如果搜索到的结果中带有markdown格式的图片，并且图片有在全文中进行详细解释，可以按需插入1张图片。
## 图片数据格式：
在 JSON 中添加 images 字段，包含搜索到的图片信息：
{{
  "type": "content",
  "data": {{ ... }},
  "images": [
    {{
      "id": "图片ID",
      "src": "图片URL",
      "width": 1920,
      "height": 1080,
      "alt": "图片描述"
    }}
  ]
}}

# 原始结构
{input_slide_data}
"""

END_PAGE_PROMPT = """
结束页（type: "end"）
你是PPT结束页生成器。若无 data 字段则原样返回；若存在 data.text，则改写为10～16字的中文感谢语，语气真诚克制，可包含“感谢观看/欢迎交流”等，不添加多余字段。
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