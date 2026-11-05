"""Label-anchored parsers for the four specimen templates, plus GSTIN look-alike repair.

Everything here works on OcrLine lists, so it can be unit-tested without running OCR.

Templates:
- GST certificate, Udyam certificate, electricity bill: two columns, label on the left, value on the right of the
  same row. Long values (addresses) wrap mid-word onto the next row, so wrapped pieces are joined without a space.
- Signatory ID card: label on one line, value on the line below it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations

from rapidfuzz import fuzz

from ..common import gstin as gst
from ..contracts import DocType
from .ocr import OcrLine

# ---------------------------------------------------------------- document type from the title

_TITLES: list[tuple[DocType, tuple[str, ...]]] = [
    ("gst_certificate", ("gstregistration",)),
    ("udyam_certificate", ("udyamregistration", "udyamcertificate")),
    ("signatory_id", ("signatoryid", "authorisedsignatory", "authorizedsignatory")),
    ("address_proof", ("electricitybill", "utilitybill", "waterbill", "gasbill")),
]


def compact(text: str | None) -> str:
    """Lower-case letters and digits only. OCR often drops or adds spaces, so most comparisons use this."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def detect_type(lines: list[OcrLine]) -> DocType | None:
    """Find the template from its title (any of the first few lines near the top)."""
    top = sorted(lines, key=lambda ln: ln.y0)[:4]
    for ln in top:
        c = compact(ln.text)
        for doc_type, keys in _TITLES:
            if any(k in c for k in keys):
                return doc_type
    return None


# ---------------------------------------------------------------- label anchoring

# field name -> label as printed (compared after compact()). Labels marked None are continuation labels
# ("place of business" is the second line of "Address of principal place of business") and are ignored.
LABELS: dict[DocType, dict[str, str | None]] = {
    "gst_certificate": {
        "gstin": "GSTIN", "legal_name": "Legal name", "trade_name": "Trade name", "constitution": "Constitution",
        "address": "Address of principal", "_cont": None, "liability_date": "Date of liability",
        "registration_type": "Type of registration",
    },
    "udyam_certificate": {
        "udyam_number": "Udyam reg. number", "enterprise_name": "Enterprise name", "enterprise_type": "Type of enterprise",
        "major_activity": "Major activity", "address": "Address", "city": "City", "state": "State",
        "registration_date": "Date of registration",
    },
    "address_proof": {
        "consumer_no": "Consumer no.", "holder_name": "Billed to", "supply_address": "Supply address",
        "bill_date": "Bill date", "units": "Units consumed", "amount_due": "Amount due (INR)",
    },
    "signatory_id": {
        "name": "Name", "designation": "Designation", "business_name": "For business", "id_number": "ID no.",
        "valid_till": "Valid till",
    },
}
CONTINUATION_LABELS = {"gst_certificate": ["place of business"]}
WRAPPING_FIELDS = {"address", "supply_address"}  # values that may wrap onto the next row


def _label_score(text: str, label: str) -> float:
    a, b = compact(text), compact(label)
    if not a or not b:
        return 0.0
    return fuzz.ratio(a, b)


def _match_labels(lines: list[OcrLine], doc_type: DocType) -> tuple[dict[str, OcrLine], set[int]]:
    """Return {field: label line} and the ids of lines that are labels (including continuation labels)."""
    wanted = {k: v for k, v in LABELS[doc_type].items() if v}
    conts = CONTINUATION_LABELS.get(doc_type, [])
    found: dict[str, tuple[float, OcrLine]] = {}
    label_ids: set[int] = set()
    for ln in lines:
        best_field, best = None, 0.0
        for fld, label in wanted.items():
            s = _label_score(ln.text, label)
            if s > best:
                best_field, best = fld, s
        threshold = 92 if len(compact(wanted.get(best_field or "", ""))) <= 5 else 82  # short labels ("City") must be near-exact
        if best_field and best >= threshold:
            if best_field not in found or best > found[best_field][0]:
                found[best_field] = (best, ln)
            label_ids.add(id(ln))
        elif any(_label_score(ln.text, c) >= 82 for c in conts):
            label_ids.add(id(ln))
    return {f: ln for f, (_, ln) in found.items()}, label_ids


