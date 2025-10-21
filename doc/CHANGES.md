# 前端
## 前端添加独立的大纲页面，并修改样式
[Outline](../frontend/src/views/Outline)

## 前端添加PPT的模版选择页面，并修改样式
[PPT](../frontend/src/views/PPT)

## 前端修改后端API连接URL
[vite.config.ts](../frontend/vite.config.ts)

## PPT播放时全屏不能正常显示的问题
```
src/utils/fullscreen.ts
src/hooks/useScreening.ts
```

## 去掉加载默认的3页PPT
```
[App.vue](../frontend/src/App.vue)
onMounted(async () => {
  // const slides = await api.getFileData('slides')
  // slidesStore.setSlides(slides)
  ```

## 去掉大纲和模版选择页面不能下滑的问题
[global.scss](../frontend/src/assets/styles/global.scss) 去掉-  overflow: hidden;

## PPT的生成的页面先跳转，后逐页生成，使用Yield生成器
```useAIPPT.ts```

## PPT的loading状态组件
```src/views/Editor/index.vue```

## 在生成新的PPT前重置已有PPT内容
```
src/store/slides.ts
slideStore.resetSlides()
│    144 + resetSlides() {                                                                             │
│    145 +   this.slides = [                                                                           │
│    146 +     {                                                                                       │
│    147 +       id: nanoid(),                                                                         │
│    148 +       elements: [],                                                                         │
│    149 +     }                                                                                       │
│    150 +   ]                                                                                         │
│    151 +   this.slideIndex = 0                                                                       │
│    152 + },                                                                                          │
│    153 +
```

## 默认的第一页是空的
```
src/store/slides.ts
 │    160 + if (this.slides.length === 1 && this.slides[0].elements.length === 0) {                     │
 │    161 +   this.slides = slides                                                                      │
 │    162 +   this.slideIndex = 0                                                                       │
 │    163 +   return                                                                                    │
 │    164 + }                                                                                           │
 │    165 +
 ```

## 前端图片Interface扩充, frontend/src/types/AIPPT.ts
```
// 图片信息接口
export interface AIPPTImage {
  id: string
  src: string
  width: number
  height: number
  alt?: string
  photographer?: string
  url?: string
}

// 基础幻灯片接口，包含图片字段
export interface AIPPTBaseSlide {
  images?: AIPPTImage[]
}

export interface AIPPTCover extends AIPPTBaseSlide {
  type: 'cover'
  data: {
    title: string
    text: string
  }
}

export interface AIPPTContents extends AIPPTBaseSlide {
  type: 'contents'
  data: {
    items: string[]
  }
  offset?: number
}

export interface AIPPTTransition extends AIPPTBaseSlide {
  type: 'transition'
  data: {
    title: string
    text: string
  }
}

export interface AIPPTContent extends AIPPTBaseSlide {
  type: 'content'
  data: {
    title: string
    items: {
      title: string
      text: string
    }[]
  },
  offset?: number
}

export interface AIPPTEnd extends AIPPTBaseSlide {
  type: 'end'
}

export type AIPPTSlide = AIPPTCover | AIPPTContents | AIPPTTransition | AIPPTContent | AIPPTEnd
```

## 添加参考引用类型type=reference，即当前的PPT的内容有依据，依据来自哪里，网页或者文章等
todo: 前端依据修改好，但是模版[template](../backend/main_api/template)文件和示例代码的数据还未更新[mock_main.py](../backend/mock_api/mock_main.py)
```
userAIPPT.ts # 添加reference引用类型的页面type处理
index.ts 
store/slides.ts
types/AIPPT.ts  #AIPPTReference类型约束
MarkupPanel.vue  # 添加前端显示引用类型
```

# 后端

## 添加mock api方便测试
[mock_api](../backend/mock_api)

## 添加A2A+ADK的Agent，方便在线搜索
[simpleOutline](../backend/simpleOutline)

## 添加主程序
[main_api](../backend/main_api)

## 测试程序
[test_main.py](../backend/test_main.py)

## 生成大纲内容的后端主程序
```
[slide_agent](../backend/slide_agent)
main_api.py
```

## 新增搜索PEXELS图片工具，如果未设置PEXELS_API_KEY则会模拟搜索配图
```backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py```

## 对Agent进行改造，添加了循环检查，检查输出Json的key字段必须不能少，但是可以多，因为可能添加图片等。

## 增加上传时文件的标识符，用于发送给后端Agent
```
文件：frontend/src/store/main.ts
    isOutlineFromFile: false, //是否上传了文件，上传了文件，就根据文件生成ppt的大纲
    generateFromUploadedFile: false, // 是否是依据上传的文件生成PPT
    generateFromWebSearch: false, // 是否是依据网络搜索生成PPT

文件：frontend/src/services/index.ts 
函数AIPPT_Content，请求后端，携带generateFromUploadedFile和generateFromWebSearch

文件： frontend/src/views/PPT/index.vue
       <div v-if="isOutlineFromFile" class="generate-option">
          <Checkbox v-model:value="generateFromUploadedFile">根据上传的文件生成PPT</Checkbox>
          <Checkbox v-model:value="generateFromWebSearch">使用网络搜索生成PPT</Checkbox>
        </div>
```

