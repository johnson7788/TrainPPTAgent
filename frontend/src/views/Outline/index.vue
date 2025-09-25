<template>
  <div class="aippt-page">
    <!-- 全局背景：渐变 + 网格 -->
    <div class="page-bg" aria-hidden="true">
      <div class="tech-grid"></div>
      <div class="float-sphere s1"></div>
      <div class="float-sphere s2"></div>
      <div class="float-sphere s3"></div>
    </div>

    <div class="aippt-dialog">
      <div class="header-section">
        <button class="template-btn" @click="goToEditor">
          <span class="btn-inner">制作模板</span>
        </button>
        
        <div class="brand">
          <h1 class="title">
            <span class="title-main">PPTAgent</span>
            <span class="title-badge">AI</span>
          </h1>
          <div class="subtitle">
            {{ step === 'outline' ? '智能大纲已生成 · 选择模板开始创作' : 'AI驱动的演示文稿生成系统' }}
          </div>
        </div>

        <div class="progress-flow">
          <div class="flow-item" :class="{ active: step === 'setup' }">
            <div class="flow-dot"></div>
            <span class="flow-text">INPUT</span>
          </div>
          <div class="flow-connector" :class="{ active: step === 'outline' }"></div>
          <div class="flow-item" :class="{ active: step === 'outline' }">
            <div class="flow-dot"></div>
            <span class="flow-text">PROCESS</span>
          </div>
        </div>
      </div>

      <div v-if="step === 'setup'" class="setup-section">
        <div class="input-module">
          <div class="input-field">
            <textarea
              ref="inputRef"
              v-model="keyword"
              class="text-input"
              placeholder="输入演示主题或粘贴文档内容..."
              rows="6"
            ></textarea>
            <div class="input-actions">
              <span class="character-count">{{ keyword.length }}/10000</span>
              <div class="buttons-wrapper">
                <button class="generate-btn" @click="createOutline" :disabled="!keyword.trim() || showProcessingModal">
                  <span class="btn-icon">✨</span>
                  {{ showProcessingModal ? '生成中...' : 'AI 生成' }}
                </button>
                <input
                  type="file"
                  ref="fileInputRef"
                  style="display: none"
                  @change="handleFileChange"
                />
                <button class="generate-btn" @click="triggerFileUpload" :disabled="showProcessingModal">
                  <span class="btn-icon">📄</span>
                  依据文件撰写
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="bubble-section">
          <div class="section-title">
            <span class="title-text">快速选择</span>
          </div>
          <div class="bubble-container">
            <div class="bubble-track">
              <div class="bubble-list">
                <button
                  v-for="(item, index) in [...recommends, ...recommends]"
                  :key="`${index}-1`"
                  class="bubble-item"
                  @click="setKeyword(recommends[index % recommends.length])"
                >
                  {{ item }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="config-module">
          <div class="section-title">
            <span class="title-text">参数配置</span>
          </div>
          <div class="config-grid">
            <div class="config-item">
              <label class="config-label">语言</label>
              <select v-model="language" class="config-select">
                <option value="中文">中文</option>
                <option value="English">English</option>
                <option value="日本語">日本語</option>
              </select>
            </div>
            <div class="config-item">
              <label class="config-label">AI模型</label>
              <select v-model="model" class="config-select">
                <option value="GLM-4.5-Air">GLM-4.5-Air</option>
                <option value="GLM-4.5-Flash">GLM-4.5-Flash</option>
                <option value="ark-doubao-seed-1.6-flash">Doubao-Seed-1.6-flash</option>
                <option value="ark-doubao-seed-1.6">Doubao-Seed-1.6</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div v-if="step === 'outline'" class="outline-section">
        <div class="outline-header">
          <div class="section-title">
            <span class="title-text">内容大纲</span>
          </div>
          <div class="hint-text">可编辑内容 · 右键管理节点</div>
        </div>

        <div class="outline-container">
          <div v-if="outlineCreating" class="generating-view">
            <div class="gen-indicator">
              <div class="gen-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span class="gen-text">AI正在生成</span>
            </div>
            <pre ref="outlineRef" class="outline-display">{{ outline }}</pre>
          </div>
          <div v-else class="editor-view">
            <OutlineEditor v-model:value="outline" />
          </div>
        </div>

        <div v-if="!outlineCreating" class="action-group">
          <button class="act-btn secondary" @click="resetToSetup">
            重新生成
          </button>
          <button class="act-btn primary" @click="goPPT">
            创建PPT
          </button>
        </div>
      </div>
    </div>
        <!-- Processing Modal -->
    <div v-if="showProcessingModal" class="processing-modal-overlay">
      <div class="processing-modal">
        <div class="processing-content">
          <div class="processing-spinner"></div>
          <div class="processing-text">正在处理中，请稍候...</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services'
import useAIPPT from '@/hooks/useAIPPT'
import message from '@/utils/message'
import FullscreenSpin from '@/components/FullscreenSpin.vue'
import OutlineEditor from '@/components/OutlineEditor.vue'
import { useMainStore } from '@/store/main'

const router = useRouter()
const { getMdContent } = useAIPPT()
const mainStore = useMainStore()

const language = ref('中文')
const keyword = ref('')
const outline = ref('')
const loading = ref(false)
const outlineCreating = ref(false)
const step = ref<'setup' | 'outline'>('setup')
const model = ref('GLM-4.5-Air')
const outlineRef = ref<HTMLElement>()
const inputRef = ref<HTMLTextAreaElement>()
const fileInputRef = ref<HTMLInputElement>()
const showProcessingModal = ref(false)

const recommends = ref([
  '2025科技前沿动态',
  '大数据如何改变世界',
  '餐饮市场调查与研究',
  'AIGC在教育领域的应用',
  '社交媒体与品牌营销',
  '5G技术如何改变我们的生活',
  '年度工作总结与展望',
  '区块链技术及其应用',
  '大学生职业生涯规划',
  '公司年会策划方案',
])

onMounted(() => {
  setTimeout(() => {
    inputRef.value?.focus()
  }, 500)
})

const setKeyword = (value: string) => {
  keyword.value = value
  inputRef.value?.focus()
}

const resetToSetup = () => {
  outline.value = ''
  step.value = 'setup'
  mainStore.setOutlineFromFile(false)
  setTimeout(() => {
    inputRef.value?.focus()
  }, 100)
}

const goToEditor = () => {
  router.push('/editor')
}

const createOutline = async () => {
  if (!keyword.value.trim()) {
    message.error('请先输入PPT主题')
    return
  }
  mainStore.setOutlineFromFile(false)

  loading.value = true
  outlineCreating.value = true
  //进度蒙版
  showProcessingModal.value = true

  try {
    const stream = await api.AIPPT_Outline({
      content: keyword.value,
      language: language.value,
      model: model.value,
    })

    loading.value = false
    step.value = 'outline'
    showProcessingModal.value = false

    const reader: ReadableStreamDefaultReader = stream.body.getReader()
    const decoder = new TextDecoder('utf-8')

    const readStream = () => {
      reader.read().then(({ done, value }) => {
        if (done) {
          outline.value = getMdContent(outline.value)
          outline.value = outline.value.replace(/<!--[\s\S]*?-->/g, '').replace(/<think>[\s\S]*?<\/think>/g, '')
          outlineCreating.value = false
          return
        }

        const chunk = decoder.decode(value, { stream: true })
        outline.value += chunk

        if (outlineRef.value) {
          outlineRef.value.scrollTop = outlineRef.value.scrollHeight + 20
        }

        readStream()
      })
    }
    readStream()
  } catch (error) {
    loading.value = false
    outlineCreating.value = false
    showProcessingModal.value = false
    message.error('生成失败，请重试')
  }
}

const goPPT = () => {
  router.push({
    name: 'PPT',
    query: {
      outline: outline.value,
      language: language.value,
      model: model.value,
    }
  })
}

const triggerFileUpload = () => {
  fileInputRef.value?.click()
}

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const file = input.files[0]
    uploadWordAndCreateOutline(file)
  }
}