def _parse_two_column(lines: list[OcrLine], doc_type: DocType, page_width: int) -> dict[str, str]:
    labels, label_ids = _match_labels(lines, doc_type)
    if not labels:
        return {}
    label_left = min(ln.x0 for ln in labels.values())
    value_left = label_left + 0.2 * page_width
    ordered = sorted(labels.items(), key=lambda kv: kv[1].yc)
    gaps = sorted(b[1].yc - a[1].yc for a, b in zip(ordered, ordered[1:]))
    text_h = sorted(ln.height for ln in labels.values())[len(labels) // 2] or 20
    pitch = gaps[len(gaps) // 2] if gaps else 3 * text_h  # distance between label rows
    values = [ln for ln in lines if id(ln) not in label_ids and ln.x0 >= value_left]
    out: dict[str, list[OcrLine]] = {}
    for ln in sorted(values, key=lambda v: v.yc):
        # The value belongs to the closest label on the same row; a line with no label on its row continues
        # the label above it (wrapped addresses), but only for fields that wrap.
        same_row = [(abs(ln.yc - lab.yc), fld) for fld, lab in ordered if abs(ln.yc - lab.yc) <= 0.35 * pitch]
        if same_row:
            out.setdefault(min(same_row)[1], []).append(ln)
            continue
        above = [(fld, lab) for fld, lab in ordered if lab.yc < ln.yc]
        if above and above[-1][0] in WRAPPING_FIELDS and ln.yc - above[-1][1].yc <= 1.35 * pitch:
            out.setdefault(above[-1][0], []).append(ln)
    result = {}
    for fld, parts in out.items():
        parts = sorted(parts, key=lambda v: (round(v.yc / (0.5 * pitch)), v.x0))
        joiner = "" if fld in WRAPPING_FIELDS else " "
        result[fld] = joiner.join(p.text for p in parts).strip()
    # Fields whose label was found but has no value are reported as empty (e.g. K01's blank Udyam number).
    for fld in labels:
        result.setdefault(fld, "")
    return result


def _parse_stacked(lines: list[OcrLine], doc_type: DocType) -> dict[str, str]:
    labels, label_ids = _match_labels(lines, doc_type)
    result: dict[str, str] = {}
    for fld, lab in labels.items():
        below = [ln for ln in lines if id(ln) not in label_ids and ln.yc > lab.yc
                 and ln.yc - lab.yc <= 2.5 * max(lab.height, 10) and abs(ln.x0 - lab.x0) <= 3 * max(lab.height, 10)]
        result[fld] = min(below, key=lambda ln: ln.yc).text.strip() if below else ""
    return result


def parse_fields(lines: list[OcrLine], doc_type: DocType, page_width: int) -> dict[str, str]:
    if doc_type == "signatory_id":
        return _parse_stacked(lines, doc_type)
    return _parse_two_column(lines, doc_type, page_width)


# ---------------------------------------------------------------- value clean-up

_DATE_RE = re.compile(r"(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})")
_DMY_RE = re.compile(r"(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4})")
_DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "D": "0", "I": "1", "l": "1", "|": "1", "S": "5", "B": "8", "Z": "2"})


def parse_date(text: str | None) -> date | None:
    """'2026-05-30' (also with / or .) or '30-05-2026'. Look-alike letters inside the digits are fixed first."""
    if not text:
        return None
    t = text.translate(_DIGIT_FIX)
    for rx, order in ((_DATE_RE, "ymd"), (_DMY_RE, "dmy")):
        m = rx.search(t)
        if m:
            a, b, c = (int(x) for x in m.groups())
            y, mo, d = (a, b, c) if order == "ymd" else (c, b, a)
            try:
                return date(y, mo, d)
            except ValueError:
                return None
    return None


_PIN_RE = re.compile(r"(\d{6})\D*$")


def address_pin(address: str | None) -> str | None:
    """The 6-digit PIN code at the end of an address ('... Maharashtra - 411231')."""
    if not address:
        return None
    m = _PIN_RE.search(re.sub(r"\s", "", address))
    return m.group(1) if m else None


