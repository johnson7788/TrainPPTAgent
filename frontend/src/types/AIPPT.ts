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