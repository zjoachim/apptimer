from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# 配色
DARK_BG = RGBColor(15, 15, 25)
ACCENT_BLUE = RGBColor(59, 130, 246)
ACCENT_PURPLE = RGBColor(139, 92, 246)
ACCENT_GREEN = RGBColor(34, 197, 94)
ACCENT_ORANGE = RGBColor(249, 115, 22)
ACCENT_PINK = RGBColor(236, 72, 153)
WHITE = RGBColor(255, 255, 255)
LIGHT_GRAY = RGBColor(180, 180, 200)
CARD_BG = RGBColor(25, 25, 40)
CARD_BG2 = RGBColor(30, 30, 50)

def add_bg(slide):
    bg = slide.background
    fill = bg.fill
    fill.gradient()
    fill.gradient_stops[0].color.rgb = RGBColor(10, 10, 20)
    fill.gradient_stops[0].position = 0.0
    fill.gradient_stops[1].color.rgb = RGBColor(20, 20, 45)
    fill.gradient_stops[1].position = 1.0

def add_card(slide, left, top, width, height, border_color=ACCENT_BLUE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_BG
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.5)
    return shape

def add_line(slide, left, top, width, color=ACCENT_BLUE):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Inches(0.06))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()

def add_page_title(slide, text):
    add_line(slide, Inches(0.8), Inches(1.15), Inches(1.8))
    box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11), Inches(0.8))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(32)
    p.font.color.rgb = WHITE
    p.font.bold = True

def add_text_card(slide, left, top, width, height, title, items, color=ACCENT_BLUE):
    add_card(slide, left, top, width, height, color)
    tb = slide.shapes.add_textbox(left + Inches(0.3), top + Inches(0.2), width - Inches(0.6), Inches(0.5))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(18)
    p.font.color.rgb = color
    p.font.bold = True

    cb = slide.shapes.add_textbox(left + Inches(0.3), top + Inches(0.7), width - Inches(0.6), height - Inches(1))
    tf = cb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.font.size = Pt(14)
        p.font.color.rgb = LIGHT_GRAY
        p.space_after = Pt(6)

# =============================================
# Slide 1: 封面
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)

# 装饰
for i in range(5):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(9.5 + i*0.7), Inches(5.8 + i*0.2), Inches(0.7), Inches(0.7))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor(40 + i*10, 80 + i*15, 200 + i*10)
    s.fill.fore_color.brightness = 0.4
    s.line.fill.background()

add_line(slide, Inches(3), Inches(2.2), Inches(7.3))

box = slide.shapes.add_textbox(Inches(1.5), Inches(2.6), Inches(10), Inches(1.5))
tf = box.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "基于Python的Windows程序使用时间追踪器设计与实现"
p.font.size = Pt(40)
p.font.color.rgb = WHITE
p.font.bold = True
p.alignment = PP_ALIGN.CENTER

box = slide.shapes.add_textbox(Inches(1.5), Inches(4.3), Inches(10), Inches(0.8))
tf = box.text_frame
p = tf.paragraphs[0]
p.text = "研究性学习报告"
p.font.size = Pt(26)
p.font.color.rgb = ACCENT_BLUE
p.alignment = PP_ALIGN.CENTER

box = slide.shapes.add_textbox(Inches(1.5), Inches(5.5), Inches(10), Inches(0.6))
tf = box.text_frame
p = tf.paragraphs[0]
p.text = "赵家乐    指导教师：余晓柱"
p.font.size = Pt(18)
p.font.color.rgb = LIGHT_GRAY
p.alignment = PP_ALIGN.CENTER

# =============================================
# Slide 2: 课题背景
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "一、课题/项目背景")

add_text_card(slide, Inches(0.5), Inches(1.5), Inches(3.8), Inches(5.3),
    "移动端", [
        "Android/iOS 内置屏幕使用时间",
        "用户已养成查看习惯",
        "系统级集成，体验流畅"
    ], ACCENT_PURPLE)

