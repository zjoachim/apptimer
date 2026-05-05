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

#hero-clock-canvas {
  position: fixed; left: 0; top: 0;
  width: 67vw; height: 100vh;
  z-index: 0; pointer-events: none;
}

/* 右侧面板居中 */
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
  margin-left: -0.3rem; /* 往左微移 */
}
.VPHero .tagline { text-align: left; font-size: 0.85rem !important; }
.VPHero .actions { justify-content: flex-start; }

@media (max-width: 768px) {
  #hero-clock-canvas { display: none; }
  .VPHero { margin-left: 0 !important; width: 100vw !important; }
  html, body { overflow: auto; }
}
</style>
