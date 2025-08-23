# GRPO:
硬约束（必须满足）：JSON 合法、必填字段、页序、每页 items 数等。
软目标（越好越高分）：信息覆盖率、标题精炼度、页面切分是否自然、风格一致性等。

# 奖励设计（RL）
1) 硬约束（0/1 或大惩罚）

JSON 可解析且符合 Schema；

页面类型仅允许枚举值；

必填字段齐全：cover/transition/content 的 data.title，contents.items 非空；

content.data.items 数组长度在允许范围（例如 2～4，或你设定的模板上限 ≤ 12）；

首/尾页类型正确；页序与 transition → content 的章节归属一致。

2) 软目标（分段给分，0~1）

覆盖率：被 ### 与其列表项覆盖的比例（按条目映射到某页计分）；

精炼度：标题/正文是否短于阈值（过长降分）；

分页自然度：同一 ### 的条目尽量连续、不跨页乱序；

目录质量：contents.items 是否准确反映 ## 层；

风格一致：同一 deck 的文风一致、术语统一（可用小型分类器打分）。


# JSON Schema（用于校验与约束解码）
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["type"],
    "properties": {
      "type": { "enum": ["cover","contents","transition","content","end"] },
      "data": { "type": ["object","null"] }
    },
    "allOf": [
      {
        "if": { "properties": { "type": { "const": "cover" } } },
        "then": {
          "required": ["data"],
          "properties": {
            "data": {
              "type": "object",
              "required": ["title"],
              "properties": {
                "title": { "type": "string", "minLength": 1, "maxLength": 32 },
                "text":  { "type": "string" }
              }
            }
          }
        }
      },
      {
        "if": { "properties": { "type": { "const": "contents" } } },
        "then": {
          "required": ["data"],
          "properties": {
            "data": {
              "type": "object",
              "required": ["items"],
              "properties": {
                "items": {
                  "type": "array",
                  "minItems": 1,
                  "maxItems": 20,
                  "items": { "type": "string" }
                }
              }
            }
          }
        }
      },
      {
        "if": { "properties": { "type": { "const": "transition" } } },
        "then": {
          "required": ["data"],
          "properties": {
            "data": {
              "type": "object",
              "required": ["title"],
              "properties": {
                "title": { "type": "string", "minLength": 1, "maxLength": 32 },
                "text":  { "type": "string" }
              }
            }
          }
        }
      },
      {
        "if": { "properties": { "type": { "const": "content" } } },
        "then": {
          "required": ["data"],
          "properties": {
            "data": {
              "type": "object",
              "required": ["title","items"],
              "properties": {
                "title": { "type": "string", "minLength": 1, "maxLength": 32 },
                "items": {
                  "type": "array",
                  "minItems": 1,
                  "maxItems": 12,
                  "items": {
                    "type": "object",
                    "required": ["title","text"],
                    "properties": {
                      "title": { "type": "string", "minLength": 1, "maxLength": 24 },
                      "text":  { "type": "string", "minLength": 1, "maxLength": 120 }
                    }
                  }
                }
              }
            }
          }
        }
      },
      {
        "if": { "properties": { "type": { "const": "end" } } },
        "then": { }
      }
    ]
  }
}
