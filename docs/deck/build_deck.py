"""Build docs/deck/udyam-digital-business-case.pptx on the official template backgrounds.

Run in a throwaway venv outside the repo (needs python-pptx):
    python docs/deck/build_deck.py
All numbers come from data/smb_leads.csv via docs/metrics.md; projections are labelled as assumptions.
"""
from __future__ import annotations

import io
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "case" / "Submission Template_Sync.pptx"
OUT = HERE / "udyam-digital-business-case.pptx"

RED = RGBColor(0xC8, 0x10, 0x2E)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x5F, 0x63, 0x68)
LIGHT = RGBColor(0xF4, 0xF5, 0xF7)
PINK = RGBColor(0xFD, 0xEC, 0xEE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x1E, 0x7B, 0x4F)
FONT = "Arial"
SOURCE = "Source: smb_leads.csv (synthetic), 5,000 leads, Apr–Jun 2026."

# --- template ---------------------------------------------------------------
prs = Presentation(str(TEMPLATE))
backgrounds = []
for s in prs.slides:
    pic = next(sh for sh in s.shapes if sh.shape_type == 13)
    backgrounds.append(pic.image.blob)
TITLE_BG, CONTENT_BG = backgrounds
sld_ids = prs.slides._sldIdLst
for sld_id in list(sld_ids):
    prs.part.drop_rel(sld_id.rId)
    sld_ids.remove(sld_id)
BLANK = next(l for l in prs.slide_layouts if l.name == "BLANK")
SW, SH = prs.slide_width, prs.slide_height


def new_slide(bg: bytes, notes: str = ""):
    s = prs.slides.add_slide(BLANK)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    s.shapes.add_picture(io.BytesIO(bg), 0, 0, SW, SH)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def text(s, x, y, w, h, paras, size=12, color=DARK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, fill=None, line=None, margin=0.05, spacing=None):
    """paras: str or list of str / list of runs [(text, {bold,color,size})]."""
    if fill is not None or line is not None:
        shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        shp.adjustments[0] = 0.08
        if fill is None:
            shp.fill.background()
        else:
            shp.fill.solid()
            shp.fill.fore_color.rgb = fill
        if line is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = line
            shp.line.width = Pt(1)
        shp.shadow.inherit = False
    else:
        shp = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(margin))
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        if spacing:
            para.space_after = Pt(spacing)
        runs = p if isinstance(p, list) else [(p, {})]
        for t, st in runs:
            r = para.add_run()
            r.text = t
            f = r.font
            f.name = FONT
            f.size = Pt(st.get("size", size))
            f.bold = st.get("bold", bold)
            f.color.rgb = st.get("color", color)
    return shp


def rect(s, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE, dash=False):
    shp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1.25)
        if dash:
            from pptx.enum.dml import MSO_LINE
            shp.line.dash_style = MSO_LINE.DASH
    shp.shadow.inherit = False
    return shp


def title(s, t, sub=None):
    text(s, 0.55, 0.62, 8.9, 0.45, t, size=22, bold=True)
    rect(s, 0.6, 1.08, 0.6, 0.04, RED)
    if sub:
        text(s, 1.3, 0.98, 8.1, 0.25, sub, size=11, color=GREY)


def footer(s, t=SOURCE):
    text(s, 0.55, 5.2, 7.4, 0.25, t, size=8, color=GREY)


def table(s, x, y, w, rows, col_w, size=10, row_h=0.3, header_fill=DARK, highlight=None):
    shp = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shp.table
    tbl.first_row = True
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.06)
            c.margin_top = c.margin_bottom = Inches(0.02)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = header_fill
            elif highlight is not None and i == highlight:
                c.fill.fore_color.rgb = PINK
            else:
                c.fill.fore_color.rgb = WHITE if i % 2 else LIGHT
            tf = c.text_frame
            tf.word_wrap = True
            tf.paragraphs[0].text = ""
            r = tf.paragraphs[0].add_run()
            r.text = str(val)
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = i == 0 or (j == 0)
            r.font.color.rgb = WHITE if i == 0 else DARK
            tf.paragraphs[0].alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
    return tbl


