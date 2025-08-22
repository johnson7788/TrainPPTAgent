<template>
  <div class="aippt-container">
    <!-- Header Section（与大纲页一致） -->
    <div class="header-section">
      <div class="brand">
        <h1 class="title">
          <span class="title-icon">🤖</span>
          PPTAgent
        </h1>
        <div class="subtitle">从下方挑选合适的模板，开始生成PPT</div>
      </div>

      <!-- 进度指示：在大纲页的基础上新增第3步 -->
      <div class="progress-indicator">
        <div class="progress-step">
          <div class="step-circle">1</div>
          <span>输入主题</span>
        </div>
        <div class="progress-line completed"></div>
        <div class="progress-step">
          <div class="step-circle">2</div>
          <span>确认大纲</span>
        </div>
        <div class="progress-line completed"></div>
        <div class="progress-step active">
          <div class="step-circle">3</div>
          <span>选择模板</span>
        </div>
      </div>
    </div>

    <!-- Template Section（与大纲页的白卡片风格一致） -->
    <div class="template-section">
      <h3 class="section-title">🎨 可用模板</h3>
      <div class="templates-grid">
        <div
          class="template-card"
          :class="{ selected: selectedTemplate === template.id }"
          v-for="template in templates"
          :key="template.id"
          @click="selectedTemplate = template.id"
        >
          <div class="template-image">
            <img :src="template.cover" :alt="template.name" />
            <div class="overlay">
              <div class="check-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20,6 9,17 4,12"></polyline>
                </svg>
              </div>
            </div>
          </div>
          <div class="template-info">
            <span class="template-name">{{ template.name || '经典模板' }}</span>
          </div>
        </div>
      </div>

      <div class="template-actions">
        <button class="primary-btn" @click="createPPT()">
          <span class="btn-icon">🚀</span>
          生成PPT
        </button>
        <button class="secondary-btn" @click="$router.back()">
          <span class="btn-icon">↩️</span>
          返回大纲
        </button>
      </div>
    </div>

    <FullscreenSpin :loading="loading" tip="AI生成中，请耐心等待 ..." />
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import api from '@/services'
import useAIPPT from '@/hooks/useAIPPT'
import type { AIPPTSlide } from '@/types/AIPPT'
import type { Slide, SlideTheme } from '@/types/slides'
import { useMainStore, useSlidesStore } from '@/store'
import FullscreenSpin from '@/components/FullscreenSpin.vue'

const route = useRoute()
const router = useRouter()
const mainStore = useMainStore()
const slideStore = useSlidesStore()
const { templates } = storeToRefs(slideStore)
const { AIPPT, presetImgPool } = useAIPPT()

const outline = ref(route.query.outline as string)
const language = ref(route.query.language as string)
const model = ref(route.query.model as string)
const style = ref('通用')
const img = ref('')

const selectedTemplate = ref('template_1')
const loading = ref(false)

const createPPT = async () => {
  loading.value = true

  const stream = await api.AIPPT({
    content: outline.value,
    language: language.value,
    style: style.value,
    model: model.value,
  })

  if (img.value === 'test') {
    const imgs = await api.getMockData('imgs')
    presetImgPool(imgs)
  }

  const templateData = await api.getFileData(selectedTemplate.value)
  const templateSlides: Slide[] = templateData.slides
  const templateTheme: SlideTheme = templateData.theme

  const reader: ReadableStreamDefaultReader = stream.body.getReader()
  const decoder = new TextDecoder('utf-8')

  const readStream = () => {
    reader.read().then(({ done, value }) => {
      if (done) {
        loading.value = false
        mainStore.setAIPPTDialogState(false)
        slideStore.setTheme(templateTheme)
        router.push('/editor')
        return
      }

      const chunk = decoder.decode(value, { stream: true })
      try {
        const text = chunk.replace('```json', '').replace('```', '').trim()
        if (text) {
          const slide: AIPPTSlide = JSON.parse(text) // 解析清洗后的内容
          AIPPT(templateSlides, [slide])
        }
      } catch (err) {
        // eslint-disable-next-line
        console.error(err)
      }

      readStream()
    })
  }
  readStream()
}
</script>

<style lang="scss" scoped>
/* 与大纲页保持同样的页面骨架与背景 */
:global(html, body, #app) {
  height: auto;
  min-height: 100%;
  overflow-y: auto !important;
}

.aippt-container {
  max-width: 100%;
  margin: 0 auto;
  padding: 2rem 4rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Header Section（复用大纲页风格） */
.header-section {
  text-align: center;
  margin-bottom: 3rem;
  color: white;
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
      filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
    }
  }

  .subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    line-height: 1.6;
    max-width: 600px;
    margin: 0 auto;
  }
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* 进度条（新增第3步） */
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

    &.active {
      opacity: 1;
      font-weight: 600;
    }

    .step-circle {
      width: 2rem;
      height: 2rem;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      border: 2px solid rgba(255, 255, 255, 0.3);
      transition: all 0.3s ease;
    }

    &.active .step-circle {
      background: rgba(255, 255, 255, 0.9);
      color: #667eea;
      transform: scale(1.1);
    }
  }

  .progress-line {
    width: 4rem;
    height: 2px;
    background: rgba(255, 255, 255, 0.3);
    transition: background 0.3s ease;

    &.completed {
      background: rgba(255, 255, 255, 0.7);
    }
  }
}

/* Template Section：与大纲页的白卡片风格一致 */
.template-section {
  background: white;
  border-radius: 1.5rem;
  padding: 2.5rem;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);

  .section-title {
    font-size: 1.3rem;
    font-weight: 600;
    margin-bottom: 1.25rem;
    color: #334155;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
}

/* 模板网格与卡片（颜色、圆角、阴影与大纲页一致风格） */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.template-card {
  position: relative;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 24px rgba(102, 126, 234, 0.18);
    border-color: #cbd5e1;
  }

  &.selected {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15), 0 10px 24px rgba(102, 126, 234, 0.25);

    .overlay {
      opacity: 1;
      visibility: visible;
    }

    .template-info {
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;
    }
  }

  .template-image {
    position: relative;
    aspect-ratio: 16/9;
    overflow: hidden;
    background: #f8fafc;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease;
      display: block;
    }

    .overlay {
      position: absolute;
      inset: 0;
      background: rgba(102, 126, 234, 0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;

      .check-icon {
        width: 32px;
        height: 32px;
        color: white;
        background: #667eea;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 14px rgba(102, 126, 234, 0.45);

        svg {
          width: 16px;
          height: 16px;
        }
      }
    }
  }

  .template-info {
    padding: 0.75rem 1rem;
    background: #f8fafc;
    transition: all 0.3s ease;

    .template-name {
      font-size: 0.95rem;
      font-weight: 600;
      color: inherit;
    }
  }

  &:hover .template-image img {
    transform: scale(1.05);
  }
}

/* Actions：复用大纲页按钮风格 */
.template-actions {
  margin-top: 1.5rem;
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

/* Responsive Design（与大纲页一致） */
@media (max-width: 768px) {
  .aippt-container {
    padding: 1rem;
  }

  .template-section {
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

  .template-actions {
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

  .template-section {
    padding: 1rem;
  }
}
</style>
