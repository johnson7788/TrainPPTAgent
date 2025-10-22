from copy import deepcopy
import os
import asyncio
import json
from fastapi import UploadFile, File
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from pathlib import Path

app = FastAPI()
TEMPLATE_DIR = Path(__file__).resolve().parent / "template"

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool

# The example markdown response provided by the user
markdown_response = """# 2025科技前沿动态

## 人工智能与机器学习
### 大型语言模型的突破
- GPT-6实现多模态理解与生成，文本、图像、音频无缝融合
- 多语言处理能力达到人类水平，支持100+种语言的深度理解
- 模型参数优化，训练能耗降低70%，推理速度提升3倍
- 自监督学习能力增强，减少标注数据依赖达90%
- 伦理安全框架完善，内置事实核查机制

### 通用人工智能进展
- AGI系统在有限领域实现超越专家水平的表现
- 多智能体协作系统解决复杂问题的能力显著提升
- 元学习算法实现快速适应新任务的能力
- 神经符号AI结合逻辑推理与神经网络优势
- 自主AI系统获得有限环境下的决策能力

### 人工智能伦理与治理
- 全球AI治理框架初步建立，包含跨国合作机制
- AI透明度与可解释性成为强制性要求
- 偏见检测与缓解技术成熟，减少算法歧视
- 数据隐私保护与AI应用的平衡机制形成
- AI安全研究重点关注对抗性攻击防御

## 量子计算与量子互联网
### 量子计算硬件突破
- 50+量子比特量子处理器实现稳定运行
- 量子纠错技术取得重大进展，错误率降低至10^-6
- 高温超导量子芯片实现室温量子计算原型
- 光量子计算机处理特定问题的速度提升100倍
- 量子-经典混合计算架构走向实用化

### 量子互联网发展
- 量子密钥分发网络覆盖主要城市，实现安全通信
- 量子中继器技术突破，量子态传输距离达1000公里
- 量子路由器与量子交换机标准形成
- 全球量子互联网基础设施初步规划完成
- 量子安全协议成为金融、政府通信标准

### 量子计算应用探索
- 药物分子模拟实现原子级别精确计算
- 优化算法解决物流、能源分配等复杂问题
- 人工智能加速器利用量子计算提升模型训练速度
- 金融风险分析模型计算效率提升1000倍
- 材料科学发现新型超导材料与催化剂
"""
#图片的幻灯片的响应格式，替换背景图，这里的images是背景图，有时会替换，有时不会
image_data = {
    "type": "content",
    "data": {
        "title": "暴力犯罪",
        "items": [
            {"title": "暴力犯罪","text": "AI助手已实现高度个性化，能够学习用户习惯、偏好和需求，提供定制化服务，成为日常生活和工作的得力助手，显著提升个人效率与体验。"},
            {"title": "暴力犯罪","text": "AI助手已实现高度个性化，能够学习用户习惯、偏好和需求，提供定制化服务，成为日常生活和工作的得力助手，显著提升个人效率与体验。"},
        ]
    },
    "images": [
        {
            "id": "图片ID",
            "src": "https://www.hertz.com/content/dam/hertz/global/blog-articles/things-to-do/hertz230-things-to-do-londons-top-10-attractions/Big-Ben-Clock-Tower.jpg",
            "width": 1920,
            "height": 1080,
            "alt": "不同年份的谋杀率"
        }
    ]
}
# 元素中的图片，不是背景图
image_item_data = {
    "type": "content",
    "data": {
        "title": "暴力犯罪",
        "items": [
            {
            "kind": "image",
            "title": "暴力犯罪",
            "text": "AI助手已实现高度个性化，能够学习用户习惯、偏好和需求，提供定制化服务，成为日常生活和工作的得力助手，显著提升个人效率与体验。",
            "src": "https://www.hertz.com/content/dam/hertz/global/blog-articles/things-to-do/hertz230-things-to-do-londons-top-10-attractions/Big-Ben-Clock-Tower.jpg"
            },
        ]
    },
}
data_response_content = [
    # {"type": "cover", "data": {"title": "2025科技前沿动态", "text": "探索人工智能、量子计算、生物技术等领域的最新突破与未来发展方向"}},
    # {"type": "contents", "data": {"items": ["人工智能新突破", "量子计算商业化进程", "生物技术与医疗革新", "新能源与可持续发展", "通信技术与连接未来", "先进制造与机器人技术"]}},
    # {"type": "transition", "data": {"title": "人工智能新突破", "text": "人工智能技术实现多模态融合、参数效率优化与个性化服务，推动各行业创新应用"}},
    image_item_data
    # {"type": "content", "data": {"title": "大语言模型的进化", "items": [
    #     {"title": "多模态融合", "text": "大语言模型已实现文本、图像、音频等多模态信息的深度融合理解，使AI系统能够更接近人类感知世界的方式，处理复杂场景下的信息整合与推理任务。"},
    #     {"title": "参数效率优化", "text": "通过模型架构创新与训练算法优化，新一代大语言模型显著降低了训练成本，同时保持了甚至提升了模型性能，使更多研究机构和企业能够参与AI技术研发与应用。"},
    #     {"title": "自主推理能力", "text": "AI系统的自主推理和规划能力显著增强，能够基于复杂环境做出更接近人类思维方式的决策，在科学研究、问题解决等领域展现出前所未有的潜力。"},
    #     {"title": "个性化AI助手", "text": "AI助手已实现高度个性化，能够学习用户习惯、偏好和需求，提供定制化服务，成为日常生活和工作的得力助手，显著提升个人效率与体验。"},
    #     {"title": "安全伦理框架", "text": "随着AI应用的普及，安全与伦理框架逐步完善，通过算法优化、数据治理和监管措施，有效减少AI系统中的偏见与滥用风险，促进技术健康发展。"}
    # ]}},
    # {"type": "content", "data": {"title": "生成式AI的商业应用", "items": [
    #     {"title": "内容创作变革", "text": "生成式AI已全面变革内容创作行业，自动化生成高质量文章、视频和音乐的能力显著提升，大幅降低了内容生产成本，提高了创作效率，为创意产业带来新的发展机遇。"},
    #     {"title": "药物研发加速", "text": "AI技术显著缩短了药物研发周期，通过分子结构设计与药物特性预测，加速了新药发现过程，为治疗复杂疾病提供了更多可能性，降低了研发成本与风险。"},
    #     {"title": "工业设计优化", "text": "在工业设计领域，生成式AI实现了快速原型迭代和优化，能够根据需求自动生成多种设计方案，并评估其可行性与性能，大幅提高了设计效率与创新性。"},
    #     {"title": "精准营销投放", "text": "生成式AI在营销领域实现千人千面的个性化广告投放，通过分析用户行为与偏好，精准匹配内容与目标受众，显著提升了营销效果与转化率。"},
    #     {"title": "自适应教育", "text": "教育领域通过AI提供自适应学习路径和智能辅导系统，根据学生能力与学习进度动态调整内容难度与教学方式，实现个性化教育，提升学习效果。"}
    # ]}},
    # {"type": "content", "data": {"title": "AI与脑科学的交叉研究", "items": [
    #     {"title": "脑机接口突破", "text": "脑机接口技术取得重大突破，实现了更高精度的思维解码，使大脑信号能够更准确地转化为控制指令，为医疗康复和人机交互开辟了新途径。"},
    #     {"title": "神经形态芯片", "text": "神经形态芯片模仿人脑结构与工作机制，大幅提升了能效比，在处理复杂模式识别与学习任务时展现出显著优势，为低功耗AI计算提供了新方向。"},
    #     {"title": "脑疾病精准医疗", "text": "AI辅助脑疾病诊断和治疗系统已实现临床应用，通过分析神经影像与脑电数据，提高了阿尔茨海默症、帕金森病等神经系统疾病的早期诊断准确性与治疗效果。"},
    #     {"title": "意识上传探索", "text": "意识上传与数字永生概念已从理论走向初步实验阶段，通过脑部扫描与神经网络建模，科学家们正在探索保存人类认知特征的可能性，为未来脑机融合奠定基础。"},
    #     {"title": "认知科学启发", "text": "认知科学研究为AI提供了新的理论框架与算法启发，而AI的发展也反过来促进了脑科学研究，形成双向促进的良性循环，推动了两个领域的共同进步。"}
    # ]}},
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "月度活跃趋势（折线图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "2025 上半年活跃用户",
    #         "text": "2025年的我国的1到6月份的本产品在不同设备上的月活统计",
    #         "chartType": "line",
    #         "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
    #         "series": [
    #           { "name": "iOS", "data": [12, 15, 18, 22, 24, 27] },
    #           { "name": "Android", "data": [10, 13, 17, 20, 23, 25] }
    #         ],
    #         "options": {
    #           "legend": { "top": 8 },
    #           "xAxis": { "boundaryGap": False },
    #           "yAxis": { "name": "万" }
    #         }
    #       }
    #     ]
    #   }
    # },
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "地区销售（条形图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "各地区销量",
    #         "text": "国内各个区域的销量占比图",
    #         "chartType": "bar",
    #         "labels": ["华北", "华东", "华南", "西南", "华中"],
    #         "series": [
    #           { "name": "销量", "data": [320, 480, 450, 260, 390] }
    #         ],
    #         "options": {
    #           "legend": { "show": False },
    #           "xAxis": { "type": "value", "name": "台" },
    #           "yAxis": { "type": "category" }
    #         }
    #       }
    #     ]
    #   }
    # },
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "品类占比（饼图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "品类占比",
    #         "text": "全国的各地区的产品销量占比如下图",
    #         "chartType": "pie",
    #         "labels": ["A 类", "B 类", "C 类", "D 类"],
    #         "series": [
    #           { "name": "占比", "data": [35, 25, 20, 20] }
    #         ],
    #         "options": {
    #           "legend": { "bottom": 8 },
    #           "tooltip": { "trigger": "item", "formatter": "{b}: {d}%" }
    #         }
    #       }
    #     ]
    #   }
    # },
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "部门业绩（横向柱状图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "部门业绩对比",
    #         "text": "2025年上半年各部门销售业绩对比（单位：万元）",
    #         "chartType": "column",
    #         "labels": ["销售部", "市场部", "研发部", "客服部", "行政部"],
    #         "series": [
    #           { "name": "业绩额", "data": [480, 360, 540, 300, 220] }
    #         ],
    #         "options": {
    #           "legend": { "show": True },
    #           "xAxis": { "type": "value", "name": "万元" },
    #           "yAxis": { "type": "category" }
    #         }
    #       }
    #     ]
    #   }
    # },
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "销售结构（环形图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "销售结构分析",
    #         "text": "2025年各产品线销售结构环形占比图",
    #         "chartType": "ring",
    #         "labels": ["手机", "平板", "笔记本", "智能穿戴"],
    #         "series": [
    #           { "name": "销售占比", "data": [45, 25, 20, 10] }
    #         ],
    #         "options": {
    #           "legend": { "top": "bottom" },
    #           "tooltip": { "trigger": "item", "formatter": "{b}: {d}%" }
    #         }
    #       }
    #     ]
    #   }
    # },
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "季度收入趋势（面积图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "2025年季度收入变化",
    #         "text": "2025年公司四个季度的总收入趋势（单位：亿元）",
    #         "chartType": "area",
    #         "labels": ["Q1", "Q2", "Q3", "Q4"],
    #         "series": [
    #           { "name": "主营业务收入", "data": [8.5, 9.2, 10.8, 11.5] },
    #           { "name": "其他收入", "data": [1.0, 1.3, 1.1, 1.6] }
    #         ],
    #         "options": {
    #           "lineSmooth": True,
    #           "yAxis": { "name": "亿元" },
    #           "xAxis": { "boundaryGap": True }
    #         }
    #       }
    #     ]
    #   }
    # },
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "用户满意度（雷达图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "主要指标满意度",
    #         "text": "不同维度下的用户满意度对比",
    #         "chartType": "radar",
    #         "labels": ["性能", "外观", "价格", "售后", "易用性"],
    #         "series": [
    #           { "name": "iOS 用户", "data": [85, 90, 70, 80, 95] },
    #           { "name": "Android 用户", "data": [80, 85, 78, 75, 88] }
    #         ],
    #         "options": {
    #           "legend": { "top": "bottom" },
    #           "tooltip": { "trigger": "item" }
    #         }
    #       }
    #     ]
    #   }
    # },
    # {"type": "content", "data": {"title": "行业发展趋势", "items": [{"kind": "chart", "title": "食品行业发展趋势分布", "text": "展示数字化、预制菜等领域在行业发展中的关注占比。", "chartType": "pie", "labels": ["数字化智能化", "预制菜与供应链", "消费升级", "可持续发展"], "series": [{"name": "占比", "data": [30, 35, 20, 15]}], "options": {"xAxis": {"name": "领域"}, "yAxis": {"name": "占比(%)"}}}]}},
    # {"type": "content", "data": {"title": "人口特征分析", "items": [{"kind": "chart", "title": "人口结构类型分布示意", "text": "展示典型区域按年龄分组的人口比例，帮助把握市场主力人群情况。", "chartType": "bar", "labels": ["0-14岁", "15-24岁", "25-44岁", "45-64岁", "65岁以上"], "series": [{"name": "人口占比（%）", "data": [12, 15, 34, 25, 14]}], "options": {"xAxis": {"name": "年龄段"}, "yAxis": {"name": "占比%"}}}]}},
    # {"type": "content", "data": {"title": "安全环保提示", "items": [{"title": "提示地层流体及压力异常",
    #                                                                  "text": "地层流体及压力异常可能引发井喷或漏失，需通过实时监测钻井液密度和流量变化来识别。这类异常常出现在高压油气层或断层带附近，提前预警可避免重大安全事故。现场应配备压力传感器与自动报警系统，确保操作人员能及时响应。"},
    #                                                                 {"title": "说明开发方式及钻压干扰",
    #                                                                  "text": "不同的开发方式（如注水、气驱）会影响地层压力分布，可能导致钻压波动或井壁失稳。合理设计钻压参数并结合地质模型分析，有助于减少对邻井的干扰。例如，在多井区作业时，应避免同时高负荷钻进以降低风险。"},
    #                                                                 {"title": "检测有毒有害气体含量",
    #                                                                  "text": "有毒有害气体如硫化氢、甲烷等可能积聚在井口或作业区域，威胁人员健康甚至引发爆炸。需使用便携式气体检测仪定期巡检，并设置通风系统与报警阈值。一旦超标立即撤离并启动应急程序。"},
    #                                                                 {"title": "评估环境影响及防护措施",
    #                                                                  "text": "钻探活动可能造成土壤污染、噪声扰民或生态破坏，应在施工前开展环境影响评估。采取防渗漏装置、降噪屏障和植被恢复等措施，可有效减轻对周边环境的影响。同时建立环境监测机制，确保合规运行。"},
    #                                                                 {"kind": "chart", "title": "环境风险等级分布",
    #                                                                  "text": "不同作业环节的环境风险等级对比",
    #                                                                  "chartType": "bar",
    #                                                                  "labels": ["钻井作业", "完井测试", "运输装卸",
    #                                                                             "废弃物处理"], "series": [
    #                                                                     {"name": "风险等级", "data": [7, 6, 5, 8]}],
    #                                                                  "options": {"xAxis": {"name": "作业环节"},
    #                                                                              "yAxis": {
    #                                                                                  "name": "风险等级（1-10）"}}}]}}
    ,
    # {
    #   "type": "content",
    #   "data": {
    #     "title": "价格与销量关系（散点图）",
    #     "items": [
    #       {
    #         "kind": "chart",
    #         "title": "价格与销量关系分析",
    #         "text": "不同产品价格与销量之间的分布情况",
    #         "chartType": "scatter",
    #         "labels": ["样本产品"],
    #         "series": [
    #           { "name": "价格（千元）", "data": [3.2, 4.5, 5.1, 6.8, 8.0, 9.5] },
    #           { "name": "销量（万台）", "data": [45, 38, 30, 24, 18, 12] }
    #         ],
    #         "options": {
    #           "legend": { "show": True },
    #           "xAxis": { "name": "价格（千元）" },
    #           "yAxis": { "name": "销量（万台）" },
    #           "tooltip": { "trigger": "item" }
    #         }
    #       }
    #     ]
    #   }
    # },  # 散点图不能显示legend，奇怪？？
    image_data,
    {"type": "end"}
]

