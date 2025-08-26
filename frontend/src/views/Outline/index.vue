<template>
  <div class="aippt-page">
    <!-- 全局背景：渐变 + 网格 -->
    <div class="page-bg" aria-hidden="true">
      <div class="bg-blob b1"></div>
      <div class="bg-blob b2"></div>
      <div class="grid"></div>
    </div>

    <div class="aippt-dialog">
      <!-- Header Section -->
      <div class="header-section">
        <div class="brand">
          <h1 class="title">
            <span class="title-icon">🤖</span>
            PPTAgent
          </h1>
          <div class="subtitle">
            {{ step === 'outline' ? '确认下方内容大纲，开始选择模板' : '输入您的PPT主题，AI将为您生成专业大纲' }}
          </div>
        </div>
        <div class="progress-indicator">
          <div class="progress-step" :class="{ active: step === 'setup' }">
            <div class="step-circle">1</div>
            <span>输入主题</span>
          </div>
          <div class="progress-line" :class="{ completed: step === 'outline' }"></div>
          <div class="progress-step" :class="{ active: step === 'outline' }">
            <div class="step-circle">2</div>
            <span>确认大纲</span>
          </div>
        </div>
      </div>

      <!-- Setup Step -->
      <div v-if="step === 'setup'" class="setup-section">
        <div class="input-section">
          <div class="input-wrapper">
            <input
              ref="inputRef"
              v-model="keyword"
              :maxlength="50"
              class="main-input"
              placeholder="请输入PPT主题，如：大学生职业生涯规划"
              @keyup.enter="createOutline"
            />
            <div class="input-actions">
              <span class="character-count">{{ keyword.length }}/50</span>
              <button class="generate-btn" @click="createOutline" :disabled="!keyword.trim()">
                <span class="btn-icon">✨</span>
                AI 生成
              </button>
            </div>
          </div>
        </div>

        <!-- Recommendations -->
        <div class="recommendations-section">
          <h3 class="section-title">💡 推荐主题</h3>
          <div class="recommendations-grid">
            <button
              v-for="(item, index) in recommends"
              :key="index"
              class="recommend-item"
              @click="setKeyword(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>

        <!-- Configuration -->
        <div class="config-section">
          <h3 class="section-title">⚙️ 高级配置</h3>
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

      <!-- Outline Step -->
      <div v-if="step === 'outline'" class="outline-section">
        <div class="outline-header">
          <h3 class="section-title">📄 内容大纲</h3>
          <div class="outline-info">
            <span class="info-text">点击编辑内容，右键添加/删除大纲项</span>
          </div>
        </div>

        <div class="outline-content">
          <div v-if="outlineCreating" class="outline-preview">
            <div class="typing-indicator">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
            <pre ref="outlineRef" class="outline-text">{{ outline }}</pre>
          </div>
          <div v-else class="outline-editor">
            <OutlineEditor v-model:value="outline" />
          </div>
        </div>

        <div v-if="!outlineCreating" class="outline-actions">
          <button class="primary-btn" @click="goPPT">
            <span class="btn-icon">🎨</span>
            生成PPT
          </button>
          <button class="secondary-btn" @click="resetToSetup">
            <span class="btn-icon">↩️</span>
            重新生成
          </button>
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

const router = useRouter()
const { getMdContent } = useAIPPT()

const language = ref('中文')
const keyword = ref('')
const outline = ref('')
const loading = ref(false)
const outlineCreating = ref(false)
const step = ref<'setup' | 'outline'>('setup')
const model = ref('GLM-4.5-Air')
const outlineRef = ref<HTMLElement>()
const inputRef = ref<HTMLInputElement>()

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
  setTimeout(() => {
    inputRef.value?.focus()
  }, 100)
}

