import DefaultTheme from 'vitepress/theme'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ router }) {
    if (typeof window === 'undefined') return

    function isHome() {
      return location.pathname === '/apptimer/' || location.pathname === '/apptimer/index.html'
    }
    function toggleCanvas() {
      const c = document.getElementById('hero-clock-canvas')
      if (c) c.style.display = isHome() ? 'block' : 'none'
    }

    // 初始设置
    setTimeout(() => toggleCanvas(), 50)

    // 页面切换过渡 + 画布显隐
    router.onBeforeRouteChange = () => {
      const el = document.querySelector('.VPContent')
      if (el) { el.style.opacity = '0'; el.style.transform = 'translateY(4px)'; el.style.transition = 'none' }
    }
    router.onAfterRouteChanged = (to) => {
      const el = document.querySelector('.VPContent')
      if (el) {
        requestAnimationFrame(() => {
          el.style.transition = 'opacity 0.25s ease, transform 0.25s ease'
          el.style.opacity = '1'; el.style.transform = 'translateY(0)'
        })
      }
      toggleCanvas()
      // 非首页恢复滚动
      if (!isHome()) {
        document.documentElement.style.overflow = ''
        document.body.style.overflow = ''
      }
    }

    // ── Three.js 常驻 ──
    if (document.getElementById('hero-clock-canvas')) return

    import('https://unpkg.com/three@0.160.0/build/three.module.js').then(THREE => {
      const scene = new THREE.Scene()
      const cam = new THREE.PerspectiveCamera(50, (innerWidth*0.67)/innerHeight, 0.5, 80)
      cam.position.set(0, 0, 10)

      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
      renderer.setSize(innerWidth*0.67, innerHeight)
      renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
      const canvas = renderer.domElement
      canvas.id = 'hero-clock-canvas'
      canvas.style.display = 'block'
      document.body.prepend(canvas)
      // 根据实际 URL 修正
      setTimeout(() => { canvas.style.display = isHome() ? 'block' : 'none' }, 100)

      function ptsFrom(geo, n) {
        const src = geo.getAttribute('position')
        const b = new Float32Array(n*3)
        for (let i=0; i<n; i++) { const j=Math.floor(Math.random()*src.count); b[i*3]=src.getX(j); b[i*3+1]=src.getY(j); b[i*3+2]=src.getZ(j) }
        return new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(b,3))
      }

      const ringGroups = []
      const ringMat = new THREE.PointsMaterial({ color:0xffffff, size:0.035, transparent:true, opacity:0.5, blending:THREE.AdditiveBlending, depthWrite:false })
      for (let a=0; a<3; a++) {
        const g = new THREE.Group()
        g.rotation.set(Math.random()*Math.PI*2, Math.random()*Math.PI*2, Math.random()*Math.PI*2)
        g.add(new THREE.Points(ptsFrom(new THREE.TorusGeometry(2.3+a*0.15, 0.03, 16, 100), 1600), ringMat))
        scene.add(g); ringGroups.push(g)
      }

      const faceGroup = new THREE.Group(); scene.add(faceGroup)
      const faceMat = new THREE.PointsMaterial({ color:0xffffff, size:0.04, transparent:true, opacity:0.65, blending:THREE.AdditiveBlending, depthWrite:false })
      { const h=new THREE.BoxGeometry(0.05,1.4,0.05,2,12,2); h.translate(0,0.7,0); faceGroup.add(new THREE.Points(ptsFrom(h,300), faceMat)) }
      { const m=new THREE.BoxGeometry(0.035,2.0,0.035,2,14,2); m.translate(0,1.0,0); faceGroup.add(new THREE.Points(ptsFrom(m,400), faceMat)) }
      const sp=[]
      sp.push({g:new THREE.SphereGeometry(0.12,12,12), n:200})
      for (let i=0; i<12; i++) { const ang=(i/12)*Math.PI*2; const s=new THREE.SphereGeometry(i%3===0?0.08:0.04,8,8); s.translate(Math.cos(ang)*2.4, Math.sin(ang)*2.4,0); sp.push({g:s, n:i%3===0?100:40}) }
      { const t=sp.reduce((s,x)=>s+x.n,0); const p=new Float32Array(t*3); let o=0; for (const {g,n} of sp) { const sg=ptsFrom(g,n); p.set(sg.getAttribute('position').array,o*3); o+=n } const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.BufferAttribute(p,3)); faceGroup.add(new THREE.Points(geo, faceMat)) }

      const clk = new THREE.Clock()
      ;(function loop() {
        requestAnimationFrame(loop)
        const t = clk.getElapsedTime()
        ringGroups.forEach((g,i) => {
          g.rotation.x += 0.002 + i*0.0012
          g.rotation.y += 0.003 - i*0.0008
          g.rotation.z += 0.0015 + i*0.001
        })
        faceGroup.children[0].rotation.z = t*0.21
        faceGroup.children[1].rotation.z = t*0.78
        renderer.render(scene, cam)
      })()
      window.addEventListener('resize', () => { const w = innerWidth*0.67; cam.aspect = w/innerHeight; cam.updateProjectionMatrix(); renderer.setSize(w, innerHeight) })
    })
  }
}
