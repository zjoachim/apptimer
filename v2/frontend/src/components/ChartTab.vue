<script setup>
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps(['snapshot', 'fmt'])
const chartType = ref('pie')
const source = ref('today')
const chartEl = ref(null)
let _chart = null

const todayUsage = computed(() => props.snapshot?.today_usage ?? {})
const cumUsage = computed(() => props.snapshot?.cumulative_usage ?? {})

function draw() {
  if (!chartEl.value) return
  if (!_chart) _chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  const data = Object.entries(source.value==='today'?todayUsage.value:cumUsage.value).slice(0,10)
  if (data.length===0) { _chart.clear(); return }
  const base = { backgroundColor:'transparent', textStyle:{ color:'rgba(255,255,255,0.45)',fontSize:10,fontFamily:'Inter,PingFang SC,Microsoft YaHei' } }
  const colors = ['#fff','#ddd','#bbb','#999','#888','#777','#666','#555','#444','#333']
  if (chartType.value==='pie') {
    _chart.setOption({ ...base, tooltip:{ formatter:'{b}: {d}%' },
      series:[{ type:'pie',radius:['45%','70%'],center:['50%','48%'],
        data:data.map(([app,sec],i)=>({ name:app,value:sec,itemStyle:{color:colors[i%10]} })),
        label:{ color:'rgba(255,255,255,0.45)',fontSize:10 } }] })
  } else {
    _chart.setOption({ ...base, tooltip:{ formatter:p=>`${p.name}<br/>${props.fmt(p.value)}` },
      grid:{ left:60,right:20,top:20,bottom:60 },
      xAxis:{ type:'category',data:data.map(([a])=>a.length>10?a.slice(0,10)+'..':a),axisLabel:{ color:'rgba(255,255,255,0.35)',fontSize:9,rotate:45 },axisLine:{ lineStyle:{ color:'rgba(255,255,255,0.08)' } } },
      yAxis:{ type:'value',axisLabel:{ color:'rgba(255,255,255,0.35)',fontSize:10,formatter:v=>props.fmt(v) },splitLine:{ lineStyle:{ color:'rgba(255,255,255,0.04)' } } },
      series:[{ type:'bar',data:data.map(([,sec],i)=>({ value:sec,itemStyle:{color:colors[i%10],borderRadius:[2,2,0,0]} })),
        label:{ show:true,position:'top',color:'rgba(255,255,255,0.35)',fontSize:9,formatter:p=>props.fmt(p.value) } }] })
  }
}

watch([chartType,source],()=>nextTick(draw))
watch(()=>props.snapshot,()=>nextTick(draw),{ deep:true })
onMounted(()=>nextTick(draw))
onUnmounted(()=>{ if(_chart) _chart.dispose() })
</script>

<template>
  <div class="p-5 space-y-3">
    <div class="flex gap-2 justify-center">
      <button v-for="t in [{k:'pie',l:'饼图'},{k:'bar',l:'柱状图'}]" :key="t.k" @click="chartType=t.k"
        :style="chartType===t.k?'background:var(--accent);color:var(--text)':'color:var(--text-dim)'"
        class="px-3 py-1 text-xs rounded-full transition-colors" style="border:1px solid var(--border);font-weight:300">{{ t.l }}</button>
      <span class="mx-1" style="color:var(--text-dim);font-weight:100">|</span>
      <button v-for="s in [{k:'today',l:'今日'},{k:'cumulative',l:'累计'}]" :key="s.k" @click="source=s.k"
        :style="source===s.k?'background:var(--accent);color:var(--text)':'color:var(--text-dim)'"
        class="px-3 py-1 text-xs rounded-full transition-colors" style="border:1px solid var(--border);font-weight:300">{{ s.l }}</button>
    </div>
    <div ref="chartEl" style="height:calc(100vh - 150px);min-height:400px"></div>
  </div>
</template>
