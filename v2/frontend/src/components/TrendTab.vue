<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api.js'

const props = defineProps(['snapshot', 'fmt'])
const app1 = ref('')
const app2 = ref('')
const days = ref(7)
const chartEl = ref(null)
let _chart = null

const appList = ref([])

function updateAppList() {
  const cum = props.snapshot?.cumulative_usage ?? {}
  appList.value = Object.keys(cum)
  if (!app1.value && appList.value.length > 0) app1.value = appList.value[0]
}

async function draw() {
  if (!app1.value || !chartEl.value) return
  if (!_chart) _chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  const d1 = await api.getTrend(app1.value, days.value)
  const d2 = app2.value ? await api.getTrend(app2.value, days.value) : null

  const series = [{
    name: app1.value, type: 'line', smooth: true,
    data: d1.map(x => x.seconds),
    lineStyle: { color: 'rgba(255,255,255,0.6)', width: 1 },
    itemStyle: { color: 'rgba(255,255,255,0.6)' },
  }]
  if (d2) series.push({
    name: app2.value, type: 'line', smooth: true,
    data: d2.map(x => x.seconds),
    lineStyle: { color: 'rgba(255,255,255,0.25)', width: 1 },
    itemStyle: { color: 'rgba(255,255,255,0.25)' },
  })

  _chart.setOption({
    backgroundColor: 'transparent',
    textStyle: { color: 'rgba(255,255,255,0.45)', fontSize: 10, fontFamily: 'Inter,PingFang SC,Microsoft YaHei' },
    tooltip: { trigger: 'axis', formatter: p => p.map(x => `${x.seriesName}: ${props.fmt(x.value)}`).join('<br/>') },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: d1.map(x => x.date.slice(5)), axisLabel: { color: 'rgba(255,255,255,0.35)', fontSize: 10 }, axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } } },
    yAxis: { type: 'value', axisLabel: { color: 'rgba(255,255,255,0.35)', fontSize: 10, formatter: v => props.fmt(v) }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    legend: { data: d2 ? [app1.value, app2.value] : [app1.value], textStyle: { color: 'rgba(255,255,255,0.45)', fontSize: 9 }, bottom: 0 },
    series,
  })
}

watch([app1, app2, days], () => nextTick(draw))
watch(() => props.snapshot, () => { updateAppList(); nextTick(draw) }, { deep: true })
onMounted(() => { updateAppList(); nextTick(draw) })
onUnmounted(() => { if (_chart) _chart.dispose() })
</script>

<template>
  <div class="p-5 space-y-3">
    <div class="flex flex-wrap gap-2 items-center text-xs" style="font-weight:300">
      <select v-model="app1" class="rounded-full px-3 py-1 text-xs border" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300">
        <option v-for="a in appList" :key="a" :value="a">{{ a }}</option>
      </select>
      <span style="color:var(--text-dim)">vs</span>
      <select v-model="app2" class="rounded-full px-3 py-1 text-xs border" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300">
        <option value="">--</option>
        <option v-for="a in appList" :key="a" :value="a">{{ a }}</option>
      </select>
      <select v-model.number="days" class="rounded-full px-3 py-1 text-xs border" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300">
        <option :value="3">3天</option>
        <option :value="7">7天</option>
        <option :value="14">14天</option>
        <option :value="30">30天</option>
      </select>
    </div>
    <div ref="chartEl" class="w-full h-80"></div>
  </div>
</template>