async def stream_generator():
    """A generator that yields parts of the markdown response to simulate streaming."""
    for char in markdown_response:
        yield char
        await asyncio.sleep(0.01) # Simulate network latency

@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    if request.stream:
        return StreamingResponse(stream_generator(), media_type="text/plain")
    else:
        return {"text": markdown_response}

class AipptContentRequest(BaseModel):
    content: str

class AipptByIDRequest(BaseModel):
    id: str

def preset_json_to_slides(markdown_text):
    """不用传递参数 markdown_text，使用假的数据 data_response_content。
    如果发现 items 中有 kind == 'chart'，则将其单独拆成一条 slide。
    """
    slides = []
    for one in data_response_content:
        one_type = one["type"]
        if one_type == "content":
            # 获取原始 items
            items = one["data"].get("items", [])
            # 分离普通项和图表项
            normal_items = []
            chart_items = []
            sibling_fields = {
                k: deepcopy(v)
                for k, v in one.items()
                if k not in ("type", "data")  # 保留同级信息，但不覆盖 type/data
            }

            for item in items:
                if item.get("kind") == "chart":
                    chart_items.append(item)
                else:
                    normal_items.append(item)

            # 如果有普通项，保留一条主内容 slide
            if normal_items:
                new_one = {
                    "type": "content",
                    "data": {
                        "title": one["data"].get("title", ""),
                        "items": normal_items
                    },
                    **deepcopy(sibling_fields)
                }
                slides.append(new_one)

            # 每个 chart 单独作为一条 slide
            for chart in chart_items:
                new_chart_slide = {
                    "type": "content",
                    "data": {
                        "title": one["data"].get("title", ""),
                        "items": [chart]
                    }
                }
                slides.append(new_chart_slide)
        else:
            slides.append(one)
    return slides

