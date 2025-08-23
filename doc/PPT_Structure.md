生成流程、模板要求，以及最后这段“犯罪心理学研究”示例数据的**数据格式**与**使用规范**。

# 一、顶层结构与渲染顺序

* **数据是一个数组**，每个元素代表一页（或一段可映射到模板的一页）。
* **数组顺序 = 最终 PPT 的页序**（无需额外的序号字段）。
* 每页对象都有统一外壳：

  ```json
  {
    "type": "<页面类型>",
    "data": { ...该类型需要的字段... }
  }
  ```
* 合法页面类型与用途：

  * `cover`：封面页
  * `contents`：目录页
  * `transition`：章节过渡页
  * `content`：内容页
  * `end`：结束/致谢页

# 二、各页面类型的数据结构（依据示例与模板标注约定）

> 括号里标出主要对应的模板“节点标记”。

### 1) 封面 `cover`

```json
{
  "type": "cover",
  "data": {
    "title": "string",   // ← 标题（“标题”）
    "text": "string?"    // ← 副标题/导语（“正文”），可选
    // 图片：由模板图片标记承载（背景/插图），数据里未强制要求字段
  }
}
```

### 2) 目录 `contents`

```json
{
  "type": "contents",
  "data": {
    "items": ["string", "..."] // ← 目录项（“列表项目”）
    // 图片：同上（背景/插图），无需强制字段
  }
}
```

* **数量支持**：1～20 项（通过模板拼接/裁减机制适配，不必为每个数量单独做模板）。

### 3) 过渡 `transition`

```json
{
  "type": "transition",
  "data": {
    "title": "string",   // ← 章节标题（“标题”）
    "text": "string?"    // ← 衔接说明（“正文”）
    // 模板可含“节编号”标记：通常由渲染逻辑按章节顺序填充；示例数据未包含该字段
    // 图片：可由模板图片标记承载
  }
}
```

### 4) 内容 `content`

```json
{
  "type": "content",
  "data": {
    "title": "string",          // ← 该页主题（“标题”）
    "items": [                  // 2～4 项为模板基本覆盖；引擎逻辑可扩展到 1～12
      {
        "title": "string",      // ← 列表项标题（“列表项标题”）
        "text": "string"        // ← 列表项正文（“列表项目”）
        // “项目编号”通常由渲染时自动编号，数据无须提供
        // 项目插图：由模板图片标记承载
      }
    ]
  }
}
```

### 5) 结束 `end`

```json
{
  "type": "end"
  // 可无 data；若模板需要图片，走图片标记位
}
```

> **图片如何对接？**
> 模板中通过“图片标记”占位（背景/插图/项目插图）。当前线上示例**不强制数据里写图片字段**；若要启用配图，只需按 AIPPT 方法的接口传入**候选图片集合**，引擎再按模板图片标记进行匹配替换即可。

# 三、模板侧要求（PPTist 标注规范）

* 模板是普通 PPTist 页面 + **类型标注**，不是“特殊格式”的独立模板。
* 需要覆盖的页面（**最少 12 页**，以满足替换与随机挑选）：

  * 1×封面
  * 6×目录（分别覆盖 2～6 项与 10 项）
  * 1×过渡
  * 3×内容（分别覆盖 2、3、4 项）
  * 1×结束
* **节点标记**：

  * 文本标记：可用于文本框/带字形状（例如：标题、正文、列表项标题、列表项目、项目编号…）
  * 图片标记：仅用于图片节点（背景、插图、项目插图…）
  * 可扩展更多类型（如图表），但须与数据或渲染逻辑有清晰映射。

> **随机性**：若同类页面做了多款模板（如 3 个封面），生成时会随机取用，提高风格多样性。

# 四、最常见的校验点（数据与模板匹配）

1. **必填字段**是否填写：

   * `cover.data.title`、`transition.data.title`、`content.data.title` 必填
   * `contents.data.items`、`content.data.items` 必须是**非空数组**（目录最少 1 项；内容页建议 2～4 项，渲染器最多可支持到 12）
2. **类型值**是否正确：只能是 `cover`/`contents`/`transition`/`content`/`end`。
3. **文本适配**：标题/正文不宜过长，以免超出模板排版边界（过长则考虑换页或拆分为多条 `content`）。
4. **编号与项目数**：无需在数据内写编号；若项目数超出模板上限，依赖渲染器的拼接/裁减机制。
5. **图片占位**：若启用配图，需确保模板中已有相应“图片标记”；数据侧不强制携带图片字段，但要向引擎提供**可匹配的候选图片集合**。

# 五、与示例数据的一一对应（抽样说明）

* 第 1 条：`type: "cover"` → 填充封面**标题/正文**。
* 第 2 条：`type: "contents"` → 6 条目录项，匹配“列表项目”。
* 第 3 条：`type: "transition"` → 章节过渡**标题/正文**。
* 第 4～6 条：`type: "content"` → 分别为“定义与历史”“基本理论”“个体因素”…每条含 4 个项目（标题+正文）。
* 若模板含“节编号”，渲染时按过渡页顺序自动赋值（示例无该字段）。
* 末尾：`{ "type": "end" }` → 结束页，无需 data。

# 六、（可直接落地的）TypeScript 等价结构（基于示例与规范的推断）

> 如果你要在 `src/types/AIPPT.ts` 中做类型约束，可用类似定义：

```ts
export type AIPPT =
  | SlideCover
  | SlideContents
  | SlideTransition
  | SlideContent
  | SlideEnd
  | Array<SlideCover | SlideContents | SlideTransition | SlideContent | SlideEnd>;

export interface SlideBase<T extends string, D = unknown> {
  type: T;
  data?: D;
}

export type SlideCover = SlideBase<"cover", {
  title: string;
  text?: string;
}>;

export type SlideContents = SlideBase<"contents", {
  items: string[]; // 1~20
}>;

export type SlideTransition = SlideBase<"transition", {
  title: string;
  text?: string;
  // sectionNo?: number; // 若模板需要编号，可由渲染层自动生成；示例未使用
}>;

export type SlideContent = SlideBase<"content", {
  title: string;
  items: Array<{
    title: string;
    text: string;
  }>; // 建议 2~4；渲染层最多支持 1~12
}>;

export type SlideEnd = SlideBase<"end">;
```

# 七、最小可行“生成流程”对接要点

1. **准备模板**（PPTist 中完成页面设计 → 打开“幻灯片类型标注”→ 标记页面/节点类型 → 导出 JSON）。
2. **准备数据**（如本示例），确保字段齐全、数量符合页面标记。
3. **可选：准备配图集合**（用于匹配模板中的图片标记位）。
4. **生成**：引擎按数组顺序依次选取同类模板（必要时拼接/裁减），将 `data` 映射到对应标记并输出 PPT。
