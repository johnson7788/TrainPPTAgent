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

export type AnyContentItem = AIPPTContentChartItem | AIPPTContentTextItem | AIPPTLegacyTextItem


// ==============================
// 👉 内容页：items 支持“文本项 + 图表项”
//    同时兼容旧结构 { title, text }（无 kind 字段）
// ==============================

/** 旧版（兼容）文本项：无 kind 字段 */
export interface AIPPTLegacyTextItem {
  title: string
  text: string
}

/** 新版文本项：显式带 kind 区分 */
export interface AIPPTContentTextItem {
  kind: 'text'
  title: string
  text: string
}

/** 仅支持的图表类型：折线图(line) / 柱状图(bar) / 饼图(pie) */
export type AIPPTChartType = 'line' | 'bar' | 'pie'

/** 图表序列（数据列） */
export interface AIPPTChartSeries {
  name?: string
  data: number[] // 必须与 labels.length 对齐
}

/** 新增：内容页里的图表项（仅支持 line/bar/pie） */
export interface AIPPTContentChartItem {
  kind: 'chart'
  /** 可选：图表主标题 */
  title?: string
  /** 折线图/柱状图/饼图 */
  chartType: AIPPTChartType
  /** 类目轴或饼图扇区标签 */
  labels: string[]
  /** 数据序列；饼图仅使用第一组 series */
  series: AIPPTChartSeries[]
  /** 透传到图表渲染层（如 EChartsOption 的增量配置） */
  options?: Record<string, any>
  /** 主题色与文字色（可选） */
  themeColors?: string[]
  textColor?: string
}

/** 内容页可包含的 item 联合类型（含兼容项） */
export type AIPPTContentItem =
  | AIPPTLegacyTextItem
  | AIPPTContentTextItem
  | AIPPTContentChartItem

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
      text: string
      number?: string | number
      pmid?: string
      url?: string
      doi?: string
    }[]
  }
  offset?: number
}

export interface AIPPTEnd extends AIPPTBaseSlide {
  type: 'end'
}

export type AIPPTSlide =
  | AIPPTCover
  | AIPPTContents
  | AIPPTTransition
  | AIPPTContent
  | AIPPTReference
  | AIPPTEnd

// ==============================
// 类型守卫 & 运行时校验辅助
// ==============================

export function isChartItem(
  item: AIPPTContentItem
): item is AIPPTContentChartItem {
  return (item as any).kind === 'chart'
}

export function isTextItem(
  item: AIPPTContentItem
): item is AIPPTContentTextItem {
  return (item as any).kind === 'text'
}

/** 兼容旧版：没有 kind 但具备 title/text 即视作旧文本项 */
export function isLegacyTextItem(
  item: AIPPTContentItem
): item is AIPPTLegacyTextItem {
  const anyItem = item as any
  return (
    anyItem &&
    anyItem.kind === undefined &&
    typeof anyItem.title === 'string' &&
    typeof anyItem.text === 'string'
  )
}

/** （可选）运行时校验：限制仅 line/bar/pie */
export const SUPPORTED_CHART_TYPES = ['line', 'bar', 'pie'] as const
export function isSupportedChartType(t: any): t is AIPPTChartType {
  return (SUPPORTED_CHART_TYPES as readonly string[]).includes(t)
}
