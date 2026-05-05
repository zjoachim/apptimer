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

/* 3D 画布全屏背景 */
#hero-clock-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.VPHome { position: relative; z-index: 1; }

/* 卡片半透明底，让背景透出来一点 */
.VPFeature .box {
  background: rgba(255,255,255,0.08) !important;
  backdrop-filter: blur(4px);
}
html[class="dark"] .VPFeature .box,
html.dark .VPFeature .box {
  background: rgba(0,0,0,0.25) !important;
}
</style>

<script setup>
import { onMounted } from 'vue'

onMounted(async () => {
  // ── 3D 卡片倾斜 ──
  document.querySelectorAll('.VPFeature').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width - 0.5
      const y = (e.clientY - rect.top) / rect.height - 0.5
      card.style.transform = `perspective(1000px) rotateY(${x * 12}deg) rotateX(${-y * 12}deg) scale3d(1.03,1.03,1.03)`
    })
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) scale3d(1,1,1)'
    })
  })

  // ── Three.js 粒子点云时钟 ──
  const THREE = await import('https://unpkg.com/three@0.160.0/build/three.module.js')

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.1, 100)
  camera.position.z = 14

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setSize(innerWidth, innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.domElement.id = 'hero-clock-canvas'
  document.body.prepend(renderer.domElement)

  const clockGroup = new THREE.Group()
  scene.add(clockGroup)

  // ── 辅助：从几何体采样点 ──
  function sampleGeo(geo, count) {
    const pos = geo.getAttribute('position')
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const idx = Math.floor(Math.random() * pos.count)
      arr[i * 3] = pos.getX(idx)
      arr[i * 3 + 1] = pos.getY(idx)
      arr[i * 3 + 2] = pos.getZ(idx)
    }
    return new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(arr, 3))
  }

  // ── 收集所有点 ──
  const parts = []

  // 圆环（表盘）
  parts.push({ geo: new THREE.TorusGeometry(2.6, 0.08, 32, 128), count: 3000, color: 0x3498db })
  // 时针
  parts.push({ geo: (() => { const g = new THREE.BoxGeometry(0.14, 1.8, 0.14, 4, 12, 4); g.translate(0, 0.9, 0); g.rotateZ(Math.PI/6); return g })(), count: 600, color: 0xaaccff })
  // 分针
  parts.push({ geo: (() => { const g = new THREE.BoxGeometry(0.1, 2.5, 0.1, 4, 16, 4); g.translate(0, 1.25, 0); g.rotateZ(-Math.PI/4); return g })(), count: 800, color: 0xccddff })
  // 中心点
  parts.push({ geo: new THREE.SphereGeometry(0.18, 24, 24), count: 400, color: 0x9b59b6 })

  // 12 个刻度点（加大）
  for (let i = 0; i < 12; i++) {
    const angle = (i / 12) * Math.PI * 2
    const dotGeo = new THREE.SphereGeometry(i % 3 === 0 ? 0.12 : 0.07, 16, 16)
    dotGeo.translate(Math.cos(angle) * 2.6, Math.sin(angle) * 2.6, 0)
    parts.push({ geo: dotGeo, count: i % 3 === 0 ? 200 : 100, color: 0x9b59b6 })
  }

  // 合并为一个点云
  const total = parts.reduce((s, p) => s + p.count, 0)
  const allPos = new Float32Array(total * 3)
  const allCol = new Float32Array(total * 3)
  let offset = 0
  for (const p of parts) {
    const sg = sampleGeo(p.geo, p.count)
    const sp = sg.getAttribute('position').array
    for (let i = 0; i < p.count; i++) {
      allPos[(offset + i) * 3] = sp[i * 3]
      allPos[(offset + i) * 3 + 1] = sp[i * 3 + 1]
      allPos[(offset + i) * 3 + 2] = sp[i * 3 + 2] + (Math.random() - 0.5) * 0.08 // 微随机深度
      const c = new THREE.Color(p.color)
      allCol[(offset + i) * 3] = c.r
      allCol[(offset + i) * 3 + 1] = c.g
      allCol[(offset + i) * 3 + 2] = c.b
    }
    offset += p.count
  }

  const bg = new THREE.BufferGeometry()
  bg.setAttribute('position', new THREE.BufferAttribute(allPos, 3))
  bg.setAttribute('color', new THREE.BufferAttribute(allCol, 3))

  const mat = new THREE.PointsMaterial({ size: 0.04, vertexColors: true, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false })
  clockGroup.add(new THREE.Points(bg, mat))

  // ── 鼠标视差 ──
  let mouseX = 0, mouseY = 0, targetX = 0, targetY = 0
  window.addEventListener('mousemove', (e) => {
    targetX = (e.clientX / innerWidth - 0.5) * 2
    targetY = (e.clientY / innerHeight - 0.5) * 2
  })

  function animate() {
    requestAnimationFrame(animate)
    mouseX += (targetX - mouseX) * 0.03
    mouseY += (targetY - mouseY) * 0.03
    clockGroup.rotation.y += 0.002
    clockGroup.rotation.x += (mouseY * 0.25 - clockGroup.rotation.x) * 0.02
    clockGroup.rotation.z += (-mouseX * 0.15 - clockGroup.rotation.z) * 0.02
    renderer.render(scene, camera)
  }
  animate()

  window.addEventListener('resize', () => {
    camera.aspect = innerWidth / innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(innerWidth, innerHeight)
  })
})
</script>
