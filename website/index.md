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

#hero-clock-canvas {
  position: fixed; left: 0; top: 0;
  width: 67vw; height: 100vh;
  z-index: 0; pointer-events: none;
}

.VPHero, .feature-list {
  margin-left: 67vw !important;
  width: 33vw !important;
}
.VPHero { min-height: 70vh; display: flex; align-items: center; }
.VPHome { max-width: none !important; }
.VPHero .container { max-width: none !important; margin: 0 2rem; }

/* 底部竖排卡片 */
.feature-list {
  padding: 3rem 2rem 6rem;
  counter-reset: fn;
}
.feature-list .item {
  border-top: 1px solid rgba(255,255,255,0.08);
  padding: 1rem 0;
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.feature-list .item:last-child { border-bottom: 1px solid rgba(255,255,255,0.08); }
.feature-list .item .idx {
  font-size: 0.7rem; font-weight: 400; letter-spacing: 0.1em;
  color: rgba(255,255,255,0.3); margin-bottom: 0.25rem;
}
.feature-list .item h3 {
  font-size: 1rem; font-weight: 400; margin: 0 0 0.2rem; letter-spacing: 0.03em;
}
.feature-list .item p {
  font-size: 0.78rem; color: rgba(255,255,255,0.45); margin: 0; line-height: 1.5;
}

@media (max-width: 768px) {
  #hero-clock-canvas { display: none; }
  .VPHero, .feature-list { margin-left: 0 !important; width: 100vw !important; }
}
</style>

<div class="feature-list">

<div class="item"><div class="idx">01</div><h3>自动追踪</h3><p>后台静默运行，自动检测当前活动窗口，离开电脑自动暂停</p></div>
<div class="item"><div class="idx">02</div><h3>程序分类</h3><p>工作、学习、娱乐、社交、开发、设计等多类标签</p></div>
<div class="item"><div class="idx">03</div><h3>日报周报月报</h3><p>数据按日期组织，自动生成报表，趋势跨天对比</p></div>
<div class="item"><div class="idx">04</div><h3>饼图 + 柱状图</h3><p>内置可视化图表，占比和趋势一目了然</p></div>
<div class="item"><div class="idx">05</div><h3>目标 + 提醒</h3><p>每日使用上限设定，超时弹窗，连续使用休息提示</p></div>
<div class="item"><div class="idx">06</div><h3>CSV 导出</h3><p>一键导出数据，Excel 直接打开分析</p></div>

</div>

<script setup>
import { onMounted, onUnmounted } from 'vue'

let animId = null, renderer = null, sceneData = null

onMounted(async () => {
  if (!document.querySelector('.VPHome')) return

  // ── 恢复已有画布 ──
  let canvas = document.getElementById('hero-clock-canvas')
  if (canvas) {
    canvas.style.display = 'block'
    if (sceneData) {
      const { ringGroups, faceGroup, cam, scene, r } = sceneData
      const clk = new THREE.Clock()
      const loop = () => {
        animId = requestAnimationFrame(loop)
        const t = clk.getElapsedTime()
        ringGroups.forEach((g, i) => {
          g.rotation.x += (0.002 + i * 0.0015)
          g.rotation.y += (0.003 - i * 0.001)
        })
        faceGroup.children[0].rotation.z = t * 0.21
        faceGroup.children[1].rotation.z = t * 0.78
        r.render(scene, cam)
      }
      loop()
    }
    return
  }

  const THREE = await import('https://unpkg.com/three@0.160.0/build/three.module.js')
  const scene = new THREE.Scene()
  const cam = new THREE.PerspectiveCamera(50, (innerWidth*0.67)/innerHeight, 0.5, 80)
  cam.position.set(0, 0, 10)

  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setSize(innerWidth*0.67, innerHeight)
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

  // ── 三根环：各自独立 Group，绕原点转 ──
  const ringGroups = []
  const ringMat = new THREE.PointsMaterial({ color:0xffffff, size:0.035, transparent:true, opacity:0.5, blending:THREE.AdditiveBlending, depthWrite:false })
  const axes = [[1,0.3,0],[0.2,1,0.1],[0,0.2,1]]
  for (let a=0; a<3; a++) {
    const g = new THREE.Group()
    const ring = new THREE.TorusGeometry(2.3 + a*0.15, 0.03, 16, 100)
    // 初始随机旋转
    g.rotation.set(Math.random()*Math.PI*2, Math.random()*Math.PI*2, Math.random()*Math.PI*2)
    g.add(new THREE.Points(ptsFrom(ring, 1600), ringMat))
    scene.add(g)
    ringGroups.push(g)
  }

  // ── 表盘组 ──
  const faceGroup = new THREE.Group(); scene.add(faceGroup)
  const faceMat = new THREE.PointsMaterial({ color:0xffffff, size:0.04, transparent:true, opacity:0.65, blending:THREE.AdditiveBlending, depthWrite:false })
  { const h = new THREE.BoxGeometry(0.05, 1.4, 0.05, 2,12,2); h.translate(0,0.7,0); faceGroup.add(new THREE.Points(ptsFrom(h,300), faceMat)) }
  { const m = new THREE.BoxGeometry(0.035, 2.0, 0.035, 2,14,2); m.translate(0,1.0,0); faceGroup.add(new THREE.Points(ptsFrom(m,400), faceMat)) }
  // 刻度 + 中心
  const sp = []; sp.push({g:new THREE.SphereGeometry(0.12,12,12), n:200})
  for (let i=0; i<12; i++) { const ang=(i/12)*Math.PI*2; const s=new THREE.SphereGeometry(i%3===0?0.08:0.04,8,8); s.translate(Math.cos(ang)*2.4, Math.sin(ang)*2.4,0); sp.push({g:s,n:i%3===0?100:40}) }
  { const t=sp.reduce((s,x)=>s+x.n,0); const p=new Float32Array(t*3); let o=0; for (const {g,n} of sp) { const sg=ptsFrom(g,n); p.set(sg.getAttribute('position').array, o*3); o+=n } const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.BufferAttribute(p,3)); faceGroup.add(new THREE.Points(geo, faceMat)) }

  sceneData = { ringGroups, faceGroup, cam, scene, r: renderer }

  // ── 动画 ──
  const clk = new THREE.Clock()
  function loop() {
    animId = requestAnimationFrame(loop)
    const t = clk.getElapsedTime()
    ringGroups.forEach((g, i) => {
      g.rotation.x += 0.002 + i * 0.0012
      g.rotation.y += 0.003 - i * 0.0008
      g.rotation.z += 0.0015 + i * 0.001
    })
    faceGroup.children[0].rotation.z = t * 0.21
    faceGroup.children[1].rotation.z = t * 0.78
    renderer.render(scene, cam)
  }
  loop()

  window.addEventListener('resize', () => {
    const w = innerWidth*0.67
    cam.aspect = w/innerHeight; cam.updateProjectionMatrix()
    renderer.setSize(w, innerHeight)
  })
})

onUnmounted(() => {
  const canvas = document.getElementById('hero-clock-canvas')
  if (canvas) canvas.style.display = 'none'
  if (animId) { cancelAnimationFrame(animId); animId = null }
})
</script>