## 对于跨域资源添加后端代理
后端添加 /proxy接口

前端frontend/src/hooks/useExport.ts添加
```
+//代理下载地址
+const PROXY_ENDPOINT = '/api/proxy'
+          if (isBase64Image(el.src)) {
+            options.data = el.src
+          } else {
+            // ★ 外链图片统一转 dataURL，走代理
+            options.data = await getSafeImageDataURL(el.src)
+          }
```

## 图表的渲染
```
核心文件
src/types/AIPPT.ts
src/hooks/useAIPPT.ts
src/views/components/element/ChartElement
处理逻辑：
src/types/AIPPT.ts中定义图表的类型 AIPPTContentChartItem， 支持 ECharts-like 的数据格式（labels 对应横轴或扇区，series 是多维数据集）。
export type AIPPTChartType = 'line' | 'bar' | 'pie'

src/hooks/useAIPPT.ts中的isChartItem判断返回的数据类型是否为AIPPTContentChartItem，然后进行渲染

模板匹配逻辑， AIPPTGenerator() 中，处理 item.type === 'content' 的部分
找到可用的模版
const _contentTemplates = getUseableContentTemplates(contentTemplates, items)

getNewChartElement 负责核心渲染
AIPPTContentChartItem → isChartItem → getNewChartElement → PPTChartElement → ChartRenderer
src/views/components/element/ChartElement， 内部真正渲染图表的部分交给 <Chart /> 子组件处理。src/views/components/element/ChartElement/Chart.vue中的echarts进行最终渲染。
```

## Bug修复，AI生成PPT时总是追加到最后
```
frontend/src/hooks/useAddSlidesOrElements.ts 中的函数addSlidesFromDataToEnd
frontend/src/store/slides.ts 中的addSlideToEnd
```


##  图表渲染中的文字部分进行渲染
```
src/hooks/useAIPPT.ts中的 AIPPTGenerator主要进行数据的解析，包括后端的大模型返回数据和模版的选择，根据选择的模版，对模版中的数据进行替换和显示。
contentTemplate代表模版， elements代表对后端返回的items数据进行解析后的html的数据。
contentTemplate是当前选择的模版，如何对这个模版进行解析，那么就是如下这个函数的操作逻辑
const elements = contentTemplate.elements.map(el => {
  if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
的里面打上断点，条件是 el.type === 'text'，即查看模版中的元素的类型是text时，如何进行更多的操作
如果后端传过来的items.length为1，可能是绘图的数据，那么就对绘图的中的text进行解析
          if (items.length === 1) {
            const only = items[0]
            if ((isTextItem(only) || isLegacyTextItem(only)) && checkTextType(el, 'content') && only.text) {
              return getNewTextElement({ el: el as any, text: only.text, maxLine: 6 })
            }
            // 如果只有1个元素，并且是图表，那么提取图表中的text作为显示的文本
            if (isChartItem(only) && checkTextType(el, 'content') && only.text) {
              return getNewTextElement({ el: el as any, text: only.text, maxLine: 6 })
            }
          }
yield { ...contentTemplate, id: nanoid(10), elements }

前端中的items的内容如下
```items = [
    {
        "kind": "chart",
        "title": "2025 上半年活跃用户",
        "text": "2025 上半年活跃用户text",
        "chartType": "line",
        "labels": [
            "1月",
            "2月",
            "3月",
            "4月",
            "5月",
            "6月"
        ],
        "series": [
            {
                "name": "iOS",
                "data": [
                    12,
                    15,
                    18,
                    22,
                    24,
                    27
                ]
            },
            {
                "name": "Android",
                "data": [
                    10,
                    13,
                    17,
                    20,
                    23,
                    25
                ]
            }
        ],
        "options": {
            "legend": {
                "top": 8
            },
            "xAxis": {
                "boundaryGap": false
            },
            "yAxis": {
                "name": "万"
            }
        }
    }
]```


## 所有的图表类型,全部是echarts支持的
| chartType | 图表中文名   | 数据要求                       | 特点      |
| --------- | ------- | -------------------------- | ------- |
| `line`    | 折线图     | 多序列，每序列为数值数组               | 可平滑、可堆叠 |
| `bar`     | 条形图（纵向） | `labels` 为类别，`series` 为数组  | y 轴为分类  |
| `column`  | 柱状图（横向） | 与 `bar` 相反                 | x 轴为分类  |
| `pie`     | 饼图      | 单序列，`labels` = 分类          | 比例展示    |
| `ring`    | 环形图     | 单序列，带 `radius` 环形效果        | 比例展示    |
| `area`    | 面积图     | 类似 `line`，但填充面积            | 趋势变化明显  |
| `radar`   | 雷达图     | `labels` 为维度，`series` 为数值组 | 对比维度表现  |
| `scatter` | 散点图     | 两个数列，分别为 X/Y 坐标            | 相关性分析   |

src/types/AIPPT.ts中的SUPPORTED_CHART_TYPES和AIPPTChartType
export type AIPPTChartType =
  | 'line' // 折线图
  | 'bar' // 条形图（纵向）
  | 'column' // 柱状图（横向）
  | 'pie' // 饼图
  | 'ring' // 环形图
  | 'area' // 面积图
  | 'radar' // 雷达图
  | 'scatter' // 散点图
```

