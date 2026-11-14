from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

doc = Document()

# 设置默认字体
style = doc.styles['Normal']
font = style.font
font.name = '宋体'
font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

# 标题样式
title_style = doc.styles['Title']
title_style.font.size = Pt(22)
title_style.font.bold = True
title_style.font.name = '黑体'
title_style.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
title_style.font.color.rgb = RGBColor(0, 0, 0)

# Heading 1样式
h1_style = doc.styles['Heading 1']
h1_style.font.size = Pt(16)
h1_style.font.bold = True
h1_style.font.name = '黑体'
h1_style.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
h1_style.font.color.rgb = RGBColor(0, 0, 0)

# Heading 2样式
h2_style = doc.styles['Heading 2']
h2_style.font.size = Pt(14)
h2_style.font.bold = True
h2_style.font.name = '黑体'
h2_style.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
h2_style.font.color.rgb = RGBColor(0, 0, 0)

def add_paragraph(text, style='Normal', bold=False, indent=False):
    p = doc.add_paragraph(text, style=style)
    if indent:
        p.paragraph_format.left_indent = Cm(1)
    for run in p.runs:
        run.font.name = '宋体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        if bold:
            run.font.bold = True
    return p

def add_list(text, indent_level=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5 + indent_level * 0.8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = '宋体'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    run.font.size = Pt(12)
    return p

# =============================================
# 封面
# =============================================
for _ in range(4):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('基于Python的Windows程序使用时间追踪器设计与实现')
run.font.name = '黑体'
run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
run.font.size = Pt(22)
run.font.bold = True

doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('研究性学习报告')
run.font.name = '宋体'
run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
run.font.size = Pt(16)

for _ in range(3):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('作者：赵家乐')
run.font.name = '宋体'
run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
run.font.size = Pt(14)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('指导教师：余晓柱')
run.font.name = '宋体'
run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
run.font.size = Pt(14)

doc.add_page_break()

# =============================================
# 正文内容
# =============================================

# 一、课题/项目背景
doc.add_heading('一、课题/项目背景', level=1)

add_list('项目灵感来源于移动端与电脑端的功能差异：')

add_list('Android手机内置"屏幕使用时间"功能，iOS也有类似功能，用户已养成查看习惯', 1)
add_list('Windows电脑缺少类似的原生功能，用户无法方便地监控屏幕使用时间', 1)
add_list('现有第三方工具功能单一、界面简陋，大多需要付费使用', 1)

add_list('')
add_list('项目目标：')

add_list('开发一款免费、易用、功能全面的Windows程序使用时间追踪器', 1)
add_list('通过AI辅助编程（Vibe Coding）方式实现', 1)
add_list('为Windows用户提供实用的时间管理工具', 1)

# 二、调查研究内容与方法
doc.add_heading('二、调查研究内容与方法', level=1)

doc.add_heading('1. 研究内容', level=2)

add_list('Windows系统下程序使用时间的检测原理和方法')
add_list('AI辅助编程（Vibe Coding）在软件开发中的实际应用')
add_list('数据可视化技术在用户界面设计中的应用')
add_list('Python语言在系统级编程中的能力边界')

doc.add_heading('2. 研究方法', level=2)

add_list('查阅相关开源项目代码')
add_list('通过Claude Code进行实际开发，记录开发过程')
add_list('对比AI辅助开发与传统开发方式的差异')

doc.add_heading('3. 实施过程', level=2)

add_list('1. 需求分析 — 确定项目目标和功能范围')
add_list('2. 技术选择 — 选择合适的开发工具和框架')
add_list('3. 架构设计 — 设计系统架构和数据流程')
add_list('4. 编码实现 — 使用Claude Code编写代码')
add_list('5. 测试优化 — 进行功能测试和性能优化')
add_list('6. 部署发布 — 打包exe和文档编写')

# 三、具体任务
doc.add_heading('三、具体任务', level=1)

add_list('1. 需求分析与规划')
add_list('调研现有程序使用时间追踪工具的功能和不足', 1)
add_list('确定项目的核心功能和发展方向', 1)
add_list('制定开发计划和时间安排', 1)

add_list('')
add_list('2. 技术研究与选型')
add_list('研究Windows API在程序使用时间检测中的应用', 1)
add_list('探索Python语言开发Windows桌面应用的可行性', 1)
add_list('选择合适的前端框架和可视化库', 1)

add_list('')
add_list('3. 系统架构设计')
add_list('设计前后端分离的系统架构', 1)
add_list('规划数据存储和处理流程', 1)
add_list('设计用户界面和交互流程', 1)

add_list('')
add_list('4. 核心功能开发')
add_list('实现程序使用时间的检测和记录功能', 1)
add_list('开发数据统计和分析模块', 1)
add_list('实现数据可视化展示', 1)

add_list('')
add_list('5. 界面设计与优化')
add_list('设计深色主题用户界面', 1)
add_list('优化用户交互体验', 1)
add_list('实现系统托盘图标和开机自启动功能', 1)

add_list('')
add_list('6. 测试与调试')
add_list('进行功能完整性和稳定性测试', 1)
add_list('修复发现的bug和问题', 1)
add_list('优化程序性能和用户体验', 1)

add_list('')
add_list('7. 部署与文档')
add_list('使用PyInstaller打包为exe可执行文件', 1)
add_list('编写用户使用手册和技术文档', 1)
add_list('部署项目展示网站', 1)

# 四、所需设备
doc.add_heading('四、所需设备', level=1)

doc.add_heading('硬件设备', level=2)

add_list('一台运行Windows 11操作系统的电脑')
add_list('稳定的网络连接，用于Claude Code调用DeepSeek大模型API')

doc.add_heading('软件环境', level=2)

add_list('Python 3.14开发环境')
add_list('Claude Code（AI编程工具）')
add_list('Visual Studio Code（代码编辑器）')
add_list('Git（版本控制工具）')
add_list('Node.js（前端构建环境）')
add_list('VMware虚拟机（用于测试Win10环境兼容性）')

# 五、有利条件分析
doc.add_heading('五、有利条件分析', level=1)

doc.add_heading('技术基础', level=2)

add_list('已掌握Python编程基础知识')
add_list('能看懂较为简单的Python代码')
add_list('了解前端后端相关概念')
add_list('具备基本的软件开发流程认知')

doc.add_heading('工具支持', level=2)

add_list('Claude Code提供强大的AI辅助编程能力')
add_list('丰富的开源库和框架可供使用')
add_list('GitHub平台提供代码托管和协作支持')

doc.add_heading('环境条件', level=2)

add_list('家庭环境支持自主学习和开发')
add_list('有足够的时间进行项目开发')

# 六、预计困难与措施
doc.add_heading('六、预计困难与措施', level=1)

doc.add_heading('技术难点', level=2)

add_list('困难：Windows API调用和系统级编程较为复杂')
add_list('措施：查阅官方文档，参考开源项目实现，逐步调试')

doc.add_heading('开发效率', level=2)

add_list('困难：AI生成的代码可能需要大量修改和优化')
add_list('措施：合理规划开发步骤，分阶段验证，及时调整')

doc.add_heading('功能完善', level=2)

add_list('困难：时间紧迫，难以实现所有预期功能')
add_list('措施：优先实现核心功能，次要功能后期迭代')

# 七、预期成果
doc.add_heading('七、预期成果', level=1)

doc.add_heading('软件成果', level=2)

add_list('功能完整的Windows程序使用时间追踪器')
add_list('包含今日统计、累计数据、趋势图表等核心功能')
add_list('支持深色主题、托盘图标、开机自启等特性')

doc.add_heading('设计成果', level=2)

add_list('经过数据可视化设计的用户界面')
add_list('多种可视化图表（饼图、折线图、柱状图）')
add_list('深色主题界面，提升视觉体验')

doc.add_heading('技术文档', level=2)

add_list('用户使用手册')
add_list('技术实现说明')

doc.add_heading('展示网站', level=2)

add_list('项目介绍和功能展示网站')
add_list('部署在GitHub Pages上，可在线访问')

# 八、资料分析结论
doc.add_heading('八、资料分析结论', level=1)

add_list('1. Vibe Coding重新定义了人机协作编程模式')
add_list('CHI 2026论文指出，Vibe Coding将开发者的角色从"确定性指令执行者"转变为"概率性对话协作者"', 1)

add_list('')
add_list('2. ECharts框架体现了声明式可视化设计原则')
add_list('提供开箱即用的图表类型，同时支持灵活配置', 1)

add_list('')
add_list('3. 屏幕时间追踪应用设计需平衡功能与简洁')
add_list('采用简洁直观的界面设计，提供有意义的数据洞察', 1)

add_list('')
add_list('4. 用户体验设计是技术应用成功的关键因素')
add_list('技术应用的成功离不开对用户需求的深入理解和对交互体验的精心设计', 1)

add_list('')
add_list('5. 本项目的理论支撑与实践价值')
add_list('基于Vibe Coding理念，使用Claude Code辅助开发，通过ECharts实现数据可视化', 1)

# 九、研究结论与反思
doc.add_heading('九、研究结论与反思', level=1)

doc.add_heading('研究结论', level=2)

add_list('本项目通过Vibe Coding方式，验证了AI辅助编程在实际软件开发中的可行性')
add_list('Vibe Coding显著降低了开发门槛，使非专业开发者也能快速实现功能完整的桌面应用')
add_list('ECharts数据可视化技术的应用，使抽象的使用时间数据转化为直观的图表展示')

doc.add_heading('研究反思', level=2)

add_list('AI辅助编程存在局限性，AI生成的代码需要人工验证和调试')
add_list('需求描述不够精确会导致开发方向偏差')
add_list('AI对复杂业务逻辑的理解仍有不足，需要开发者具备一定的技术判断能力')
add_list('Vibe Coding是一种有价值的开发方式，但不能完全替代传统编程')

# 十、致谢
doc.add_heading('十、致谢', level=1)

add_list('感谢指导教师余晓柱在研究过程中提供的专业指导和建议，帮助我明确了研究方向和技术路线。')
add_list('')
add_list('感谢Claude Code团队开发的AI编程工具，为本项目提供了高效的开发支持。')
add_list('')
add_list('感谢Apache ECharts开源社区提供的数据可视化解决方案。')
add_list('')
add_list('最后，感谢父母和同学在项目开发过程中的支持和鼓励。')

# 保存
output_path = r'C:\Users\Joachim\Desktop\转存\研究报告.docx'
doc.save(output_path)
print('Word文档已重新生成完成')
