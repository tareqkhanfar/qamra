"""The educator's copy of the «دوسية التأسيس» plans as PDFs (Tareq's decision 1, 2026-09-28).

    uv run python scripts/educator_pdf.py            # out/workbook/educator-kg1.pdf and educator-kg2.pdf

Converts docs/workbook/educator-kg*.md (generated from the curriculum YAML by `qamra_workbook.plan
render`) to an A4 right-to-left PDF with the embedded fonts. The documents use a small Markdown subset:
headings, paragraphs, nested "- " lists, tables, "> " quotes and **bold**, which is all this converts.
"""

import asyncio
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/workbook"
OUT = ROOT / "out/workbook"
FONTS = (ROOT / "packages/pdf/src/qamra_pdf/fonts").as_uri()
FOOTER = (
    '<div style="width:100%;font:8px sans-serif;color:#585C72;text-align:center">'
    '<span class="pageNumber"></span> / <span class="totalPages"></span></div>'
)
CSS = """
@font-face { font-family: "Baloo Bhaijaan 2"; font-weight: 700 900;
             src: url("{fonts}/BalooBhaijaan2-ExtraBold.ttf"); }
@font-face { font-family: "IBM Plex Sans Arabic"; font-weight: 400 500;
             src: url("{fonts}/IBMPlexSansArabic-Regular.ttf"); }
@font-face { font-family: "IBM Plex Sans Arabic"; font-weight: 600 900;
             src: url("{fonts}/IBMPlexSansArabic-SemiBold.ttf"); }
@page { size: A4; margin: 16mm 15mm 18mm; }
body { font: 10.5pt/1.75 "IBM Plex Sans Arabic", sans-serif; color: #1C2140; margin: 0; }
h1 { font: 800 22pt/1.3 "Baloo Bhaijaan 2", sans-serif; color: #16204A; margin: 0 0 4mm; }
h2 { font: 800 15pt/1.35 "Baloo Bhaijaan 2", sans-serif; color: #16204A; margin: 8mm 0 3mm;
     border-top: 0.6mm solid #F2B33D; padding-top: 3mm; break-after: avoid; }
h3 { font: 700 12pt/1.4 "Baloo Bhaijaan 2", sans-serif; color: #16204A; margin: 5mm 0 2mm;
     break-after: avoid; }
p { margin: 0 0 2.5mm; }
ul { margin: 0 0 2.5mm; padding-inline-start: 6mm; }
li { margin-bottom: 1.2mm; }
blockquote { margin: 0 0 4mm; padding: 3mm 4mm; background: #FCEFD2; border-radius: 2mm; font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 9pt; margin: 2mm 0 4mm; }
th, td { border-bottom: 0.25mm solid #E4D6BC; padding: 1.4mm 1.8mm; text-align: start; vertical-align: top; }
thead th { background: #FCEFD2; font-weight: 600; }
tr { break-inside: avoid; }
code { font-family: monospace; font-size: 9pt; }
"""


def inline(text: str) -> str:
    out = html.escape(text.strip())
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", out)


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def to_html(markdown: str) -> str:
    """The Markdown subset of the educator documents → HTML."""
    out: list[str] = []
    lines = markdown.splitlines()
    i = 0
    depth = 0  # open <ul> levels

    def close_lists(to: int = 0) -> None:
        nonlocal depth
        while depth > to:
            out.append("</li></ul>")
            depth -= 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--") or stripped in ('<div dir="rtl">', "</div>"):
            i += 1
            continue
        bullet = re.match(r"^( *)- (.*)$", line)
        if bullet:
            level = len(bullet.group(1)) // 2 + 1
            if level > depth:
                while depth < level:
                    out.append("<ul><li>")
                    depth += 1
            else:
                close_lists(level)
                out.append("</li><li>")
            out.append(inline(bullet.group(2)))
            i += 1
            continue
        if depth and line.startswith("  "):  # a paragraph inside the current list item
            out.append(f"<p>{inline(stripped)}</p>")
            i += 1
            continue
        close_lists()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            out.append(f"<h{level}>{inline(stripped[level:])}</h{level}>")
        elif stripped.startswith(">"):
            out.append(f"<blockquote>{inline(stripped.lstrip('> '))}</blockquote>")
        elif stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            head, body = _cells(rows[0]), [r for r in rows[1:] if not re.match(r"^\|[\s|:-]+\|$", r.strip())]
            out.append(
                "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            )
            out += ["<tr>" + "".join(f"<td>{inline(c)}</td>" for c in _cells(r)) + "</tr>" for r in body]
            out.append("</tbody></table>")
            continue
        else:
            para = [stripped]
            while (
                i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^\s*([-#>|]|<)", lines[i + 1])
            ):
                i += 1
                para.append(lines[i].strip())
            out.append(f"<p>{inline(' '.join(para))}</p>")
        i += 1
    close_lists()
    return "\n".join(out)


async def render(level: str) -> Path:
    from qamra_pdf import html_to_pdf

    body = to_html((DOCS / f"educator-{level}.md").read_text(encoding="utf-8"))
    page = (
        f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        f"<style>{CSS.replace('{fonts}', FONTS)}</style></head><body>{body}</body></html>"
    )
    OUT.mkdir(parents=True, exist_ok=True)
    return await html_to_pdf(page, OUT / f"educator-{level}.pdf", footer=FOOTER)


def main() -> int:
    for level in ("kg1", "kg2"):
        print("wrote", asyncio.run(render(level)).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
