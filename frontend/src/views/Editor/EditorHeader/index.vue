<template>
  <div class="editor-header">
    <div class="left">
      <Popover trigger="click" placement="bottom-start" v-model:value="mainMenuVisible">
        <template #content>
          <div class="main-menu">
            <div class="ai-menu" @click="router.push('/'); mainMenuVisible = false">
              <div class="icon"><IconClick theme="two-tone" :fill="['#ffc158', '#fff']" /></div>
              <div class="aippt-content">
                <div class="aippt"><span>PPTAgent</span></div>
                <div class="aippt-subtitle">输入一句话，智能生成演示文稿</div>
              </div>
            </div>
          </div>
          <Divider :margin="10" />
          <div class="import-section">
            <div class="import-label">导入文件</div>
            <div class="import-grid">
              <FileInput class="import-block" accept="application/vnd.openxmlformats-officedocument.presentationml.presentation" @change="files => {
                importPPTXFile(files)
                mainMenuVisible = false
              }">
                <span class="icon"><IconFilePdf theme="multi-color" :fill="['#333', '#d14424', '#fff']" /></span>
                <span class="label">PPTX</span>
                <span class="sub-label">（测试）</span>
              </FileInput>
              <FileInput class="import-block" accept=".json" @change="files => {
                importJSON(files)
                mainMenuVisible = false
              }">
                <span class="icon"><IconFileJpg theme="multi-color" :fill="['#333', '#d14424', '#fff']" /></span>
                <span class="label">JSON</span>
                <span class="sub-label">（测试）</span>
              </FileInput>
              <FileInput class="import-block" accept=".pptist" @change="files => {
                importSpecificFile(files)
                mainMenuVisible = false
              }">
                <span class="icon"><IconNotes theme="multi-color" :fill="['#333', '#d14424', '#fff']" /></span>
                <span class="label">PPTIST</span>
                <span class="sub-label">（专属格式）</span>
              </FileInput>
              <!-- 新增：测试PPTist按钮 -->
              <div class="import-block" @click="testPPTist">
                <span class="icon"><IconNotes theme="multi-color" :fill="['#333', '#d14424', '#fff']" /></span>
                <span class="label">测试PPTist</span>
                <span class="sub-label">（快速体验）</span>
              </div>
            </div>
          </div>
          <Divider :margin="10" />
          <PopoverMenuItem class="popover-menu-item" @click="setDialogForExport('pptx')"><IconDownload class="icon" /> 导出文件</PopoverMenuItem>
          <Divider :margin="10" />
          <PopoverMenuItem class="popover-menu-item" @click="resetSlides(); mainMenuVisible = false"><IconRefresh class="icon" /> 重置幻灯片</PopoverMenuItem>
          <PopoverMenuItem class="popover-menu-item" @click="openMarkupPanel(); mainMenuVisible = false"><IconMark class="icon" /> 幻灯片类型标注</PopoverMenuItem>
          <PopoverMenuItem class="popover-menu-item" @click="mainMenuVisible = false; hotkeyDrawerVisible = true"><IconCommand class="icon" /> 快捷操作</PopoverMenuItem>
        </template>
        <div class="menu-item"><IconHamburgerButton class="icon" /></div>
      </Popover>

      <div class="title">
        <Input
          class="title-input"
          ref="titleInputRef"
          v-model:value="titleValue"
          @blur="handleUpdateTitle()"
          v-if="editingTitle"
        ></Input>
        <div
          class="title-text"
          @click="startEditTitle()"
          :title="title"
          v-else
        >{{ title }}</div>
      </div>
    </div>

    <div class="right">
      <div class="group-menu-item">
        <div class="menu-item" v-tooltip="'幻灯片放映（F5）'" @click="enterScreening()">
          <IconPpt class="icon" />
        </div>
        <Popover trigger="click" center>
          <template #content>
            <PopoverMenuItem class="popover-menu-item" @click="enterScreeningFromStart()"><IconSlideTwo class="icon" /> 从头开始</PopoverMenuItem>
            <PopoverMenuItem class="popover-menu-item" @click="enterScreening()"><IconPpt class="icon" /> 从当前页开始</PopoverMenuItem>
          </template>
          <div class="arrow-btn"><IconDown class="arrow" /></div>
        </Popover>
      </div>
      <div class="menu-item" v-tooltip="'导出'" @click="setDialogForExport('pptx')">
        <IconDownload class="icon" />
      </div>
    </div>

    <Drawer
      :width="320"
      v-model:visible="hotkeyDrawerVisible"
      placement="right"
    >
      <HotkeyDoc />
      <template v-slot:title>快捷操作</template>
    </Drawer>

    <!-- 隐藏：模板文件选择器（由"测试PPTist"触发） -->
    <input
      ref="tmplPicker"
      type="file"
      accept=".json,.pptist"
      style="display:none"
      @change="onPickTemplate"
    />

    <!-- AIPPT JSON 输入抽屉 -->
    <Drawer
      :width="560"
      v-model:visible="aipptDrawerVisible"
      placement="right"
    >
      <template #title>渲染 AIPPT</template>
      <div class="aippt-form">
        <div class="tips">
          已选择模板：<strong>{{ templateFileName || '尚未选择' }}</strong>
        </div>
        <div class="field">
          <div class="label">AIPPT JSON</div>
          <textarea
            v-model="aipptInput"
            class="aippt-textarea"
            placeholder='在此粘贴 AIPPT.json 内容（如 {"cover": {...}, "contents":[...], "content":[...], "end":[...]}）'
          ></textarea>
        </div>
        <div class="btns">
          <div class="menu-item" @click="renderAIPPTNow">
            <IconPpt class="icon" />
            <span style="margin-left:6px;">渲染并载入</span>
          </div>
        </div>
      </div>
    </Drawer>

    <!-- 原有：导入 Loading -->
    <FullscreenSpin :loading="exporting" tip="正在导入..." />
    <!-- 新增：AIPPT 渲染 Loading -->
    <FullscreenSpin :loading="aipptLoading" tip="正在渲染 AIPPT..." />
  </div>
