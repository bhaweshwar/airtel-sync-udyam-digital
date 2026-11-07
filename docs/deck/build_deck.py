"""Build docs/deck/udyam-digital-business-case.pptx on the official submission template.

The case asks for a business case in 10 slides or fewer covering target customer, value, pricing or savings,
rollout and risks. This deck uses the template's two backgrounds (title, content) and nothing else from it.

Run in a throwaway venv outside the repo (needs python-pptx):
    python docs/deck/build_deck.py
Numbers come from data/smb_leads.csv via docs/metrics.md; targets and projections are labelled as assumptions.
Screenshots in screens/ are from the running app (light theme, phone width), with synthetic data.
"""
from __future__ import annotations

import io
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "case" / "Submission Template_Sync.pptx"
SCREENS = HERE / "screens"
OUT = HERE / "udyam-digital-business-case.pptx"

RED = RGBColor(0xC8, 0x10, 0x2E)      # the template's red, used sparingly
INK = RGBColor(0x1F, 0x1F, 0x1F)
GREY = RGBColor(0x5F, 0x63, 0x68)
MID = RGBColor(0x9A, 0xA0, 0xA6)
LINE = RGBColor(0xDA, 0xDD, 0xE1)
PANEL = RGBColor(0xF3, 0xF4, 0xF6)
TINT = RGBColor(0xFB, 0xEA, 0xEC)     # light red tint for the one highlighted item on a slide
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Arial"
SOURCE = "Source: smb_leads.csv (synthetic), 5,000 leads, Apr–Jun 2026."
LIVE_URL = "udyam-digital-779328647112.asia-south1.run.app"

# Content area on the content background: logos sit above y=0.65", the partner mark and red band below y=5.2".
X0, X1 = 0.55, 9.45
W = X1 - X0

# ------------------------------------------------------------------ template

prs = Presentation(str(TEMPLATE))
TITLE_BG, CONTENT_BG = [next(sh for sh in s.shapes if sh.shape_type == 13).image.blob for s in prs.slides]
for sld_id in list(prs.slides._sldIdLst):
    prs.part.drop_rel(sld_id.rId)
    prs.slides._sldIdLst.remove(sld_id)
BLANK = next(l for l in prs.slide_layouts if l.name == "BLANK")
SW, SH = prs.slide_width, prs.slide_height


def new_slide(bg: bytes, notes: str):
    s = prs.slides.add_slide(BLANK)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    s.shapes.add_picture(io.BytesIO(bg), 0, 0, SW, SH)
    s.notes_slide.notes_text_frame.text = notes
    return s


# ------------------------------------------------------------------ helpers

