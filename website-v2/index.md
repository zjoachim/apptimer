---
layout: home
title: AppTimer

hero:
  name: AppTimer
  text: 清楚你的时间去哪了
  tagline: Vue 3 + ECharts 可视化，Edge 无边框窗口，7 个功能标签页
  actions:
    - theme: brand
      text: 下载 v2（Win11）
      link: /AppTimer-v2.exe
    - theme: alt
      text: 下载 v1（Win10）
      link: /AppTimer-v1.exe
    - theme: alt
      text: 使用指南
      link: /guide
---

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: -webkit-linear-gradient(120deg, #aaa, #fff);
}

/* 骨架屏：Three.js 加载前显示时钟轮廓呼吸动画 */
.VPHome::before {
  content: '';
  position: fixed; left: 0; top: 0;
  width: 67vw; height: 100vh;
  z-index: -1;
  background:
    radial-gradient(circle at 50% 50%, transparent 28%, rgba(255,255,255,0.12) 29%, rgba(255,255,255,0.12) 30.5%, transparent 31%),
    linear-gradient(55deg, transparent 49.5%, rgba(255,255,255,0.1) 49.5%, rgba(255,255,255,0.1) 50.5%, transparent 50.5%),
    linear-gradient(0deg, transparent 49.5%, rgba(255,255,255,0.08) 49.5%, rgba(255,255,255,0.08) 50.5%, transparent 50.5%);
  background-size: 100% 100%, 60% 60%, 50% 50%;
  background-position: center;
  background-repeat: no-repeat;
  animation: skeleton-breathe 1.5s ease-in-out infinite;
}
@keyframes skeleton-breathe {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}
@media (max-width: 768px) {
  .VPHome::before {
    width: 100vw; height: 45vh;
  }
}

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
