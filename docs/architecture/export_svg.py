"""Generate docs/architecture/architecture.svg (+ .png) by hand-laid SVG."""
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1]
W, H = 1600, 1010
RED, GREY, AMBER = "#c81e1e", "#555", "#b45309"
parts = []


def rect(x, y, w, h, fill="#fff", stroke="#999", rx=10, sw=1.5, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, s, size=13, weight="normal", color="#111", anchor="middle", italic=False):
    st = ' font-style="italic"' if italic else ""
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{st}>{escape(s)}</text>')


def node(x, y, w, h, title, lines=(), fill="#fff", stroke="#888"):
    rect(x, y, w, h, fill, stroke)
    cy = y + 26 if lines else y + h / 2 + 6
    text(x + w / 2, cy, title, 16, "bold")
    for i, l in enumerate(lines):
        text(x + w / 2, cy + 20 + 17 * i, l, 13, color="#333")


def label(x, y, s, color):
    w = 6.4 * len(s) + 10
    parts.append(f'<rect x="{x - w / 2}" y="{y - 12}" width="{w}" height="17" rx="3" fill="#fff" opacity="0.92"/>')
    text(x, y, s, 12, color=color)


def head(x1, y1, x2, y2, color):
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    pts = [(x2, y2), (x2 - 12 * math.cos(a) + 6 * math.sin(a), y2 - 12 * math.sin(a) - 6 * math.cos(a)),
           (x2 - 12 * math.cos(a) - 6 * math.sin(a), y2 - 12 * math.sin(a) + 6 * math.cos(a))]
    parts.append('<polygon points="%s" fill="%s"/>' % (" ".join(f"{x:.1f},{y:.1f}" for x, y in pts), color))


def arrow(pts, color=GREY, lab=None, lab_at=None, both=False, dash=None, lab2=None):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{ds}/>')
    head(*pts[-2], *pts[-1], color)
    if both:
        head(*pts[1], *pts[0], color)
    if lab:
        lx, ly = lab_at
        label(lx, ly, lab, color)
        if lab2:
            label(lx, ly + 16, lab2, color)


