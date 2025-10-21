import axios from './config'

// export const SERVER_URL = 'http://localhost:5000'
export const SERVER_URL = '/api'

interface AIPPTOutlinePayload {
  content: string
  language: string
  model: string
}

interface AIPPTPayload {
  content: string
  language: string
  style?: string
  model?: string
  generateFromUploadedFile?: boolean
  generateFromWebSearch?: boolean
  sessionId?: string
}

interface AIWritingPayload {
  content: string
  command: string
}

interface AIByIDPayload {
  id: string|number
  language?: string
}


export default {
  getMockData(filename: string): Promise<any> {
    return axios.get(`./mocks/${filename}.json`)
  },

  getFileData(filename: string): Promise<any> {
    return axios.get(`${SERVER_URL}/data/${filename}.json`)
  },

  getTemplates(): Promise<any> {
    return axios.get(`${SERVER_URL}/templates`)
  },

  AIPPT_Outline({
    content,
    language,
    model,
  }: AIPPTOutlinePayload): Promise<any> {
    return fetch(`${SERVER_URL}/tools/aippt_outline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content,
        language,
        model,
        stream: true,
      }),
    })
  },

  AIPPT_Content({
    content,
    language,
    style,
    model,
    generateFromUploadedFile,
    generateFromWebSearch,
    sessionId,
  }: AIPPTPayload): Promise<any> {
    return fetch(`${SERVER_URL}/tools/aippt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content,
        language,
        model,
        style,
        stream: true,
        generateFromUploadedFile,
        generateFromWebSearch,
        sessionId,
      }),
    })
  },

  AIPPTByID({
    id,
    language,
  }: AIByIDPayload): Promise<any> {
    return fetch(`${SERVER_URL}/tools/aippt_by_id`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id,
        language,
      }),
    })
  },

  AI_Writing({
    content,
    command,
  }: AIWritingPayload): Promise<any> {
    return fetch(`${SERVER_URL}/tools/ai_writing`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content,
        command,
        stream: true,
      }),
    })
  },

  AIPPT_Outline_From_File(file: File, user_id: string, language: string): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', user_id)
    formData.append('language', language)
    return fetch(`${SERVER_URL}/tools/aippt_outline_from_file`, {
      method: 'POST',
      body: formData,
    })
  },
}