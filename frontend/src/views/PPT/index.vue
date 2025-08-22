<template>
  <div class="aippt-dialog">
    <div class="header">
      <span class="title">AIPPT</span>
      <span class="subtite">从下方挑选合适的模板，开始生成PPT</span>
    </div>
    
    <div class="select-template">
      <div class="templates">
        <div class="template" 
          :class="{ 'selected': selectedTemplate === template.id }" 
          v-for="template in templates" 
          :key="template.id" 
          @click="selectedTemplate = template.id"
        >
          <img :src="template.cover" :alt="template.name">
        </div>
      </div>
      <div class="btns">
        <Button class="btn" type="primary" @click="createPPT()">生成</Button>
        <Button class="btn" @click="$router.back()">返回大纲</Button>
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
import Button from '@/components/Button.vue'
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
        router.push('/')
        return
      }
  
      const chunk = decoder.decode(value, { stream: true })
      try {
        const text = chunk.replace('```json', '').replace('```', '').trim()
        if (text) {
          const slide: AIPPTSlide = JSON.parse(chunk)
          AIPPT(templateSlides, [slide])
        }
      }
      catch (err) {
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
.aippt-dialog {
  margin: -20px;
  padding: 30px;
}
.header {
  margin-bottom: 12px;

  .title {
    font-weight: 700;
    font-size: 20px;
    margin-right: 8px;
    background: linear-gradient(270deg, #d897fd, #33bcfc);
    background-clip: text;
    color: transparent;
    vertical-align: text-bottom;
    line-height: 1.1;
  }
  .subtite {
    color: #888;
    font-size: 12px;
  }
}
.select-template {
  .templates {
    display: flex;
    margin-bottom: 10px;
    @include flex-grid-layout();
  
    .template {
      border: 2px solid $borderColor;
      border-radius: $borderRadius;
      width: 324px;
      height: 184px;
      margin-bottom: 12px;

      &:not(:nth-child(2n)) {
        margin-right: 12px;
      }

      &.selected {
        border-color: $themeColor;
      }
  
      img {
        width: 100%;
      }
    }
  }
  .btns {
    display: flex;
    justify-content: center;
    align-items: center;

    .btn {
      width: 120px;
      margin: 0 5px;
    }
  }
}

@media screen and (width <= 800px) {
  .select-template {
    .templates {
      max-height: 450px;
      display: block;
      overflow: auto;
    
      .template {
        width: 100%;
        height: unset;
        margin-bottom: 0 !important;
        margin-right: 0 !important;

        & + .template {
          margin-top: 20px;
        }
      }
    }
  }
}
</style>