add_text_card(slide, Inches(4.7), Inches(1.5), Inches(3.8), Inches(5.3),
    "电脑端痛点", [
        "Windows 缺少原生功能",
        "第三方工具需付费",
        "功能单一，界面简陋"
    ], ACCENT_ORANGE)

add_text_card(slide, Inches(8.9), Inches(1.5), Inches(3.8), Inches(5.3),
    "项目目标", [
        "开发免费、易用的追踪器",
        "通过 Vibe Coding 方式实现",
        "全面的时间管理功能"
    ], ACCENT_GREEN)

# =============================================
# Slide 3: 研究内容与方法
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "二、调查研究内容与方法")

add_text_card(slide, Inches(0.5), Inches(1.5), Inches(5.8), Inches(2.3),
    "研究内容", [
        "1. Windows 程序使用时间检测原理与方法",
        "2. AI 辅助编程（Vibe Coding）实际应用",
        "3. 数据可视化技术在 UI 设计中的应用",
        "4. Python 在系统级编程中的能力边界"
    ], ACCENT_BLUE)

add_text_card(slide, Inches(0.5), Inches(4.1), Inches(5.8), Inches(2.3),
    "研究方法", [
        "1. 查阅相关开源项目代码",
        "2. Claude Code 实际开发，记录过程",
        "3. 对比 AI 辅助开发与传统开发差异"
    ], ACCENT_PURPLE)

add_text_card(slide, Inches(6.8), Inches(1.5), Inches(5.8), Inches(4.9),
    "实施过程", [
        "1. 需求分析 — 确定目标与功能范围",
        "2. 技术选择 — 选定工具和框架",
        "3. 架构设计 — 系统架构与数据流程",
        "4. 编码实现 — 使用 Claude Code 编写代码",
        "5. 测试优化 — 功能测试与性能优化",
        "6. 部署发布 — 打包 exe 与文档编写"
    ], ACCENT_GREEN)

# =============================================
# Slide 4: 具体任务
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "三、具体任务")

tasks = [
    ("01", "需求分析", "调研现有工具\n确定核心功能", ACCENT_BLUE),
    ("02", "技术选型", "研究 Windows API\n探索 Python 可行性", ACCENT_PURPLE),
    ("03", "架构设计", "前后端分离架构\n规划数据流程", ACCENT_GREEN),
    ("04", "功能开发", "时间检测记录\n统计分析与可视化", ACCENT_ORANGE),
    ("05", "界面优化", "深色主题设计\n交互与托盘图标", ACCENT_PINK),
    ("06", "测试调试", "稳定性测试\n修复 bug、性能优化", ACCENT_BLUE),
    ("07", "部署文档", "打包 exe\n编写文档、部署网站", ACCENT_PURPLE),
]

for i, (num, title, desc, color) in enumerate(tasks):
    row = i // 4
    col = i % 4
    left = Inches(0.5 + col * 3.15)
    top = Inches(1.5 + row * 2.9)
    add_card(slide, left, top, Inches(2.85), Inches(2.4), color)

    # 序号
    nb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), Inches(0.8), Inches(0.6))
    tf = nb.text_frame
    p = tf.paragraphs[0]
    p.text = num
    p.font.size = Pt(28)
    p.font.color.rgb = color
    p.font.bold = True

    # 标题
    tb = slide.shapes.add_textbox(left + Inches(1), top + Inches(0.25), Inches(1.6), Inches(0.5))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(17)
    p.font.color.rgb = WHITE
    p.font.bold = True

    # 描述
    db = slide.shapes.add_textbox(left + Inches(0.3), top + Inches(1), Inches(2.3), Inches(1.2))
    tf = db.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = desc
    p.font.size = Pt(13)
    p.font.color.rgb = LIGHT_GRAY

# =============================================
# Slide 5: 所需设备
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "四、所需设备")

add_text_card(slide, Inches(0.5), Inches(1.5), Inches(5.8), Inches(5.3),
    "硬件设备", [
        "一台运行 Windows 11 的电脑",
        "稳定的网络连接",
        "用于 Claude Code 调用 DeepSeek 大模型 API"
    ], ACCENT_BLUE)

