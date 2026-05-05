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
    width: 100vw !important; height: 45vh !important;
    top: 0; left: 0;
  }

  .VPHero {
    margin-left: 0 !important; width: 100vw !important;
    height: auto; min-height: auto;
    position: relative; top: 45vh;
    display: block; padding: 1rem 1.5rem 2rem;
  }
  .VPHero .name { font-size: 1.8rem !important; }
  .VPHero .text { font-size: 1rem !important; white-space: normal !important; margin-left: 0 !important; }
  .VPHero .tagline { font-size: 0.8rem !important; }
}
</style>

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