const uploadWordAndCreateOutline = async (file: File) => {
  mainStore.setOutlineFromFile(true)
  loading.value = true
  outlineCreating.value = true
  showProcessingModal.value = true

  try {
    const stream = await api.AIPPT_Outline_From_File(file, mainStore.sessionId)

    loading.value = false
    step.value = 'outline'
    showProcessingModal.value = false

    const reader: ReadableStreamDefaultReader = stream.body.getReader()
    const decoder = new TextDecoder('utf-8')

    const readStream = () => {
      reader.read().then(({ done, value }) => {
        if (done) {
          outline.value = getMdContent(outline.value)
          outline.value = outline.value.replace(/<!--[\s\S]*?-->/g, '').replace(/<think>[\s\S]*?<\/think>/g, '')
          outlineCreating.value = false
          return
        }

        const chunk = decoder.decode(value, { stream: true })
        outline.value += chunk

        if (outlineRef.value) {
          outlineRef.value.scrollTop = outlineRef.value.scrollHeight + 20
        }

        readStream()
      })
    }
    readStream()
  } catch (error) {
    loading.value = false
    outlineCreating.value = false
    showProcessingModal.value = false
    message.error('生成失败，请重试')
  }
}
</script>

<style lang="scss" scoped>
/* 与大纲页保持同样的页面骨架与背景 */
  /* 页面容器，提供稳定的全屏背景承载 */
