import json
from playwright.sync_api import sync_playwright

URL = "https://zjoachim.github.io/apptimer/guide.html"
JS = """() => {
  const el = document.querySelector('.aside-container');
  const out = [];
  let n = el;
  while (n && n !== document.documentElement) {
    const cs = getComputedStyle(n);
    const flags = [];
    if (cs.transform !== 'none') flags.push('transform=' + cs.transform);
    if (cs.filter !== 'none') flags.push('filter=' + cs.filter);
    if (cs.perspective !== 'none') flags.push('perspective');
    if (cs.willChange !== 'auto') flags.push('will-change=' + cs.willChange);
    if (cs.contain !== 'none') flags.push('contain=' + cs.contain);
    if (cs.backdropFilter && cs.backdropFilter !== 'none') flags.push('backdrop-filter');
    if (flags.length) out.push({tag: n.tagName.toLowerCase(), cls: n.className, style: n.getAttribute('style') || '', flags});
    n = n.parentElement;
  }
  return {ancestorsWithContainingBlock: out, inlineOnVPContent: (document.querySelector('.VPContent')||{}).getAttribute ? document.querySelector('.VPContent').getAttribute('style') : null};
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 900})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1500)
    print("=== fresh load ===")
    print(json.dumps(pg.evaluate(JS), ensure_ascii=False, indent=1))
    # simulate in-site navigation (what theme/index.js reacts to)
    pg.click("text=常见问题")
    pg.wait_for_timeout(1200)
    pg.click("text=使用指南")
    pg.wait_for_timeout(1200)
    print("=== after in-site navigation ===")
    print(json.dumps(pg.evaluate(JS), ensure_ascii=False, indent=1))
    b.close()