</template>

<script lang="ts" setup>
import { nextTick, ref, useTemplateRef } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useMainStore, useSlidesStore } from '@/store'
import useScreening from '@/hooks/useScreening'
import useImport from '@/hooks/useImport'
import useSlideHandler from '@/hooks/useSlideHandler'
import useHistorySnapshot from '@/hooks/useHistorySnapshot'
import type { DialogForExportTypes } from '@/types/export'
import type { AIPPTSlide } from '@/types/AIPPT'
import message from '@/utils/message'

import HotkeyDoc from './HotkeyDoc.vue'
import FileInput from '@/components/FileInput.vue'
import FullscreenSpin from '@/components/FullscreenSpin.vue'
import Drawer from '@/components/Drawer.vue'
import Input from '@/components/Input.vue'
import Popover from '@/components/Popover.vue'
import PopoverMenuItem from '@/components/PopoverMenuItem.vue'
import Divider from '@/components/Divider.vue'

// 关键：统一走 AIPPTGenerator（本地生成，不依赖后端）
import useAIPPT from '@/hooks/useAIPPT'

const router = useRouter()
const mainStore = useMainStore()
const slidesStore = useSlidesStore()
const { title } = storeToRefs(slidesStore)
const { enterScreening, enterScreeningFromStart } = useScreening()
const { importSpecificFile, importPPTXFile, importJSON, exporting } = useImport()
const { resetSlides } = useSlideHandler()
const { AIPPTGenerator } = useAIPPT()
const { addHistorySnapshot } = useHistorySnapshot()