defs = "".join(
    f'<marker id="a-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in (RED, GREY, AMBER))

# Title
text(40, 42, "Udyam Digital: solution architecture and data flows", 24, "bold", anchor="start")
text(W - 40, 42, "Accel Business · synthetic data only", 14, color="#555", anchor="end")

# Columns
PX, PW = 40, 300          # phone column
AX, AW = 520, 560         # API box
MX, MW = 555, 490         # modules inside API
SX, SW = 1260, 300        # stores

# Phone
rect(PX, 70, PW, 620, "#f7f7f7", "#666", 16, 2)
text(PX + PW / 2, 98, "Owner's phone", 18, "bold")
text(PX + PW / 2, 116, "mobile-first SPA · React · EN / HI", 13, color="#444")
node(PX + 20, 130, PW - 40, 80, "Advisor chat + voice", ["browser speech-to-text"])
node(PX + 20, 250, PW - 40, 80, "Quote", ["one monthly price, add-on toggles"])
node(PX + 20, 370, PW - 40, 90, "Consent + Smart KYC", ["per-purpose consent (EN/HI)", "camera / upload"])
node(PX + 20, 570, PW - 40, 90, "Checkout + tracker", ["order ID + PIN", "book install slot"])

node(PX, 740, PW, 90, "Back office", ["sales, inside sales, partners", "passcode header"], "#f7f7f7", "#666")

# API
rect(AX, 70, AW, 830, "#fbfbff", "#3730a3", 16, 2)
text(AX + AW / 2, 98, "One FastAPI app  (HTTPS  /api)", 18, "bold", "#3730a3")
node(MX, 130, MW, 80, "Advisor", ["LLM chain: Groq → Gemini → rules-only fallback", "asks only for missing fields"])
node(MX, 250, MW, 80, "Rules engine", ["eligibility (tier, size, GSTIN), dependencies,", "price + 18% GST · catalogue from CSV"])
node(MX, 370, MW, 90, "Smart KYC", ["RapidOCR in memory · blur / skew / type checks", "name, GSTIN, Udyam, address-age cross-checks"], "#fff5f5", RED)
node(MX + 160, 480, MW - 160, 60, "Mock GSTIN / Udyam registries")
node(MX, 570, MW, 90, "Orders + tracker", ["status machine, slots, per-item ETAs", "phone encrypted (Fernet)"], "#fff5f5", RED)
node(MX, 740, MW, 90, "Back-office API", ["lead score (0–1) + HOT/WARM/COLD band", "suggested channel: FIELD · PARTNER · SELF_SERVE_LINK"])
rect(MX, 848, MW, 36, "#eef2ff", "#3730a3", 8)
text(MX + MW / 2, 871, "Masking + log redaction on every response and log line (GSTIN, Udyam, ID, phone)", 13, "bold", "#3730a3")

# Stores
node(SX, 120, SW, 100, "External LLM APIs", ["Groq, Gemini", "(skipped in rules-only mode)"], "#fffbeb", AMBER)
rect(SX, 270, SW, 400, "#eef2ff", "#3730a3", 12, 2)
text(SX + SW / 2, 300, "SQLite", 18, "bold", "#3730a3")
for i, l in enumerate(["advisor sessions, handoffs", "quotes", "consents (version, purposes)",
                       "KYC results: checks, verdict,", "masked fields only (no images)",
                       "orders + events", "phone encrypted at rest", "",
                       "retention: 180 days after", "activation · 30 days if rejected",
                       "withdraw consent = delete KYC data"]):
    text(SX + SW / 2, 328 + 20 * i, l, 13, color="#222")
node(SX, 740, SW, 110, "Case CSVs (read-only)", ["product catalogue · 5,000 leads", "mock GSTIN + Udyam registries"], "#f3f4f6", "#666")

# Edges
L = PX + PW
arrow([(L, 160), (MX, 160)], GREY, "business description,", (L + 108, 133), lab2="EN/HI (text or voice)")
arrow([(MX + MW, 152), (SX, 152)], AMBER, "business description only", (1152, 124), lab2="no IDs, phone, documents, images")
arrow([(SX, 198), (MX + MW, 198)], GREY, "reply + profile fields", (1152, 214))
arrow([(MX + 245, 210), (MX + 245, 250)], GREY, "profile", (MX + 290, 235))
arrow([(L, 280), (MX, 280)], RED, "profile + add-ons", (L + 108, 270), lab2="GSTIN only if needed")
arrow([(MX, 312), (L, 312)], GREY)
label(L + 108, 326, "monthly price + GST", GREY)
arrow([(MX + MW, 210), (SX, 300)], GREY, "session, handoff", (1150, 240))
arrow([(MX + MW, 290), (SX, 340)], GREY, "saved quote", (1150, 312))
arrow([(L, 400), (MX, 400)], RED, "consent: version + purposes", (L + 108, 392))
arrow([(L, 440), (MX, 440)], RED, "document photos", (L + 108, 432), lab2="in memory, never stored")
arrow([(MX + MW, 415), (SX, 430)], RED, "verdict, checks,", (1152, 410), lab2="masked fields")
arrow([(MX + 245, 460), (MX + 245, 480)], GREY)
arrow([(SX, 765), (1170, 765), (1170, 510), (MX + MW, 510)], GREY, "registry rows", (1108, 500))
arrow([(MX + 70, 460), (MX + 70, 570)], GREY, "on_kyc_result", (MX + 75, 520))
arrow([(L, 600), (MX, 600)], RED, "contact name + phone", (L + 108, 592))
arrow([(MX, 640), (L, 640)], RED, "order ID + PIN, timeline", (L + 108, 632))
arrow([(MX + MW, 615), (SX, 615)], RED, "order, phone (encrypted)", (1152, 607))
arrow([(L, 770), (MX, 770)], GREY, "passcode", (L + 108, 762))
arrow([(MX, 805), (L, 805)], GREY, "ranked leads,", (L + 108, 797), lab2="masked identifiers")
arrow([(SX, 810), (MX + MW, 810)], GREY, "leads", (1152, 802))
arrow([(MX + MW, 745), (1225, 745), (1225, 670)], GREY, both=True)
label(1225, 690, "handoffs, orders,", GREY)
label(1225, 706, "KYC reviews", GREY)

# Legend + footer
y = 940
parts.append(f'<line x1="40" y1="{y}" x2="80" y2="{y}" stroke="{RED}" stroke-width="3"/>')
text(88, y + 5, "personal data", 13, anchor="start")
parts.append(f'<line x1="210" y1="{y}" x2="250" y2="{y}" stroke="{AMBER}" stroke-width="3"/>')
text(258, y + 5, "leaves our server (LLM): business description only", 13, anchor="start")
parts.append(f'<line x1="590" y1="{y}" x2="630" y2="{y}" stroke="{GREY}" stroke-width="3"/>')
text(638, y + 5, "non-personal", 13, anchor="start")
text(40, 975, "Documents are processed in memory only and never written to disk. Identifiers are masked everywhere. "
     "Demo-only controls require demo mode. All businesses, people and IDs are fictional.", 13, color="#444", anchor="start")

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'font-family="Helvetica"><defs>{defs}</defs>'
       f'<rect width="{W}" height="{H}" fill="#fff"/>' + "".join(parts) + "</svg>")
open(OUT + ".svg", "w").write(svg)

import fitz  # noqa: E402
pix = fitz.open(OUT + ".svg")[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
pix.save(OUT + ".png")
print("ok", pix.width, pix.height)