# item中的插图的数据结构设计
```
image_data = {
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


title替换模版中的title
items中的title替换模版中的subtitle
items中的text替换模版中的textType为content的部分
items中的src替换模版中的itemFigure

模版
    {
      "id": "MS-hziVq3X",
      "elements": [
        {
          "type": "text",
          "id": "OfJpp013X8",
          "left": 217.7925625601871,
          "top": 29.49407353172103,
          "width": 504.15183867141155,
          "height": 56,
          "content": "<p style=\"\"><span style=\"font-size: 36px;\"><span style=\"color: #47acc5;\">模板内容页标题</span></span></p>",
          "rotate": 0,
          "defaultFontName": "",
          "defaultColor": "#333",
          "vertical": false,
          "lineHeight": 1,
          "paragraphSpace": 0,
          "textType": "title"
        },
        {
          "type": "shape",
          "id": "qQXSjy1cnf",
          "left": 179.1199646954184,
          "top": 38.157774599336676,
          "width": 38.67259786476868,
          "height": 38.67259786476868,
          "viewBox": [
            200,
            200
          ],
          "path": "M 100 0 L 120 80 L 200 100 L 120 120 L 100 200 L 80 120 L 0 100 L 80 80 L 100 0 Z",
          "fill": "#47acc5",
          "fixedRatio": true,
          "rotate": 0,
          "lock": false
        },
        {
          "type": "text",
          "id": "nPi7CBzUO2",
          "left": 179.1199646954184,
          "top": 154.96238702817647,
          "width": 619.3794604596253,
          "height": 68,
          "content": "<p style=\"\">内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项</p>",
          "rotate": 0,
          "defaultFontName": "",
          "defaultColor": "#333",
          "vertical": false,
          "textType": "content"
        },
        {
          "type": "line",
          "id": "VQ45FroEET",
          "left": 178.89434562661643,
          "top": 99.6496006669523,
          "start": [
            0,
            0
          ],
          "end": [
            540.4804270462632,
            0
          ],
          "points": [
            "",
            ""
          ],
          "color": "#47acc5",
          "style": "solid",
          "width": 2,
          "lock": false
        },
        {
          "type": "image",
          "id": "n8APEvRXX_",
          "src": "/api/data/free-photo-of-colorful-backstreet-in-istanbul-with-yellow-scooter.jpeg",
          "width": 506.32897622034153,
          "height": 238.22778331167066,
          "left": 209.2358396843033,
          "top": 256.01129718234984,
          "fixedRatio": true,
          "rotate": 0,
          "lock": false,
          "imageType": "itemFigure"
        },
        {
          "type": "line",
          "id": "5hD6paOWBq",
          "left": 526.2786365658366,
          "top": 383.19941800118625,
          "start": [
            0,
            154.21115065243185
          ],
          "end": [
            462.6334519572953,
            0
          ],
          "points": [
            "",
            ""
          ],
          "color": "#47acc5",
          "style": "solid",
          "width": 2,
          "broken": [
            462.6334519572953,
            154.21115065243185
          ],
          "lock": true
        },
        {
          "type": "line",
          "id": "ronrdh-Fxp",
          "left": 514.4366585112695,
          "top": 395.42361728944246,
          "start": [
            0,
            154.21115065243185
          ],
          "end": [
            462.6334519572953,
            0
          ],
          "points": [
            "",
            ""
          ],
          "color": "#47acc5",
          "style": "solid",
          "width": 2,
          "broken": [
            462.6334519572953,
            154.21115065243185
          ],
          "lock": true
        },
        {
          "type": "line",
          "id": "3YueFRgq_A",
          "left": 863.0319172597865,
          "top": 11.792537811387902,
          "start": [
            0,
            0
          ],
          "end": [
            126.03795966785276,
            53.38078291814942
          ],
          "points": [
            "",
            ""
          ],
          "color": "#47acc5",
          "style": "solid",
          "width": 2,
          "broken": [
            126.03795966785276,
            0
          ],
          "lock": true
        },
        {
          "type": "text",
          "id": "oaOUTPgT5p",
          "left": 198.45626362780274,
          "top": 104.96238702817648,
          "width": 514.1163025648884,
          "height": 50,
          "content": "<p style=\"text-align: center;\"><strong><span style=\"font-size: 20px;\">图像的标题</span></strong></p>",
          "rotate": 0,
          "defaultFontName": "",
          "defaultColor": "#333",
          "vertical": false,
          "textType": "subtitle"
        }
      ],
      "background": {
        "type": "solid",
        "color": "#fff"
      },
      "type": "content"
    },
```