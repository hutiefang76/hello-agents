"""扫描 PDF 页文本，注入 H1/H2 大纲（书签）。"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).parent
HTML = ROOT / "_combined.html"
PDF_IN = Path(r"C:\Users\Administrator\Downloads\Hello-Agents-大大大大大芳整理版.pdf")
PDF_OUT = Path(r"C:\Users\Administrator\Downloads\Hello-Agents-大大大大大芳整理版-带书签.pdf")


def extract_headings():
    """从 HTML 抽 H1/H2 顺序列表。"""
    soup = BeautifulSoup(HTML.read_text(encoding="utf-8"), "html.parser")
    headings = []
    for h in soup.find_all(["h1", "h2"]):
        level = int(h.name[1])
        text = h.get_text(strip=True)
        if not text or text == "Contents" or text == "目录":
            continue
        headings.append((level, text))
    return headings


def normalize(s: str) -> str:
    return re.sub(r"\s+", "", s)


def find_pages(reader: PdfReader, headings):
    """正向扫描 PDF：每个 heading 首次出现的页号（0-based）。"""
    matches = []
    n_pages = len(reader.pages)
    print(f"[info] PDF 页数: {n_pages}, 待匹配标题: {len(headings)}")

    # 一次性提取所有页文本（缓存）
    print("[info] 提取页文本...")
    page_texts = []
    for i in range(n_pages):
        try:
            page_texts.append(normalize(reader.pages[i].extract_text() or ""))
        except Exception:
            page_texts.append("")
        if (i + 1) % 100 == 0:
            print(f"  ...{i+1}/{n_pages}")

    # 识别 TOC 页：含我们 30+ 个标题的页就是 TOC
    targets = [(lvl, txt, normalize(txt)) for lvl, txt in headings if normalize(txt)]
    toc_end = 0
    for i in range(min(50, n_pages)):
        hit_count = sum(1 for _, _, t in targets if t and t in page_texts[i])
        if hit_count >= 30:
            toc_end = i + 1  # TOC 占用到第 i 页（含），下一页开始正文
    print(f"[info] TOC 范围：第 1-{toc_end} 页（跳过）")

    cursor = toc_end
    for idx, (level, text, target) in enumerate(targets):
        if not target:
            continue
        found = -1
        for i in range(cursor, n_pages):
            if target in page_texts[i]:
                found = i
                break
        if found == -1:
            short = target[:8]
            if len(short) >= 4:
                for i in range(cursor, n_pages):
                    if short in page_texts[i]:
                        found = i
                        break
        if found != -1:
            matches.append((level, text, found))
            cursor = found
            if idx % 20 == 0:
                print(f"  [{idx}/{len(targets)}] L{level} p{found+1} {text[:30]}")
        else:
            print(f"  [SKIP] L{level} {text[:30]}")
    return matches


def write_outline(matches):
    reader = PdfReader(str(PDF_IN))
    writer = PdfWriter(clone_from=reader)

    # 按层级构建：维护 H1 父节点
    h1_parent = None
    for level, text, page in matches:
        if level == 1:
            h1_parent = writer.add_outline_item(text, page, parent=None)
        else:
            writer.add_outline_item(text, page, parent=h1_parent)

    with open(PDF_OUT, "wb") as f:
        writer.write(f)
    print(f"[ok] 写出: {PDF_OUT} ({PDF_OUT.stat().st_size//1024} KB)")


def main():
    if not PDF_IN.exists():
        print(f"[err] {PDF_IN} 不存在")
        sys.exit(1)
    if not HTML.exists():
        print(f"[err] {HTML} 不存在")
        sys.exit(2)

    headings = extract_headings()
    print(f"[info] 提取到 {len(headings)} 个标题")

    reader = PdfReader(str(PDF_IN))
    matches = find_pages(reader, headings)
    print(f"[info] 成功匹配 {len(matches)}/{len(headings)}")

    write_outline(matches)


if __name__ == "__main__":
    main()
