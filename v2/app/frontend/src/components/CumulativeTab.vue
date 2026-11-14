<script setup>
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api.js'

const props = defineProps(['snapshot', 'fmt'])
const exportingCumCsv = ref(false)
const chartType = ref('bar')
const chartEl = ref(null)
let _chart = null

const cumulative = computed(() => props.snapshot?.cumulative_usage ?? {})
const categories = computed(() => props.snapshot?.categories ?? {})
const cumTotal = computed(() => props.snapshot?.total_cumulative || 1)
const appList = computed(() => Object.entries(cumulative.value).slice(0, 30))

function drawChart() {
  if (!chartEl.value) return
  if (!_chart) _chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  const data = Object.entries(cumulative.value).slice(0, 10)
  if (data.length === 0) { _chart.clear(); return }
  const base = { backgroundColor:'transparent', textStyle:{ color:'rgba(255,255,255,0.45)', fontSize:10, fontFamily:'Inter,PingFang SC,Microsoft YaHei' } }
  const colors = ['#fff','#ccc','#aaa','#999','#888','#777','#666','#555','#444','#333']
  if (chartType.value === 'pie') {
    _chart.setOption({ ...base, tooltip:{ formatter:'{b}: {d}%' },
      series:[{ type:'pie', radius:['45%','70%'], center:['50%','48%'],
        data: data.map(([app,sec],i)=>({ name:app,value:sec,itemStyle:{ color:colors[i%10] } })),
        label:{ color:'rgba(255,255,255,0.45)', fontSize:10 } }] })
  } else {
    _chart.setOption({ ...base, tooltip:{ formatter:p=>`${p.name}<br/>${props.fmt(p.value)}` },
      grid:{ left:60,right:20,top:20,bottom:60 },
      xAxis:{ type:'category', data:data.map(([a])=>a.length>10?a.slice(0,10)+'..':a), axisLabel:{ color:'rgba(255,255,255,0.35)',fontSize:9,rotate:45 }, axisLine:{ lineStyle:{ color:'rgba(255,255,255,0.08)' } } },
      yAxis:{ type:'value', axisLabel:{ color:'rgba(255,255,255,0.35)',fontSize:10,formatter:v=>props.fmt(v) }, splitLine:{ lineStyle:{ color:'rgba(255,255,255,0.04)' } } },
      series:[{ type:'bar', data:data.map(([,sec],i)=>({ value:sec, itemStyle:{ color:colors[i%10], borderRadius:[2,2,0,0] } })),
        label:{ show:true,position:'top',color:'rgba(255,255,255,0.35)',fontSize:9,formatter:p=>props.fmt(p.value) } }] })
  }
}

watch(chartType, ()=>nextTick(drawChart))
watch(()=>props.snapshot, ()=>nextTick(drawChart), { deep:true })
onMounted(()=>nextTick(drawChart))
async function doExportCumulativeCsv() {
  exportingCumCsv.value = true
  try {
    const r = await api.exportCumulativeCsv()
    if (r.ok) alert(`CSV 已导出到:\n${r.path}`)
    else alert(`导出失败: ${r.error}`)
  } finally { exportingCumCsv.value = false }
}

onUnmounted(()=>{ if(_chart) _chart.dispose() })
</script>

<template>
  <div class="p-5 space-y-4">
    <div class="text-center">
      <div class="text-2xl tracking-wider" style="font-weight:200;letter-spacing:0.06em">{{ fmt(cumTotal) }}</div>
      <div class="text-xs mt-1" style="color:var(--text-dim);font-weight:300">累计总使用时间</div>
    </div>

    <div class="flex gap-2 justify-center">
      <button @click="chartType='bar'" :style="chartType==='bar'?'background:var(--accent);color:var(--text)':'color:var(--text-dim)'"
        class="px-3 py-1 text-xs rounded-full transition-colors" style="border:1px solid var(--border);font-weight:300">柱状图</button>
      <button @click="chartType='pie'" :style="chartType==='pie'?'background:var(--accent);color:var(--text)':'color:var(--text-dim)'"
        class="px-3 py-1 text-xs rounded-full transition-colors" style="border:1px solid var(--border);font-weight:300">饼图</button>
    </div>

    <div ref="chartEl" class="w-full h-60"></div>

    <div style="border-top:1px solid var(--border)"></div>

    <div v-if="appList.length===0" class="text-center py-12 text-xs" style="color:var(--text-dim);font-weight:300">暂无累计数据</div>
    <div v-for="[app,sec] in appList" :key="app"
      class="flex items-center gap-3 text-xs py-2 px-3 rounded-lg" style="border:1px solid var(--border)">
      <span class="flex-1 truncate" style="font-weight:300">{{ app }}</span>
      <span class="w-10 text-right" style="color:var(--text-dim)">{{ categories[app]||'' }}</span>
      <span class="w-20 text-right font-mono" style="color:var(--text)">{{ fmt(sec) }}</span>
      <span class="w-12 text-right" style="color:var(--text-dim)">{{ (sec/cumTotal*100).toFixed(1) }}%</span>
      <div class="w-16 h-px rounded" style="background:var(--border)">
        <div class="h-px rounded" style="background:var(--text)" :style="{width:Math.min(sec/cumTotal*100,100)+'%'}" />
      </div>
    </div>

    <div class="flex justify-center pt-4" style="border-top:1px solid var(--border)">
      <button @click="doExportCumulativeCsv" :disabled="exportingCumCsv"
        class="px-4 py-2 text-xs rounded-full transition-colors"
        style="color:var(--text-dim);border:1px solid var(--border);font-weight:300;background:transparent">
        {{ exportingCumCsv ? '导出中...' : '导出累计 CSV' }}
      </button>
    </div>
  </div>
</template>
