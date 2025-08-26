<template>
  <div class="aippt-page">
    <!-- 全局背景：渐变 + 网格 -->
    <div class="page-bg" aria-hidden="true">
      <div class="bg-blob b1"></div>
      <div class="bg-blob b2"></div>
      <div class="grid"></div>
    </div>

    <div class="aippt-dialog">
      <!-- 头部：标题/说明 居中、层级清晰 -->
      <header class="header" role="banner">
        <div class="header-content">
          <h1 class="title">PPTAgent</h1>
          <p class="subtitle">从下方挑选合适的模板，开始生成 PPT</p>
          <div class="header-decoration" aria-hidden="true">
            <div class="decoration-dot"></div>
            <div class="decoration-dot"></div>
            <div class="decoration-dot"></div>
          </div>
        </div>
      </header>

      <section class="select-template" aria-label="模板选择">
        <div class="templates-container">
          <div class="templates">
            <div
              class="template-card"
              :class="{ selected: selectedTemplate === template.id }"
              v-for="template in templates"
              :key="template.id"
              @click="!loading && (selectedTemplate = template.id)"
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
        </div>

        <div class="actions">
          <Button class="btn btn-primary" type="primary" :disabled="loading || !selectedTemplate" @click="createPPT()">
            <span>{{ loading ? '正在生成…' : '生成PPT' }}</span>
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12,6 12,12 16,14"></polyline>
            </svg>
          </Button>
          <Button class="btn btn-secondary" :disabled="loading" @click="$router.back()">
            <span>返回大纲</span>
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15,18 9,12 15,6"></polyline>
            </svg>
          </Button>
        </div>
      </section>
    </div>

    
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
import Button from '@/components/Button.vue'
import FullscreenSpin from '@/components/FullscreenSpin.vue'

const route = useRoute()
const router = useRouter()
const mainStore = useMainStore()
const slideStore = useSlidesStore()
const { templates } = storeToRefs(slideStore)
const { sessionId } = storeToRefs(mainStore)
const { AIPPTGenerator, presetImgPool } = useAIPPT()

const outline = ref(route.query.outline as string)
const language = ref(route.query.language as string)
const model = ref(route.query.model as string)
const style = ref('通用')
const img = ref('')
const selectedTemplate = ref<string>(templates.value?.[0]?.id || 'template_1')
const loading = ref(false)

const createPPT = async () => {
  if (!selectedTemplate.value) return
  mainStore.setGenerating(true)
  loading.value = true

  slideStore.resetSlides()

  router.push(`/editor?session_id=${sessionId.value}`)

  try {
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
    slideStore.setTheme(templateTheme)

    const reader: ReadableStreamDefaultReader = stream.body.getReader()
    const decoder = new TextDecoder('utf-8')

    const readStream = () => {
      reader.read().then(({ done, value }) => {
        if (done) {
          loading.value = false
          mainStore.setAIPPTDialogState(false)
          mainStore.setGenerating(false)
          return
        }

        const chunk = decoder.decode(value, { stream: true })
        try {
          const text = chunk.replace(/```json|```/g, '').trim()
          if (text) {
            const slide: AIPPTSlide = JSON.parse(text)
            const slideGenerator = AIPPTGenerator(templateSlides, [slide])
            for (const generatedSlide of slideGenerator) {
              slideStore.addSlide(generatedSlide)
            }
          }
        } catch (err) {
          // eslint-disable-next-line no-console
          console.error(err)
        }

        readStream()
      })
    }
    readStream()
  } catch (e) {
    loading.value = false
    mainStore.setGenerating(false)
    // eslint-disable-next-line no-console
    console.error(e)
  }
}
</script>

<style lang="scss" scoped>
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

/* 头部区块：居中布局 */
.header {
  text-align: center;
  margin-bottom: 28px;
  .title {
    font-weight: 900;
    font-size: 36px;
    margin: 0 0 10px 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    letter-spacing: -0.5px;
    line-height: 1.15;
  }
  .subtitle {
    color: #475569;
    font-size: 16px;
    margin: 0 auto;
    font-weight: 500;
    line-height: 1.6;
    max-width: 680px;
  }
  .header-decoration {
    margin: 14px auto 0;
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: center;
    .decoration-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      opacity: 0.7; animation: pulse 2s ease-in-out infinite;
      &:nth-child(2) { animation-delay: 0.25s; }
      &:nth-child(3) { animation-delay: 0.5s; }
    }
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.2); opacity: 1; }
}

/* 模板区域 */
.select-template {
  .templates-container {
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: saturate(120%) blur(2px);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
  }

  .templates {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 18px;
  }

  .template-card {
    position: relative;
    border: 2px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    background: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 26px -4px rgba(0, 0, 0, 0.12);
      border-color: #cbd5e1;
    }

    &.selected {
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15), 0 12px 28px -6px rgba(59, 130, 246, 0.25);
      .overlay { opacity: 1; visibility: visible; }
      .template-info { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #fff; }
    }

    .template-image {
      position: relative; aspect-ratio: 16/9; overflow: hidden;
      img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s ease; }
      .overlay {
        position: absolute; inset: 0; background: rgba(59, 130, 246, 0.18);
        display: flex; align-items: center; justify-content: center;
        opacity: 0; visibility: hidden; transition: all 0.25s ease;
        .check-icon {
          width: 32px; height: 32px; color: #fff; background: #3b82f6; border-radius: 50%;
          display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
          svg { width: 16px; height: 16px; }
        }
      }
    }

    .template-info {
      padding: 12px 14px; background: #f8fafc; transition: all 0.25s ease;
      .template-name { font-size: 14px; font-weight: 700; color: inherit; }
    }

    &:hover .template-image img { transform: scale(1.045); }
  }

  .actions {
    display: flex; justify-content: center; gap: 14px; align-items: center; margin-top: 18px;
    .btn {
      min-width: 148px; height: 48px; display: flex; align-items: center; justify-content: center; gap: 8px;
      font-weight: 700; font-size: 14px; border-radius: 12px; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative; overflow: hidden;
      &:disabled { opacity: 0.6; cursor: not-allowed; filter: grayscale(10%); }
      .btn-icon { width: 18px; height: 18px; transition: transform 0.25s ease; }
      &.btn-primary {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border: none; color: #fff;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.38);
        &:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(59, 130, 246, 0.5); .btn-icon { transform: rotate(90deg); } }
        &:active:not(:disabled) { transform: translateY(0); }
      }
      &.btn-secondary {
        background: #fff; border: 2px solid #e2e8f0; color: #64748b;
        &:hover:not(:disabled) {
          border-color: #cbd5e1; background: #f8fafc; color: #475569; transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08); .btn-icon { transform: translateX(-2px); }
        }
        &:active:not(:disabled) { transform: translateY(0); }
      }
    }
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .aippt-dialog { padding: 24px 16px; }
  .header { .title { font-size: 28px; } .subtitle { font-size: 14px; } }
  .select-template {
    .templates-container { padding: 16px; }
    .templates { grid-template-columns: 1fr; gap: 14px; }
    .actions { flex-direction: column; gap: 12px; .btn { width: 100%; max-width: 320px; } }
  }
}
@media (max-width: 480px) {
  .header .title { font-size: 24px; }
}
</style>