const mainMenuVisible = ref(false)
const hotkeyDrawerVisible = ref(false)
const editingTitle = ref(false)
const titleValue = ref('')
const titleInputRef = useTemplateRef<InstanceType<typeof Input>>('titleInputRef')

// —— 本地渲染（测试 AIPPT）相关状态 ——
const tmplPicker = useTemplateRef<HTMLInputElement>('tmplPicker')
const aipptDrawerVisible = ref(false)
const aipptInput = ref('')

// 注意：这是"模板文件对象"（本地读取的 .json/.pptist），避免与"模板 ID"混淆
const selectedTemplateFile = ref<any>(null)
const templateFileName = ref('')
const aipptLoading = ref(false)

// ========== 修复后的写入 Slides 函数 ==========
const applySlides = (slides: any[]) => {
  if (slides.length === 0) return

  // 清除当前选中的元素
  mainStore.setActiveElementIdList([])

  // 设置幻灯片数据
  slidesStore.setSlides(slides)
  slidesStore.updateSlideIndex(0) // 关键：设置当前幻灯片索引

  // 添加历史快照确保界面更新
  addHistorySnapshot()
}

// ========== 标题编辑 ==========
const startEditTitle = () => {
  titleValue.value = title.value
  editingTitle.value = true
  nextTick(() => titleInputRef.value?.focus())
}
const handleUpdateTitle = () => {
  slidesStore.setTitle(titleValue.value)
  editingTitle.value = false
}

// 其它 UI 控制
const setDialogForExport = (type: DialogForExportTypes) => { mainStore.setDialogForExport(type); mainMenuVisible.value = false }
const openMarkupPanel = () => { mainStore.setMarkupPanelState(true) }

// "测试PPTist" → 选择模板文件
const testPPTist = () => { mainMenuVisible.value = false; tmplPicker.value?.click() }

// 模板文件选择完成
const onPickTemplate = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    templateFileName.value = file.name
    const text = await file.text()
    selectedTemplateFile.value = JSON.parse(text)
    aipptInput.value = ''
    aipptDrawerVisible.value = true
    message.success('模板已载入，请粘贴 AIPPT JSON')
  } catch (err) {
    console.error(err)
    message.error('模板读取失败：请确认是有效的 JSON')
  } finally {
    input.value = '' // 允许下次选择同名文件
  }
}

// ====== 工具函数：模板类型探测 / AIPPT 规范化 / 类型同义词映射 ======
const sniffTypesFromTemplate = (tpl: any): string[] => {
  const out = new Set<string>()
  const walk = (n: any) => {
    if (!n) return
    if (Array.isArray(n)) return n.forEach(walk)
    if (typeof n === 'object') {
      if (typeof (n as any).type === 'string') out.add((n as any).type)
      for (const k in n) walk((n as any)[k])
    }
  }
  walk(tpl)
  if (Array.isArray(tpl?.slides)) tpl.slides.forEach((s: any) => typeof s?.type === 'string' && out.add(s.type))
  return Array.from(out)
}

// 将"简易 AIPPT JSON"转换为标准的 AIPPTSlide[]（每页带 type）
interface AIPPTSlideLike { type: string; [k: string]: any }
const normalizeToAipptSlides = (a: any): AIPPTSlide[] => {
  const slides: AIPPTSlide[] = []

  // 封面页
  if (a.cover) {
    slides.push({
      type: 'cover',
      data: {
        title: a.cover.title || '',
        text: a.cover.text || ''
      }
    })
  }

  // 目录页
  if (Array.isArray(a.contents) && a.contents[0]) {
    slides.push({
      type: 'contents',
      data: {
        items: a.contents[0].content || []
      }
    })
  }

  // 内容页
  if (Array.isArray(a.content)) {
    a.content.forEach((sec: any) => {
      // 过渡页
      if (sec?.title) {
        slides.push({
          type: 'transition',
          data: {
            title: sec.title,
            text: ''
          }
        })
      }
      // 内容页
      if (Array.isArray(sec?.content) && sec.content.length) {
        slides.push({
          type: 'content',
          data: {
            title: sec.title || '',
            items: sec.content.map((item: any) => ({
              title: typeof item === 'string' ? item : (item.title || ''),
              text: typeof item === 'string' ? '' : (item.text || item.content || '')
            }))
          }
        })
      }
    })
  }

  // 结束页
  if (Array.isArray(a.end) && a.end.length > 0) {
    slides.push({ type: 'end' })
  }

  return slides
}

