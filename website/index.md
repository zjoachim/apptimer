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

/* ── 画布：左侧 2/3 ── */
#hero-clock-canvas {
  position: fixed;
  left: 0; top: 0;
  width: 67vw; height: 100vh;
  z-index: 0;
  pointer-events: none;
}

/* ── 右侧 1/3 放 hero + 卡片 ── */
.VPHero, .VPFeatures {
  margin-left: 67vw !important;
  width: 33vw !important;
}
.VPHero { min-height: 100vh; display: flex; align-items: center; }
.VPHome { max-width: none !important; }
.VPHero .container { max-width: none !important; margin: 0 2rem; }

/* features 区 */
.VPFeatures { padding-top: 2rem; padding-bottom: 4rem; }
.VPFeatures .container { max-width: none !important; margin: 0 1.5rem; }
.VPFeatures .items { display: flex; flex-direction: column; gap: 0.8rem; }

/* 卡片 */
.VPFeature .box {
  background: transparent !important;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  transition: border-color 0.3s, transform 0.4s ease-out;
}
.VPFeature .box:hover { border-color: rgba(255,255,255,0.25); }

@media (max-width: 768px) {
  #hero-clock-canvas { display: none; }
  .VPHero, .VPFeatures { margin-left: 0 !important; width: 100vw !important; }
}
</style>

<script setup>
import { onMounted, onUnmounted } from 'vue'

let animId = null

onMounted(async () => {
  if (!document.querySelector('.VPHome')) return

  // 之前隐藏的画布恢复
  let canvas = document.getElementById('hero-clock-canvas')
  if (canvas) { canvas.style.display = 'block'; return }

  // ── 卡片 ──
  document.querySelectorAll('.VPFeature').forEach(card => {
    const mv = e => {
      const r = card.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      card.style.transform = `perspective(1000px) rotateY(${x*8}deg) rotateX(${-y*8}deg) scale3d(1.02,1.02,1.02)`
    }
    const lv = () => { card.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) scale3d(1,1,1)' }
    card.addEventListener('mousemove', mv)
    card.addEventListener('mouseleave', lv)
  })

  const THREE = await import('https://unpkg.com/three@0.160.0/build/three.module.js')
  const scene = new THREE.Scene()
  const cam = new THREE.PerspectiveCamera(50, (innerWidth*0.67) / innerHeight, 0.5, 80)
  cam.position.set(0, 0.5, 11)

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setSize(innerWidth * 0.67, innerHeight)
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
  canvas = renderer.domElement
  canvas.id = 'hero-clock-canvas'
  document.body.prepend(canvas)

  function ptsFrom(geo, n) {
    const src = geo.getAttribute('position')
    const b = new Float32Array(n*3)
    for (let i=0; i<n; i++) { const j=Math.floor(Math.random()*src.count); b[i*3]=src.getX(j); b[i*3+1]=src.getY(j); b[i*3+2]=src.getZ(j) }
    return new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(b,3))
  }

  // 环组
  const ringGroup = new THREE.Group(); scene.add(ringGroup)
  const ringMat = new THREE.PointsMaterial({ color:0xffffff, size:0.035, transparent:true, opacity:0.55, blending:THREE.AdditiveBlending, depthWrite:false })
  for (let a=0; a<3; a++) {
    const ring = new THREE.TorusGeometry(2.4, 0.035, 18, 120)
    ring.rotateX(a*Math.PI/3); ring.rotateY(a*Math.PI/4)
    ringGroup.add(new THREE.Points(ptsFrom(ring, 1800), ringMat))
  }

  // 表盘组
  const faceGroup = new THREE.Group(); scene.add(faceGroup)
  const faceMat = new THREE.PointsMaterial({ color:0xffffff, size:0.04, transparent:true, opacity:0.7, blending:THREE.AdditiveBlending, depthWrite:false })
  { const h = new THREE.BoxGeometry(0.05, 1.5, 0.05, 2,12,2); h.translate(0,0.75,0); faceGroup.add(new THREE.Points(ptsFrom(h,350), faceMat)) }
  { const m = new THREE.BoxGeometry(0.035, 2.1, 0.035, 2,16,2); m.translate(0,1.05,0); faceGroup.add(new THREE.Points(ptsFrom(m,450), faceMat)) }
  // 刻度+中心
  const sp = []; sp.push({g:new THREE.SphereGeometry(0.14,16,16), n:250})
  for (let i=0; i<12; i++) { const a=(i/12)*Math.PI*2; const s=new THREE.SphereGeometry(i%3===0?0.09:0.05,8,8); s.translate(Math.cos(a)*2.4, Math.sin(a)*2.4,0); sp.push({g:s,n:i%3===0?120:50}) }
  { const t=sp.reduce((s,x)=>s+x.n,0); const p=new Float32Array(t*3); let o=0; for (const {g,n} of sp) { const sg=ptsFrom(g,n); p.set(sg.getAttribute('position').array, o*3); o+=n } const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(p,3)); faceGroup.add(new THREE.Points(g, faceMat)) }

  // 鼠标
  let mx=0,my=0,tx=0,ty=0
  const onMove = e => { tx=(e.clientX/innerWidth-0.5)*2; ty=(e.clientY/innerHeight-0.5)*2 }
  window.addEventListener('mousemove', onMove)

  const clk = new THREE.Clock()
  function loop() {
    animId = requestAnimationFrame(loop)
    const t = clk.getElapsedTime()
    mx+=(tx-mx)*0.03; my+=(ty-my)*0.03

    ringGroup.children.forEach((c,i)=>{
      c.rotation.x += 0.0015
      c.rotation.y += 0.002
      c.rotation.z += 0.001
    })
    ringGroup.rotation.x += (my*0.2 - ringGroup.rotation.x)*0.02
    ringGroup.rotation.y += (-mx*0.15 - ringGroup.rotation.y)*0.02

    // 指针：~30s / ~8s 一圈
    faceGroup.children[0].rotation.z = t * 0.21
    faceGroup.children[1].rotation.z = t * 0.78
    faceGroup.rotation.x += (my*0.12 - faceGroup.rotation.x)*0.02
    faceGroup.rotation.y += (-mx*0.08 - faceGroup.rotation.y)*0.02

    renderer.render(scene, cam)
  }
  loop()

  const onResize = () => {
    const w = innerWidth * 0.67
    cam.aspect = w / innerHeight; cam.updateProjectionMatrix()
    renderer.setSize(w, innerHeight)
  }
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  const canvas = document.getElementById('hero-clock-canvas')
  if (canvas) canvas.style.display = 'none'
  if (animId) cancelAnimationFrame(animId)
})
</script>
