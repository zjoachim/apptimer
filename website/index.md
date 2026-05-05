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

  // ── Three.js 3D 时钟 ──
  const THREE = await import('https://unpkg.com/three@0.160.0/build/three.module.js')

  // ── 场景 / 相机 / 渲染器 ──
  const hero = document.querySelector('.VPHero')
  if (!hero) return
  const rect = hero.getBoundingClientRect()
  const w = rect.width
  const h = rect.height

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100)
  camera.position.z = 12

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.domElement.id = 'hero-clock-canvas'
  hero.appendChild(renderer.domElement)

  // ── 光照 ──
  scene.add(new THREE.AmbientLight(0x444466, 3))
  const light1 = new THREE.DirectionalLight(0x3498db, 4)
  light1.position.set(5, 5, 5)
  scene.add(light1)
  const light2 = new THREE.DirectionalLight(0x9b59b6, 3)
  light2.position.set(-5, -3, -2)
  scene.add(light2)

  // ── 时钟模型 ──
  const clockGroup = new THREE.Group()
  scene.add(clockGroup)

  // 表盘环
  const ringGeo = new THREE.TorusGeometry(2.6, 0.06, 32, 128)
  const ringMat = new THREE.MeshStandardMaterial({ color: 0x3498db, metalness: 0.8, roughness: 0.3 })
  clockGroup.add(new THREE.Mesh(ringGeo, ringMat))

  // 时针
  const hourGeo = new THREE.BoxGeometry(0.12, 1.6, 0.08)
  const hourMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.6, roughness: 0.4 })
  const hourHand = new THREE.Mesh(hourGeo, hourMat)
  hourHand.position.y = 0.8
  hourHand.rotation.z = Math.PI / 6
  clockGroup.add(hourHand)

  // 分针
  const minGeo = new THREE.BoxGeometry(0.08, 2.2, 0.06)
  const minMat = new THREE.MeshStandardMaterial({ color: 0xe0e0ff, metalness: 0.5, roughness: 0.4 })
  const minHand = new THREE.Mesh(minGeo, minMat)
  minHand.position.y = 1.1
  minHand.rotation.z = -Math.PI / 4
  clockGroup.add(minHand)

  // 中心轴
  const centerGeo = new THREE.CylinderGeometry(0.15, 0.15, 0.15, 32)
  const centerMat = new THREE.MeshStandardMaterial({ color: 0x9b59b6, metalness: 0.9, roughness: 0.2 })
  clockGroup.add(new THREE.Mesh(centerGeo, centerMat))

  // 刻度点（12个）
  for (let i = 0; i < 12; i++) {
    const angle = (i / 12) * Math.PI * 2
    const dotGeo = new THREE.SphereGeometry(0.06, 16, 16)
    const dotMat = new THREE.MeshStandardMaterial({ color: 0x9b59b6, metalness: 0.7, roughness: 0.3 })
    const dot = new THREE.Mesh(dotGeo, dotMat)
    dot.position.set(Math.cos(angle) * 2.6, Math.sin(angle) * 2.6, 0)
    clockGroup.add(dot)
  }

  // ── 鼠标视差 ──
  let mouseX = 0, mouseY = 0, targetX = 0, targetY = 0
  window.addEventListener('mousemove', (e) => {
    targetX = (e.clientX / window.innerWidth - 0.5) * 2
    targetY = (e.clientY / window.innerHeight - 0.5) * 2
  })

  // ── 动画循环 ──
  function animate() {
    requestAnimationFrame(animate)
    mouseX += (targetX - mouseX) * 0.05
    mouseY += (targetY - mouseY) * 0.05
    clockGroup.rotation.y += 0.003
    clockGroup.rotation.x = mouseY * 0.3
    clockGroup.rotation.z = -mouseX * 0.2
    renderer.render(scene, camera)
  }
  animate()

  // ── 响应窗口大小 ──
  window.addEventListener('resize', () => {
    const r = hero.getBoundingClientRect()
    camera.aspect = r.width / r.height
    camera.updateProjectionMatrix()
    renderer.setSize(r.width, r.height)
  })
})
</script>
