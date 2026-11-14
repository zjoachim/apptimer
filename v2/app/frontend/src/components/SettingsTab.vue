<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const props = defineProps(['snapshot', 'fmt'])
const idleThreshold = ref(120)
const saveInterval = ref(30)
const retentionDays = ref(60)
const reminderInterval = ref(45)
const startupEnabled = ref(false)
const saved = ref(false)

onMounted(async () => {
  const r = await api.getStartupStatus()
  startupEnabled.value = r.enabled
})

async function apply() {
  await api.saveSettings({
    idle_threshold: idleThreshold.value,
    auto_save_interval: saveInterval.value,
    retention_days: retentionDays.value,
    reminder_interval: reminderInterval.value * 60,
  })
  saved.value = true
  setTimeout(() => saved.value = false, 2000)
}

async function uninstall() {
  if (!confirm('确认卸载 AppTimer？\n\n将移除开机自启动项。')) return
  const deleteData = confirm('是否删除所有使用记录？\n\n选「确定」将永久删除所有历史数据\n选「取消」保留数据')
  await api.uninstall(deleteData)
}

async function toggleStartup() {
  const r = await api.setStartup(startupEnabled.value)
  if (!r.ok) { startupEnabled.value = !startupEnabled.value; alert(r.error) }
}
</script>

<template>
  <div class="p-5 max-w-md mx-auto space-y-3">
    <div class="text-xs tracking-wider pb-2" style="font-weight:300;letter-spacing:0.06em">设置</div>

    <label class="flex items-center justify-between py-2 px-3 rounded-lg" style="border:1px solid var(--border)">
      <span class="text-xs" style="font-weight:300">开机自启动</span>
      <input type="checkbox" v-model="startupEnabled" @change="toggleStartup" class="accent-white" />
    </label>

    <div v-for="item in [
      { label:'空闲阈值 (秒)', v:idleThreshold, min:30, max:600 },
      { label:'保存间隔 (秒)', v:saveInterval, min:10, max:300 },
      { label:'数据保留 (天, 0=永久)', v:retentionDays, min:0, max:365 },
      { label:'连续提醒 (分钟, 0=关闭)', v:reminderInterval, min:0, max:180 },
    ]" :key="item.label" class="flex items-center justify-between py-2 px-3 rounded-lg" style="border:1px solid var(--border)">
      <span class="text-xs" style="color:var(--text-dim);font-weight:300">{{ item.label }}</span>
      <input v-model.number="item.v.value" type="number" :min="item.min" :max="item.max"
        class="w-20 rounded-full px-3 py-1.5 text-xs border text-center transition-colors" style="background:rgba(255,255,255,0.06);color:var(--text);border-color:rgba(255,255,255,0.2);font-weight:300" />
    </div>

    <button @click="apply" class="w-full py-2 text-xs rounded-full transition-colors" style="background:var(--accent);color:var(--text);border:1px solid var(--border);font-weight:300">
      {{ saved ? '已保存' : '应用设置' }}
    </button>

    <div class="flex gap-2 pt-3" style="border-top:1px solid var(--border)">
      <button @click="api.openDataFolder()" class="flex-1 py-2 text-xs rounded-full transition-colors" style="color:var(--text-dim);border:1px solid var(--border);font-weight:300">打开数据文件夹</button>
      <button @click="uninstall" class="flex-1 py-2 text-xs rounded-full transition-colors" style="color:var(--text-dim);border:1px solid var(--border);font-weight:300">卸载</button>
    </div>

    <div class="text-center text-xs pt-4" style="color:rgba(255,255,255,0.15);font-weight:300">AppTimer v2.0 — pyweb + Vue3</div>
  </div>
</template>