async def aippt_content_streamer(markdown_content: str):
    """Parses markdown and streams slide data as JSON objects."""
    # slides = parse_markdown_to_slides(markdown_content)
    slides = preset_json_to_slides(markdown_content)
    for slide in slides:
        yield json.dumps(slide, ensure_ascii=False) + '\n'
        await asyncio.sleep(1)

async def aippt_file_id_streamer(id: str):
    """根据用户的已有的文件数据中的文件id来生成ppt
    id: 文件的id
    """
    yield json.dumps({"type": "status", "message": "正在解析文件..."}, ensure_ascii=False) + '\n'
    await asyncio.sleep(3)
    yield json.dumps({"type": "status", "message": "正在生成大纲..."}, ensure_ascii=False) + '\n'
    await asyncio.sleep(1.5)
    yield json.dumps({"type": "status", "message": "大纲生成完毕，即将生成PPT..."}, ensure_ascii=False) + '\n'
    await asyncio.sleep(1)
    slides = preset_json_to_slides(id)
    for slide in slides:
        yield json.dumps(slide, ensure_ascii=False) + '\n'
        await asyncio.sleep(1)


@app.post("/tools/aippt_by_id")
async def aippt_by_id(request: AipptByIDRequest):
    return StreamingResponse(aippt_file_id_streamer(request.id), media_type="application/json; charset=utf-8")


