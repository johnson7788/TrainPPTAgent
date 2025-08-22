<template>
  <div class="aippt-dialog">
    <div class="header">
      <span class="title">AIPPT</span>
      <span class="subtite" v-if="step === 'outline'">确认下方内容大纲（点击编辑内容，右键添加/删除大纲项），开始选择模板</span>
      <span class="subtite" v-else>在下方输入您的PPT主题，并适当补充信息，如行业、岗位、学科、用途等</span>
    </div>
    
    <template v-if="step === 'setup'">
      <Input class="input" 
        ref="inputRef"
        v-model:value="keyword" 
        :maxlength="50" 
        placeholder="请输入PPT主题，如：大学生职业生涯规划" 
        @enter="createOutline()"
      >
        <template #suffix>
          <span class="count">{{ keyword.length }} / 50</span>
          <div class="submit" type="primary" @click="createOutline()"><IconSend class="icon" /> AI 生成</div>
        </template>
      </Input>
      <div class="recommends">
        <div class="recommend" v-for="(item, index) in recommends" :key="index" @click="setKeyword(item)">{{ item }}</div>
      </div>
      <div class="configs">
        <div class="config-item">
          <div class="label">语言：</div>
          <Select 
            class="config-content"
            style="width: 80px;"
            v-model:value="language"
            :options="[
              { label: '中文', value: '中文' },
              { label: '英文', value: 'English' },
              { label: '日文', value: '日本語' },
            ]"
          />
        </div>
        <div class="config-item">
          <div class="label">模型：</div>
          <Select 
            class="config-content"
            style="width: 190px;"
            v-model:value="model"
            :options="[
              { label: 'GLM-4.5-Air', value: 'GLM-4.5-Air' },
              { label: 'GLM-4.5-Flash', value: 'GLM-4.5-Flash' },
              { label: 'Doubao-Seed-1.6-flash', value: 'ark-doubao-seed-1.6-flash' },
              { label: 'Doubao-Seed-1.6', value: 'ark-doubao-seed-1.6' },
            ]"
          />
        </div>
      </div>
    </template>
    <div class="preview" v-if="step === 'outline'">
      <pre ref="outlineRef" v-if="outlineCreating">{{ outline }}</pre>
       <div class="outline-view" v-else>
         <OutlineEditor v-model:value="outline" />
       </div>
      <div class="btns" v-if="!outlineCreating">
        <Button class="btn" type="primary" @click="goPPT">生成PPT</Button>
        <Button class="btn" @click="outline = ''; step = 'setup'">返回重新生成</Button>
      </div>
    </div>

    <FullscreenSpin :loading="loading" tip="AI生成中，请耐心等待 ..." />
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services'
import useAIPPT from '@/hooks/useAIPPT'
import message from '@/utils/message'
import Input from '@/components/Input.vue'
import Button from '@/components/Button.vue'
import Select from '@/components/Select.vue'
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
const inputRef = ref<InstanceType<typeof Input>>()

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
    inputRef.value!.focus()
  }, 500)
})

const setKeyword = (value: string) => {
  keyword.value = value
  inputRef.value!.focus()
}

const createOutline = async () => {
  if (!keyword.value) return message.error('请先输入PPT主题')

  loading.value = true
  outlineCreating.value = true
  
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
.preview {
  pre {
    max-height: 450px;
    padding: 10px;
    margin-bottom: 15px;
    background-color: #f1f1f1;
    overflow: auto;
  }
  .outline-view {
    max-height: 450px;
    padding: 10px;
    margin-bottom: 15px;
    background-color: #f1f1f1;
    overflow: auto;
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
.recommends {
  display: flex;
  flex-wrap: wrap;
  margin-top: 10px;

  .recommend {
    font-size: 12px;
    background-color: #f1f1f1;
    border-radius: $borderRadius;
    padding: 3px 5px;
    margin-right: 5px;
    margin-top: 5px;
    cursor: pointer;

    &:hover {
      color: $themeColor;
    }
  }
}
.configs {
  margin-top: 15px;
  display: flex;
  justify-content: space-between;

  .config-item {
    font-size: 13px;
    display: flex;
    align-items: center;
  }
}
.count {
  font-size: 12px;
  color: #999;
  margin-right: 10px;
}
.submit {
  height: 20px;
  font-size: 12px;
  background-color: $themeColor;
  color: #fff;
  display: flex;
  align-items: center;
  padding: 0 8px 0 6px;
  border-radius: $borderRadius;
  cursor: pointer;

  &:hover {
    background-color: $themeHoverColor;
  }

  .icon {
    font-size: 15px;
    margin-right: 3px;
  }
}

@media screen and (width <= 800px) {
  .configs {
    margin-top: 15px;
    display: flex;
    flex-direction: column;

    .config-item {
      margin-top: 8px;

      .label {
        flex-shrink: 0;
      }

      .config-content {
        width: 100% !important;
      }
    }
  }
}
</style>