add_text_card(slide, Inches(6.8), Inches(1.5), Inches(5.8), Inches(5.3),
    "软件环境", [
        "Python 3.14 开发环境",
        "Claude Code（AI 编程工具）",
        "Visual Studio Code（代码编辑器）",
        "Git（版本控制）",
        "Node.js（前端构建）",
        "VMware 虚拟机（测试 Win10 兼容性）"
    ], ACCENT_PURPLE)

# =============================================
# Slide 6: 有利条件分析
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "五、有利条件分析")

add_text_card(slide, Inches(0.5), Inches(1.5), Inches(3.8), Inches(5.3),
    "技术基础", [
        "已掌握 Python 编程基础",
        "能看懂简单的 Python 代码",
        "了解前端后端相关概念",
        "具备基本软件开发流程认知"
    ], ACCENT_GREEN)

add_text_card(slide, Inches(4.7), Inches(1.5), Inches(3.8), Inches(5.3),
    "工具支持", [
        "Claude Code AI 辅助编程能力",
        "丰富的开源库和框架",
        "GitHub 代码托管平台"
    ], ACCENT_BLUE)

add_text_card(slide, Inches(8.9), Inches(1.5), Inches(3.8), Inches(5.3),
    "环境条件", [
        "家庭环境支持自主学习和开发",
        "有足够时间进行项目开发"
    ], ACCENT_ORANGE)

# =============================================
# Slide 7: 预计困难与措施
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "六、预计困难与措施")

add_text_card(slide, Inches(0.5), Inches(1.5), Inches(3.8), Inches(5.3),
    "技术难点", [
        "困难：Windows API 调用复杂",
        "系统级编程难度高",
        "",
        "措施：查阅官方文档",
        "参考开源项目实现",
        "逐步调试解决"
    ], ACCENT_ORANGE)

add_text_card(slide, Inches(4.7), Inches(1.5), Inches(3.8), Inches(5.3),
    "开发效率", [
        "困难：AI 代码需大量修改",
        "优化工作量大",
        "",
        "措施：合理规划步骤",
        "分阶段验证",
        "及时调整方向"
    ], ACCENT_PURPLE)

add_text_card(slide, Inches(8.9), Inches(1.5), Inches(3.8), Inches(5.3),
    "功能完善", [
        "困难：时间紧迫",
        "难以实现全部功能",
        "",
        "措施：优先核心功能",
        "次要功能后期迭代"
    ], ACCENT_PINK)

# =============================================
# Slide 8: 预期成果
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "七、预期成果")

add_text_card(slide, Inches(0.5), Inches(1.5), Inches(3.8), Inches(5.3),
    "软件成果", [
        "功能完整的 Windows 追踪器",
        "今日统计 / 累计数据 / 趋势图表",
        "深色主题 / 托盘图标 / 开机自启"
    ], ACCENT_BLUE)

add_text_card(slide, Inches(4.7), Inches(1.5), Inches(3.8), Inches(5.3),
    "设计成果", [
        "经过数据可视化设计的 UI",
        "饼图 / 折线图 / 柱状图",
        "深色主题提升视觉体验"
    ], ACCENT_PURPLE)

add_text_card(slide, Inches(8.9), Inches(1.5), Inches(3.8), Inches(5.3),
    "文档与网站", [
        "用户使用手册",
        "技术实现说明",
        "GitHub Pages 展示网站"
    ], ACCENT_GREEN)

# =============================================
# Slide 9: 资料分析结论
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "八、资料分析结论")

conclusions = [
    ("1", "Vibe Coding 重新定义人机协作", "开发者角色从指令执行者\n转变为概率性对话协作者", ACCENT_BLUE),
    ("2", "ECharts 体现声明式设计", "开箱即用的图表类型\n支持灵活配置", ACCENT_PURPLE),
    ("3", "平衡功能与简洁", "简洁直观的界面设计\n提供有意义的数据洞察", ACCENT_GREEN),
    ("4", "用户体验是成功关键", "深入理解用户需求\n精心设计交互体验", ACCENT_ORANGE),
    ("5", "理论支撑与实践价值", "基于 Vibe Coding 理念\nClaude Code 开发\nECharts 实现可视化", ACCENT_PINK),
]

