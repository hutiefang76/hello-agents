"""HTML 路线生成 PDF：pandoc → 标准 HTML → Chrome headless → PDF。"""
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
OUT_DIR = Path(r"C:\Users\Administrator\Downloads")
OUT_PDF = OUT_DIR / "Hello-Agents-大大大大大芳整理版.pdf"
TMP_MD = ROOT / "_combined.md"
TMP_HTML = ROOT / "_combined.html"
CSS_FILE = ROOT / "_book.css"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

ORDER = [
    ("docs/前言.md", "前言"),
    ("docs/chapter1/第一章 初识智能体.md", None),
    ("docs/chapter2/第二章 智能体发展史.md", None),
    ("docs/chapter3/第三章 大语言模型基础.md", None),
    ("docs/chapter4/第四章 智能体经典范式构建.md", None),
    ("docs/chapter5/第五章 基于低代码平台的智能体搭建.md", None),
    ("docs/chapter6/第六章 框架开发实践.md", None),
    ("docs/chapter7/第七章 构建你的Agent框架.md", None),
    ("docs/chapter8/第八章 记忆与检索.md", None),
    ("docs/chapter9/第九章 上下文工程.md", None),
    ("docs/chapter10/第十章 智能体通信协议.md", None),
    ("docs/chapter11/第十一章 Agentic-RL.md", None),
    ("docs/chapter12/第十二章 智能体性能评估.md", None),
    ("docs/chapter13/第十三章 智能旅行助手.md", None),
    ("docs/chapter14/第十四章 自动化深度研究智能体.md", None),
    ("docs/chapter15/第十五章 构建赛博小镇.md", None),
    ("docs/chapter16/第十六章 毕业设计.md", None),
]

EXTRAS = [
    "Extra-Chapter/Extra01-面试问题总结.md",
    "Extra-Chapter/Extra01-参考答案.md",
    "Extra-Chapter/Extra02-上下文工程补充知识.md",
    "Extra-Chapter/Extra03-Dify智能体创建保姆级操作流程.md",
    "Extra-Chapter/Extra04-DatawhaleFAQ.md",
    "Extra-Chapter/Extra05-AgentSkills解读.md",
    "Extra-Chapter/Extra06-GUIAgent科普与实战.md",
    "Extra-Chapter/Extra07-环境配置.md",
    "Extra-Chapter/Extra08-如何写出好的Skill.md",
    "Extra-Chapter/Extra09-Agent应用开发实践踩坑与经验分享.md",
]

COVER = """# Hello-Agents · 大大大大大芳 学习整理版 {.cover-title}

<div class="cover-meta">

整理者：知乎 大大大大大芳<br>
微信：hutiefang　·　GitHub：hutiefang76

整理自互联网公开学习资料<br>
仅供个人学习交流，非商业用途

</div>

<div class="page-break"></div>

# 关于本整理版

- **整理者**：知乎 大大大大大芳
- **微信**：hutiefang
- **GitHub**：hutiefang76
- **协议**：CC BY-NC-SA 4.0
- **用途**：仅供个人学习交流，非商业用途

<div class="page-break"></div>

"""


DOCS_IMG_DIR = ROOT / "docs" / "images"
GITHUB_RAW_PREFIX = "https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/"


def remap_remote(src: str) -> str:
    """把指向原仓库 raw GitHub 的 URL 映射回本地文件（仓库已 clone 在本地）。"""
    if src.startswith(GITHUB_RAW_PREFIX):
        rel = src[len(GITHUB_RAW_PREFIX):]
        local = (ROOT / rel).resolve()
        if local.exists():
            return local.as_posix()
    return src


def fix_paths(text: str, base_dir: Path) -> str:
    """转换图片路径为 file:/// 绝对，并把 <img> 转成 markdown ![]()。"""
    # 1) 拍平内链 [text](#anchor) -> text
    text = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", text)

    # 2) <img src="..." ...> 转成 markdown ![](...)
    def html_img(m):
        src = m.group(1).strip()
        # 远程 GitHub raw → 本地映射
        src = remap_remote(src)
        if src.startswith(("http://", "https://", "data:")):
            return f"![]({src})"
        # 已经是绝对本地路径
        if src.startswith(("/", "file://")) or "C:/" in src or "C:\\" in src:
            return f"![]({src})"
        # 相对路径
        abs_p = (base_dir / src).resolve()
        if abs_p.exists():
            return f"![]({abs_p.as_posix()})"
        return ""
    text = re.sub(r'<img\s+[^>]*src="([^"]+)"[^>]*/?>', html_img, text)

    # 3) markdown 图片相对路径 → 绝对路径，并映射远程 GitHub
    def md_img(m):
        alt = m.group(1)
        path = m.group(2).strip()
        path = remap_remote(path)
        if path.startswith(("http://", "https://", "/", "file://", "data:")):
            return f"![{alt}]({path})"
        if "C:/" in path or "C:\\" in path:
            return f"![{alt}]({path})"
        abs_p = (base_dir / path).resolve()
        return f"![{alt}]({abs_p.as_posix()})"
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", md_img, text)
    return text