@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    return StreamingResponse(aippt_content_streamer(request.content), media_type="application/json; charset=utf-8")

@app.get("/data/{filename}")
async def get_data(filename: str):
    file_path = TEMPLATE_DIR / filename
    return FileResponse(str(file_path))

@app.post("/tools/aippt_outline_from_file")
async def aippt_outline_from_file(file: UploadFile = File(...)):
    print(f"上传的文件是: {file.filename}")
    return StreamingResponse(stream_generator(), media_type="text/plain")

@app.get("/templates")
async def get_templates():
    templates = [
        { "name": "红色通用", "id": "template_1", "cover": "/api/data/template_1.jpg" },
        { "name": "蓝色通用", "id": "template_2", "cover": "/api/data/template_2.jpg" },
        { "name": "紫色通用", "id": "template_3", "cover": "/api/data/template_3.jpg" },
        { "name": "莫兰迪配色", "id": "template_4", "cover": "/api/data/template_4.jpg" },
        { "name": "引用", "id": "template_5", "cover": "/api/data/template_5.jpg" },
        { "name": "图片和表格", "id": "template_6", "cover": "/api/data/template_6.jpg" },
        {"name": "单图带字", "id": "template_7", "cover": "/api/data/template_6.jpg"},
        {"name": "单图不带字", "id": "template_8", "cover": "/api/data/template_6.jpg"},
        {"name": "项目中的图片", "id": "template_9", "cover": "/api/data/template_6.jpg"},
    ]

    return {"data": templates}

@app.get("/proxy")
async def proxy(request: Request, url: str = Query(..., description="Target absolute URL")):
    """
    透明代理上游资源，转发部分请求头，透传关键响应头，并允许前端同源访问。
    适合图片/音视频等二进制内容。
    """
    HEADERS_TO_FORWARD = {"Range", "User-Agent"}  # 需要时可扩展
    HEADERS_TO_COPY = {
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
    }
    forward_headers = {}
    for h in HEADERS_TO_FORWARD:
        v = request.headers.get(h)
        if v:
            forward_headers[h] = v

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            upstream = await client.get(url, headers=forward_headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream fetch error: {e!s}")

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error")

    headers = {}
    for h in HEADERS_TO_COPY:
        if h in upstream.headers:
            headers[h] = upstream.headers[h]

    # 允许被前端同源读取
    headers["Access-Control-Allow-Origin"] = "*"
    # 给静态资源加简单缓存（按需调整）
    headers.setdefault("Cache-Control", "public, max-age=86400")

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("Content-Type"),
    )

@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=6800)

