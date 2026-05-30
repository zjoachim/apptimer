<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const props = defineProps(['snapshot', 'fmt'])
const dates = ref([])
const selDate = ref('')
const report = ref('')

async function loadDates() {
  dates.value = await api.getAllDates()
  if (dates.value.length > 0) {
    selDate.value = dates.value[dates.value.length - 1]
    await loadReport()
  }
}
async function loadReport() {
  if (!selDate.value) return
  const r = await api.getHistory(selDate.value)
  report.value = r.report
}
onMounted(loadDates)
</script>

<template>
  <div class="p-5 space-y-3">
    <div class="flex gap-2 items-center">
      <select v-model="selDate" @change="loadReport" class="rounded-full px-3 py-1 text-xs border" style="background:var(--bg);color:var(--text);border-color:var(--border);font-weight:300">
        <option v-for="d in dates" :key="d" :value="d">{{ d }}</option>
      </select>
      <button @click="loadDates" class="px-3 py-1 text-xs rounded-full transition-colors" style="color:var(--text-dim);border:1px solid var(--border);font-weight:300">刷新</button>
    </div>
    <pre class="text-xs p-4 rounded-lg whitespace-pre-wrap max-h-96 overflow-auto font-mono leading-relaxed" style="background:var(--bg-soft);color:var(--text-dim);border:1px solid var(--border)">{{ report }}</pre>
  </div>
</template>
