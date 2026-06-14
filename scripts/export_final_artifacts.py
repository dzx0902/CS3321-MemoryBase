from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import markdown
from bs4 import BeautifulSoup, Tag


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
REPORT_MD = DOCS_DIR / "final-report.md"
REPORT_HTML = DOCS_DIR / "final-report.print.html"
REPORT_PDF = DOCS_DIR / "final-report.pdf"
SLIDES_HTML = DOCS_DIR / "final-assets" / "slides" / "gap7-final-defense.html"
SLIDES_PDF = DOCS_DIR / "final-assets" / "slides" / "gap7-final-defense.pdf"

EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)

REPORT_STYLE = """
@page {
  size: A4;
  margin: 11mm 10mm 12mm 10mm;
}

:root {
  --text: #1f2328;
  --muted: #5b6570;
  --line: #d8dee4;
  --soft: #f6f8fa;
  --accent: #1b365d;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  color: var(--text);
  background: white;
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  font-size: 10pt;
  line-height: 1.58;
}

main {
  max-width: 100%;
  margin: 0 auto;
}

h1, h2, h3, h4 {
  color: var(--accent);
  line-height: 1.32;
  break-after: avoid;
}

h1 {
  font-size: 20pt;
  margin: 0 0 6pt;
}

h2 {
  font-size: 15.5pt;
  margin: 14pt 0 6pt;
  padding-bottom: 3pt;
  border-bottom: 1px solid var(--line);
}

h3 {
  font-size: 12.5pt;
  margin: 10pt 0 4pt;
}

h4 {
  font-size: 11.2pt;
  margin: 8pt 0 4pt;
}

p, ul, ol, table, pre, blockquote, figure {
  margin: 0 0 6pt;
}

ul, ol {
  padding-left: 1.3em;
}

li {
  margin: 1.5pt 0;
}

code {
  font-family: "JetBrains Mono", Consolas, monospace;
  background: var(--soft);
  padding: 0.08em 0.28em;
  border-radius: 3px;
  font-size: 0.92em;
}

pre {
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 8pt 9pt;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  break-inside: avoid;
}

pre code {
  background: transparent;
  padding: 0;
}

blockquote {
  border-left: 3px solid var(--line);
  padding-left: 9pt;
  color: var(--muted);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 8.8pt;
  break-inside: avoid;
}

th, td {
  border: 1px solid var(--line);
  padding: 4pt 5pt;
  vertical-align: top;
}

th {
  background: var(--soft);
  text-align: left;
}

.meta-block {
  margin: 0 0 8pt;
  padding: 6pt 8pt;
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 7px;
}

.meta-block p {
  margin: 0 0 3pt;
}

.meta-block p:last-child {
  margin-bottom: 0;
}

.report-figure {
  margin: 6pt 0 8pt;
  break-inside: avoid;
}

.report-figure img {
  display: block;
  max-width: 100%;
  max-height: 115mm;
  width: auto;
  height: auto;
  margin: 0 auto 4pt;
  border: 1px solid var(--line);
}

.report-figure figcaption {
  font-size: 8.8pt;
  color: var(--muted);
  font-style: italic;
  text-align: left;
}

.figure-grid {
  display: flex;
  gap: 9pt;
  align-items: flex-start;
  margin: 6pt 0 8pt;
}

.figure-grid .report-figure {
  flex: 1 1 0;
  margin: 0;
}

.figure-grid .report-figure img {
  max-height: 70mm;
  width: 100%;
  object-fit: contain;
}

hr {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 10pt 0;
}

em {
  color: var(--muted);
}
"""


def _pick_browser() -> Path:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No Edge/Chrome executable found for PDF export.")


def _promote_figures(soup: BeautifulSoup) -> None:
    for paragraph in list(soup.find_all("p")):
        if len(paragraph.contents) != 1:
            continue
        image = paragraph.find("img", recursive=False)
        if image is None:
            continue

        figure = soup.new_tag("figure", attrs={"class": "report-figure"})
        figure.append(image.extract())
        paragraph.replace_with(figure)

        caption_p = figure.find_next_sibling("p")
        if caption_p is None:
            continue

        em = caption_p.find("em", recursive=False)
        if em is None:
            continue

        caption_text = em.get_text(" ", strip=True)
        if not caption_text.startswith("图 "):
            continue

        caption = soup.new_tag("figcaption")
        caption.string = caption_text
        figure.append(caption)
        caption_p.decompose()


def _wrap_meta_block(soup: BeautifulSoup) -> None:
    h1 = soup.find("h1")
    if h1 is None:
        return

    meta_paragraphs: list[Tag] = []
    node = h1.find_next_sibling()
    while isinstance(node, Tag) and node.name == "p":
        text = node.get_text(" ", strip=True)
        if not (text.startswith("课程：") or text.startswith("小组成员：")):
            break
        meta_paragraphs.append(node)
        node = node.find_next_sibling()

    if not meta_paragraphs:
        return

    wrapper = soup.new_tag("div", attrs={"class": "meta-block"})
    meta_paragraphs[0].insert_before(wrapper)
    for paragraph in meta_paragraphs:
        wrapper.append(paragraph.extract())


def _wrap_llm_compare_grid(soup: BeautifulSoup) -> None:
    heading = next(
        (
            tag
            for tag in soup.find_all(["h3", "h4"])
            if "Optional LLM candidate extraction 对比" in tag.get_text(" ", strip=True)
        ),
        None,
    )
    if heading is None:
        return

    figures: list[Tag] = []
    node = heading.find_next_sibling()
    while isinstance(node, Tag):
        if node.name in {"h3", "h4", "h2"}:
            break
        if node.name == "figure" and "report-figure" in node.get("class", []):
            figures.append(node)
            if len(figures) == 2:
                break
        node = node.find_next_sibling()

    if len(figures) != 2:
        return

    grid = soup.new_tag("div", attrs={"class": "figure-grid"})
    figures[0].insert_before(grid)
    for figure in figures:
        grid.append(figure.extract())


def _render_report_html() -> None:
    markdown_text = REPORT_MD.read_text(encoding="utf-8")
    body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    soup = BeautifulSoup(body, "lxml")
    _promote_figures(soup)
    _wrap_meta_block(soup)
    _wrap_llm_compare_grid(soup)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MemoryBase Final Report</title>
<style>
{REPORT_STYLE}
</style>
</head>
<body>
<main>
{str(soup)}
</main>
</body>
</html>
"""
    REPORT_HTML.write_text(html, encoding="utf-8")


def _print_to_pdf(html_path: Path, pdf_path: Path) -> None:
    browser = _pick_browser()
    subprocess.run(
        [
            str(browser),
            "--headless",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ],
        check=True,
    )


def export_report() -> None:
    _render_report_html()
    try:
        _print_to_pdf(REPORT_HTML, REPORT_PDF)
    finally:
        if REPORT_HTML.exists():
            REPORT_HTML.unlink()


def export_slides() -> None:
    _print_to_pdf(SLIDES_HTML, SLIDES_PDF)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export final report and slides PDFs.")
    parser.add_argument(
        "--target",
        choices=("all", "report", "slides"),
        default="all",
        help="Which artifacts to export.",
    )
    args = parser.parse_args()

    if args.target in {"all", "report"}:
        export_report()
    if args.target in {"all", "slides"}:
        export_slides()


if __name__ == "__main__":
    main()
