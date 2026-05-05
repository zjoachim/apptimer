import DefaultTheme from 'vitepress/theme'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ router }) {
    if (typeof window === 'undefined') return
    router.onAfterRouteChanged = () => {
      setTimeout(() => {
        document.querySelectorAll('.reveal').forEach(el => {
          const rect = el.getBoundingClientRect()
          if (rect.top < innerHeight) el.classList.add('visible')
        })
      }, 100)
    }
    // scroll reveal
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible') })
    }, { threshold: 0.1 })
    setTimeout(() => {
      document.querySelectorAll('.reveal').forEach(el => obs.observe(el))
    }, 200)
  }
}