def text(s, x, y, w, h, paras, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space=0, line_spacing=None):
    """paras: a string, or a list whose items are strings or lists of (text, style) runs."""
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, p in enumerate([paras] if isinstance(paras, str) else paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        if space and i:
            para.space_before = Pt(space)
        if line_spacing:
            para.line_spacing = line_spacing
        for t, st in (p if isinstance(p, list) else [(p, {})]):
            r = para.add_run()
            r.text = t
            f = r.font
            f.name = FONT
            f.size = Pt(st.get("size", size))
            f.bold = st.get("bold", bold)
            f.color.rgb = st.get("color", color)
    return box


def box(s, x, y, w, h, fill=PANEL, line=None, radius=0.06, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    shp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = radius
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    return shp


def hline(s, x, y, w, color=LINE):
    return box(s, x, y, w, 0.012, fill=color, shape=MSO_SHAPE.RECTANGLE)


def vline(s, x, y, h, color=LINE):
    return box(s, x, y, 0.014, h, fill=color, shape=MSO_SHAPE.RECTANGLE)


def screen(s, name, x, y, h=None, w=None, radius=8000):
    """A screenshot in a rounded frame with a hairline border (the deck's one repeated motif)."""
    pic = s.shapes.add_picture(str(SCREENS / f"{name}.jpg"), Inches(x), Inches(y),
                               height=Inches(h) if h else None, width=Inches(w) if w else None)
    pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
    geom = pic._element.spPr.find(qn("a:prstGeom"))
    av = geom.find(qn("a:avLst"))
    if av is None:
        av = etree.SubElement(geom, qn("a:avLst"))
    gd = etree.SubElement(av, qn("a:gd"))
    gd.set("name", "adj")
    gd.set("fmla", f"val {radius}")
    pic.line.color.rgb = LINE
    pic.line.width = Pt(0.75)
    return pic


def dot(s, x, y, d, fill, label="", size=11, color=WHITE):
    c = box(s, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    if label:
        tf = c.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), True, color
    return c


def title(s, t, sub):
    text(s, X0, 0.7, W, 0.5, t, size=26, bold=True)
    text(s, X0, 1.2, W, 0.3, sub, size=13, color=GREY)


def footer(s, t=SOURCE):
    text(s, X0, 5.22, 7.3, 0.25, t, size=9, color=GREY)


def style_bar_chart(chart, colors, number_format):
    chart.has_legend = False
    chart.font.name = FONT
    chart.font.size = Pt(11)
    chart.font.color.rgb = GREY
    plot = chart.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = number_format
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(11)
    dl.font.bold = True
    dl.font.color.rgb = INK
    for pt, c in zip(plot.series[0].points, colors):
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = c
    cat = chart.category_axis
    cat.reverse_order = True
    cat.has_major_gridlines = False
    cat.format.line.color.rgb = LINE
    cat.tick_labels.font.size = Pt(11)
    cat.tick_labels.font.color.rgb = INK
    val = chart.value_axis
    val.visible = False
    val.has_major_gridlines = False


# ------------------------------------------------------------------ 1. title

s = new_slide(TITLE_BG, "Udyam Digital: a phone-first journey that takes a small business from first question to a "
                        "live connection in one sitting. The prototype is live at the URL on the slide.")
text(s, 0.65, 2.85, 4.2, 0.6, "Udyam Digital", size=36, bold=True, color=WHITE)
text(s, 0.65, 3.5, 4.0, 0.7, "From first question to a live connection in one sitting, on a phone, in Hindi or English",
     size=14, color=RGBColor(0xE8, 0xE8, 0xE8), line_spacing=1.1)
text(s, 0.65, 4.3, 4.3, 0.8, [
    "Business case · Enterprise Track A · Accel Business",
    "Live prototype:",
    [(LIVE_URL, {"color": WHITE})],
], size=10.5, color=RGBColor(0xBD, 0xC1, 0xC6), space=3)

# ------------------------------------------------------------------ 2. problem

s = new_slide(CONTENT_BG, "Only 7.4% of leads activate, it takes 17.6 days, and each activation costs about ₹15,000. "
                          "The steepest drop is from needs assessed to quote accepted.")
title(s, "Only 368 of 5,000 leads became customers",
      "The steepest drop is between needs assessed and quote accepted: only 44% go on")
data = CategoryChartData()
data.categories = ["Leads", "Contacted", "Needs assessed", "Quote accepted", "KYC complete", "Activated"]
data.add_series("Leads", (5000, 3406, 1974, 861, 588, 368))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(X0), Inches(1.7), Inches(5.2), Inches(3.4), data)
style_bar_chart(gf.chart, [MID, MID, MID, INK, MID, RED], '#,##0')
gf.chart.has_title = False

stats = [("7.4%", "of leads activate"), ("17.6", "days from lead to live"),
         ("₹15,053", "acquisition cost per activation"), ("3.0", "status calls per customer")]
for i, (big, label) in enumerate(stats):
    cx, cy = 6.05 + (i % 2) * 1.75, 1.75 + (i // 2) * 1.7
    box(s, cx, cy, 1.6, 1.5)
    text(s, cx + 0.15, cy + 0.2, 1.35, 0.5, big, size=22, bold=True, color=RED if i == 0 else INK)
    text(s, cx + 0.15, cy + 0.75, 1.35, 0.6, label, size=11, color=GREY)
footer(s)

# ------------------------------------------------------------------ 3. target customer

s = new_slide(CONTENT_BG, "Professional offices first: highest value per effort and already digital. Micro retail is "
                          "the volume play, reached cheaply through links and partners.")
title(s, "Offices first, micro retail for volume",
      "Four segments in the lead data, each with its own starting bundle and sales route")
segments = [
    ("Professional offices", "25% of leads", "11.1%", "₹6,575", "14%", "Digital first", True),
    ("Micro retail", "54% of leads", "4.1%", "₹2,470", "23%", "Links + partners", False),
    ("Multi-site", "15% of leads", "11.0%", "₹28,080", "11%", "Field visit", False),
    ("Manufacturers", "6% of leads", "12.8%", "₹15,910", "8%", "Field visit", False),
]
cw, gap = 2.08, 0.19
for i, (name, share, act, bundle, churn, route, lead) in enumerate(segments):
    x = X0 + i * (cw + gap)
    box(s, x, 1.72, cw, 2.95, fill=TINT if lead else PANEL)
    text(s, x + 0.18, 1.86, cw - 0.3, 0.25, "Start here" if lead else " ", size=10, bold=True, color=RED)
    text(s, x + 0.18, 2.08, cw - 0.3, 0.5, name, size=14, bold=True, anchor=MSO_ANCHOR.BOTTOM)
    text(s, x + 0.18, 2.6, cw - 0.3, 0.25, share, size=11, color=GREY)
    text(s, x + 0.18, 2.9, cw - 0.3, 0.45, act, size=26, bold=True)
    text(s, x + 0.18, 3.33, cw - 0.3, 0.25, "activate", size=11, color=GREY)
    text(s, x + 0.18, 3.65, cw - 0.3, 0.55, [[(bundle, {"bold": True, "color": INK}), (" bundle a month", {})],
                                             [(churn, {"bold": True, "color": INK}), (" churn in 6 months", {})]],
         size=11, color=GREY, space=3)
    text(s, x + 0.18, 4.22, cw - 0.3, 0.4, route, size=11, bold=True)
text(s, X0, 4.82, W, 0.3, [[("GSTIN holders activate at 9.6%, others at 2.0%, ", {"bold": True}),
                           ("so the journey checks GSTIN early.", {})]], size=12)
footer(s)

# ------------------------------------------------------------------ 4. the journey

s = new_slide(CONTENT_BG, "Walk the four screens. Each one removes a reason owners drop out today. These are real "
                          "screenshots of the live prototype.")
title(s, "One sitting on a phone: ask, quote, verify, track",
      "Each step removes a reason owners drop out today")
steps = [
    ("advisor", "1", "Ask", "Chat or speak, English or Hindi. Asks only what's missing.", "No time for a visit (531)"),
    ("quote", "2", "Quote", "One monthly price with GST, a reason per item, add-ons on or off.", "Quote too complex or slow (385)"),
    ("kyc", "3", "Smart KYC", "Four photos checked in seconds, with a hint for each retake.", "Paperwork and documents (273)"),
    ("track", "4", "Track", "Order ID + PIN, self-booked install slot, ETA per item.", "3 status calls per customer"),
]
for i, (img, n, name, what, fixes) in enumerate(steps):
    x = X0 + i * (cw + gap)
    dot(s, x, 1.7, 0.3, INK, n)
    text(s, x + 0.4, 1.7, cw - 0.4, 0.3, name, size=14, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    screen(s, img, x, 2.12, h=1.95)
    text(s, x, 4.15, cw, 0.6, what, size=10.5, color=GREY)
    text(s, x, 4.72, cw, 0.4, [[("Fixes: ", {"bold": True, "color": RED}), (fixes, {})]], size=10.5)
footer(s, "Drop counts from smb_leads.csv (synthetic). Screens from the live prototype with sample data.")

# ------------------------------------------------------------------ 5. rules decide, the LLM talks

s = new_slide(CONTENT_BG, "The LLM never decides eligibility or price. The rules engine does, from the catalogue. "
                          "If both LLMs fail, the owner still gets a quote from rules-only mode.")
title(s, "Rules set every price; the LLM only talks",
      "So an AI mistake can never put a wrong product or price in front of an owner")
flow = [
    ("Owner", "speaks or types about the business, in Hindi or English", PANEL, INK),
    ("LLM listens", "pulls out profile fields; sees the business description only", PANEL, INK),
    ("Rules decide", "eligibility (tier, size, GSTIN, dependencies) and price, from the catalogue", INK, WHITE),
    ("LLM explains", "puts the engine's quote in plain words; can't add a product or change a price", PANEL, INK),
]
fw, fg = 1.98, 0.32
for i, (head, body, fill, fg_col) in enumerate(flow):
    x = X0 + i * (fw + fg)
    box(s, x, 1.75, fw, 1.45, fill=fill)
    text(s, x + 0.16, 1.9, fw - 0.3, 0.3, head, size=13, bold=True, color=fg_col)
    text(s, x + 0.16, 2.25, fw - 0.3, 0.9, body, size=10.5,
         color=RGBColor(0xD0, 0xD3, 0xD7) if fill == INK else GREY)
    if i < len(flow) - 1:
        arrow = box(s, x + fw + 0.07, 2.37, 0.18, 0.2, fill=MID, shape=MSO_SHAPE.RIGHT_ARROW)
points = [
    ("Never stuck", "Groq, then Gemini, then rules-only mode. If both LLMs time out, the owner still gets a quote."),
    ("Private by design", "The LLM never receives IDs, phone numbers, documents or photos."),
    ("A person when needed", "One tap hands the chat to the back office, with the conversation so far."),
]
pw = (W - 2 * 0.3) / 3
for i, (head, body) in enumerate(points):
    x = X0 + i * (pw + 0.3)
    hline(s, x, 3.55, pw)
    text(s, x, 3.7, pw, 0.3, head, size=13, bold=True)
    text(s, x, 4.02, pw, 0.9, body, size=11, color=GREY)
footer(s, "Advisor scenarios run against rules-only mode in tests; unit tests never call a real LLM.")

# ------------------------------------------------------------------ 6. smart KYC

s = new_slide(CONTENT_BG, "KYC goes from days of paper to seconds, and stays DPDP-compliant: consent per purpose, "
                          "no stored photos, masked identifiers.")
title(s, "KYC in seconds, built for the DPDP Act",
      "Four photos in, a clear verdict out, and a precise hint when one photo needs a retake")
screen(s, "kyc", X0, 1.72, h=3.35)
kx = 2.75
kyc_steps = [
    ("Consent", "Per purpose, versioned, in English or Hindi. Withdrawing deletes the KYC data."),
    ("Four photos, read in memory", "GST and Udyam certificates, signatory ID, a recent bill. Never stored."),
    ("Cross-checked", "GSTIN checksum and registry status, Udyam match, names, bill within 90 days."),
    ("A verdict", "Verified, action required (retake one photo), manual review, or rejected."),
]
for i, (head, body) in enumerate(kyc_steps):
    y = 1.75 + i * 0.66
    dot(s, kx, y, 0.3, INK, str(i + 1))
    text(s, kx + 0.45, y - 0.01, 6.2, 0.3, head, size=13, bold=True)
    text(s, kx + 0.45, y + 0.26, 6.2, 0.35, body, size=11, color=GREY)
facts = [("No Aadhaar", "never collected"), ("No images kept", "masked fields only"),
         ("180 days", "retention after go-live")]
fw2 = (X1 - kx - 2 * 0.2) / 3
for i, (big, small) in enumerate(facts):
    x = kx + i * (fw2 + 0.2)
    box(s, x, 4.45, fw2, 0.65)
    text(s, x + 0.14, 4.53, fw2 - 0.25, 0.25, big, size=12, bold=True)
    text(s, x + 0.14, 4.78, fw2 - 0.25, 0.25, small, size=10, color=GREY)
footer(s, "Sample applicants K01–K12 are the case pack's synthetic documents; all 12 verdicts match in our tests.")

# ------------------------------------------------------------------ 7. channels

s = new_slide(CONTENT_BG, "The digital journey routes work to people where people add the most: field reps to "
                          "high-value sites, partners to tier-2 and Hindi-first owners, links to the unreachable.")
title(s, "Field reps and partners get the leads worth a visit",
      "Every lead the advisor didn't close gets a score and a suggested channel")
screen(s, "backoffice", X0, 1.72, w=5.0, radius=3000)
text(s, X0, 4.75, 5.0, 0.35, "Back office: dropped leads ranked by score, with the reasons",
     size=10.5, color=GREY)
routes = [
    ("Field visit", "Multi-site and manufacturers: 11.0% and 12.8% activation, ₹28,080 and ₹15,910 bundles."),
    ("Local partner", "Tier-2 cities, Hindi-first and micro owners. Same app in assisted mode, commission per sale."),
    ("Advisor link", "1,124 unreachable or wrong-number leads get an SMS or WhatsApp link and start alone."),
]
rx = 5.85
for i, (head, body) in enumerate(routes):
    y = 1.75 + i * 1.02
    if i:
        hline(s, rx, y - 0.13, X1 - rx)
    text(s, rx, y, X1 - rx, 0.3, head, size=13, bold=True)
    text(s, rx, y + 0.3, X1 - rx, 0.65, body, size=11, color=GREY)
text(s, rx, 4.75, X1 - rx, 0.35, [[("Lead score: ", {"bold": True, "color": INK}),
                                   ("AUC 0.73 on unseen June leads; the top 10% activate 2.1× as often.", {})]],
     size=10.5, color=GREY)
footer(s)

# ------------------------------------------------------------------ 8. value

s = new_slide(CONTENT_BG, "Five metrics. Every target is an assumption the pilot has to prove, measured per cohort "
                          "against matched non-pilot cities.")
title(s, "Five numbers the pilot has to move",
      "Baselines are from the lead data; targets are assumptions for the pilot to prove")
rows = [
    ("Lead → activation", "7.4%", "12%", "Advisor, instant quote, self-serve link"),
    ("Time to activate", "17.6 days", "≤ 7 days", "Quote and KYC in one sitting, self-booked slot"),
    ("Cost per activation", "₹15,053", "≤ ₹8,000", "Fewer visits, each one where value is highest"),
    ("Status calls per customer", "3.0", "≤ 0.5", "Tracker with ETAs, no need to call"),
    ("6-month churn", "~15%", "≤ 10%", "Only bundles the business is eligible for"),
]
text(s, 3.45, 1.68, 1.6, 0.25, "Today", size=10, bold=True, color=GREY)
text(s, 5.35, 1.68, 1.6, 0.25, "Pilot target", size=10, bold=True, color=RED)
text(s, 7.15, 1.68, 2.3, 0.25, "What moves it", size=10, bold=True, color=GREY)
for i, (metric, base, target, lever) in enumerate(rows):
    y = 1.98 + i * 0.63
    hline(s, X0, y, W)
    text(s, X0, y + 0.1, 2.8, 0.45, metric, size=13, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 3.45, y + 0.1, 1.6, 0.45, base, size=18, color=GREY, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 5.35, y + 0.1, 1.7, 0.45, target, size=18, bold=True, color=RED, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 7.15, y + 0.1, 2.3, 0.45, lever, size=10.5, color=GREY, anchor=MSO_ANCHOR.MIDDLE)
hline(s, X0, 1.98 + 5 * 0.63, W)
footer(s, SOURCE + " Targets are proposed, not measured.")

# ------------------------------------------------------------------ 9. pricing and savings

s = new_slide(CONTENT_BG, "Digital sources already cost a fraction per activation. The plan shifts volume to them "
                          "and keeps field visits for high-value sites.")
title(s, "Digital sources already win on cost per customer",
      "Lead cost per activation by source, and what the targets would be worth")
data = CategoryChartData()
data.categories = ["WhatsApp campaign", "Referral", "Inbound call", "Website form", "Channel partner", "Field sales"]
data.add_series("Cost", (4000, 4100, 5100, 6400, 20900, 24200))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(X0), Inches(1.7), Inches(5.0), Inches(3.3), data)
style_bar_chart(gf.chart, [INK, INK, INK, INK, MID, MID], '"₹"#,##0')
gf.chart.has_title = False
rx = 5.95
callouts = [
    ("~600", "activations a quarter from the same 5,000 leads, instead of 368 (at 12%)"),
    ("~₹7,000", "saved per activation if cost falls from ₹15,053 to ₹8,000"),
]
for i, (big, label) in enumerate(callouts):
    y = 1.72 + i * 1.08
    text(s, rx, y, X1 - rx, 0.45, big, size=26, bold=True, color=RED)
    text(s, rx, y + 0.48, X1 - rx, 0.5, label, size=11, color=GREY)
text(s, rx, 3.95, X1 - rx, 0.25, "Months of revenue to recover the cost", size=11, bold=True)
for i, (seg, now, then) in enumerate([("Professional offices", "2.3", "1.2"), ("Micro retail", "6.1", "3.2")]):
    y = 4.3 + i * 0.36
    text(s, rx, y, 1.9, 0.3, seg, size=11)
    text(s, rx + 1.95, y, 0.6, 0.3, now, size=11, color=GREY, align=PP_ALIGN.RIGHT)
    text(s, rx + 2.6, y, 0.15, 0.3, "→", size=11, color=GREY)
    text(s, rx + 2.8, y, 0.6, 0.3, then, size=11, bold=True, align=PP_ALIGN.RIGHT)
footer(s, "Cost per lead ÷ activation rate (lead cost only; blended full cost is ₹15,053). Revenue, not margin. "
          "Projections are assumptions.")

# ------------------------------------------------------------------ 10. rollout and risks

s = new_slide(CONTENT_BG, "An 8-week pilot in 4 cities with a go/no-go on the five metrics. The main risks and how "
                          "the design already handles each.")
title(s, "An 8-week pilot, with the risks designed in",
      "Delhi and Mumbai (tier 1), Indore and Lucknow (tier 2, Hindi-first)")
phases = [
    ("Weeks 1–2 · Set up", "Connect the catalogue and registries. Train partners on assisted mode."),
    ("Weeks 3–6 · Run", "Offices go digital first; micro retail via links and partners; field takes multi-site."),
    ("Weeks 7–8 · Read out", "Compare with matched cities on the five numbers. Go or no-go."),
]
vline(s, X0 + 0.11, 1.9, 2.7)
for i, (head, body) in enumerate(phases):
    y = 1.75 + i * 1.08
    dot(s, X0, y, 0.22, RED if i == 1 else INK)
    text(s, X0 + 0.4, y - 0.04, 3.2, 0.3, head, size=13, bold=True)
    text(s, X0 + 0.4, y + 0.28, 3.2, 0.7, body, size=11, color=GREY)
risks = [
    ("LLM gives a wrong answer", "Rules set products and prices; rules-only fallback; human handoff"),
    ("OCR misreads a document", "Quality checks, one-photo retake hints, manual review queue"),
    ("Field and partners push back", "They get the high-value leads, plus commission on assisted sales"),
    ("Personal data exposure", "Consent per purpose, no stored images, masking, encrypted phone"),
    ("Installs miss the date", "Slots only from real capacity; delays shown, not hidden"),
]
tx = 4.45
text(s, tx, 1.68, 2.0, 0.25, "Risk", size=10, bold=True, color=GREY)
text(s, tx + 2.15, 1.68, 2.8, 0.25, "How the design handles it", size=10, bold=True, color=GREY)
for i, (risk, fix) in enumerate(risks):
    y = 1.98 + i * 0.62
    hline(s, tx, y, X1 - tx)
    text(s, tx, y + 0.08, 2.0, 0.5, risk, size=11, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, tx + 2.15, y + 0.08, X1 - tx - 2.15, 0.5, fix, size=10.5, color=GREY, anchor=MSO_ANCHOR.MIDDLE)
hline(s, tx, 1.98 + 5 * 0.62, X1 - tx)
footer(s, "Pilot cities are a proposal. Lead volumes per city are in smb_leads.csv (synthetic).")

prs.save(str(OUT))
print("wrote", OUT, len(prs.slides._sldIdLst), "slides")
