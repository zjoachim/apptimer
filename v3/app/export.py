"""导出 PDF 报告（fpdf2 + 系统微软雅黑）。"""
from datetime import datetime
from pathlib import Path

from . import db, store

FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT = "msyh"


def _fmt(sec):
    sec = int(max(0, sec or 0))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%d 小时 %d 分" % (h, m)
    if m:
        return "%d 分 %d 秒" % (m, s)
    return "%d 秒" % s


def _category_totals(usage, categories):
    out = {}
    for app, sec in usage.items():
        cat = categories.get(app) or "未分类"
        out[cat] = out.get(cat, 0.0) + sec
    return sorted(out.items(), key=lambda kv: -kv[1])


def export_pdf(path=None):
    """生成当日报告 PDF，返回 (ok, 路径或错误信息)。"""
    conn = store.connection()
    date = datetime.now().strftime("%Y-%m-%d")
    usage = db.today_usage(conn, date)
    cumulative = db.cumulative(conn)
    categories = db.categories(conn)
    total = sum(usage.values()) or 1.0

    out = Path(path) if path else (store.data_root() / ("报告_%s.pdf" % date))
    try:
        from fpdf import FPDF   # 惰性导入：fpdf2 会带进 fontTools，常驻会多吃约 40MB

        out.parent.mkdir(parents=True, exist_ok=True)
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(True, 14)
        pdf.add_font(FONT, "", FONT_PATH)
        pdf.add_page()
        pdf.set_font(FONT, size=18)
        pdf.cell(0, 12, "程序使用报告", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT, size=10)
        pdf.set_text_color(110, 110, 120)
        pdf.cell(0, 6, "%s · 由 AppTimer 生成于 %s"
                 % (date, datetime.now().strftime("%Y-%m-%d %H:%M")),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        pdf.set_text_color(30, 30, 35)
        pdf.set_font(FONT, size=12)
        pdf.cell(0, 8, "今日合计：%s · 应用 %d 个 · 已分类 %d 个"
                 % (_fmt(total), len(usage), sum(1 for v in categories.values() if v)),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # 今日明细
        pdf.set_font(FONT, size=11)
        pdf.cell(0, 7, "今日明细", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT, size=9)
        pdf.set_text_color(90, 90, 100)
        widths = (96, 28, 28, 20)
        for w, head in zip(widths, ("应用", "今日", "累计", "占比")):
            pdf.cell(w, 6, head, border="B")
        pdf.ln(6)
        pdf.set_text_color(30, 30, 35)
        for name, sec in list(usage.items())[:40]:
            pdf.cell(widths[0], 6, name[:44], border="B")
            pdf.cell(widths[1], 6, _fmt(sec), border="B", align="R")
            pdf.cell(widths[2], 6, _fmt(cumulative.get(name, 0)), border="B", align="R")
            pdf.cell(widths[3], 6, "%.1f%%" % (sec / total * 100), border="B", align="R")
            pdf.ln(6)
        if not usage:
            pdf.cell(0, 6, "今日暂无记录", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # 分类汇总
        pdf.set_font(FONT, size=11)
        pdf.cell(0, 7, "分类汇总", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT, size=9)
        rows = _category_totals(usage, categories)
        if not rows:
            pdf.cell(0, 6, "暂无分类数据", new_x="LMARGIN", new_y="NEXT")
        for cat, sec in rows:
            pdf.cell(96, 6, cat, border="B")
            pdf.cell(28, 6, _fmt(sec), border="B", align="R")
            pdf.cell(20, 6, "%.1f%%" % (sec / total * 100), border="B", align="R")
            pdf.ln(6)
        pdf.output(str(out))
        return True, out
    except Exception as exc:      # 字体缺失、磁盘写保护等
        return False, str(exc)