for i, (num, title, desc, color) in enumerate(conclusions):
    left = Inches(0.4 + i * 2.55)
    add_card(slide, left, Inches(1.6), Inches(2.3), Inches(5), color)

    nb = slide.shapes.add_textbox(left + Inches(0.2), Inches(1.8), Inches(0.5), Inches(0.5))
    tf = nb.text_frame
    p = tf.paragraphs[0]
    p.text = num
    p.font.size = Pt(30)
    p.font.color.rgb = color
    p.font.bold = True

    tb = slide.shapes.add_textbox(left + Inches(0.2), Inches(2.5), Inches(1.9), Inches(1))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(14)
    p.font.color.rgb = WHITE
    p.font.bold = True

    db = slide.shapes.add_textbox(left + Inches(0.2), Inches(3.8), Inches(1.9), Inches(2.5))
    tf = db.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = desc
    p.font.size = Pt(12)
    p.font.color.rgb = LIGHT_GRAY

# =============================================
# Slide 10: 研究结论与反思
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_page_title(slide, "九、研究结论与反思")

add_text_card(slide, Inches(0.5), Inches(1.5), Inches(5.8), Inches(5.3),
    "研究结论", [
        "验证了 AI 辅助编程在实际开发中的可行性",
        "Vibe Coding 显著降低了开发门槛",
        "非专业开发者也能实现功能完整的桌面应用",
        "ECharts 将抽象数据转化为直观图表展示"
    ], ACCENT_GREEN)

add_text_card(slide, Inches(6.8), Inches(1.5), Inches(5.8), Inches(5.3),
    "研究反思", [
        "AI 生成的代码需要人工验证和调试",
        "需求描述不精确会导致开发方向偏差",
        "AI 对复杂业务逻辑理解有局限",
        "Vibe Coding 有价值但不能完全替代传统编程"
    ], ACCENT_ORANGE)

# =============================================
# Slide 11: 致谢
# =============================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)

for i in range(3):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(2 + i * 3.5), Inches(5.5), Inches(0.8), Inches(0.8))
    s.fill.solid()
    s.fill.fore_color.rgb = [ACCENT_BLUE, ACCENT_PURPLE, ACCENT_GREEN][i]
    s.fill.fore_color.brightness = 0.3
    s.line.fill.background()

add_line(slide, Inches(4.5), Inches(2), Inches(4.3))

tb = slide.shapes.add_textbox(Inches(1), Inches(2.3), Inches(11.3), Inches(0.8))
tf = tb.text_frame
p = tf.paragraphs[0]
p.text = "十、致谢"
p.font.size = Pt(36)
p.font.color.rgb = WHITE
p.font.bold = True
p.alignment = PP_ALIGN.CENTER

tb = slide.shapes.add_textbox(Inches(2), Inches(3.5), Inches(9.3), Inches(3))
tf = tb.text_frame
tf.word_wrap = True

lines = [
    "感谢指导教师余晓柱在研究过程中提供的专业指导和建议，帮助我明确了研究方向和技术路线。",
    "感谢 Claude Code 团队开发的 AI 编程工具，为本项目提供了高效的开发支持。",
    "感谢 Apache ECharts 开源社区提供的数据可视化解决方案。",
    "最后，感谢父母和同学在项目开发过程中的支持和鼓励。"
]
for i, line in enumerate(lines):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = line
    p.font.size = Pt(18)
    p.font.color.rgb = LIGHT_GRAY
    p.alignment = PP_ALIGN.CENTER
    p.space_before = Pt(16)

# 保存
output_path = r"C:\Users\Joachim\Desktop\转存\演示文稿.pptx"
prs.save(output_path)
print("PPT 已重新设计完成")