def placeholder(s, x, y, w, h, label):
    shp = rect(s, x, y, w, h, LIGHT, GREY, MSO_SHAPE.ROUNDED_RECTANGLE, dash=True)
    shp.adjustments[0] = 0.08
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = f"[SCREENSHOT]\n{label}"
    r.font.name = FONT
    r.font.size = Pt(9)
    r.font.bold = True
    r.font.color.rgb = GREY
    shp.name = f"SCREENSHOT PLACEHOLDER: {label}"
    return shp


def arrow(s, x, y, w=0.25, h=0.22, color=RED):
    rect(s, x, y, w, h, color, shape=MSO_SHAPE.RIGHT_ARROW)


B = lambda t: (t, {"bold": True})            # noqa: E731
R = lambda t: (t, {"bold": True, "color": RED})  # noqa: E731

# --- 1. Title -----------------------------------------------------------------
s = new_slide(TITLE_BG, "Udyam Digital: a phone-first journey for Accel Business small-business customers.")
text(s, 0.6, 2.75, 3.9, 0.6, "Udyam Digital", size=34, bold=True, color=WHITE)
text(s, 0.6, 3.38, 3.9, 0.7, "From a question to a live connection in one sitting, on a phone, in Hindi or English",
     size=14, color=WHITE)
text(s, 0.6, 4.2, 3.9, 0.5, ["Accel Business · small-business acquisition and onboarding",
                             "YTL Hackathon 2026 · Enterprise Track A · all data synthetic"],
     size=10, color=RGBColor(0xDD, 0xDD, 0xDD))

# --- 2. Problem ---------------------------------------------------------------
s = new_slide(CONTENT_BG, "Only 7.4% of leads activate. The steepest drop is needs assessed to quote accepted (44%).")
title(s, "The problem, in the data", "Only 368 of 5,000 leads activated in a quarter")
funnel = [("Leads", 5000, ""), ("Contacted", 3406, "68%"), ("Needs assessed", 1974, "58%"),
          ("Quote accepted", 861, "44%"), ("KYC complete", 588, "68%"), ("Activated", 368, "63%")]