def split_proprietor(legal_name: str | None) -> tuple[str | None, str | None]:
    """'Joseph Singh (Prop. Ganesh Woodcraft)' -> ('Joseph Singh', 'Ganesh Woodcraft'); other names -> (None, name)."""
    if not legal_name:
        return None, None
    m = re.match(r"^\s*(.+?)\s*\(\s*Prop\.?\s*(.+?)\s*\)?\s*$", legal_name, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, legal_name.strip()


# ---------------------------------------------------------------- GSTIN look-alike repair

LOOKALIKES = {"O": "0", "0": "O", "I": "1", "1": "I", "Z": "2", "2": "Z", "S": "5", "5": "S", "B": "8", "8": "B"}
_DIGIT = set("0123456789")
_LETTER = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_ALNUM = _DIGIT | _LETTER
# Allowed characters per position: state code, PAN (5 letters, 4 digits, 1 letter), entity number, 'Z', check char.
GSTIN_POSITIONS: list[set[str]] = (
    [_DIGIT] * 2 + [_LETTER] * 5 + [_DIGIT] * 4 + [_LETTER] + [_ALNUM - {"0"}] + [{"Z"}] + [_ALNUM]
)
MAX_SWAPS = 2


@dataclass
class GstinRead:
    raw: str                        # what OCR read (normalised)
    value: str                      # the GSTIN we use: the repaired one, or the raw read
    repaired: bool = False
    swaps: list[int] = field(default_factory=list)   # 1-based positions that were swapped
    candidates_passing: int = 0     # how many look-alike candidates passed the checksum


def repair_gstin(raw: str) -> GstinRead:
    """Fix OCR look-alike misreads (O/0, I/1, Z/2, S/5, B/8) in at most MAX_SWAPS positions.

    A swap is only considered where both characters fit the GSTIN pattern at that position; positions where the
    read character breaks the pattern must be swapped. The repair is accepted only if exactly one candidate
    passes the checksum. The registry is never consulted, so a tampered GSTIN (K06) stays invalid.
    """
    g = gst.normalize(raw)
    out = GstinRead(raw=g, value=g)
    if len(g) != 15 or any(c not in _ALNUM for c in g):
        return out
    if gst.is_valid(g):
        return out
    forced, optional = [], []
    for i, ch in enumerate(g):
        allowed = GSTIN_POSITIONS[i]
        alt = LOOKALIKES.get(ch)
        if ch not in allowed:
            if alt is None or alt not in allowed:
                return out  # a character that no look-alike swap can fix
            forced.append(i)
        elif alt is not None and alt in allowed:
            optional.append(i)
    if len(forced) > MAX_SWAPS:
        return out
    base = list(g)
    for i in forced:
        base[i] = LOOKALIKES[base[i]]
    passing: list[tuple[str, list[int]]] = []
    for k in range(0, MAX_SWAPS - len(forced) + 1):
        for extra in combinations(optional, k):
            cand = base.copy()
            for i in extra:
                cand[i] = LOOKALIKES[cand[i]]
            s = "".join(cand)
            if s != g and gst.is_valid(s):
                passing.append((s, sorted(forced + list(extra))))
    out.candidates_passing = len(passing)
    if len(passing) == 1:
        out.value, swaps = passing[0]
        out.repaired = True
        out.swaps = [i + 1 for i in swaps]
    elif forced and not passing:
        out.value = "".join(base)  # still invalid, but at least in GSTIN shape so the format check is fair
    return out


_GSTIN_IN_TEXT = re.compile(r"[0-9OISZB]{2}[A-Z0-9]{10}[A-Z0-9]{3}")


def find_gstin(text: str) -> str | None:
    """Best-effort GSTIN-shaped token in free text (used when the GSTIN label was not found)."""
    m = _GSTIN_IN_TEXT.search(gst.normalize(text))
    return m.group(0) if m else None


# ---------------------------------------------------------------- per-document parse

@dataclass
class ParsedDoc:
    doc_type: DocType                 # the slot it was uploaded to
    detected_type: DocType | None
    blurry: bool
    blur_score: float
    skew_deg: float
    fields: dict[str, str]            # raw values (unmasked): kept in memory only
    gstin: GstinRead | None = None

    @property
    def readable(self) -> bool:
        return not self.blurry and bool(self.fields)


def parse_document(doc_type: DocType, lines: list[OcrLine], page_width: int, *, blurry: bool = False,
                   blur_score: float = 0.0, skew_deg: float = 0.0) -> ParsedDoc:
    detected = detect_type(lines)
    template = detected or doc_type
    fields = parse_fields(lines, template, page_width)
    doc = ParsedDoc(doc_type=doc_type, detected_type=detected, blurry=blurry, blur_score=blur_score,
                    skew_deg=skew_deg, fields=fields)
    for key in NAME_FIELDS & fields.keys():
        fields[key] = respace(fields[key])
    if template == "gst_certificate":
        raw = fields.get("gstin") or find_gstin(" ".join(ln.text for ln in lines)) or ""
        if raw:
            doc.gstin = repair_gstin(raw)
            fields["gstin"] = doc.gstin.value
    if template == "udyam_certificate" and fields.get("udyam_number"):
        fields["udyam_number"] = normalize_udyam_read(fields["udyam_number"])
    return doc


NAME_FIELDS = {"legal_name", "trade_name", "enterprise_name", "name", "business_name", "holder_name"}


def respace(text: str) -> str:
    """Put back spaces OCR drops between words in names: 'NishaArora' -> 'Nisha Arora', 'Tours&Travels' -> 'Tours & Travels'."""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"\s*&\s*", " & ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_udyam_read(raw: str) -> str:
    """'UDYAM-MH-00-95166g6' style reads: fix look-alikes in the numeric parts only, then normalise."""
    compact_raw = re.sub(r"[^A-Z0-9]", "", raw.upper())
    m = re.fullmatch(r"UDYAM([A-Z0-9]{2})([A-Z0-9]{2})([A-Z0-9]{7})", compact_raw)
    if not m:
        return gst.normalize_udyam(raw)
    state, district, serial = m.groups()
    to_letter = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z"})
    to_digit = str.maketrans({"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2", "D": "0"})
    return f"UDYAM-{state.translate(to_letter)}-{district.translate(to_digit)}-{serial.translate(to_digit)}"
