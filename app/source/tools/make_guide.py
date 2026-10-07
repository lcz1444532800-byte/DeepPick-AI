"""Render the bundled Markdown guide as a self-contained offline HTML page."""
import html
import re
from pathlib import Path

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', type=Path, required=True)
base = parser.parse_args().directory.resolve()
source = (base / 'User-Guide.md').read_text('utf-8')

def inline(text):
    text = html.escape(text)
    text = re.sub(r'\[([^\]]+)\]\((https://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text.replace('\\\\', '\\')

parts, navigation = [], []
lines = source.splitlines()
index = 0
faq = False
detail = False
while index < len(lines):
    line = lines[index]
    if not line.strip():
        index += 1
        continue
    if line.startswith('# '):
        parts.append('<h1>' + inline(line[2:]) + '</h1>')
    elif line.startswith('## '):
        if detail:
            parts.append('</div></details>')
            detail = False
        title = line[3:]
        identity = 'section-' + str(len(navigation) + 1)
        navigation.append((identity, title))
        parts.append('<h2 id="' + identity + '">' + inline(title) + '</h2>')
        faq = title.startswith('9.')
    elif line.startswith('### '):
        if detail:
            parts.append('</div></details>')
        if faq:
            parts.append('<details><summary>' + inline(line[4:]) + '</summary><div class="answer">')
            detail = True
        else:
            parts.append('<h3>' + inline(line[4:]) + '</h3>')
    elif line.startswith('|'):
        rows = []
        while index < len(lines) and lines[index].startswith('|'):
            cells = [cell.strip() for cell in lines[index].strip('|').split('|')]
            if not all(re.fullmatch(r'[:\s-]+', cell) for cell in cells):
                rows.append(cells)
            index += 1
        parts.append('<div class="table"><table><thead><tr>' + ''.join('<th>' + inline(cell) + '</th>' for cell in rows[0]) + '</tr></thead><tbody>')
        for row in rows[1:]:
            parts.append('<tr>' + ''.join('<td>' + inline(cell) + '</td>' for cell in row) + '</tr>')
        parts.append('</tbody></table></div>')
        continue
    elif re.match(r'^\d+\. ', line):
        parts.append('<ol>')
        while index < len(lines) and re.match(r'^\d+\. ', lines[index]):
            parts.append('<li>' + inline(re.sub(r'^\d+\. ', '', lines[index])) + '</li>')
            index += 1
        parts.append('</ol>')
        continue
    else:
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].startswith(('#', '|')):
            paragraph.append(lines[index])
            index += 1
        parts.append('<p>' + inline(' '.join(paragraph)) + '</p>')
        continue
    index += 1
if detail:
    parts.append('</div></details>')

css = '''
:root{color-scheme:light;--ink:#17202b;--muted:#697484;--line:#e8ebef;--accent:#1c694e}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:34px}
body{margin:0;background:#fff;color:var(--ink);font:16px/1.85 "Segoe UI",Arial,sans-serif}
.shell{max-width:1160px;margin:auto;display:grid;grid-template-columns:220px minmax(0,1fr);gap:62px;padding:52px 36px 70px}
nav{position:sticky;top:40px;align-self:start}nav .brand{font-weight:650;font-size:22px;margin-bottom:5px}.tag{color:var(--muted);font-size:13px;margin-bottom:26px}
nav a{display:block;padding:7px 12px;margin:3px 0;border-radius:7px;color:#596474;font-size:14px;text-decoration:none}nav a:hover{background:#f2f7f4;color:var(--accent)}
h1{font-size:46px;letter-spacing:-1.7px;line-height:1.1;margin:0 0 20px}h1+p{color:var(--muted);font-size:19px;margin-bottom:8px}h1+p+p{color:#89929e;font-size:13px;margin-top:0;margin-bottom:40px}
h2{font-size:25px;line-height:1.4;margin:54px 0 22px;letter-spacing:-.5px;padding-top:15px;border-top:1px solid var(--line)}h3{font-size:18px}
p{margin:15px 0}a{color:var(--accent);text-underline-offset:4px}strong{font-weight:650}li{padding-left:4px;margin:10px 0}ol{padding-left:24px}
.table{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:22px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px 15px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{background:#f5f7f8;font-weight:650}tr:last-child td{border-bottom:0}
code{background:#f4f6f7;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}details{border:1px solid var(--line);border-radius:10px;margin:11px 0;background:#fff}summary{cursor:pointer;font-size:16px;font-weight:600;padding:17px 19px;line-height:1.5}details[open]{border-color:#b9d5c7}details[open] summary{background:#f4f8f5;border-radius:10px 10px 0 0}.answer{padding:0 19px 8px;font-size:15px}
.footer{margin-top:45px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
@media(max-width:850px){.shell{grid-template-columns:1fr;gap:28px;padding:28px 22px}nav{position:static}nav .links{display:flex;flex-wrap:wrap;gap:4px}nav a{padding:4px 8px;font-size:13px}.tag{margin-bottom:10px}h1{font-size:38px}h2{margin-top:35px}}
@media print{nav{display:none}.shell{display:block;padding:0;max-width:none}body{font-size:11pt}h1{font-size:28pt}h2{page-break-after:avoid}details .answer{display:block!important}details{break-inside:avoid}a{color:#222}}
'''
nav = ''.join('<a href="#' + identity + '">' + html.escape(title) + '</a>' for identity, title in navigation)
page = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>DeepPick AI · User Guide & FAQ</title><style>' + css + '</style></head><body><div class="shell"><nav><div class="brand">DeepPick AI</div><div class="tag">1.2.3 · Offline user guide</div><div class="links">' + nav + '</div></nav><main>' + '\n'.join(parts) + '<div class="footer">Developer:Chunze Liu · 2026-10-07</div></main></div><script>window.addEventListener("beforeprint",()=>{document.querySelectorAll("details").forEach(d=>d.open=true)});</script></body></html>'
(base / 'User-Guide.html').write_text(page, 'utf-8')
assert len(navigation) == 10
assert page.count('<details>') == 24
print('Offline guide generated: 10 sections, 24 FAQ entries.')
