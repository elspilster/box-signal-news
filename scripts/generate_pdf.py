#!/usr/bin/env python3
"""Generate a printable, attributed headlines directory for each dated edition."""
import json
import pathlib
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "pdf"
OUT.mkdir(exist_ok=True)
FONT = pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
BOLD = pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
if FONT.exists() and BOLD.exists():
    pdfmetrics.registerFont(TTFont("NewsRegular", str(FONT)))
    pdfmetrics.registerFont(TTFont("NewsBold", str(BOLD)))
    regular, bold = "NewsRegular", "NewsBold"
else:
    regular, bold = "Helvetica", "Helvetica-Bold"

def para(text, style):
    return Paragraph(escape(str(text)), style)

def build(issue_path):
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
    date = issue["date"]
    destination = OUT / (date + ".pdf")
    doc = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=18*mm,
                            leftMargin=18*mm, topMargin=18*mm, bottomMargin=20*mm,
                            title="Box Signal News - " + date,
                            author="Box Signal News")
    mast = ParagraphStyle("mast", fontName=bold, fontSize=29, leading=36, alignment=TA_CENTER,
                          textColor=colors.HexColor("#192431"), spaceAfter=7)
    small = ParagraphStyle("small", fontName=regular, fontSize=8.5, leading=12,
                           textColor=colors.HexColor("#525b65"), spaceAfter=7)
    section = ParagraphStyle("section", fontName=bold, fontSize=15, leading=19,
                             textColor=colors.HexColor("#ad3929"), spaceBefore=15, spaceAfter=9)
    headline = ParagraphStyle("headline", fontName=bold, fontSize=11.2, leading=15.5,
                              textColor=colors.HexColor("#192431"), spaceAfter=4)
    link = ParagraphStyle("link", fontName=regular, fontSize=8.2, leading=12,
                          textColor=colors.HexColor("#23577b"), spaceAfter=11,
                          wordWrap="CJK")
    flow = [para("BOX SIGNAL NEWS", mast),
            para("THE DAILY EDITION  |  " + date + "  |  YOUR WINDOW ON THE WORLD", small),
            HRFlowable(width="100%", thickness=2, color=colors.HexColor("#192431")),
            Spacer(1, 9),
            para("A printable directory of headlines. Read full reports at the credited publishers using the links below. This publication does not reproduce full articles.", small)]
    groups = {}
    for item in issue.get("stories", []):
        if item.get("title") and item.get("url"):
            groups.setdefault(item.get("category", "Other"), []).append(item)
    for category in ["UK", "World", "Business", "Technology", "Science", "Entertainment", "Sport", "Other"]:
        entries = groups.get(category, [])
        if not entries:
            continue
        flow.append(para(category.upper(), section))
        for item in entries:
            url = item["url"]
            if not url.startswith(("https://", "http://")):
                continue
            # Escape user-controlled feed fields; links are clickable in the PDF.
            safe_url = escape(url, {'"': '&quot;'})
            source = escape(item.get("source", "Publisher"))
            flow.append(KeepTogether([
                para(item["title"], headline),
                Paragraph(source + '  |  <link href="' + safe_url + '">Read original report</link>', link)
            ]))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(18*mm, 12*mm, "BOX SIGNAL NEWS  •  boxsignal.uk/news/")
        canvas.drawRightString(A4[0]-18*mm, 12*mm, str(doc.page))
        canvas.restoreState()
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    print("Generated", destination)

def main():
    for issue in sorted((DATA / "issues").glob("????-??-??.json")):
        destination = OUT / (issue.stem + ".pdf")
        # Today's issue changes throughout the day; refresh it each run.
        if not destination.exists() or issue.stat().st_mtime > destination.stat().st_mtime:
            build(issue)

if __name__ == "__main__":
    main()
