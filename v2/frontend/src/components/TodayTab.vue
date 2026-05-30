<script setup>
import { computed } from 'vue'
const props = defineProps(['snapshot', 'fmt'])

const usage = computed(() => props.snapshot?.today_usage ?? {})
const categories = computed(() => props.snapshot?.categories ?? {})
const total = computed(() => props.snapshot?.total_seconds || 1)
const cumulative = computed(() => props.snapshot?.cumulative_usage ?? {})

const catStats = computed(() => {
  const m = {}
  for (const [app, sec] of Object.entries(usage.value)) {
    const cat = categories.value[app] || '未分类'
    m[cat] = (m[cat] || 0) + sec
  }
  return m
})
const catTotal = computed(() => Math.max(Object.values(catStats.value).reduce((a, b) => a + b, 0), 1))
const top = computed(() => Object.entries(usage.value).slice(0, 30))
</script>

<template>
  <div class="p-5 space-y-4">
    <!-- 总时间 -->
    <div class="text-center py-6">
      <div class="text-3xl tracking-wider" style="font-weight:200;letter-spacing:0.06em">{{ fmt(total) }}</div>
      <div class="text-xs mt-2" style="color:var(--text-dim);font-weight:300">今日总使用时间</div>
    </div>

    <!-- 分类标签 -->
    <div class="flex flex-wrap gap-1.5">
      <span v-for="(sec, cat) in catStats" :key="cat"
        class="px-3 py-1 text-xs rounded-full"
        style="background:var(--accent);color:var(--text);font-weight:300;letter-spacing:0.04em"
      >{{ cat }} {{ (sec / catTotal * 100).toFixed(0) }}%</span>
      <span v-if="Object.keys(catStats).length===0" class="text-xs" style="color:var(--text-dim)">暂无分类数据</span>
    </div>

    <!-- 分隔 -->
    <div style="border-top:1px solid var(--border)"></div>

    <!-- 列表 -->
    <div v-if="top.length===0" class="text-center py-12 text-xs" style="color:var(--text-dim);font-weight:300">暂无数据，等待程序活动...</div>
    <div v-for="[app, sec] in top" :key="app"
      class="flex items-center gap-3 text-xs py-2 px-3 rounded-lg transition-colors duration-200"
      style="border:1px solid var(--border)"
    >
      <span class="flex-1 truncate" style="font-weight:300">{{ app }}</span>
      <span class="w-10 text-right" style="color:var(--text-dim)">{{ categories[app] || '' }}</span>
      <span class="w-16 text-right font-mono" style="color:var(--text)">{{ fmt(sec) }}</span>
      <span class="w-16 text-right font-mono" style="color:var(--text-dim)">{{ fmt(cumulative[app]||0) }}</span>
      <span class="w-10 text-right" style="color:var(--text-dim)">{{ (sec/total*100).toFixed(1) }}%</span>
      <div class="w-16 h-px rounded" style="background:var(--border)">
        <div class="h-px rounded" style="background:var(--text);width:Math.min((sec/total*100),100)+'%'"
          :style="{ width: Math.min((sec/total*100),100) + '%' }" />
      </div>
    </div>
  </div>
</template>
