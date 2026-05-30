<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import TodayTab from './components/TodayTab.vue'
import CumulativeTab from './components/CumulativeTab.vue'
import ChartTab from './components/ChartTab.vue'
import TrendTab from './components/TrendTab.vue'
import CategoriesTab from './components/CategoriesTab.vue'
import HistoryTab from './components/HistoryTab.vue'
import SettingsTab from './components/SettingsTab.vue'
import api from './api.js'

const snapshot = ref(null)
const activeTab = ref('today')
const exporting = ref('')
let _timer = null

const tabs = [
  { key: 'today', label: '概览' },
  { key: 'cumulative', label: '累计' },
  { key: 'chart', label: '图表' },
  { key: 'trend', label: '趋势' },
  { key: 'categories', label: '分类' },
  { key: 'history', label: '历史' },
  { key: 'settings', label: '设置' },
]

const totalSeconds = computed(() => snapshot.value?.total_seconds ?? 0)
const currentApp = computed(() => snapshot.value?.current_app ?? '空闲')
const todayStr = computed(() => snapshot.value?.today_str ?? '--')

async function refresh() {
  try { snapshot.value = await api.getSnapshot() } catch (e) { /* ignore */ }
}

function fmtDuration(sec) {
  if (!sec || sec < 0) return '0秒'
  sec = Math.floor(sec)
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

async function doExportPdf() {
  exporting.value = 'pdf'
  try {
    const r = await api.exportPdf()
    if (r.ok) alert(`PDF 已导出到:\n${r.path}`)
    else alert(`导出失败: ${r.error}`)
  } finally { exporting.value = '' }
}

async function doExportCsv() {
  exporting.value = 'csv'
  try {
    const r = await api.exportCsv()
    if (r.ok) alert(`CSV 已导出到:\n${r.path}`)
    else alert(`导出失败: ${r.error}`)
  } finally { exporting.value = '' }
}

async function doQuit() {
  if (confirm('确认退出 AppTimer？')) {
    await api.quitApp()
  }
}

onMounted(() => { refresh(); _timer = setInterval(refresh, 3000) })
onUnmounted(() => { if (_timer) clearInterval(_timer) })
</script>

<template>
  <div class="h-screen flex flex-col" style="background:var(--bg)">
    <!-- 顶栏：极简 -->
    <header class="flex items-center justify-between px-5 h-11 shrink-0" style="border-bottom:1px solid var(--border);backdrop-filter:blur(12px)">
      <div class="flex items-center gap-3">
        <span class="text-xs tracking-wider" style="font-weight:300;color:var(--text);letter-spacing:0.06em">AppTimer</span>
        <span class="text-xs" style="color:var(--text-dim);font-weight:300">v2.0</span>
      </div>
      <div class="flex items-center gap-2" data-test="export-btns-2026">
        <button @click="doExportPdf" :disabled="exporting==='pdf'"
          class="px-3 py-1 text-xs rounded-full transition-colors"
          style="color:var(--text-dim);border:1px solid var(--border);font-weight:300;background:transparent">
          {{ exporting==='pdf' ? '导出中...' : '导出 PDF' }}
        </button>
        <button @click="doExportCsv" :disabled="exporting==='csv'"
          class="px-3 py-1 text-xs rounded-full transition-colors"
          style="color:var(--text-dim);border:1px solid var(--border);font-weight:300;background:transparent">
          {{ exporting==='csv' ? '导出中...' : '导出 CSV' }}
        </button>
        <button @click="doQuit"
          class="px-3 py-1 text-xs rounded-full transition-colors"
          style="color:var(--text-dim);border:1px solid var(--border);font-weight:300;background:transparent">
          退出
        </button>
      </div>
      <div class="flex items-center gap-4 text-xs" style="font-weight:300;color:var(--text-dim)">
        <span>{{ todayStr }}</span>
        <span>{{ currentApp }}</span>
        <span class="text-xs font-mono" style="color:var(--text)">{{ fmtDuration(totalSeconds) }}</span>
      </div>
    </header>

    <!-- Tab 导航 -->
    <nav class="flex gap-0 px-5 shrink-0" style="border-bottom:1px solid var(--border)">
      <button
        v-for="t in tabs" :key="t.key" @click="activeTab = t.key"
        :style="activeTab === t.key
          ? 'color:var(--text);border-bottom:1px solid var(--text)'
          : 'color:var(--text-dim);border-bottom:1px solid transparent'"
        class="px-4 py-2 text-xs transition-colors duration-200"
        style="font-weight:300;letter-spacing:0.04em;background:transparent"
      >{{ t.label }}</button>
    </nav>

    <!-- 内容 -->
    <main class="flex-1 overflow-auto">
      <TodayTab     v-if="activeTab === 'today'"      :snapshot="snapshot"  :fmt="fmtDuration" />
      <CumulativeTab v-if="activeTab === 'cumulative'" :snapshot="snapshot"  :fmt="fmtDuration" />
      <ChartTab     v-if="activeTab === 'chart'"       :snapshot="snapshot"  :fmt="fmtDuration" />
      <TrendTab     v-if="activeTab === 'trend'"       :snapshot="snapshot"  :fmt="fmtDuration" />
      <CategoriesTab v-if="activeTab === 'categories'" :snapshot="snapshot"  :fmt="fmtDuration" />
      <HistoryTab   v-if="activeTab === 'history'"     :snapshot="snapshot"  :fmt="fmtDuration" />
      <SettingsTab  v-if="activeTab === 'settings'"    :snapshot="snapshot"  :fmt="fmtDuration" />
    </main>
  </div>
</template>