// 将规范 slides 的类型名映射为模板实际支持的类型名
const remapTypesToTemplate = (slides: AIPPTSlide[], supported: string[]): AIPPTSlide[] => {
  const has = (t: string) => supported.includes(t)
  const alias: Record<string, string> = {}
  if (!has('toc') && has('catalog')) alias['toc'] = 'catalog'
  if (!has('section') && has('title')) alias['section'] = 'title'
  if (!has('bullets') && has('list')) alias['bullets'] = 'list'
  if (!has('end') && has('thankyou')) alias['end'] = 'thankyou'
  return slides.map(s => ({ ...s, type: alias[s.type] || s.type })) as AIPPTSlide[]
}

// ============== 渲染并载入（本地模式；无需后端） ==============
const renderAIPPTNow = async () => {
  if (!selectedTemplateFile.value) return message.error('请先选择模板文件')

  // 解析用户粘贴的 AIPPT 数据
  let raw: any
  try { raw = JSON.parse(aipptInput.value || '{}') }
  catch { return message.error('AIPPT JSON 解析失败，请检查格式') }

  try {
    aipptLoading.value = true

    const tpl = selectedTemplateFile.value
    const templateSlides = Array.isArray(tpl?.slides) ? tpl.slides : []
    const templateTheme = tpl?.theme
    if (!templateSlides.length) throw new Error('模板缺少 slides 字段或为空')

    // 设主题（若模板提供）
    if (templateTheme && typeof (slidesStore as any).setTheme === 'function') {
      ;(slidesStore as any).setTheme(templateTheme)
    }

    // 规范化 + 同义词映射 + 预检
    const supported = sniffTypesFromTemplate(tpl)

    // 检查输入数据格式：如果是数组则直接使用，如果是对象则转换
    let normalized: AIPPTSlide[]
    if (Array.isArray(raw)) {
      // 输入数据已经是 AIPPTSlide[] 格式，直接使用
      normalized = raw
      console.log('使用数组格式的 AIPPT 数据:', normalized)
    } else {
      // 输入数据是对象格式，需要转换
      normalized = normalizeToAipptSlides(raw)
      console.log('转换对象格式的 AIPPT 数据:', normalized)
    }

    const aSlides = remapTypesToTemplate(normalized, supported)
    const unknown = Array.from(new Set(aSlides.map(s => s.type).filter(t => !supported.includes(t))))
    if (unknown.length) throw new Error(`以下类型未在当前模板中找到：${unknown.join('、')}；模板支持：${supported.join('、') || '未探测到'}`)

    // 用与 createPPT 相同的生成器本地生成
    const gen = AIPPTGenerator(templateSlides, aSlides)
    const outSlides: any[] = []
    for (const s of gen) outSlides.push(s)

    // 调试信息
    console.log('Generated slides:', outSlides)
    console.log('First slide structure:', outSlides[0])

    applySlides(outSlides)          // ← 关键：统一用安全写入方法
    aipptDrawerVisible.value = false
    message.success('渲染完成，已载入到画布')
  } catch (err: any) {
    console.error(err)
    message.error('渲染失败：' + (err?.message || '请检查模板类型标注与 AIPPT 结构是否匹配'))
  } finally {
    aipptLoading.value = false
  }
}

</script>


