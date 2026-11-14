import json
from playwright.sync_api import sync_playwright

URL = "https://zjoachim.github.io/apptimer/guide.html"
JS = """() => {
  const el = document.querySelector('.aside-container');
  if (!el) return {missing: true};
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const link = document.querySelector('.outline-link.active');
  return {
    position: cs.position,
    top: Math.round(r.top),
    height: Math.round(r.height),
    scrollY: Math.round(window.scrollY),
    visible: r.top < window.innerHeight && r.bottom > 0,
    activeItem: link ? link.textContent.trim() : null
  };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1500)
    pg.screenshot(path="D:/apptimer/杂/toc_top.png")
    top = pg.evaluate(JS)
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    pg.wait_for_timeout(1500)
    pg.screenshot(path="D:/apptimer/杂/toc_bottom.png")
    bottom = pg.evaluate(JS)
    print(json.dumps({"top": top, "bottom": bottom}, ensure_ascii=False, indent=1))
    b.close()
