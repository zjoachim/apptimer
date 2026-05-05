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
  --vp-home-hero-name-background: -webkit-linear-gradient(120deg, #c0c0c0, #ffffff);
}

/* ── 画布：上半屏 2/3 ── */
#hero-clock-canvas {
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 67vh;
  z-index: 0;
  pointer-events: none;
}

/* hero 区透明，叠在画布上 */
.VPHero { background: transparent !important; min-height: 55vh; }
.VPHero .container { background: transparent; }

/* features 区不透明底，占下半 1/3 */
.VPFeatures {
  background: var(--vp-c-bg) !important;
  position: relative; z-index: 1;
  margin-top: 55vh;
  padding-top: 2rem;
  border-radius: 16px 16px 0 0;
}

/* 卡片：细边框 + 微弱底 */
.VPFeature .box {
  background: transparent !important;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  transition: border-color 0.3s, transform 0.4s ease-out, box-shadow 0.4s ease-out;
}
.VPFeature .box:hover {
  border-color: rgba(255,255,255,0.25);
}

@media (max-width: 768px) {
  #hero-clock-canvas { display: none; }
  .VPFeatures { margin-top: 0; }
}
</style>

<script setup>
import { onMounted } from 'vue'

onMounted(async () => {
  // 只在首页跑
  if (!document.querySelector('.VPHome')) return
  if (document.getElementById('hero-clock-canvas')) return

  // ── 卡片倾斜 ──
  document.querySelectorAll('.VPFeature').forEach(card => {
    const mv = e => {
      const r = card.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      card.style.transform = `perspective(1000px) rotateY(${x*10}deg) rotateX(${-y*10}deg) scale3d(1.03,1.03,1.03)`
    }
    const lv = () => { card.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) scale3d(1,1,1)' }
    card.addEventListener('mousemove', mv)
    card.addEventListener('mouseleave', lv)
  })

  const THREE = await import('https://unpkg.com/three@0.160.0/build/three.module.js')
  const scene = new THREE.Scene()
  const cam = new THREE.PerspectiveCamera(50, innerWidth / (innerHeight * 0.67), 0.5, 80)
  cam.position.set(0, 0.8, 13)

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setSize(innerWidth, innerHeight * 0.67)
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
  renderer.domElement.id = 'hero-clock-canvas'
  document.body.prepend(renderer.domElement)

  function ptsFrom(geo, n) {
    const src = geo.getAttribute('position')
    const b = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) { const j = Math.floor(Math.random() * src.count); b[i*3]=src.getX(j); b[i*3+1]=src.getY(j); b[i*3+2]=src.getZ(j) }
    return new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(b, 3))
  }

  // ── 环组（三根环各自独立）──
  const ringGroup = new THREE.Group(); scene.add(ringGroup)
  const ringMat = new THREE.PointsMaterial({ color:0xffffff, size:0.04, transparent:true, opacity:0.6, blending:THREE.AdditiveBlending, depthWrite:false })
  for (let a = 0; a < 3; a++) {
    const ring = new THREE.TorusGeometry(2.6, 0.04, 20, 140)
    ring.rotateX(a * Math.PI / 3)
    ring.rotateY(a * Math.PI / 4 * a)
    const sg = ptsFrom(ring, 2000)
    ringGroup.add(new THREE.Points(sg, ringMat))
  }

  // ── 表盘组（指针独立 + 刻度中心合并）──
  const faceGroup = new THREE.Group(); scene.add(faceGroup)
  const faceMat = new THREE.PointsMaterial({ color:0xffffff, size:0.04, transparent:true, opacity:0.7, blending:THREE.AdditiveBlending, depthWrite:false })

  // 时针（独立子节点 0）
  { const h = new THREE.BoxGeometry(0.06, 1.6, 0.06, 2, 14, 2); h.translate(0,0.8,0); faceGroup.add(new THREE.Points(ptsFrom(h, 400), faceMat)) }
  // 分针（独立子节点 1）
  { const m = new THREE.BoxGeometry(0.04, 2.2, 0.04, 2, 18, 2); m.translate(0,1.1,0); faceGroup.add(new THREE.Points(ptsFrom(m, 500), faceMat)) }

  // 刻度 + 中心合并为一个子节点
  const staticParts = []
  staticParts.push({ g: new THREE.SphereGeometry(0.15, 20, 20), n: 300 })
  for (let i = 0; i < 12; i++) {
    const a = (i/12)*Math.PI*2
    const s = new THREE.SphereGeometry(i%3===0?0.1:0.05, 10, 10)
    s.translate(Math.cos(a)*2.6, Math.sin(a)*2.6, 0)
    staticParts.push({g:s, n: i%3===0?150:60})
  }
  {
    const total = staticParts.reduce((s,x)=>s+x.n,0)
    const pos = new Float32Array(total*3); let off=0
    for (const {g,n} of staticParts) { const sg = ptsFrom(g,n); pos.set(sg.getAttribute('position').array, off*3); off+=n }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    faceGroup.add(new THREE.Points(geo, faceMat))
  }

  // ── 鼠标 ──
  let mx=0,my=0,tx=0,ty=0
  window.addEventListener('mousemove', e=>{ tx=(e.clientX/innerWidth-0.5)*2; ty=(e.clientY/innerHeight-0.5)*2 })

  // ── 动画 ──
  const clock = new THREE.Clock()
  function loop() {
    requestAnimationFrame(loop)
    const t = clock.getElapsedTime()
    mx += (tx-mx)*0.04; my += (ty-my)*0.04

    // 环组：各自绕不同轴转
    ringGroup.children.forEach((child, i) => {
      if (i===0) child.rotation.z += 0.003
      else if (i===1) child.rotation.x += 0.004
      else child.rotation.y += 0.005
    })
    ringGroup.rotation.x += (my*0.25 - ringGroup.rotation.x)*0.03
    ringGroup.rotation.y += (-mx*0.2 - ringGroup.rotation.y)*0.03

    // 表盘组：XY 平面内，指针转 + 整体微倾
    // 时针：12s 一圈，分针：3s 一圈
    faceGroup.children[0].rotation.z = t * 0.52  // ~12s
    faceGroup.children[1].rotation.z = t * 2.09  // ~3s
    faceGroup.rotation.x += (my*0.15 - faceGroup.rotation.x)*0.03
    faceGroup.rotation.y += (-mx*0.1 - faceGroup.rotation.y)*0.03

    renderer.render(scene, cam)
  }
  loop()

  window.addEventListener('resize', () => {
    const h = innerHeight * 0.67
    cam.aspect = innerWidth / h; cam.updateProjectionMatrix()
    renderer.setSize(innerWidth, h)
  })
})
</script>
