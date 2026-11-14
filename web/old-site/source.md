# 源代码

AppTimer 全部功能由单个文件 `app_timer.py` 实现，约 1200 行。

<button id="copy-btn" style="cursor:pointer;padding:0.6rem 1.5rem;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:#fff;border-radius:4px;font-size:0.9rem;font-family:inherit;">复制源代码</button>
<span id="copy-msg" style="margin-left:0.8rem;font-size:0.8rem;color:rgba(255,255,255,0.4);"></span>

<script setup>
import { onMounted } from 'vue'
onMounted(async () => {
  const btn = document.getElementById('copy-btn')
  const msg = document.getElementById('copy-msg')
  if (!btn) return
  btn.onclick = async () => {
    try {
      const res = await fetch('/app_timer.py')
      const text = await res.text()
      await navigator.clipboard.writeText(text)
      msg.textContent = '已复制'
      setTimeout(() => { msg.textContent = '' }, 2000)
    } catch {
      msg.textContent = '复制失败，请手动从 GitHub 获取'
    }
  }
})
</script>
