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

export type ChartType = 'line' | 'bar' | 'pie'
export interface AIPPTContentChartItem {
  kind: 'chart'
  title?: string
  chartType: ChartType
  labels: string[]
  series: { name?: string; data: number[] }[]
  options?: Record<string, any>
  themeColors?: string[]
  textColor?: string
}
export interface AIPPTContentTextItem {
  kind: 'text'
  title: string
  text: string
}
export interface AIPPTLegacyTextItem {
  title: string
  text: string
}
export type AnyContentItem = AIPPTContentChartItem | AIPPTContentTextItem | AIPPTLegacyTextItem

export interface AIPPTContent extends AIPPTBaseSlide {
  type: 'content'
  data: {
    title: string
    items: AnyContentItem[]
  },
  offset?: number
}

export interface AIPPTReference extends AIPPTBaseSlide {
  type: 'reference'
  data: {
    title: string
    references: {
      number?: string|number
      pmid?: string
      url?: string
      doi?: string
    }[]
  },
  offset?: number
}

export interface AIPPTEnd extends AIPPTBaseSlide {
  type: 'end'
}

export type AIPPTSlide = AIPPTCover | AIPPTContents | AIPPTTransition | AIPPTContent | AIPPTReference | AIPPTEnd