bx, by, bw = 1.85, 1.38, 3.0
for i, (name, n, pct) in enumerate(funnel):
    yy = by + i * 0.43
    text(s, 0.55, yy, 1.3, 0.34, name, size=10, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    w = max(bw * n / 5000, 0.08)
    rect(s, bx, yy + 0.03, w, 0.28, RED if name in ("Quote accepted", "Activated") else GREY)
    text(s, bx + w + 0.05, yy, 1.2, 0.34, [[B(f"{n:,}"), (f"  {pct}" if pct else "", {"color": GREY, "size": 9})]],
         size=10, anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.55, 4.0, 4.6, 0.3, "% = conversion from the previous stage. Steepest drop: needs assessed → quote.",
     size=9, color=GREY)
kpis = [("7.4%", "lead → activation"), ("17.6 days", "lead → activation"),
        ("₹15,053", "acquisition cost per activation"), ("3.0", "status calls per customer")]
for i, (big, small) in enumerate(kpis):
    xx, yy = 5.55 + (i % 2) * 1.95, 1.38 + (i // 2) * 0.95
    text(s, xx, yy, 1.85, 0.85, [[(big, {"size": 20, "bold": True, "color": RED})], small], size=9,
         fill=LIGHT, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
text(s, 5.55, 3.33, 3.8, 0.6, [[B("GSTIN leads activate at "), R("9.6%"), B(" vs "), R("2.0%"), B(" without")],
                               "so the journey checks GSTIN early and helps owners without one"],
     size=10, fill=LIGHT, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
text(s, 0.55, 4.35, 8.85, 0.75,
     [[R("≈ 1,583 drops are journey-fixable: "),
       ("owner had no time for a visit 531 · visit not scheduled 296 · quote too complex 206 · quote took too long 179 · "
        "install delayed > 21 days 98 · missing GST/Udyam 94 · paperwork too long 79 · signatory 53 · details mismatch 47", {})],
      [R("+ 1,124 unreachable "), ("(805 after 3 attempts, 319 wrong number) ", {}),
       B("that a self-serve link can reach.")]],
     size=10, fill=PINK, anchor=MSO_ANCHOR.MIDDLE, margin=0.1)
footer(s)

# --- 3. Segments --------------------------------------------------------------
s = new_slide(CONTENT_BG, "Lead with professional offices; micro retail is the volume play.")
title(s, "Target segments and their bundles", "Lead with professional offices; win micro retail on volume")
rows = [["Segment", "Share of leads", "Activation", "Median bundle / month", "6-mo churn", "Starter bundle (from the catalogue)", "Route"],
        ["Professional offices", "25%", "11.1%", "₹6,575", "14%",
         "Biz Fibre 300 + failover, postpaid 599, cloud email, backup, endpoint security", "Digital first"],
        ["Micro retail", "54%", "4.1%", "₹2,470", "23%",
         "Biz Fibre 100 or 5G AirFiber, postpaid 299, Cloud POS, secure Wi-Fi, WhatsApp", "Self-serve + partners"],
        ["Multi-site", "15%", "11.0%", "₹28,080", "11%",
         "Fibre per site, managed SD-WAN, failover, managed firewall, cloud CCTV", "Field-assisted"],
        ["Manufacturers", "6%", "12.8%", "₹15,910", "8%",
         "Internet leased line, static IP, managed firewall, machine-monitoring IoT", "Field-assisted"]]
table(s, 0.55, 1.35, 8.9, rows, [1.35, 0.75, 0.75, 0.95, 0.7, 3.15, 1.25], size=9, row_h=0.5, highlight=1)
text(s, 0.55, 4.05, 4.35, 1.05,
     [[R("Why professional offices first")],
      "Highest value per effort: 11.1% activation at ₹6,575 a month, medium price sensitivity, and already used "
      "to digital tools (clinics, CA firms, coaching centres)."], size=10, fill=LIGHT, margin=0.1)
text(s, 5.05, 4.05, 4.4, 1.05,
     [[R("Micro retail is the volume play")],
      "54% of leads, but 4.1% activation and 23% churn. Reach them at low cost through self-serve links and "
      "partners, not field visits."], size=10, fill=LIGHT, margin=0.1)
footer(s, SOURCE + " Bundles are the engine's starting point; the advisor adjusts them to each business.")

# --- 4. Journey ---------------------------------------------------------------
s = new_slide(CONTENT_BG, "Walk the five screens. Screenshots get added during integration.")
title(s, "The journey: one sitting, on a phone", "Each step removes a reason owners drop out today")
steps = [("1  Ask", "Advisor chat or voice, EN/HI. Asks only what's missing.", "no time for a visit · visit not scheduled"),
         ("2  Quote", "One monthly price with GST, reasons per item, add-on toggles.", "quote too complex · took too long"),
         ("3  Smart KYC", "Per-purpose consent, photo checks, GSTIN/Udyam lookup, retake hints.", "paperwork · missing / mismatched documents"),
         ("4  Track", "Order ID + PIN, self-booked install slot, ETA per item.", "status calls · install delays"),
         ("5  Back office", "Leads the advisor couldn't close, scored and routed.", "unreachable · wrong number")]
cw = 1.7
for i, (name, what, fixes) in enumerate(steps):
    xx = 0.55 + i * (cw + 0.1)
    text(s, xx, 1.3, cw, 0.3, name, size=12, bold=True, color=RED)
    placeholder(s, xx + 0.2, 1.62, cw - 0.4, 2.05, ["Advisor: Hindi voice, dental clinic", "Quote with CCTV toggled on",
                                                    "KYC: K11 retake, K03 verified", "Tracker: slot booked → live",
                                                    "Back office: ranked leads"][i])
    text(s, xx, 3.72, cw, 0.62, what, size=9)
    text(s, xx, 4.38, cw, 0.7, [[("Fixes: ", {"bold": True, "color": RED}), (fixes, {})]], size=9, fill=PINK, margin=0.07)
footer(s, "Screenshots are placeholders until integration. Drop reasons are from smb_leads.csv (synthetic).")

# --- 5. Advisor safety --------------------------------------------------------
s = new_slide(CONTENT_BG, "The LLM never decides eligibility or price. The rules engine does.")
title(s, "How the advisor stays safe: rules decide, the LLM talks")
flow = [("Owner", "speaks or types about the business, in Hindi or English"),
        ("LLM", "pulls out profile fields and writes the reply. It sees the business description only"),
        ("Rules engine", "checks eligibility (city tier, size, GSTIN, dependencies) and sets the price from the catalogue"),
        ("LLM", "explains the engine's quote in plain words. It can't add a product or change a price")]
fw = 2.05
for i, (who, what) in enumerate(flow):
    xx = 0.55 + i * (fw + 0.23)
    fill = PINK if who == "Rules engine" else LIGHT
    text(s, xx, 1.35, fw, 1.25, [[(who, {"bold": True, "size": 12, "color": RED})], what], size=10,
         fill=fill, margin=0.1, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if i < 3:
        arrow(s, xx + fw + 0.0, 1.87, 0.22, 0.2)
guards = [[B("Deterministic core. "), ("Products, eligibility, dependencies and prices come from the catalogue rules; "
                                         "ineligible items are shown with the reason (tier, size, GSTIN, dependency).", {})],
          [B("Fallback chain. "), ("Groq → Gemini → rules-only mode. If both LLMs time out, the owner still gets a "
                                    "quote, and the screen shows which mode answered.", {})],
          [B("Privacy by design. "), ("The LLM never receives IDs, phone numbers, documents or images.", {})],
          [B("Human handoff. "), ("If the owner asks for a person, or the advisor can't help, it hands off to the back "
                                   "office with the conversation so far.", {})],
          [B("Tested offline. "), ("Scripted advisor scenarios run against the rules mode, and unit tests never call a "
                                    "real LLM.", {})]]
text(s, 0.55, 2.8, 8.9, 2.3, guards, size=10.5, spacing=5)

# --- 6. Smart KYC + DPDP ------------------------------------------------------
s = new_slide(CONTENT_BG, "KYC goes from days of paper to seconds, and stays DPDP-compliant.")
title(s, "Smart KYC, built for the DPDP Act", "Near-instant checks, with consent and data minimisation")
kyc = [("Consent", "per purpose, versioned, EN/HI"),
       ("4 photos", "GST cert, Udyam cert, signatory ID, address proof"),
       ("Read in memory", "RapidOCR, blur and skew checks, never stored"),
       ("Cross-check", "GSTIN checksum + registry status, Udyam match, names, bill ≤ 90 days"),
       ("Verdict", "verified · action required (retake one photo) · manual review · rejected")]
for i, (h, d) in enumerate(kyc):
    yy = 1.35 + i * 0.72
    text(s, 0.55, yy, 4.2, 0.62, [[(h, {"bold": True, "color": RED, "size": 11})], d], size=9.5,
         fill=LIGHT, margin=0.08, anchor=MSO_ANCHOR.MIDDLE)
dpdp = [[R("DPDP choices")],
        [B("Consent per purpose: "), ("required KYC check plus an optional purpose; withdrawing consent deletes the KYC data", {})],
        [B("Minimisation: "), ("each step asks only what it needs; Aadhaar is never collected", {})],
        [B("No document storage: "), ("photos are read in memory, and only checks and masked fields are kept", {})],
        [B("Retention: "), ("180 days after activation, 30 days if rejected", {})],
        [B("Masking: "), ("GSTIN, Udyam, ID and phone are masked in the UI and logs; phone is encrypted at rest", {})],
        [B("Production adds: "), ("DigiLocker pull, Aadhaar e-sign, audit log, role-based access", {})]]
text(s, 5.0, 1.35, 4.45, 2.85, dpdp, size=9.5, fill=PINK, margin=0.12, spacing=3)
text(s, 5.0, 4.3, 4.45, 0.8,
     [[B("Targets today's drops: "), ("missing GST/Udyam 94, paperwork too long 79, signatory not available 53, "
                                      "details did not match 47", {})]], size=9.5, margin=0.05)
footer(s, "Sample applicants K01–K12 are synthetic specimen documents from the case pack.")

# --- 7. Field force and partners ----------------------------------------------
s = new_slide(CONTENT_BG, "The digital journey routes work to people where people add the most.")
title(s, "Field force and partners: digital adds, not replaces",
      "Every lead gets a propensity score and a suggested channel")
cards = [("FIELD", "Multi-site, manufacturers, and bundles ≥ ₹10k a month",
          "Reps spend visits where the value is: 11.0% and 12.8% activation, ₹28,080 and ₹15,910 median bundles."),
         ("PARTNER", "Tier-2 cities, regional-language owners, micro businesses",
          "Local partners run the same app in assisted mode and earn a commission on each assisted sale."),
         ("SELF_SERVE_LINK", "Unreachable or wrong-number leads",
          "An SMS or WhatsApp link lets 1,124 hard-to-reach leads start alone, at any hour.")]
for i, (ch, who, why) in enumerate(cards):
    xx = 0.55 + i * 3.0
    text(s, xx, 1.38, 2.85, 1.85, [[(ch, {"bold": True, "size": 13, "color": RED})], [B(who)], why], size=9.5,
         fill=LIGHT, margin=0.12, spacing=4)
rows = [["Lead source", "Activation", "Cost per lead"],
        ["Referral", "14.8%", "₹605"], ["Inbound call", "9.5%", "₹487"], ["Channel partner", "8.0%", "₹1,672"],
        ["Field sales", "7.3%", "₹1,769"], ["Website form", "4.3%", "₹274"], ["WhatsApp campaign", "2.8%", "₹112"]]
table(s, 0.55, 3.35, 4.3, rows, [1.9, 1.2, 1.2], size=9, row_h=0.25)
text(s, 5.05, 3.35, 4.4, 1.75,
     [[R("How it works")],
      "The back office ranks open leads with a lead score (HOT/WARM/COLD) and its top two factors.",
      "Inside sales takes the remaining warm leads. Advisor handoffs and KYC manual reviews land in the same queue.",
      "Assisted-sale commissions keep partners selling with the journey, not against it. The rate gets set in the pilot."],
     size=9.5, fill=PINK, margin=0.1, spacing=3)
footer(s)

# --- 8. Metrics and targets ---------------------------------------------------
s = new_slide(CONTENT_BG, "Five metrics. Every target is an assumption the pilot has to prove.")
title(s, "Metrics and targets", "Targets are assumptions to be proven in the pilot, not results")
rows = [["Metric", "Baseline (data)", "Target", "What moves it"],
        ["Lead → activation", "7.4%", "12%", "Advisor, instant quote, self-serve link, lead routing"],
        ["Time to activate", "17.6 days", "≤ 7 days", "Same-sitting quote + KYC, self-booked install slot"],
        ["Acquisition cost per activation", "₹15,053", "≤ ₹8,000", "Fewer visits; field reps go where value is highest"],
        ["Status calls per customer", "3.0", "≤ 0.5", "Tracker with order ID + PIN and per-item ETAs"],
        ["6-month churn", "~15%", "≤ 10%", "Eligibility rules: only bundles that fit the business"]]
table(s, 0.55, 1.4, 8.9, rows, [2.35, 1.35, 1.15, 4.05], size=10.5, row_h=0.45)
text(s, 0.55, 4.25, 8.9, 0.8,
     [[B("Measured per cohort "), ("(pilot city × channel × segment) from the timestamps the order timeline already "
                                   "records: quote, consent, KYC verdict, slot booked, live. Pilot cities are compared "
                                   "with matched non-pilot cities. Churn reads at 6 months, so the 8-week proxy is "
                                   "\"live within the promised slot + first bill paid\".", {})]],
     size=10, fill=LIGHT, margin=0.1)
footer(s, SOURCE + " Targets are proposed, not measured.")

# --- 9. Rollout and risks -----------------------------------------------------
s = new_slide(CONTENT_BG, "8-week pilot in 4 cities, with a go/no-go on the five metrics.")
title(s, "Rollout and risks", "8-week pilot: 2 tier-1 + 2 tier-2 cities")
phases = [("Weeks 1–2", "Set up", "Delhi, Mumbai (tier 1) + Indore, Lucknow (tier 2, Hindi-first). Train partners; "
                                 "connect the catalogue and registries."),
          ("Weeks 3–6", "Run", "Professional offices digital-first; micro retail through links and partners; "
                               "field takes multi-site and manufacturers."),
          ("Weeks 7–8", "Read out", "Compare with matched cities on the 5 metrics. Go/no-go and a "
                                    "regional-language plan.")]
for i, (wk, h, d) in enumerate(phases):
    yy = 1.35 + i * 1.22
    text(s, 0.55, yy, 1.0, 1.1, [[(wk, {"bold": True, "color": WHITE, "size": 10})], [(h, {"color": WHITE})]],
         size=10, fill=RED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 1.6, yy, 2.75, 1.1, d, size=9.5, fill=LIGHT, margin=0.08, anchor=MSO_ANCHOR.MIDDLE)
rows = [["Risk", "Mitigation"],
        ["LLM gives a wrong or unsafe answer", "Rules engine decides products and prices; rules-only fallback; human handoff"],
        ["OCR misreads a document", "Quality checks, one-photo retake hints, manual-review queue"],
        ["Field and partners see it as a threat", "Routing sends them high-value leads; commission on assisted sales"],
        ["Personal data exposure (DPDP)", "Consent per purpose, no stored images, masking, encrypted phone, retention limits"],
        ["Installs can't keep the promised date", "Slots only from available capacity; per-item ETAs; delays shown, not hidden"],
        ["Micro owners don't finish alone", "Partner-assisted mode; save and resume from the self-serve link"]]
table(s, 4.5, 1.35, 4.95, rows, [1.85, 3.1], size=8.5, row_h=0.5)
footer(s, "Pilot cities are a proposal. Lead volumes per city are in smb_leads.csv (synthetic).")

# --- 10. Economics ------------------------------------------------------------
s = new_slide(CONTENT_BG, "Digital sources already cost a fraction per activation; the plan shifts volume to them.")
title(s, "Economics", "Projections are illustrative assumptions, not results")
src = [("WhatsApp campaign", 4000), ("Referral", 4088), ("Inbound call", 5126), ("Website form", 6372),
       ("Channel partner", 20900), ("Field sales", 24233)]
text(s, 0.55, 1.3, 4.4, 0.3, [[B("Lead cost per activation, by source (derived)")]], size=10.5)
for i, (name, v) in enumerate(src):
    yy = 1.65 + i * 0.38
    text(s, 0.55, yy, 1.4, 0.3, name, size=9, anchor=MSO_ANCHOR.MIDDLE)
    w = 2.3 * v / 24233
    rect(s, 1.95, yy + 0.04, w, 0.22, GREY if v > 10000 else RED)
    text(s, 1.95 + w + 0.05, yy, 0.9, 0.3, f"≈ ₹{round(v, -2):,.0f}", size=9, bold=True, anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.55, 3.98, 4.3, 0.5, "Cost per lead ÷ activation rate, so lead cost only. Use it to compare sources, "
                              "not as a full acquisition cost (blended: ₹15,053).", size=8.5, color=GREY)
rows = [["Months of bundle revenue to recover acquisition cost", "At ₹15,053", "At ≤ ₹8,000"],
        ["Professional offices (₹6,575 / mo)", "~2.3", "~1.2"],
        ["Micro retail (₹2,470 / mo)", "~6.1", "~3.2"]]
table(s, 5.05, 1.35, 4.4, rows, [2.4, 1.0, 1.0], size=9, row_h=0.42)
text(s, 5.05, 2.75, 4.4, 1.75,
     [[R("If the targets hold (assumption)")],
      [B("~600 activations "), ("a quarter instead of 368, from the same 5,000 leads at 12%", {})],
      [B("~₹7,000 saved "), ("per activation (₹15,053 → ≤ ₹8,000)", {})],
      [B("~1,100 → ~300 status calls "), ("a quarter, even with more customers", {})],
      [B("Lower churn "), ("from bundles that fit (target ≤ 10%)", {})]],
     size=9.5, fill=PINK, margin=0.1, spacing=3)
text(s, 0.55, 4.55, 8.9, 0.55,
     [[B("Revenue, not margin. "), ("Payback uses median monthly bundle values. Partner commission rates and "
                                     "install costs aren't in the data, so the pilot measures them.", {})]],
     size=9, color=GREY)
footer(s)

prs.save(str(OUT))
print("saved", OUT, len(prs.slides), "slides")