.aippt-page {
  position: relative;
  min-height: 100dvh;
  background: linear-gradient(135deg, #f6f9fc 0%, #ffffff 100%);
  overflow: hidden;
}

.page-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  
  .tech-grid {
    position: absolute;
    inset: 0;
    background-image: 
      linear-gradient(rgba(99, 102, 241, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  .float-sphere {
    position: absolute;
    border-radius: 50%;
    
    &.s1 {
      width: 400px;
      height: 400px;
      background: radial-gradient(circle at 30% 30%, rgba(99, 102, 241, 0.15), transparent 70%);
      top: -100px;
      left: -100px;
      animation: float1 20s ease-in-out infinite;
    }
    
    &.s2 {
      width: 300px;
      height: 300px;
      background: radial-gradient(circle at 70% 70%, rgba(168, 85, 247, 0.12), transparent 70%);
      bottom: -50px;
      right: -50px;
      animation: float2 15s ease-in-out infinite;
    }
    
    &.s3 {
      width: 250px;
      height: 250px;
      background: radial-gradient(circle at 50% 50%, rgba(236, 72, 153, 0.1), transparent 70%);
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      animation: float3 25s ease-in-out infinite;
    }
  }
}

@keyframes float1 {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  33% { transform: translate(30px, -30px) rotate(120deg); }
  66% { transform: translate(-20px, 20px) rotate(240deg); }
}

@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-30px, -30px); }
}

@keyframes float3 {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.1); }
}

.aippt-dialog {
  position: relative;
  z-index: 1;
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 20px;
}

.header-section {
  text-align: center;
  margin-bottom: 50px;
  position: relative;

  .template-btn {
    position: absolute;
    top: 0;
    right: 0;
    background: linear-gradient(135deg, #667eea 0%, #a855f7 100%);
    color: white;
    border: none;
    padding: 12px 28px;
    border-radius: 100px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
  }

  .brand {
    margin-bottom: 35px;
    
    .title {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      margin: 0 0 12px 0;
      
      .title-main {
        font-size: 42px;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
      }
      
      .title-badge {
        background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
      }
    }
    
    .subtitle {
      color: #64748b;
      font-size: 15px;
    }
  }

  .progress-flow {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    
    .flow-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      
      .flow-dot {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #e2e8f0;
        transition: all 0.5s;
      }
      
      .flow-text {
        font-size: 11px;
        color: #94a3b8;
        letter-spacing: 1.5px;
        font-weight: 500;
      }
      
      &.active {
        .flow-dot {
          background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
          box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2);
        }
        
        .flow-text {
          color: #6366f1;
        }
      }
    }
    
    .flow-connector {
      width: 80px;
      height: 2px;
      background: #e2e8f0;
      margin: 0 -8px;
      margin-bottom: 24px;
      transition: all 0.5s;
      
      &.active {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);
      }
    }
  }
}

