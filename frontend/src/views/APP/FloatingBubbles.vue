<template>
  <div class="floating-bubbles">
    <!-- 主要泡泡群 -->
    <div class="bubbles-container">
      <div 
        v-for="bubble in bubbles" 
        :key="bubble.id"
        class="bubble"
        :style="bubble.style"
      >
        <div class="bubble-inner"></div>
      </div>
    </div>
    
    <!-- 背景装饰泡泡 -->
    <div class="decoration-bubbles">
      <div 
        v-for="deco in decorationBubbles" 
        :key="deco.id"
        class="decoration-bubble"
        :style="deco.style"
      ></div>
    </div>
    
    <!-- 中心加载提示 -->
    <div class="loading-content">
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <h2 class="loading-title">正在生成中...</h2>
      <p class="loading-subtitle">AI 正在为您精心制作 PPT</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted } from 'vue'

interface Bubble {
  id: number
  style: {
    left: string
    top: string
    width: string
    height: string
    animationDelay: string
    animationDuration: string
    background: string
  }
}

interface DecorationBubble {
  id: number
  style: {
    left: string
    top: string
    width: string
    height: string
    animationDelay: string
    animationDuration: string
    background: string
    opacity: string
  }
}

const bubbles = ref<Bubble[]>([])
const decorationBubbles = ref<DecorationBubble[]>([])

// 生成随机数
const random = (min: number, max: number) => Math.random() * (max - min) + min

// 生成渐变色
const generateGradient = () => {
  const colors = [
    ['#667eea', '#764ba2'],
    ['#f093fb', '#f5576c'],
    ['#4facfe', '#00f2fe'],
    ['#43e97b', '#38f9d7'],
    ['#fa709a', '#fee140'],
    ['#a8edea', '#fed6e3'],
    ['#ffecd2', '#fcb69f'],
    ['#ff9a9e', '#fecfef'],
    ['#ffebbf', '#f093fb'],
    ['#c2e9fb', '#a1c4fd']
  ]
  const color = colors[Math.floor(Math.random() * colors.length)]
  return `linear-gradient(135deg, ${color[0]} 0%, ${color[1]} 100%)`
}

// 创建主要泡泡
const createBubbles = () => {
  const newBubbles: Bubble[] = []
  for (let i = 0; i < 15; i++) {
    newBubbles.push({
      id: i,
      style: {
        left: `${random(-10, 110)}%`,
        top: `${random(-10, 110)}%`,
        width: `${random(60, 180)}px`,
        height: `${random(60, 180)}px`,
        animationDelay: `${random(0, 8)}s`,
        animationDuration: `${random(15, 25)}s`,
        background: generateGradient()
      }
    })
  }
  bubbles.value = newBubbles
}

// 创建装饰泡泡
const createDecorationBubbles = () => {
  const newDecorationBubbles: DecorationBubble[] = []
  for (let i = 0; i < 25; i++) {
    newDecorationBubbles.push({
      id: i,
      style: {
        left: `${random(-5, 105)}%`,
        top: `${random(-5, 105)}%`,
        width: `${random(20, 80)}px`,
        height: `${random(20, 80)}px`,
        animationDelay: `${random(0, 10)}s`,
        animationDuration: `${random(10, 30)}s`,
        background: generateGradient(),
        opacity: `${random(0.1, 0.4)}`
      }
    })
  }
  decorationBubbles.value = newDecorationBubbles
}

let intervalId: number

onMounted(() => {
  createBubbles()
  createDecorationBubbles()
  
  // 定期重新生成泡泡位置，创造更多动态效果
  intervalId = setInterval(() => {
    createBubbles()
    createDecorationBubbles()
  }, 20000)
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
  }
})
</script>

<style lang="scss" scoped>
.floating-bubbles {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f1f5f9 100%);
  z-index: 10;
}

.bubbles-container {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bubble {
  position: absolute;
  border-radius: 50%;
  background: var(--bubble-bg);
  opacity: 0.6;
  filter: blur(1px);
  animation: float infinite linear;
  
  .bubble-inner {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: inherit;
    position: relative;
    
    &::before {
      content: '';
      position: absolute;
      top: 20%;
      left: 20%;
      width: 30%;
      height: 30%;
      background: rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      filter: blur(2px);
    }
  }
}

.decoration-bubbles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.decoration-bubble {
  position: absolute;
  border-radius: 50%;
  background: var(--bubble-bg);
  animation: floatSlow infinite linear;
  filter: blur(2px);
}

.loading-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 20;
}

.loading-spinner {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 32px;
}

.spinner-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 3px solid transparent;
  border-radius: 50%;
  animation: spin 2s linear infinite;
  
  &:nth-child(1) {
    border-top-color: #667eea;
    animation-duration: 2s;
  }
  
  &:nth-child(2) {
    border-right-color: #764ba2;
    animation-duration: 3s;
    animation-direction: reverse;
    width: 80%;
    height: 80%;
    top: 10%;
    left: 10%;
  }
  
  &:nth-child(3) {
    border-bottom-color: #f093fb;
    animation-duration: 4s;
    width: 60%;
    height: 60%;
    top: 20%;
    left: 20%;
  }
}

.loading-title {
  font-size: 28px;
  font-weight: 800;
  margin: 0 0 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: titlePulse 2s ease-in-out infinite;
}

.loading-subtitle {
  font-size: 16px;
  color: #64748b;
  margin: 0;
  font-weight: 500;
  animation: subtitleFade 3s ease-in-out infinite;
}

/* 动画定义 */
@keyframes float {
  0% {
    transform: translateY(0px) translateX(0px) rotate(0deg);
  }
  33% {
    transform: translateY(-30px) translateX(20px) rotate(120deg);
  }
  66% {
    transform: translateY(20px) translateX(-20px) rotate(240deg);
  }
  100% {
    transform: translateY(0px) translateX(0px) rotate(360deg);
  }
}

@keyframes floatSlow {
  0% {
    transform: translateY(0px) translateX(0px) rotate(0deg) scale(1);
  }
  25% {
    transform: translateY(-20px) translateX(15px) rotate(90deg) scale(1.1);
  }
  50% {
    transform: translateY(10px) translateX(-10px) rotate(180deg) scale(0.9);
  }
  75% {
    transform: translateY(-15px) translateX(-20px) rotate(270deg) scale(1.05);
  }
  100% {
    transform: translateY(0px) translateX(0px) rotate(360deg) scale(1);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes titlePulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.9;
  }
}

@keyframes subtitleFade {
  0%, 100% {
    opacity: 0.7;
  }
  50% {
    opacity: 1;
  }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .loading-spinner {
    width: 80px;
    height: 80px;
    margin-bottom: 24px;
  }
  
  .loading-title {
    font-size: 22px;
  }
  
  .loading-subtitle {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .loading-spinner {
    width: 60px;
    height: 60px;
  }
  
  .loading-title {
    font-size: 18px;
  }
}
</style>