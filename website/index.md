---
layout: home
title: AppTimer

hero:
  name: AppTimer
  text: 清楚你的时间去哪了
  tagline: 自动追踪 Windows 程序使用时长，分类统计，可视化报表，让你掌控每一分钟
  actions:
    - theme: brand
      text: 立即下载
      link: /apptimer/AppTimer.exe
    - theme: alt
      text: 使用指南
      link: /guide

features:
  - icon: 🎯
    title: 自动追踪
    details: 后台静默运行，自动检测当前活动窗口，精确记录每个程序的真实使用时长。离开电脑自动暂停，不乱计时。
  - icon: 🏷️
    title: 程序分类标签
    details: 支持工作、学习、娱乐、社交、开发、设计等多类标签，一眼看清时间分配比例。
  - icon: 📊
    title: 日/周/月报表
    details: 数据按日期组织存储，自动生成周报和月报，使用趋势跨天对比一目了然。
  - icon: 📈
    title: 饼图 + 柱状图
    details: 内置可视化图表，今日占比饼图和跨天趋势柱状图，数据更直观。
  - icon: 🎯
    title: 目标设定 + 提醒
    details: 可为每个程序设定每日使用上限，超时弹窗提醒。连续使用超 45 分钟自动提示休息。
  - icon: 📁
    title: CSV 导出
    details: 一键导出当日或累计数据为 CSV 文件，方便在 Excel 中进一步分析。
---

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: -webkit-linear-gradient(120deg, #3498db, #9b59b6);
}

/* 页面背景透明，让画布透出来 */
.VPHome, .VPHero, .VPFeatures {
  background: transparent !important;
}
.VPFeature .box {
  background: rgba(255,255,255,0.06) !important;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
html.dark .VPFeature .box {
  background: rgba(0,0,0,0.2) !important;
}

#hero-clock-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
</style>

<script setup>
import { onMounted, onUnmounted } from 'vue'

onMounted(async () => {
  // ── 卡片倾斜 ──
  document.querySelectorAll('.VPFeature').forEach(card => {
    const onMove = (e) => {
      const r = card.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      card.style.transform = `perspective(1000px) rotateY(${x*14}deg) rotateX(${-y*14}deg) scale3d(1.04,1.04,1.04)`
    }
    const onLeave = () => { card.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) scale3d(1,1,1)' }
    card.addEventListener('mousemove', onMove)
    card.addEventListener('mouseleave', onLeave)
  })

  // ── 防重复 ──
  if (document.getElementById('hero-clock-canvas')) return

  const THREE = await import('https://unpkg.com/three@0.160.0/build/three.module.js')

  const scene = new THREE.Scene()
  const cam = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.5, 80)
  cam.position.set(0, 0, 15)

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setSize(innerWidth, innerHeight)
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
  renderer.domElement.id = 'hero-clock-canvas'
  document.body.prepend(renderer.domElement)

  const root = new THREE.Group()
  scene.add(root)

  // ── 从几何体采点 ──
  function pointsFrom(geo, count) {
    const src = geo.getAttribute('position')
    const buf = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const j = Math.floor(Math.random() * src.count)
      buf[i*3] = src.getX(j); buf[i*3+1] = src.getY(j); buf[i*3+2] = src.getZ(j)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(buf, 3))
    return g
  }

  // ── 时钟部件（全部存成 points geometry，最后合并） ──
  const geos = []

  // 三根交错的扁环，像原子轨道
  for (let a = 0; a < 3; a++) {
    const ring = new THREE.TorusGeometry(2.8, 0.05, 24, 160)
    ring.rotateX(a * Math.PI / 3)
    ring.rotateY(a * Math.PI / 4)
    geos.push({ g: ring, n: 2500 })
  }

  // 时针 — 扁长方体，有 Z 厚
  {
    const h = new THREE.BoxGeometry(0.15, 1.6, 0.3, 4, 12, 6)
    h.translate(0, 0.8, 0)
    h.rotateZ(Math.PI / 6)
    h.rotateY(0.2)
    geos.push({ g: h, n: 800 })
  }

  // 分针
  {
    const m = new THREE.BoxGeometry(0.1, 2.2, 0.2, 3, 16, 4)
    m.translate(0, 1.1, 0)
    m.rotateZ(-Math.PI / 5)
    m.rotateY(-0.15)
    geos.push({ g: m, n: 1000 })
  }

  // 中心球
  geos.push({ g: new THREE.SphereGeometry(0.2, 24, 24), n: 500 })

  // 12 个刻度小球
  for (let i = 0; i < 12; i++) {
    const r = 2.8
    const angle = (i / 12) * Math.PI * 2
    const s = new THREE.SphereGeometry(i % 3 === 0 ? 0.14 : 0.08, 12, 12)
    s.translate(Math.cos(angle) * r, Math.sin(angle) * r, 0)
    geos.push({ g: s, n: i % 3 === 0 ? 250 : 120 })
  }

  // 合并
  const total = geos.reduce((s, x) => s + x.n, 0)
  const pos = new Float32Array(total * 3)
  let off = 0
  for (const { g, n } of geos) {
    const sg = pointsFrom(g, n)
    const arr = sg.getAttribute('position').array
    for (let i = 0; i < n; i++) {
      pos[(off+i)*3]   = arr[i*3]
      pos[(off+i)*3+1] = arr[i*3+1]
      pos[(off+i)*3+2] = arr[i*3+2]
    }
    off += n
  }

  const cloudGeo = new THREE.BufferGeometry()
  cloudGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  const cloud = new THREE.Points(cloudGeo, new THREE.PointsMaterial({
    color: 0xffffff, size: 0.05, transparent: true, opacity: 0.7,
    blending: THREE.AdditiveBlending, depthWrite: false
  }))
  root.add(cloud)

  // ── 鼠标 ──
  let mx = 0, my = 0, tx = 0, ty = 0
  window.addEventListener('mousemove', e => { tx = (e.clientX/innerWidth-0.5)*2; ty = (e.clientY/innerHeight-0.5)*2 })

  function loop() {
    requestAnimationFrame(loop)
    mx += (tx - mx) * 0.04
    my += (ty - my) * 0.04
    root.rotation.y += 0.002
    root.rotation.x += (my * 0.3 - root.rotation.x) * 0.03
    root.rotation.z += (-mx * 0.2 - root.rotation.z) * 0.03
    renderer.render(scene, cam)
  }
  loop()

  window.addEventListener('resize', () => {
    cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix()
    renderer.setSize(innerWidth, innerHeight)
  })
})
</script>
