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
      link: /apptimer/AppTimer.exe
    - theme: alt
      text: 使用指南
      link: /guide
---

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: -webkit-linear-gradient(120deg, #aaa, #fff);
}

/* 首页禁止滚动 */
html, body { overflow: hidden; height: 100vh; }

/* 画布：左 2/3 全高 */
#hero-clock-canvas {
  position: fixed; left: 0; top: 0;
  width: 67vw; height: 100vh;
  z-index: 0; pointer-events: none;
}

/* 右侧面板：33vw，自滚动 */
.VPHome { max-width: none !important; }

.VPHero {
  margin-left: 67vw !important; width: 33vw !important;
  height: 100vh; overflow-y: auto; overflow-x: hidden;
  display: flex; flex-direction: column;
}
.VPHero .container { max-width: none !important; margin: 0 2rem; }
.VPHero .main { padding-top: 6vh; }

/* 功能列表嵌在 hero 下面 */
.VPHero .main::after {
  content: '';
  display: block;
  height: 1px;
  margin: 2.5rem 0 1.5rem;
  background: rgba(255,255,255,0.08);
}

.feature-list {
  padding: 0 2rem 4rem;
  margin-left: 67vw; width: 33vw;
}
.feature-list .item {
  border-top: 1px solid rgba(255,255,255,0.07);
  padding: 0.75rem 0;
}
.feature-list .item:last-child { border-bottom: 1px solid rgba(255,255,255,0.07); }
.feature-list .item .idx {
  font-size: 0.65rem; font-weight: 400; letter-spacing: 0.12em;
  color: rgba(255,255,255,0.25); margin-bottom: 0.15rem;
}
.feature-list .item h3 {
  font-size: 0.9rem; font-weight: 400; margin: 0 0 0.1rem; letter-spacing: 0.03em;
}
.feature-list .item p {
  font-size: 0.72rem; color: rgba(255,255,255,0.4); margin: 0; line-height: 1.4;
}

@media (max-width: 768px) {
  #hero-clock-canvas { display: none; }
  .VPHero, .feature-list { margin-left: 0 !important; width: 100vw !important; }
  html, body { overflow: auto; }
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
