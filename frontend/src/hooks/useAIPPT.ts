import { ref } from 'vue'
import { nanoid } from 'nanoid'
import type {
  ImageClipDataRange,
  PPTElement,
  PPTImageElement,
  PPTShapeElement,
  PPTTextElement,
  PPTChartElement,
  Slide,
  TextType
} from '@/types/slides'
import type { AIPPTSlide, AnyContentItem, AIPPTContentChartItem, AIPPTContentTextItem, AIPPTLegacyTextItem } from '@/types/AIPPT'
import { useSlidesStore } from '@/store'
import useAddSlidesOrElements from './useAddSlidesOrElements'
import useSlideHandler from './useSlideHandler'


const isChartItem = (x: any): x is AIPPTContentChartItem =>
  x && x.kind === 'chart' && Array.isArray(x.labels) && Array.isArray(x.series)
const isTextItem = (x: any): x is AIPPTContentTextItem =>
  x && x.kind === 'text' && typeof x.title === 'string' && typeof x.text === 'string'
const isLegacyTextItem = (x: any): x is AIPPTLegacyTextItem =>
  x && x.kind === undefined && typeof x.title === 'string' && typeof x.text === 'string'

interface ImgPoolItem {
  id: string
  src: string
  width: number
  height: number
}

export default () => {
  const slidesStore = useSlidesStore()
  const { addSlidesFromData } = useAddSlidesOrElements()
  const { isEmptySlide } = useSlideHandler()

  // 图片池，用于存储可用的图片资源
  const imgPool = ref<ImgPoolItem[]>([])
  // 过渡页的索引，用于显示章节编号
  const transitionIndex = ref(0)
  // 过渡页模板，确保同一演示文稿中过渡页风格一致
  const transitionTemplate = ref<Slide | null>(null)

  const checkTextType = (el: PPTElement, type: TextType) => {
    return (el.type === 'text' && (el as PPTTextElement).textType === type)
      || (el.type === 'shape' && (el as PPTShapeElement).text && (el as PPTShapeElement).text!.type === type)
  }

  const checkChartItemMark = (el: PPTElement) => {
    return el.type === 'chart' && (el as any).chartMark === 'chartItem'
  }
  
  /**
   * 获取可用的模板
   * 根据需要的元素数量和类型，选择最合适的模板
   * @param templates 所有可用模板
   * @param n 需要的元素数量
   * @param type 元素的文本类型
   * @returns 合适的模板列表
   */
  const getUseableTemplates = (templates: Slide[], n: number, type: TextType) => {
    // 特殊处理：如果只需要1个元素，尝试使用只有标题和正文的模板
    if (n === 1) {
      const list = templates.filter(slide => {
        const items = slide.elements.filter(el => checkTextType(el, type))
        const titles = slide.elements.filter(el => checkTextType(el, 'title'))
        const texts = slide.elements.filter(el => checkTextType(el, 'content'))
  
        return !items.length && titles.length === 1 && texts.length === 1
      })
  
      if (list.length) return list
    }
  
    let target: Slide | null = null
  
    // 查找具有足够元素的模板
    const list = templates.filter(slide => {
      const len = slide.elements.filter(el => checkTextType(el, type)).length
      return len >= n
    })
    
    // 如果没有足够的模板，选择元素最多的模板
    if (list.length === 0) {
      const sorted = templates.sort((a, b) => {
        const aLen = a.elements.filter(el => checkTextType(el, type)).length
        const bLen = b.elements.filter(el => checkTextType(el, type)).length
        return aLen - bLen
      })
      target = sorted[sorted.length - 1]
    }
    else {
      // 选择最接近需求数量的模板
      target = list.reduce((closest, current) => {
        const currentLen = current.elements.filter(el => checkTextType(el, type)).length
        const closestLen = closest.elements.filter(el => checkTextType(el, type)).length
        return (currentLen - n) <= (closestLen - n) ? current : closest
      })
    }
  
    // 返回所有具有相同元素数量的模板
    return templates.filter(slide => {
      const len = slide.elements.filter(el => checkTextType(el, type)).length
      const targetLen = target!.elements.filter(el => checkTextType(el, type)).length
      return len === targetLen
    })
  }

  const countChartSlots = (slide: Slide) => {
    const marked = slide.elements.filter(el => el.type === 'chart' && (el as any).chartMark === 'chartItem').length
    if (marked > 0) return marked
    return slide.elements.filter(el => el.type === 'chart').length
  }

  const countTextItemSlots = (slide: Slide) =>
    slide.elements.filter(el => (el.type === 'text' && (el as any).textType === 'item') || (el.type === 'shape' && (el as any).text?.type === 'item')).length

  const getUseableContentTemplates = (templates: Slide[], items: AnyContentItem[]) => {
    const needChart = items.filter(isChartItem).length
    const needText = items.filter(it => isTextItem(it) || isLegacyTextItem(it)).length

    let candidates = templates.filter(slide => countChartSlots(slide) >= needChart && countTextItemSlots(slide) >= needText)

    if (candidates.length === 0) {
      if (needChart > 0) {
        candidates = templates
          .filter(slide => countChartSlots(slide) > 0)
          .sort((a, b) => (countChartSlots(b) - countChartSlots(a)) || (countTextItemSlots(b) - countTextItemSlots(a)))
      } else {
        return getUseableTemplates(templates, needText, 'item')
      }
    }

    const score = (slide: Slide) => {
      const cOverflow = Math.max(0, countChartSlots(slide) - needChart)
      const tOverflow = Math.max(0, countTextItemSlots(slide) - needText)
      return cOverflow * 100 + tOverflow
    }
    const bestScore = Math.min(...candidates.map(score))
    return candidates.filter(s => score(s) === bestScore)
  }

  const getAdaptedFontsize = ({
    text,
    fontSize,
    fontFamily,
    width,
    maxLine,
  }: {
    text: string
    fontSize: number
    fontFamily: string
    width: number
    maxLine: number
  }) => {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')!

    let newFontSize = fontSize
    const minFontSize = 10
  
    // 逐步减小字体大小，直到文本能在指定行数内显示
    while (newFontSize >= minFontSize) {
      context.font = `${newFontSize}px ${fontFamily}`
      const textWidth = context.measureText(text).width
      const line = Math.ceil(textWidth / width)
  
      if (line <= maxLine) return newFontSize
  
      const step = newFontSize <= 22 ? 1 : 2
      newFontSize = newFontSize - step
    }

    return minFontSize
  }
  
  /**
   * 从HTML字符串中提取字体信息
   * @param htmlString HTML格式的文本内容
   * @returns 字体大小和字体族信息
   */
  const getFontInfo = (htmlString: string) => {
    const fontSizeRegex = /font-size:\s*(\d+(?:\.\d+)?)\s*px/i
    const fontFamilyRegex = /font-family:\s*['"]?([^'";]+)['"]?\s*(?=;|>|$)/i

    const defaultInfo = {
      fontSize: 16,
      fontFamily: 'Microsoft Yahei',
    }

    const fontSizeMatch = htmlString.match(fontSizeRegex)
    const fontFamilyMatch = htmlString.match(fontFamilyRegex)

    return {
      fontSize: fontSizeMatch ? (+fontSizeMatch[1].trim()) : defaultInfo.fontSize,
      fontFamily: fontFamilyMatch ? fontFamilyMatch[1].trim() : defaultInfo.fontFamily,
    }
  }
  
  /**
   * 创建新的文本元素，自动调整字体大小以适应容器
   * @param params 包含元素、文本内容、最大行数等参数
   * @returns 更新后的文本元素
   */
  const getNewTextElement = ({
    el,
    text,
    maxLine,
    longestText,
    digitPadding,
  }: {
    el: PPTTextElement | PPTShapeElement
    text: string
    maxLine: number
    longestText?: string
    digitPadding?: boolean
  }): PPTTextElement | PPTShapeElement => {
    const padding = 10
    const width = el.width - padding * 2 - 2

    let content = el.type === 'text' ? el.content : el.text!.content
  
    // 获取原始字体信息
    const fontInfo = getFontInfo(content)
    
    // 计算适应的字体大小
    const size = getAdaptedFontsize({
      text: longestText || text,
      fontSize: fontInfo.fontSize,
      fontFamily: fontInfo.fontFamily,
      width,
      maxLine,
    })
  
    // 解析HTML内容并替换文本
    const parser = new DOMParser()
    const doc = parser.parseFromString(content, 'text/html')
  
    const treeWalker = document.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT)
  
    const firstTextNode = treeWalker.nextNode()
    if (firstTextNode) {
      // 数字补零处理（用于编号）
      if (digitPadding && firstTextNode.textContent && firstTextNode.textContent.length === 2 && text.length === 1) {
        firstTextNode.textContent = '0' + text
      }
      else firstTextNode.textContent = text
    }
  
    // 确保有字体大小设置
    if (doc.body.innerHTML.indexOf('font-size') === -1) {
      const p = doc.querySelector('p')
      if (p) p.style.fontSize = '16px'
    }
  
    // 更新所有字体大小
    content = doc.body.innerHTML.replace(/font-size:(.+?)px/g, `font-size: ${size}px`)

    return el.type === 'text'
      ? { ...el, content, lineHeight: size < 15 ? 1.2 : el.lineHeight }
      : { ...el, text: { ...el.text!, content } }
  }

  const getNewChartElement = (el: PPTChartElement, item: AIPPTContentChartItem): PPTChartElement => {
    const legends = item.series.map(s => s.name ?? '')
    const series = item.series.map(s => s.data)
    return {
      ...el,
      chartType: item.chartType,
      data: {
        labels: item.labels,
        series,
        legends,
      },
      options: { ...(el.options || {}), ...(item.options || {}) },
      themeColors: item.themeColors || el.themeColors,
      textColor: item.textColor || el.textColor,
    }
  }

  const getUseableImage = (el: PPTImageElement): ImgPoolItem | null => {
    let img: ImgPoolItem | null = null
  
    let imgs = []
  
    // 根据元素的宽高比选择合适的图片
    if (el.width === el.height) imgs = imgPool.value.filter(img => img.width === img.height)
    else if (el.width > el.height) imgs = imgPool.value.filter(img => img.width > img.height)
    else imgs = imgPool.value.filter(img => img.width <= img.height)
    if (!imgs.length) imgs = imgPool.value
  
    // 随机选择一张图片并从池中移除
    img = imgs[Math.floor(Math.random() * imgs.length)]
    imgPool.value = imgPool.value.filter(item => item.id !== img!.id)
  
    return img
  }
  
  /**
   * 创建新的图片元素，自动裁剪以适应容器
   * @param el 原始图片元素
   * @returns 更新后的图片元素
   */
  const getNewImgElement = (el: PPTImageElement): PPTImageElement => {
    const img = getUseableImage(el)
    if (!img) return el
  
    // 计算裁剪范围以保持宽高比
    let scale = 1
    let w = el.width
    let h = el.height
    let range: ImageClipDataRange = [[0, 0], [0, 0]]
    const radio = el.width / el.height

    if (img.width / img.height >= radio) {
      // 图片更宽，左右裁剪
      scale = img.height / el.height
      w = img.width / scale
      const diff = (w - el.width) / 2 / w * 100
      range = [[diff, 0], [100 - diff, 100]]
    }
    else {
      // 图片更高，上下裁剪
      scale = img.width / el.width
      h = img.height / scale
      const diff = (h - el.height) / 2 / h * 100
      range = [[0, diff], [100, 100 - diff]]
    }
    
    const clipShape = (el.clip && el.clip.shape) ? el.clip.shape : 'rect'
    const clip = { range, shape: clipShape }
    const src = img.src
  
    return { ...el, src, clip }
  }
  
  /**
   * 提取Markdown内容
   * @param content 原始内容
   * @returns 提取的Markdown内容
   */
  const getMdContent = (content: string) => {
    const regex = /```markdown([^```]*)```/
    const match = content.match(regex)
    if (match) return match[1].trim()
    return content.replace('```markdown', '').replace('```', '')
  }
  
  /**
   * 提取JSON内容
   * @param content 原始内容
   * @returns 提取的JSON内容
   */
  const getJSONContent = (content: string) => {
    const regex = /```json([^```]*)```/
    const match = content.match(regex)
    if (match) return match[1].trim()
    return content.replace('```json', '').replace('```', '')
  }

  /**
   * 预设图片池
   * @param imgs 图片列表
   */
  const presetImgPool = (imgs: ImgPoolItem[]) => {
    imgPool.value = imgs
  }

  /**
   * AI PPT生成器（生成器函数）
   * @param templateSlides 模板幻灯片
   * @param _AISlides AI生成的幻灯片数据
   * @param imgs 图片资源
   */
  function* AIPPTGenerator(templateSlides: Slide[], _AISlides: AIPPTSlide[], imgs?: ImgPoolItem[]) {
    if (imgs) imgPool.value = imgs

    const AISlides: AIPPTSlide[] = []
    
    // 预处理：根据内容数量进行分页
    for (const template of _AISlides) {
      if (template.type === 'content') {
        const items = (template.data.items as AnyContentItem[])
        if (items.length === 5 || items.length === 6) {
          // 5-6个项目：分成2页（3+剩余）
          const items1 = items.slice(0, 3)
          const items2 = items.slice(3)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 3 })
        }
        else if (items.length === 7 || items.length === 8) {
          // 7-8个项目：分成2页（4+剩余）
          const items1 = items.slice(0, 4)
          const items2 = items.slice(4)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 4 })
        }
        else if (items.length === 9 || items.length === 10) {
          // 9-10个项目：分成3页（3+3+剩余）
          const items1 = items.slice(0, 3)
          const items2 = items.slice(3, 6)
          const items3 = items.slice(6)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 3 })
          AISlides.push({ ...template, data: { ...template.data, items: items3 }, offset: 6 })
        }
        else if (items.length > 10) {
          // 超过10个项目：分成3页（4+4+剩余）
          const items1 = items.slice(0, 4)
          const items2 = items.slice(4, 8)
          const items3 = items.slice(8)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 4 })
          AISlides.push({ ...template, data: { ...template.data, items: items3 }, offset: 8 })
        }
        else {
          AISlides.push(template)
        }
      }
      else if (template.type === 'contents') {
        // 目录页分页逻辑：每页最多10个项目
        const items = template.data.items
        if (items.length === 11) {
          // 11个项目：分成2页（6+5）
          const items1 = items.slice(0, 6)
          const items2 = items.slice(6)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 6 })
        }
        else if (items.length > 11) {
          // 超过11个项目：分成2页（10+剩余）
          const items1 = items.slice(0, 10)
          const items2 = items.slice(10)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 10 })
        }
        else {
          AISlides.push(template)
        }
      }
      else if (template.type === 'reference') {
        // 引用页分页逻辑：每页5-10个引用
        const references = template.data.references
        const totalCount = references.length
        
        if (totalCount <= 10) {
          // 10个及以下：一页显示
          AISlides.push(template)
        }
        else if (totalCount <= 20) {
          // 11-20个：分成2页，尽量平均分配
          const perPage = Math.ceil(totalCount / 2)
          const refs1 = references.slice(0, perPage)
          const refs2 = references.slice(perPage)
          AISlides.push({ ...template, data: { ...template.data, references: refs1 } })
          AISlides.push({ ...template, data: { ...template.data, references: refs2 }, offset: perPage })
        }
        else if (totalCount <= 30) {
          // 21-30个：分成3页，每页最多10个
          const refs1 = references.slice(0, 10)
          const refs2 = references.slice(10, 20)
          const refs3 = references.slice(20)
          AISlides.push({ ...template, data: { ...template.data, references: refs1 } })
          AISlides.push({ ...template, data: { ...template.data, references: refs2 }, offset: 10 })
          AISlides.push({ ...template, data: { ...template.data, references: refs3 }, offset: 20 })
        }
        else {
          // 超过30个：每页10个
          let offset = 0
          while (offset < totalCount) {
            const pageRefs = references.slice(offset, offset + 10)
            AISlides.push({
              ...template,
              data: { ...template.data, references: pageRefs },
              offset: offset
            })
            offset += 10
          }
        }
      }
      else AISlides.push(template)
    }

    // 按类型分类模板
    const coverTemplates = templateSlides.filter(slide => slide.type === 'cover')
    const contentsTemplates = templateSlides.filter(slide => slide.type === 'contents')
    const transitionTemplates = templateSlides.filter(slide => slide.type === 'transition')
    const contentTemplates = templateSlides.filter(slide => slide.type === 'content')
    const referenceTemplates = templateSlides.filter(slide => slide.type === 'reference')
    const endTemplates = templateSlides.filter(slide => slide.type === 'end')
    
    // 初始化过渡页模板（确保风格一致）
    if (!transitionTemplate.value) {
      const _transitionTemplate = transitionTemplates[Math.floor(Math.random() * transitionTemplates.length)]
      transitionTemplate.value = _transitionTemplate
    }
    
    // 处理每个AI幻灯片
    for (const item of AISlides) {
      // 封面页处理
      if (item.type === 'cover') {
        const coverTemplate = coverTemplates[Math.floor(Math.random() * coverTemplates.length)]
        const elements = coverTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el
          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }
          if (checkTextType(el, 'content') && item.data.text) {
            return getNewTextElement({ el: el as any, text: item.data.text, maxLine: 3 })
          }
          return el
        })
        yield { ...coverTemplate, id: nanoid(10), elements }
      }
      // 目录页处理
      else if (item.type === 'contents') {
        const _contentsTemplates = getUseableTemplates(contentsTemplates, item.data.items.length, 'item')
        const contentsTemplate = _contentsTemplates[Math.floor(Math.random() * _contentsTemplates.length)]

        // 对编号元素进行排序
        const sortedNumberItems = contentsTemplate.elements.filter(el => checkTextType(el, 'itemNumber'))
        const sortedNumberItemIds = sortedNumberItems.sort((a, b) => {
          // 如果元素较多，尝试从内容中提取编号进行排序
          if (sortedNumberItems.length > 6) {
            let aContent = '', bContent = ''
            if (a.type === 'text') aContent = (a as PPTTextElement).content
            if (a.type === 'shape') aContent = (a as PPTShapeElement).text!.content
            if (b.type === 'text') bContent = (b as PPTTextElement).content
            if (b.type === 'shape') bContent = (b as PPTShapeElement).text!.content
            if (aContent && bContent) {
              const aIndex = parseInt(aContent)
              const bIndex = parseInt(bContent)

              return aIndex - bIndex
            }
          }
          // 默认按位置排序（从左到右，从上到下）
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        // 对项目元素进行排序
        const sortedItems = contentsTemplate.elements.filter(el => checkTextType(el, 'item'))
        const sortedItemIds = sortedItems.sort((a, b) => {
          // 如果有编号元素，按编号元素的顺序排序
          if (sortedItems.length > 6) {
            const aItemNumber = sortedNumberItems.find(item => item.groupId === a.groupId)
            const bItemNumber = sortedNumberItems.find(item => item.groupId === b.groupId)

            if (aItemNumber && bItemNumber) {
              let aContent = '', bContent = ''
              if (aItemNumber.type === 'text') aContent = (aItemNumber as PPTTextElement).content
              if (aItemNumber.type === 'shape') aContent = (aItemNumber as PPTShapeElement).text!.content
              if (bItemNumber.type === 'text') bContent = (bItemNumber as PPTTextElement).content
              if (bItemNumber.type === 'shape') bContent = (bItemNumber as PPTShapeElement).text!.content
              if (aContent && bContent) {
                const aIndex = parseInt(aContent)
                const bIndex = parseInt(bContent)
  
                return aIndex - bIndex
              }
            }
          }
          // 默认按位置排序
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        // 找出最长的文本用于字体大小计算
        const longestText = item.data.items.reduce((longest, current) => current.length > longest.length ? current : longest, '')

        const unusedElIds: string[] = []
        const unusedGroupIds: string[] = []

        const elements = contentsTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el

          if (checkTextType(el, 'item')) {
            const index = sortedItemIds.findIndex(id => id === el.id)
            const itemTitle = item.data.items[index]
            if (itemTitle) return getNewTextElement({ el: el as any, text: itemTitle, maxLine: 1, longestText })

            // 标记未使用的元素
            unusedElIds.push(el.id)
            if (el.groupId) unusedGroupIds.push(el.groupId!)
          }

          if (checkTextType(el, 'itemNumber')) {
            const index = sortedNumberItemIds.findIndex(id => id === el.id)
            const offset = item.offset || 0
            return getNewTextElement({ el: el as any, text: index + offset + 1 + '', maxLine: 1, digitPadding: true })
          }
          return el
        }).filter(el => !unusedElIds.includes(el.id) && !(el.groupId && unusedGroupIds.includes(el.groupId)))

        yield { ...contentsTemplate, id: nanoid(10), elements }
      }
      // 过渡页处理
      else if (item.type === 'transition') {
        transitionIndex.value = transitionIndex.value + 1
        const elements = transitionTemplate.value!.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el
          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }
          if (checkTextType(el, 'content') && item.data.text) {
            return getNewTextElement({ el: el as any, text: item.data.text, maxLine: 3 })
          }
          if (checkTextType(el, 'partNumber')) {
            return getNewTextElement({ el: el as any, text: transitionIndex.value + '', maxLine: 1, digitPadding: true })
          }
          return el
        })
        yield { ...transitionTemplate.value!, id: nanoid(10), elements }
      }
      else if (item.type === 'content') {
        const items = item.data.items as AnyContentItem[]
        const _contentTemplates = getUseableContentTemplates(contentTemplates, items)
        const contentTemplate = _contentTemplates[Math.floor(Math.random() * _contentTemplates.length)]

        const sortedTitleItemIds = contentTemplate.elements
          .filter(el => checkTextType(el, 'itemTitle'))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)

        const sortedTextItemIds = contentTemplate.elements
          .filter(el => checkTextType(el, 'item'))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)

        let sortedChartItemIds = contentTemplate.elements
          .filter(el => checkChartItemMark(el))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)
        if (sortedChartItemIds.length === 0) {
          sortedChartItemIds = contentTemplate.elements
            .filter(el => el.type === 'chart')
            .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
            .map(el => el.id)
        }

        const sortedNumberItemIds = contentTemplate.elements
          .filter(el => checkTextType(el, 'itemNumber'))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)

        const textTitleList: string[] = []
        const textBodyList: string[] = []
        items.forEach(_it => {
          if (isTextItem(_it) || isLegacyTextItem(_it)) {
            if (_it.title) textTitleList.push(_it.title)
            if (_it.text) textBodyList.push(_it.text)
          }
        })
        const longestTitle = textTitleList.reduce((longest, current) => current.length > longest.length ? current : longest, '')
        const longestText  = textBodyList.reduce((longest, current) => current.length > longest.length ? current : longest, '')

        const chartItems = items.filter(isChartItem) as AIPPTContentChartItem[]

        const elements = contentTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)

          if (el.type === 'chart') {
            const idx = sortedChartItemIds.findIndex(id => id === el.id)
            const chartItem = chartItems[idx]
            if (chartItem) return getNewChartElement(el as PPTChartElement, chartItem)
            return el
          }

          if (el.type !== 'text' && el.type !== 'shape') return el

          if (items.length === 1) {
            const only = items[0]
            if ((isTextItem(only) || isLegacyTextItem(only)) && checkTextType(el, 'content') && only.text) {
              return getNewTextElement({ el: el as any, text: only.text, maxLine: 6 })
            }
          }
          else {
            // 处理项目标题
            if (checkTextType(el, 'itemTitle')) {
              const index = sortedTitleItemIds.findIndex(id => id === el.id)
              const contentItem = items[index]
              if (contentItem) {
                if (isTextItem(contentItem) && contentItem.title) {
                  return getNewTextElement({ el: el as any, text: contentItem.title, longestText: longestTitle, maxLine: 1 })
                }
                if (isLegacyTextItem(contentItem) && contentItem.title) {
                  return getNewTextElement({ el: el as any, text: contentItem.title, longestText: longestTitle, maxLine: 1 })
                }
                if (isChartItem(contentItem) && contentItem.title) {
                  return getNewTextElement({ el: el as any, text: contentItem.title, longestText: longestTitle || contentItem.title, maxLine: 1 })
                }
              }
            }

            if (checkTextType(el, 'item')) {
              const index = sortedTextItemIds.findIndex(id => id === el.id)
              const contentItem = items[index]
              if (contentItem) {
                if (isTextItem(contentItem) && contentItem.text) {
                  return getNewTextElement({ el: el as any, text: contentItem.text, longestText, maxLine: 4 })
                }
                if (isLegacyTextItem(contentItem) && contentItem.text) {
                  return getNewTextElement({ el: el as any, text: contentItem.text, longestText, maxLine: 4 })
                }
              }
            }

            if (checkTextType(el, 'itemNumber')) {
              const index = sortedNumberItemIds.findIndex(id => id === el.id)
              const offset = item.offset || 0
              return getNewTextElement({ el: el as any, text: index + offset + 1 + '', maxLine: 1, digitPadding: true })
            }
          }
          // 处理页面标题
          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }
          return el
        })

        yield { ...contentTemplate, id: nanoid(10), elements }
      }
      else if (item.type === 'reference') {
        const referenceCount = item.data.references.length
        let _referenceTemplates: Slide[] = []

        _referenceTemplates = referenceTemplates.filter(slide => {
          const refNumberCount = slide.elements.filter(el => checkTextType(el, 'referenceNumber')).length
          // 选择引用位置数量在需求数量到10个之间的模板
          return refNumberCount >= referenceCount && refNumberCount <= 10
        })
        
        // 如果没有完全匹配的模板，使用通用方法选择
        if (_referenceTemplates.length === 0) {
          _referenceTemplates = getUseableTemplates(referenceTemplates, referenceCount, 'referenceNumber')
        }
        
        const referenceTemplate = _referenceTemplates[Math.floor(Math.random() * _referenceTemplates.length)]

        // 对各种引用元素进行排序（按位置从左到右、从上到下）
        const sortedRefNumberIds = referenceTemplate.elements.filter(el => checkTextType(el, 'referenceNumber')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const sortedPmidIds = referenceTemplate.elements.filter(el => checkTextType(el, 'pmid')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const sortedUrlIds = referenceTemplate.elements.filter(el => checkTextType(el, 'url')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const sortedDoiIds = referenceTemplate.elements.filter(el => checkTextType(el, 'doi')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const unusedElIds: string[] = []
        const unusedGroupIds: string[] = []

        const elements = referenceTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el

          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }

          // 处理引用编号
          if (checkTextType(el, 'referenceNumber')) {
            const index = sortedRefNumberIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference) {
              let number = ''
              if (reference.number !== undefined) {
                // 使用自定义编号
                const offset = item.offset || 0
                number = typeof reference.number === 'number'
                  ? (reference.number + offset).toString()
                  : reference.number
              }
              else {
                // 自动生成编号
                const offset = item.offset || 0
                number = (index + offset + 1).toString()
              }
              return getNewTextElement({ el: el as any, text: `[${number}]`, maxLine: 1 })
            }
            else {
              // 没有对应的引用数据，标记为未使用
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          // 处理PMID
          if (checkTextType(el, 'pmid')) {
            const index = sortedPmidIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference && reference.pmid) {
              return getNewTextElement({ el: el as any, text: `PMID: ${reference.pmid}`, maxLine: 1 })
            }
            else {
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          // 处理URL
          if (checkTextType(el, 'url')) {
            const index = sortedUrlIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference && reference.url) {
              return getNewTextElement({ el: el as any, text: reference.url, maxLine: 2 })
            }
            else {
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          // 处理DOI
          if (checkTextType(el, 'doi')) {
            const index = sortedDoiIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference && reference.doi) {
              return getNewTextElement({ el: el as any, text: `DOI: ${reference.doi}`, maxLine: 1 })
            }
            else {
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          return el
        }).filter(el => !unusedElIds.includes(el.id) && !(el.groupId && unusedGroupIds.includes(el.groupId)))

        yield { ...referenceTemplate, id: nanoid(10), elements }
      }
      // 结束页处理
      else if (item.type === 'end') {
        const endTemplate = endTemplates[Math.floor(Math.random() * endTemplates.length)]
        const elements = endTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          return el
        })
        yield { ...endTemplate, id: nanoid(10), elements }
      }
    }
  }

  /**
   * 生成AI PPT
   * @param templateSlides 模板幻灯片
   * @param _AISlides AI生成的幻灯片数据
   * @param imgs 图片资源
   */
  const AIPPT = (templateSlides: Slide[], _AISlides: AIPPTSlide[], imgs?: ImgPoolItem[]) => {
    // 定位到最后一页
    slidesStore.updateSlideIndex(slidesStore.slides.length - 1)
    
    // 生成所有幻灯片
    const slides = [...AIPPTGenerator(templateSlides, _AISlides, imgs)]
    
    // 根据当前是否为空演示文稿决定是替换还是追加
    if (isEmptySlide.value) slidesStore.setSlides(slides)
    else addSlidesFromData(slides)
  }

  return {
    presetImgPool,
    AIPPT,
    getMdContent,
    getJSONContent,
    AIPPTGenerator,
  }
}