def build_combined():
    parts = [COVER]
    for rel, _ in ORDER:
        p = ROOT / rel
        if not p.exists():
            print(f"[skip] {rel}")
            continue
        print(f"[+] {rel}")
        body = p.read_text(encoding="utf-8")
        body = fix_paths(body, p.parent)
        parts.append('\n\n<div class="page-break"></div>\n\n')
        parts.append(body)
    parts.append('\n\n<div class="page-break"></div>\n\n# 附录：Extra-Chapter\n\n')
    for rel in EXTRAS:
        p = ROOT / rel
        if not p.exists():
            print(f"[skip] {rel}")
            continue
        print(f"[+] {rel}")
        body = p.read_text(encoding="utf-8")
        body = fix_paths(body, p.parent)
        parts.append('\n\n<div class="page-break"></div>\n\n')
        parts.append(body)
    TMP_MD.write_text("".join(parts), encoding="utf-8")
    print(f"[ok] combined md: {TMP_MD.stat().st_size//1024} KB")


CSS = """
@page { size: A4; margin: 18mm 16mm; }
body {
  font-family: "Microsoft YaHei", "PingFang SC", "Source Han Sans CN", sans-serif;
  font-size: 11pt;
  line-height: 1.7;
  color: #2c2c2c;
  max-width: 100%;
}
h1 {
  font-size: 22pt;
  color: #c0392b;
  border-bottom: 3px solid #c0392b;
  padding-bottom: 8px;
  margin-top: 28px;
  page-break-before: always;
}
h1.cover-title {
  font-size: 32pt;
  text-align: center;
  border: none;
  margin-top: 200px;
  page-break-before: avoid;
}
h2 {
  font-size: 17pt;
  color: #2c3e50;
  border-left: 5px solid #c0392b;
  padding-left: 12px;
  margin-top: 24px;
}
h3 { font-size: 14pt; color: #34495e; margin-top: 18px; }
h4 { font-size: 12.5pt; color: #555; }
p { margin: 8px 0; text-align: justify; }
a { color: #2980b9; text-decoration: none; }
strong { color: #c0392b; }
em { color: #555; }
code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
  font-size: 10pt;
  color: #c7254e;
}
pre {
  background: #2d2d2d;
  color: #f0f0f0;
  padding: 12px 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 9.5pt;
  line-height: 1.5;
  page-break-inside: avoid;
}
pre code { background: transparent; color: inherit; padding: 0; }
blockquote {
  border-left: 4px solid #f39c12;
  background: #fffbf0;
  margin: 12px 0;
  padding: 8px 16px;
  color: #555;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 10pt;
  page-break-inside: avoid;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px 10px;
  text-align: left;
}
th { background: #34495e; color: white; }
tr:nth-child(even) { background: #f8f8f8; }
img {
  max-width: 90%;
  height: auto;
  display: block;
  margin: 16px auto;
  border: 1px solid #eee;
  border-radius: 4px;
}
ul, ol { margin: 8px 0; padding-left: 28px; }
li { margin: 4px 0; }
hr { border: none; border-top: 1px dashed #ccc; margin: 20px 0; }
.page-break { page-break-before: always; height: 0; }
.cover-meta {
  text-align: center;
  font-size: 13pt;
  color: #555;
  margin-top: 60px;
}
#TOC { page-break-after: always; }
#TOC > ul { list-style: none; padding-left: 0; }
#TOC ul ul { padding-left: 20px; font-size: 10.5pt; }
#TOC a { color: #2c3e50; }
"""


def build_html():
    CSS_FILE.write_text(CSS, encoding="utf-8")
    cmd = [
        "pandoc",
        str(TMP_MD),
        "--from=markdown-yaml_metadata_block-citations+raw_html+emoji",
        "--to=html5",
        "--standalone",
        "--metadata", "title=Hello-Agents · 大大大大大芳整理版",
        "--toc",
        "--toc-depth=2",
        "--css", str(CSS_FILE),
        "-o", str(TMP_HTML),
    ]
    print("[run pandoc]")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("[stderr]", r.stderr[-2000:])
        return False
    print(f"[ok] html: {TMP_HTML.stat().st_size//1024} KB")
    return True


def html_to_pdf():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_PDF.exists():
        OUT_PDF.unlink()
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--virtual-time-budget=30000",
        f"--print-to-pdf={OUT_PDF}",
        TMP_HTML.as_uri(),
    ]
    print("[run chrome]")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if not OUT_PDF.exists():
        print("[stderr]", r.stderr[-2000:])
        print("[stdout]", r.stdout[-1000:])
        return False
    print(f"[ok] pdf: {OUT_PDF} ({OUT_PDF.stat().st_size//1024} KB)")
    return True


def main():
    build_combined()
    if not build_html():
        sys.exit(1)
    if not html_to_pdf():
        sys.exit(2)
    print("Done.")


if __name__ == "__main__":
    main()