.setup-section {
  .input-module {
    background: white;
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
    margin-bottom: 32px;
    
    .input-field {
      .text-input {
        width: 100%;
        font-size: 16px;
        padding: 12px 16px;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        outline: none;
        transition: all 0.3s;
        background: transparent;
        resize: vertical;
        min-height: 140px;
        
        &::placeholder {
          color: #cbd5e1;
        }
        
        &:focus {
          border-color: #6366f1;
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
      }

      .input-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 1.5rem 1.25rem;
      gap: 1rem;

      .character-count {
        font-size: 0.875rem;
        color: #64748b;
      }

      .buttons-wrapper {
        display: flex;
        gap: 1rem;
      }

      .generate-btn {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 0.75rem;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        transition: all 0.3s ease;
        font-size: 0.95rem;

        &:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        &:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-icon {
          font-size: 1.1rem;
        }
      }
    }
      
      .input-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 20px;
        
        .counter {
          color: #94a3b8;
          font-size: 13px;
        }
        
        .submit-btn {
          background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
          color: white;
          border: none;
          padding: 12px 32px;
          border-radius: 100px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.3s;
          
          &:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
          }
          
          &:disabled {
            opacity: 0.4;
            cursor: not-allowed;
          }
        }
      }
    }
  }

  .bubble-section {
    margin-bottom: 32px;
    
    .bubble-container {
      margin-top: 16px;
      overflow: hidden;
      position: relative;
      
      &::before,
      &::after {
        content: '';
        position: absolute;
        top: 0;
        bottom: 0;
        width: 60px;
        z-index: 2;
        pointer-events: none;
      }
      
      &::before {
        left: 0;
        background: linear-gradient(90deg, #f6f9fc, transparent);
      }
      
      &::after {
        right: 0;
        background: linear-gradient(90deg, transparent, #f6f9fc);
      }
      
      .bubble-track {
        overflow: hidden;
        padding: 8px 0;
        
        .bubble-list {
          display: flex;
          gap: 12px;
          animation: scrollBubbles 30s linear infinite;
          
          .bubble-item {
            flex-shrink: 0;
            background: white;
            border: 2px solid #e2e8f0;
            padding: 10px 20px;
            border-radius: 100px;
            color: #475569;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            white-space: nowrap;
            
            &:hover {
              background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
              color: white;
              border-color: transparent;
              transform: scale(1.05);
            }
          }
        }
      }
    }
  }

  .config-module {
    background: white;
    border-radius: 20px;
    padding: 28px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
    
    .config-grid {
      display: grid;
      grid-template-columns: 1fr 2fr;
      gap: 20px;
      margin-top: 20px;
      
      .config-item {
        .config-label {
          display: block;
          font-size: 13px;
          color: #64748b;
          margin-bottom: 8px;
          font-weight: 500;
        }
        
        .config-select {
          width: 100%;
          padding: 10px 16px;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          background: white;
          outline: none;
          transition: all 0.3s;
          color: #334155;
          cursor: pointer;
          
          &:focus {
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
          }
        }
      }
    }
  }
}

.section-title {
  margin-bottom: 16px;
  
  .title-text {
    font-size: 14px;
    font-weight: 600;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
}

.outline-section {
  background: white;
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
  
  .outline-header {
    margin-bottom: 24px;
    
    .hint-text {
      color: #94a3b8;
      font-size: 13px;
      margin-top: 8px;
    }
  }

  .outline-container {
    background: #f8fafc;
    border-radius: 16px;
    padding: 24px;
    min-height: 400px;
    margin-bottom: 28px;
    
    .generating-view {
      .gen-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin-bottom: 24px;
        
        .gen-dots {
          display: flex;
          gap: 6px;
          
          span {
            width: 8px;
            height: 8px;
            background: #6366f1;
            border-radius: 50%;
            animation: bounce 1.4s ease-in-out infinite;
            
            &:nth-child(2) { animation-delay: 0.2s; }
            &:nth-child(3) { animation-delay: 0.4s; }
          }
        }
        
        .gen-text {
          color: #6366f1;
          font-size: 14px;
          font-weight: 500;
        }
      }
      
      .outline-display {
        color: #334155;
        line-height: 1.8;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 350px;
        overflow-y: auto;
        font-family: system-ui, -apple-system, sans-serif;
        
        &::-webkit-scrollbar {
          width: 6px;
        }
        
        &::-webkit-scrollbar-track {
          background: #e2e8f0;
          border-radius: 3px;
        }
        
        &::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 3px;
          
          &:hover {
            background: #94a3b8;
          }
        }
      }
    }
    
    .editor-view {
      max-height: 400px;
      overflow-y: auto;
      
      &::-webkit-scrollbar {
        width: 6px;
      }
      
      &::-webkit-scrollbar-track {
        background: #e2e8f0;
        border-radius: 3px;
      }
      
      &::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 3px;
        
        &:hover {
          background: #94a3b8;
        }
      }
    }
  }

  .action-group {
    display: flex;
    justify-content: center;
    gap: 16px;
    
    .act-btn {
      padding: 14px 36px;
      border-radius: 100px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.3s;
      border: none;
      
      &.primary {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        
        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        }
      }
      
      &.secondary {
        background: #f1f5f9;
        color: #475569;
        
        &:hover {
          background: #e2e8f0;
        }
      }
    }
  }
}

@keyframes scrollBubbles {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

@keyframes bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

@media (max-width: 768px) {
  .header-section {
    .template-btn {
      position: static;
      margin-bottom: 24px;
    }
    
    .brand .title {
      .title-main {
        font-size: 32px;
      }
    }
  }
  
  .setup-section {
    .config-module .config-grid {
      grid-template-columns: 1fr;
    }
  }
  
  .action-group {
    flex-direction: column;
    
    .act-btn {
      width: 100%;
    }
  }
}

.processing-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}
.processing-modal {
  background: #fff;
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 20px 40px rgba(0,0,0,.15);
  max-width: 300px;
  width: 90%;
  text-align: center;
}
.processing-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.processing-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
.processing-text {
  color: #475569;
  font-size: 1rem;
  font-weight: 500;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>