const createOutline = async () => {
  if (!keyword.value.trim()) {
    message.error('请先输入PPT主题')
    return
  }

  loading.value = true
  outlineCreating.value = true

  try {
    const stream = await api.AIPPT_Outline({
      content: keyword.value,
      language: language.value,
      model: model.value,
    })

    loading.value = false
    step.value = 'outline'

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
</script>

<style lang="scss" scoped>
/* 与大纲页保持同样的页面骨架与背景 */
  /* 页面容器，提供稳定的全屏背景承载 */
.aippt-page {
  position: relative;
  min-height: 100dvh;
  overflow: hidden;
}

/* 背景层 */
.page-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: radial-gradient(1200px 600px at 10% -10%, rgba(102, 126, 234, 0.12), rgba(0, 0, 0, 0) 60%),
    radial-gradient(1000px 600px at 90% 110%, rgba(118, 75, 162, 0.12), rgba(0, 0, 0, 0) 60%),
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  pointer-events: none;
}
.page-bg .grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(15, 23, 42, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.04) 1px, transparent 1px);
  background-size: 32px 32px, 32px 32px;
  mask-image: radial-gradient(60% 50% at 50% 50%, #000 60%, transparent 100%);
}
.bg-blob {
  position: absolute;
  filter: blur(40px);
  opacity: 0.6;
}
.bg-blob.b1 { width: 520px; height: 520px; left: -160px; top: -160px; background: #c7d2fe; }
.bg-blob.b2 { width: 420px; height: 420px; right: -120px; bottom: -120px; background: #e9d5ff; }

/* 主内容卡片 */
.aippt-dialog {
  position: relative;
  z-index: 1;
  margin: 0 auto;
  padding: 40px 24px 32px;
  max-width: 1160px;
  box-sizing: border-box;
}

/* Header Section */
.header-section {
  text-align: center;
  margin-bottom: 3rem;
  color: #475569;
}

.brand {
  margin-bottom: 2rem;

  .title {
    font-size: 3rem;
    font-weight: 800;
    margin: 0 0 1rem 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
    background-size: 400% 400%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientShift 3s ease infinite;

    .title-icon {
      filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
    }
  }

  .subtitle {
    font-size: 1.1rem;
    line-height: 1.6;
    max-width: 600px;
    margin: 0 auto;
    color: #475569;
  }
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.progress-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 1rem;

  .progress-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    opacity: 0.6;
    transition: opacity 0.3s ease;
    color: #475569;

    &.active {
      opacity: 1;
      font-weight: 600;
    }

    .step-circle {
      width: 2rem;
      height: 2rem;
      border-radius: 50%;
      background: #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      border: 2px solid #cbd5e1;
      transition: all 0.3s ease;
    }

    &.active .step-circle {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      transform: scale(1.1);
      border-color: transparent;
    }
  }

  .progress-line {
    width: 4rem;
    height: 2px;
    background: #e2e8f0;
    transition: background 0.3s ease;

    &.completed {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
  }
}

/* Setup Section */
.setup-section {
  background: white;
  border-radius: 1.5rem;
  padding: 2.5rem;
  box-shadow: 0 20px 40px rgba(0,0,0,0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.2);
}

.input-section {
  margin-bottom: 2rem;

  .input-wrapper {
    position: relative;
    background: #f8fafc;
    border-radius: 1rem;
    border: 2px solid #e2e8f0;
    transition: all 0.3s ease;
    overflow: hidden;

    &:focus-within {
      border-color: #667eea;
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
    }

    .main-input {
      width: 100%;
      padding: 1.25rem 1.5rem;
      border: none;
      background: transparent;
      font-size: 1.1rem;
      outline: none;
      resize: none;

      &::placeholder {
        color: #94a3b8;
      }
    }

    .input-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.5rem 1.25rem;
      gap: 1rem;

      .character-count {
        font-size: 0.875rem;
        color: #64748b;
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
  }
}

/* Recommendations Section */
.recommendations-section {
  margin-bottom: 2rem;

  .section-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: #334155;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .recommendations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.75rem;

    .recommend-item {
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      border-radius: 0.75rem;
      padding: 0.75rem 1rem;
      cursor: pointer;
      transition: all 0.3s ease;
      font-size: 0.9rem;
      text-align: left;

      &:hover {
        background: #667eea;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      }
    }
  }
}

/* Configuration Section */
.config-section {
  .section-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: #334155;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .config-grid {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 1.5rem;

    .config-item {
      .config-label {
        display: block;
        font-weight: 500;
        margin-bottom: 0.5rem;
        color: #475569;
        font-size: 0.9rem;
      }

      .config-select {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid #d1d5db;
        border-radius: 0.5rem;
        background: white;
        font-size: 0.9rem;
        cursor: pointer;
        transition: border-color 0.3s ease;

        &:focus {
          outline: none;
          border-color: #667eea;
        }
      }
    }
  }
}

/* Outline Section */
.outline-section {
  background: white;
  border-radius: 1.5rem;
  padding: 2.5rem;
  box-shadow: 0 20px 40px rgba(0,0,0,0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.2);

  .outline-header {
    margin-bottom: 1.5rem;

    .section-title {
      font-size: 1.3rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
      color: #334155;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .outline-info {
      .info-text {
        color: #64748b;
        font-size: 0.9rem;
      }
    }
  }

  .outline-content {
    margin-bottom: 2rem;

    .outline-preview {
      position: relative;

      .typing-indicator {
        display: flex;
        gap: 0.25rem;
        margin-bottom: 1rem;
        align-items: center;

        &::before {
          content: 'AI正在生成大纲';
          margin-right: 0.5rem;
          color: #64748b;
          font-size: 0.9rem;
        }

        .typing-dot {
          width: 0.5rem;
          height: 0.5rem;
          background: #667eea;
          border-radius: 50%;
          animation: typingBounce 1.4s infinite;

          &:nth-child(2) { animation-delay: 0.2s; }
          &:nth-child(3) { animation-delay: 0.4s; }
        }
      }

      .outline-text {
        max-height: 400px;
        padding: 1.5rem;
        background: #f8fafc;
        border-radius: 1rem;
        border: 1px solid #e2e8f0;
        overflow-y: auto;
        font-family: 'SF Mono', Monaco, monospace;
        font-size: 0.9rem;
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
      }
    }

    .outline-editor {
      max-height: 400px;
      padding: 1.5rem;
      background: #f8fafc;
      border-radius: 1rem;
      border: 1px solid #e2e8f0;
      overflow-y: auto;
    }
  }

  .outline-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;

    .primary-btn {
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;
      border: none;
      padding: 1rem 2rem;
      border-radius: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.3s ease;
      font-size: 1rem;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
      }

      .btn-icon {
        font-size: 1.2rem;
      }
    }

    .secondary-btn {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #d1d5db;
      padding: 1rem 2rem;
      border-radius: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.3s ease;
      font-size: 1rem;

      &:hover {
        background: #e2e8f0;
        transform: translateY(-2px);
      }

      .btn-icon {
        font-size: 1.2rem;
      }
    }
  }
}

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-0.5rem); }
}

/* Responsive Design */
@media (max-width: 768px) {
  .aippt-dialog {
    padding: 1rem;
  }

  .setup-section,
  .outline-section {
    padding: 1.5rem;
  }

  .brand .title {
    font-size: 2.5rem;
    flex-direction: column;
    gap: 0.5rem;
  }

  .progress-indicator {
    flex-direction: column;
    gap: 1rem;

    .progress-line {
      width: 2px;
      height: 2rem;
    }
  }

  .recommendations-grid {
    grid-template-columns: 1fr;
  }

  .config-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .input-actions {
    flex-direction: column;
    align-items: stretch !important;

    .generate-btn {
      justify-content: center;
    }
  }

  .outline-actions {
    flex-direction: column;

    .primary-btn,
    .secondary-btn {
      justify-content: center;
    }
  }
}

@media (max-width: 480px) {
  .brand .title {
    font-size: 2rem;
  }

  .brand .subtitle {
    font-size: 1rem;
  }

  .setup-section,
  .outline-section {
    padding: 1rem;
  }
}
</style>
