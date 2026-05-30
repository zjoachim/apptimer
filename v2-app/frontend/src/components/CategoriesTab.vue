<script setup>
import { ref, watch } from 'vue'
import api from '../api.js'

const props = defineProps(['snapshot', 'fmt'])
const selApp = ref('')
const selCat = ref('未分类')
const goalApp = ref('')
const goalMin = ref(60)

const appList = ref([])
watch(() => props.snapshot, () => {
  appList.value = Object.keys(props.snapshot?.cumulative_usage ?? {})
}, { immediate: true })

const categories = () => props.snapshot?.categories ?? {}
const goals = () => props.snapshot?.goals ?? {}
const todayUsage = () => props.snapshot?.today_usage ?? {}
const catOptions = ['工作', '学习', '娱乐', '社交', '开发', '设计', '其他', '未分类']

async function setCategory() {
  if (!selApp.value) return
  const c = { ...categories(), [selApp.value]: selCat.value }
  await api.saveCategories(c)
}
async function delCategory(app) {
  const c = { ...categories() }
  delete c[app]
  await api.saveCategories(c)
}
async function setGoal() {
  if (!goalApp.value || goalMin.value <= 0) return
  const g = { ...goals(), [goalApp.value]: goalMin.value * 60 }
  await api.saveGoals(g)
}
async function delGoal(app) {
  const g = { ...goals() }
  delete g[app]
  await api.saveGoals(g)
}
</script>

<template>
  <div class="p-5 grid grid-cols-2 gap-5">
    <!-- 分类 -->
    <div class="space-y-2">
      <div class="text-xs tracking-wider" style="font-weight:300;letter-spacing:0.06em">程序分类</div>
      <button @click="setCategory" class="px-3 py-1 text-xs rounded-full self-start" style="background:var(--accent);color:var(--text);border:1px solid var(--border);font-weight:300">设置分类</button>
      <div class="flex gap-1 items-center">
        <select v-model="selApp" class="flex-1 px-2 py-1 text-xs border rounded-full" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300">
          <option v-for="a in appList" :key="a" :value="a">{{ a }}</option>
        </select>
        <select v-model="selCat" class="w-16 px-1 py-1 text-xs border rounded-full" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300">
          <option v-for="c in catOptions" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
      <div v-for="[app, cat] in Object.entries(categories())" :key="app"
        class="flex items-center gap-2 text-xs py-1.5 px-3 rounded-lg" style="border:1px solid var(--border)">
        <span class="truncate flex-1" style="font-weight:300">{{ app }}</span>
        <span style="color:var(--text-dim)">{{ cat }}</span>
        <button @click="delCategory(app)" class="text-xs hover:opacity-80" style="color:rgba(255,100,100,0.5)" title="删除分类">✕</button>
      </div>
    </div>

    <!-- 目标 -->
    <div class="space-y-2">
      <div class="text-xs tracking-wider" style="font-weight:300;letter-spacing:0.06em">每日目标</div>
      <button @click="setGoal" class="px-3 py-1 text-xs rounded-full self-start" style="background:var(--accent);color:var(--text);border:1px solid var(--border);font-weight:300">设定目标</button>
      <div class="flex gap-1 items-center">
        <select v-model="goalApp" class="flex-1 px-2 py-1 text-xs border rounded-full" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300">
          <option v-for="a in appList" :key="a" :value="a">{{ a }}</option>
        </select>
        <input v-model.number="goalMin" type="number" min="1" max="480" class="w-10 rounded-full px-1 py-1 text-xs border text-center" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300" />
        <span class="text-xs" style="color:var(--text-dim)">分</span>
      </div>
      <div v-for="[app, goalSec] in Object.entries(goals())" :key="app"
        class="flex items-center gap-2 text-xs py-1.5 px-3 rounded-lg" style="border:1px solid var(--border)">
        <span class="truncate flex-1" style="font-weight:300">{{ app }}</span>
        <span style="color:var(--text-dim)">{{ fmt(goalSec) }}</span>
        <span :style="{color:(todayUsage()[app]||0)>goalSec?'rgba(255,100,100,0.6)':'rgba(100,255,100,0.4)'}">{{ (todayUsage()[app]||0)>goalSec?'超':'✓' }}</span>
        <button @click="delGoal(app)" class="text-xs hover:opacity-80" style="color:rgba(255,100,100,0.5)" title="删除目标">✕</button>
      </div>
    </div>
  </div>
</template>