<style lang="scss" scoped>
.editor-header {
  background-color: #fff;
  user-select: none;
  border-bottom: 1px solid $borderColor;
  display: flex;
  justify-content: space-between;
  padding: 0 5px;
}
.left, .right {
  display: flex;
  justify-content: center;
  align-items: center;
}
.menu-item {
  height: 30px;
  height: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  padding: 0 10px;
  border-radius: $borderRadius;
  cursor: pointer;

  .icon {
    font-size: 18px;
    color: #666;
  }
  .text {
    width: 18px;
    text-align: center;
    font-size: 17px;
  }
  .ai {
    background: linear-gradient(270deg, #d897fd, #33bcfc);
    background-clip: text;
    color: transparent;
    font-weight: 700;
  }

  &:hover {
    background-color: #f1f1f1;
  }
}
.popover-menu-item {
  display: flex;
  padding: 8px 10px;

  .icon {
    font-size: 18px;
    margin-right: 12px;
  }
}
.main-menu {
  width: 330px;
}
.ai-menu {
  background: linear-gradient(270deg, #f8edff, #d4f1ff);
  color: $themeColor;
  border-radius: $borderRadius;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  cursor: pointer;

  .icon {
    font-size: 22px;
    margin-right: 16px;
  }
  .aippt-content {
    display: flex;
    flex-direction: column;
  }
  .aippt {
    font-weight: 700;
    font-size: 16px;

    span {
      background: linear-gradient(270deg, #d897fd, #33bcfc);
      background-clip: text;
      color: transparent;
    }
  }
  .aippt-subtitle {
    font-size: 12px;
    color: #777;
    margin-top: 5px;
  }
}

.import-section {
  padding: 5px 0;

  .import-label {
    font-size: 12px;
    color: #999;
    margin-bottom: 6px;
  }
  .import-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }
  .import-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 12px 8px;
    border-radius: $borderRadius;
    border: 1px solid $borderColor;
    transition: all .2s;
    cursor: pointer;
  
    &:hover {
      background-color: #f1f1f1;
      border-color: $themeColor;
    }

    &:last-child {
      background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);

      &:hover {
        background: linear-gradient(135deg, #e8f0ff 0%, #dbe8ff 100%);
      }
    }

    .icon {
      font-size: 24px;
      margin-bottom: 2px;
    }
    .label {
      font-size: 12px;
      text-align: center;
    }
    .sub-label {
      font-size: 10px;
      color: #999;
    }
  }
}

.group-menu-item {
  height: 30px;
  display: flex;
  margin: 0 8px;
  padding: 0 2px;
  border-radius: $borderRadius;

  &:hover {
    background-color: #f1f1f1;
  }

  .menu-item {
    padding: 0 3px;
  }
  .arrow-btn {
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
  }
}
.title {
  height: 30px;
  margin-left: 2px;
  font-size: 13px;

  .title-input {
    width: 200px;
    height: 100%;
    padding-left: 0;
    padding-right: 0;

    ::v-deep(input) {
      height: 28px;
      line-height: 28px;
    }
  }
  .title-text {
    min-width: 20px;
    max-width: 400px;
    line-height: 30px;
    padding: 0 6px;
    border-radius: $borderRadius;
    cursor: pointer;

    @include ellipsis-oneline();

    &:hover {
      background-color: #f1f1f1;
    }
  }
}
.github-link {
  display: inline-block;
  height: 30px;
}

/* AIPPT 抽屉样式 */
.aippt-form {
  padding: 12px;
  .tips { font-size: 12px; color: #666; margin-bottom: 10px; }
  .field { margin-top: 8px; }
  .label { font-size: 12px; color: #555; margin-bottom: 6px; }
  .aippt-textarea {
    width: 100%; height: 300px; resize: vertical;
    padding: 8px; border: 1px solid $borderColor; border-radius: $borderRadius;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px; line-height: 1.6;
  }
  .btns { margin-top: 12px; display: flex; justify-content: flex-end; }
}
</style>
