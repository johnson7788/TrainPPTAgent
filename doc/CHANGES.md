# 前端
## 前端添加独立的大纲页面，并修改样式
[Outline](../frontend/src/views/Outline)

## 前端添加PPT的模版选择页面，并修改样式
[PPT](../frontend/src/views/PPT)

## 前端修改后端API连接URL
[vite.config.ts](../frontend/vite.config.ts)

## PPT播放时全屏不能正常显示的问题
src/utils/fullscreen.ts
src/hooks/useScreening.ts

## 去掉加载默认的3页PPT
[App.vue](../frontend/src/App.vue)
onMounted(async () => {
  // const slides = await api.getFileData('slides')
  // slidesStore.setSlides(slides)

## 去掉大纲和模版选择页面不能下滑的问题
[global.scss](../frontend/src/assets/styles/global.scss) 去掉-  overflow: hidden;

## PPT的生成的页面先跳转，后逐页生成，使用Yield生成器
useAIPPT.ts

## PPT的loading状态组件
src/views/Editor/index.vue

## 在生成新的PPT前重置已有PPT内容
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

## 默认的第一页是空的
src/store/slides.ts
 │    160 + if (this.slides.length === 1 && this.slides[0].elements.length === 0) {                     │
 │    161 +   this.slides = slides                                                                      │
 │    162 +   this.slideIndex = 0                                                                       │
 │    163 +   return                                                                                    │
 │    164 + }                                                                                           │
 │    165 +

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
[slide_agent](../backend/slide_agent)
main_api.py