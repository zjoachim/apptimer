---
layout: home
title: AppTimer

hero:
  name: AppTimer
  text: 清楚你的时间去哪了
  tagline: 自动追踪 Windows 程序使用时长，分类统计，可视化报表
  actions:
    - theme: brand
      text: 下载
      link: /AppTimer.exe
    - theme: alt
      text: 使用指南
      link: /guide
---

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: -webkit-linear-gradient(120deg, #aaa, #fff);
}

/* ── 桌面端：左画布右文字 ── */
#hero-clock-canvas {
  position: fixed; left: 0; top: 0;
  width: 67vw; height: 100vh;
  z-index: 0; pointer-events: none;
}
.VPHome { max-width: none !important; }
.VPHero {
  margin-left: 67vw !important; width: 33vw !important;
  height: 100vh; display: flex; align-items: center;
}
.VPHero .container { max-width: none !important; margin: 0 2rem; }
.VPHero .main { text-align: left; padding-left: 0.5rem; }
.VPHero .name { font-size: 2.4rem !important; letter-spacing: 0.06em; }
.VPHero .text {
  font-size: 1.1rem !important; white-space: nowrap;
  margin-left: -0.3rem;
}
.VPHero .tagline { text-align: left; font-size: 0.85rem !important; }
.VPHero .actions { justify-content: flex-start; }

/* ── 移动端：画布居上，文字居下 ── */
@media (max-width: 768px) {
  html, body { overflow: auto !important; }

  #hero-clock-canvas {
    width: 100vw !important; height: 55vh !important;
    top: 0; left: 0;
  }

  .VPHero {
    margin-left: 0 !important; width: 100vw !important;
    height: auto; min-height: auto;
    padding: 58vh 1.5rem 3rem;
    display: block;
  }
  .VPHero .name { font-size: 1.8rem !important; }
  .VPHero .text { font-size: 1rem !important; white-space: normal !important; margin-left: 0 !important; }
  .VPHero .tagline { font-size: 0.8rem !important; }

  .feature-list { margin-left: 0 !important; width: 100vw !important; padding: 2rem 1.5rem 4rem; }
}
</style>

<div class="feature-list">
<div class="item"><div class="idx">01</div><h3>自动追踪</h3><p>后台静默运行，检测活动窗口，离座自动暂停</p></div>
<div class="item"><div class="idx">02</div><h3>程序分类</h3><p>工作、学习、娱乐、社交、开发、设计等标签</p></div>
<div class="item"><div class="idx">03</div><h3>日报周报月报</h3><p>按日期组织数据，自动生成报表和趋势对比</p></div>
<div class="item"><div class="idx">04</div><h3>饼图 + 柱状图</h3><p>内置可视化图表，占比趋势一目了然</p></div>
<div class="item"><div class="idx">05</div><h3>目标 + 提醒</h3><p>每日使用上限，超时弹窗，连续使用休息提示</p></div>
<div class="item"><div class="idx">06</div><h3>CSV 导出</h3><p>一键导出数据，Excel 直接打开分析</p></div>
</div>

<script setup>
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  if (!document.querySelector('.VPHome')) return
  document.documentElement.style.overflow = 'hidden'
  document.body.style.overflow = 'hidden'
})

onUnmounted(() => {
  document.documentElement.style.overflow = ''
  document.body.style.overflow = ''
})
</script>
