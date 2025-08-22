import { createRouter, createWebHistory } from 'vue-router'
import Editor from '@/views/Editor/index.vue'

const routes = [
  {
    path: '/',
    name: 'Outline',
    component: () => import('@/views/Outline/index.vue')
  },
  {
    path: '/editor',
    name: 'Editor',
    component: Editor
  },
  {
    path: '/ppt',
    name: 'PPT',
    component: () => import('@/views/PPT/index.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
