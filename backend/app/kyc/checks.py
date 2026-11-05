"""KYC checks and the verdict. Pure functions over parsed documents and the mock registries (no OCR, no DB).

Verdict: any rejection-class failure -> REJECTED; else any name-mismatch failure -> MANUAL_REVIEW;
else any other failure (owner-fixable: blur, missing document, stale bill, expired ID, ...) -> ACTION_REQUIRED;
else VERIFIED. WARN never changes the verdict.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from rapidfuzz import fuzz

from ..common import gstin as gst
from ..common import mask
from ..common.i18n_server import lt
from ..common.registry import lookup_gstin, lookup_udyam
from ..contracts import Check, DocType, GstinLookup, KycVerdict, LocalText
from .. import data
from .parse import ParsedDoc, address_pin, compact, parse_date, split_proprietor

DOC_TYPES: list[DocType] = ["gst_certificate", "udyam_certificate", "signatory_id", "address_proof"]

REJECT_CODES = {"GSTIN_CHECKSUM", "GSTIN_FOUND", "GSTIN_ACTIVE"}
NAME_CODES = {"LEGAL_NAME_MATCH", "TRADE_NAME_MATCH", "NAME_CONSISTENT", "UDYAM_FOUND", "UDYAM_NAME_MATCH",
              "SIGNATORY_MATCH"}
# Every other FAIL is owner-fixable: DOC_PRESENT, DOC_TYPE, IMAGE_READABLE, GSTIN_FORMAT, UDYAM_NUMBER, ID_VALID,
# ADDRESS_RECENT, ADDRESS_MATCH.

NAME_PASS = 90
NAME_WARN = 75
ADDRESS_MAX_AGE_DAYS = 90

DOC_NAMES: dict[DocType, LocalText] = {
    "gst_certificate": lt("GST certificate", "GST प्रमाणपत्र"),
    "udyam_certificate": lt("Udyam certificate", "उद्यम प्रमाणपत्र"),
    "signatory_id": lt("signatory ID", "हस्ताक्षरकर्ता की ID"),
    "address_proof": lt("utility bill", "बिजली/पानी का बिल"),
}
_MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]
_MONTHS_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]


def _d_en(d: date) -> str:
    return f"{d.day} {_MONTHS_EN[d.month - 1]} {d.year}"


def _d_hi(d: date) -> str:
    return f"{d.day} {_MONTHS_HI[d.month - 1]} {d.year}"


def _check(code: str, status: str, en: str, hi: str, fix: tuple[str, str] | None = None,
           doc: DocType | None = None) -> Check:
    return Check(code=code, status=status, message=lt(en, hi), fix_hint=lt(*fix) if fix else None,  # type: ignore[arg-type]
                 doc_type=doc)


def _retake(doc: DocType) -> tuple[str, str]:
    n = DOC_NAMES[doc]
    return (f"Retake the photo of your {n.en} in good light, flat and in focus.",
            f"अपने {n.hi} की फ़ोटो अच्छी रोशनी में, सीधी और साफ़ फिर से लें।")


# ---------------------------------------------------------------- name similarity

def _words(text: str | None) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def name_score(a: str | None, b: str | None) -> float:
    """rapidfuzz token_set_ratio, also tried with all spaces removed because OCR often drops them
    ('VindhyaTours &Travels'). Returns 0-100."""
    if not a or not b:
        return 0.0
    return max(fuzz.token_set_ratio(_words(a), _words(b)), fuzz.ratio(compact(a), compact(b)))


def legal_name_score(read: str | None, registry: str | None) -> float:
    """Proprietorship legal names are 'Person (Prop. Business)': score the person and the business separately
    and keep the worse, so 'Neha Banerjee (Prop. Shri Physio Clinic)' doesn't pass on the shared words alone."""
    rp, rb = split_proprietor(read)
    gp, gb = split_proprietor(registry)
    if rp and gp:
        return min(name_score(rp, gp), name_score(rb, gb))
    return name_score(read, registry)


def name_status(score: float) -> str:
    return "PASS" if score >= NAME_PASS else "WARN" if score >= NAME_WARN else "FAIL"


def business_name(doc: ParsedDoc) -> str | None:
    """The business name a document shows."""
    f = doc.fields
    if doc.doc_type == "gst_certificate":
        return f.get("trade_name") or split_proprietor(f.get("legal_name"))[1]
    if doc.doc_type == "udyam_certificate":
        return f.get("enterprise_name")
    if doc.doc_type == "signatory_id":
        return f.get("business_name")
    return f.get("holder_name")


# ---------------------------------------------------------------- address helpers

def _city_in(address: str | None) -> str | None:
    if not address:
        return None
    c = compact(address)
    known = [v["city"] for v in data.city_tiers().values()]
    hits = [city for city in known if compact(str(city)) in c]
    if hits:
        return max(hits, key=lambda x: len(str(x)))  # type: ignore[arg-type]
    parts = [p.strip() for p in address.split(",") if p.strip()]
    return parts[-2] if len(parts) >= 2 else None


# ---------------------------------------------------------------- per-document checks (also shown right after upload)

def usable(doc: ParsedDoc | None) -> bool:
    return bool(doc) and doc.readable and (doc.detected_type in (None, doc.doc_type))  # type: ignore[union-attr]


def document_checks(doc: ParsedDoc, today: date) -> list[Check]:
    """Checks that need only this document: type, blur, and its own key fields."""
    out: list[Check] = []
    slot = doc.doc_type
    name = DOC_NAMES[slot]
    if doc.detected_type and doc.detected_type != slot:
        other = DOC_NAMES[doc.detected_type]
        out.append(_check("DOC_TYPE", "FAIL", f"This looks like your {other.en}, not your {name.en}.",
                          f"यह आपका {other.hi} लगता है, {name.hi} नहीं।",
                          (f"Upload your {name.en} here.", f"यहाँ अपना {name.hi} अपलोड करें।"), slot))
        return out
    if doc.blurry:
        out.append(_check("IMAGE_READABLE", "FAIL", f"Your {name.en} photo is too blurry to read.",
                          f"आपके {name.hi} की फ़ोटो इतनी धुंधली है कि पढ़ी नहीं जा सकती।", _retake(slot), slot))
        return out
    if not doc.fields:
        out.append(_check("IMAGE_READABLE", "FAIL", f"We couldn't read any details on your {name.en}.",
                          f"हम आपके {name.hi} पर कोई जानकारी नहीं पढ़ पाए।", _retake(slot), slot))
        return out
    f = doc.fields
    if slot == "gst_certificate":
        out += _gstin_shape_checks(f.get("gstin", ""))
    elif slot == "udyam_certificate":
        out.append(_udyam_number_check(f.get("udyam_number", "")))
    elif slot == "signatory_id":
        out.append(_id_valid_check(f.get("valid_till"), today))
    elif slot == "address_proof":
        out.append(address_recent_check(parse_date(f.get("bill_date")), today))
    return out


def _gstin_shape_checks(value: str) -> list[Check]:
    doc: DocType = "gst_certificate"
    if not value or not gst.format_valid(value):
        return [_check("GSTIN_FORMAT", "FAIL", "We couldn't read a valid GSTIN on your GST certificate.",
                       "हम आपके GST प्रमाणपत्र पर सही GSTIN नहीं पढ़ पाए।", _retake(doc), doc)]
    out = [_check("GSTIN_FORMAT", "PASS", "The GSTIN has the right format.", "GSTIN का फ़ॉर्मैट सही है।", doc=doc)]
    if gst.checksum_valid(value):
        out.append(_check("GSTIN_CHECKSUM", "PASS", "The GSTIN's check digit is correct.", "GSTIN का चेक अंक सही है।", doc=doc))
    else:
        m = mask.mask_gstin(value)
        out.append(_check("GSTIN_CHECKSUM", "FAIL",
                          f"The GSTIN on your certificate ({m}) is not a valid number: its last character doesn't match.",
                          f"आपके प्रमाणपत्र पर लिखा GSTIN ({m}) सही नंबर नहीं है: उसका आख़िरी अक्षर मेल नहीं खाता।",
                          ("Check that you uploaded your own, unedited GST certificate. Our team will contact you.",
                           "जाँच लें कि आपने अपना असली, बिना बदला GST प्रमाणपत्र अपलोड किया है। हमारी टीम आपसे संपर्क करेगी।"), doc))
    return out


def _udyam_number_check(value: str) -> Check:
    doc: DocType = "udyam_certificate"
    if value and gst.udyam_format_valid(value):
        return _check("UDYAM_NUMBER", "PASS", "The Udyam number is readable.", "उद्यम नंबर पढ़ा जा सकता है।", doc=doc)
    return _check("UDYAM_NUMBER", "FAIL", "We couldn't find the Udyam registration number on your certificate.",
                  "हमें आपके प्रमाणपत्र पर उद्यम रजिस्ट्रेशन नंबर नहीं मिला।",
                  ("Upload the Udyam certificate page that shows the number (UDYAM-XX-00-0000000).",
                   "उद्यम प्रमाणपत्र का वह पेज अपलोड करें जिस पर नंबर (UDYAM-XX-00-0000000) लिखा हो।"), doc)


def _id_valid_check(valid_till: str | None, today: date) -> Check:
    doc: DocType = "signatory_id"
    d = parse_date(valid_till)
    if d is None:
        return _check("ID_VALID", "FAIL", "We couldn't read the expiry date on the signatory ID.",
                      "हम हस्ताक्षरकर्ता की ID पर समाप्ति तिथि नहीं पढ़ पाए।", _retake(doc), doc)
    if d < today:
        return _check("ID_VALID", "FAIL", f"The signatory ID expired on {_d_en(d)}.",
                      f"हस्ताक्षरकर्ता की ID {_d_hi(d)} को समाप्त हो चुकी है।",
                      ("Upload an ID that is still valid.", "ऐसी ID अपलोड करें जो अभी मान्य हो।"), doc)
    return _check("ID_VALID", "PASS", f"The signatory ID is valid till {_d_en(d)}.",
                  f"हस्ताक्षरकर्ता की ID {_d_hi(d)} तक मान्य है।", doc=doc)


def address_recent_check(bill_date: date | None, today: date) -> Check:
    """The bill must be dated within ADDRESS_MAX_AGE_DAYS before today (inclusive) and not in the future."""
    doc: DocType = "address_proof"
    oldest = date.fromordinal(today.toordinal() - ADDRESS_MAX_AGE_DAYS)
    fix = (f"Upload a utility bill dated on or after {_d_en(oldest)}.",
           f"{_d_hi(oldest)} या उसके बाद का बिल अपलोड करें।")
    if bill_date is None:
        return _check("ADDRESS_RECENT", "FAIL", "We couldn't read the date on your bill.",
                      "हम आपके बिल पर तारीख़ नहीं पढ़ पाए।", _retake(doc), doc)
    if bill_date > today:
        return _check("ADDRESS_RECENT", "FAIL", f"Your bill is dated {_d_en(bill_date)}, which is in the future.",
                      f"आपके बिल पर {_d_hi(bill_date)} की तारीख़ है, जो अभी आई नहीं है।", fix, doc)
    age = (today - bill_date).days
    if age > ADDRESS_MAX_AGE_DAYS:
        return _check("ADDRESS_RECENT", "FAIL",
                      f"Your bill is {age} days old. We need one from the last {ADDRESS_MAX_AGE_DAYS} days.",
                      f"आपका बिल {age} दिन पुराना है। हमें पिछले {ADDRESS_MAX_AGE_DAYS} दिनों का बिल चाहिए।", fix, doc)
    return _check("ADDRESS_RECENT", "PASS", f"Your bill is recent ({age} days old).",
                  f"आपका बिल हाल का है ({age} दिन पुराना)।", doc=doc)


# ---------------------------------------------------------------- full check run

@dataclass
class Outcome:
    verdict: KycVerdict
    checks: list[Check]
    gst_products_blocked: bool = False
    fields_masked: dict[str, str] = field(default_factory=dict)


def verdict_for(checks: list[Check]) -> KycVerdict:
    fails = {c.code for c in checks if c.status == "FAIL"}
    if fails & REJECT_CODES:
        return "REJECTED"
    if fails & NAME_CODES:
        return "MANUAL_REVIEW"
    if fails:
        return "ACTION_REQUIRED"
    return "VERIFIED"


def _name_check(code: str, label: tuple[str, str], read: str | None, registry: str | None, score: float,
                doc: DocType, source: tuple[str, str] = ("GST registry", "GST रजिस्ट्री")) -> Check:
    status = name_status(score)
    if status == "PASS":
        return _check(code, "PASS", f"The {label[0]} matches the {source[0]}.", f"{label[1]} {source[1]} से मेल खाता है।", doc=doc)
    if status == "WARN":
        return _check(code, "WARN", f"The {label[0]} is close to, but not the same as, the {source[0]} "
                                    f"(“{read}” vs “{registry}”).",
                      f"{label[1]} {source[1]} से लगभग मिलता है, पर पूरा नहीं (“{read}” और “{registry}”)।", doc=doc)
    return _check(code, "FAIL", f"The {label[0]} doesn't match the {source[0]} (“{read}” vs “{registry}”).",
                  f"{label[1]} {source[1]} से मेल नहीं खाता (“{read}” और “{registry}”)।",
                  ("Our team will check this by hand. Make sure every document is for the same business.",
                   "हमारी टीम इसे खुद जाँचेगी। ध्यान रखें कि सभी दस्तावेज़ एक ही व्यवसाय के हों।"), doc)


def run_checks(docs: dict[DocType, ParsedDoc], today: date) -> Outcome:
    checks: list[Check] = []
    blocked = False

    # 1. documents present, right type, readable
    missing = [t for t in DOC_TYPES if t not in docs]
    for t in missing:
        n = DOC_NAMES[t]
        checks.append(_check("DOC_PRESENT", "FAIL", f"We don't have your {n.en} yet.", f"हमें अभी आपका {n.hi} नहीं मिला है।",
                             (f"Upload a photo of your {n.en}.", f"अपने {n.hi} की फ़ोटो अपलोड करें।"), t))
    if not missing:
        checks.append(_check("DOC_PRESENT", "PASS", "All four documents received.", "चारों दस्तावेज़ मिल गए।"))
    per_doc: dict[DocType, list[Check]] = {t: document_checks(d, today) for t, d in docs.items()}
    for t in DOC_TYPES:
        checks += [c for c in per_doc.get(t, []) if c.code in ("DOC_TYPE", "IMAGE_READABLE")]
    if docs and all(usable(d) for d in docs.values()):
        checks.append(_check("IMAGE_READABLE", "PASS", "Every photo is clear enough to read.", "हर फ़ोटो पढ़ने लायक साफ़ है।"))
    ok = {t: d for t, d in docs.items() if usable(d)}

    # 2. GSTIN: format, checksum, found, active; legal and trade name vs registry
    reg: GstinLookup | None = None
    gst_doc = ok.get("gst_certificate")
    if gst_doc:
        shape = per_doc["gst_certificate"]
        checks += [c for c in shape if c.code in ("GSTIN_FORMAT", "GSTIN_CHECKSUM")]
        value = gst_doc.fields.get("gstin", "")
        if gst.is_valid(value):
            look = lookup_gstin(value)
            m = mask.mask_gstin(value)
            if not look.found:
                checks.append(_check("GSTIN_FOUND", "FAIL", f"GSTIN {m} is not in the GST registry.",
                                     f"GSTIN {m} GST रजिस्ट्री में नहीं है।",
                                     ("Check that you uploaded your own GST certificate. Our team will contact you.",
                                      "जाँच लें कि आपने अपना ही GST प्रमाणपत्र अपलोड किया है। हमारी टीम आपसे संपर्क करेगी।"),
                                     "gst_certificate"))
            else:
                reg = look
                checks.append(_check("GSTIN_FOUND", "PASS", f"GSTIN {m} is in the GST registry.",
                                     f"GSTIN {m} GST रजिस्ट्री में है।", doc="gst_certificate"))
                if look.status == "Active":
                    checks.append(_check("GSTIN_ACTIVE", "PASS", "Your GSTIN is active.", "आपका GSTIN सक्रिय है।",
                                         doc="gst_certificate"))
                else:
                    blocked = True
                    st_hi = {"Cancelled": "रद्द", "Suspended": "निलंबित"}.get(look.status or "", look.status or "")
                    checks.append(_check(
                        "GSTIN_ACTIVE", "FAIL",
                        f"Your GSTIN is {(look.status or '').lower()} in the GST registry, so we can't verify this "
                        "order. Products that need a GSTIN can't be sold until it is active again.",
                        f"GST रजिस्ट्री में आपका GSTIN {st_hi} है, इसलिए हम यह ऑर्डर सत्यापित नहीं कर सकते। "
                        "जिन प्रोडक्ट के लिए GSTIN ज़रूरी है, वे इसके दोबारा सक्रिय होने तक नहीं मिल सकते।",
                        ("Get your GST registration restored, then place the order again.",
                         "अपना GST रजिस्ट्रेशन फिर से चालू करवाएँ, फिर दोबारा ऑर्डर करें।"), "gst_certificate"))
                f = gst_doc.fields
                checks.append(_name_check("LEGAL_NAME_MATCH", ("legal name", "कानूनी नाम"), f.get("legal_name"),
                                          look.legal_name, legal_name_score(f.get("legal_name"), look.legal_name),
                                          "gst_certificate"))
                checks.append(_name_check("TRADE_NAME_MATCH", ("trade name", "व्यापार नाम"), f.get("trade_name"),
                                          look.trade_name, name_score(f.get("trade_name"), look.trade_name),
                                          "gst_certificate"))

    # 3. the business name is the same on every document
    reference = (reg.trade_name if reg else None) or (business_name(gst_doc) if gst_doc else None)
    named_docs: list[tuple[LocalText, str, DocType]] = []
    if gst_doc and split_proprietor(gst_doc.fields.get("legal_name"))[1]:
        named_docs.append((lt("legal name on the GST certificate", "GST प्रमाणपत्र पर कानूनी नाम"),
                           split_proprietor(gst_doc.fields.get("legal_name"))[1] or "", "gst_certificate"))
    for t in DOC_TYPES:
        d = ok.get(t)
        if d and business_name(d):
            label = lt(f"name on the {DOC_NAMES[t].en}", f"{DOC_NAMES[t].hi} पर नाम")
            named_docs.append((label, business_name(d) or "", t))
    if not reference and named_docs:
        reference = named_docs[0][1]
    if reference and len(named_docs) >= 2:
        odd = [(lab, val, t) for lab, val, t in named_docs if name_score(val, reference) < NAME_PASS]
        if odd:
            lab, val, t = odd[0]
            more_en = f" ({len(odd) - 1} more)" if len(odd) > 1 else ""
            more_hi = f" ({len(odd) - 1} और)" if len(odd) > 1 else ""
            checks.append(_check(
                "NAME_CONSISTENT", "FAIL",
                f"The {lab.en} is “{val}”, but your other documents say “{reference}”{more_en}.",
                f"{lab.hi} “{val}” है, पर आपके बाकी दस्तावेज़ों पर “{reference}” लिखा है{more_hi}।",
                ("Our team will check this by hand. If the business changed its name, keep the proof ready.",
                 "हमारी टीम इसे खुद जाँचेगी। अगर व्यवसाय का नाम बदला है, तो उसका प्रमाण तैयार रखें।"), t))
        else:
            checks.append(_check("NAME_CONSISTENT", "PASS", "The business name is the same on every document.",
                                 "हर दस्तावेज़ पर व्यवसाय का नाम एक जैसा है।"))

    # 4. Udyam: number present and in the registry, name matches (dates and activity are not compared)
    ud = ok.get("udyam_certificate")
    if ud:
        number = ud.fields.get("udyam_number", "")
        num_check = _udyam_number_check(number)
        checks.append(num_check)
        if num_check.status == "PASS":
            look_u = lookup_udyam(number)
            m = mask.mask_udyam(number)
            if not look_u.found:
                checks.append(_check("UDYAM_FOUND", "FAIL", f"Udyam number {m} is not in the Udyam registry.",
                                     f"उद्यम नंबर {m} उद्यम रजिस्ट्री में नहीं है।",
                                     ("Our team will check this by hand.", "हमारी टीम इसे खुद जाँचेगी।"), "udyam_certificate"))
            else:
                checks.append(_check("UDYAM_FOUND", "PASS", f"Udyam number {m} is in the Udyam registry.",
                                     f"उद्यम नंबर {m} उद्यम रजिस्ट्री में है।", doc="udyam_certificate"))
                expected = reference or ud.fields.get("enterprise_name")
                checks.append(_name_check("UDYAM_NAME_MATCH", ("business name", "व्यवसाय का नाम"), expected,
                                          look_u.enterprise_name, name_score(expected, look_u.enterprise_name),
                                          "udyam_certificate", ("Udyam registry", "उद्यम रजिस्ट्री")))

    # 5. signatory: the proprietor for a proprietorship; only a WARN for firms and companies
    sid = ok.get("signatory_id")
    if sid:
        constitution = (reg.constitution if reg else None) or (gst_doc.fields.get("constitution") if gst_doc else None) or ""
        signer = sid.fields.get("name", "")
        legal = (reg.legal_name if reg else None) or (gst_doc.fields.get("legal_name") if gst_doc else None)
        proprietor = split_proprietor(legal)[0]
        if "propriet" in constitution.lower():
            if not proprietor:
                checks.append(_check("SIGNATORY_MATCH", "WARN", "We couldn't find the proprietor's name to compare with the ID.",
                                     "ID से मिलाने के लिए हमें मालिक का नाम नहीं मिला।", doc="signatory_id"))
            elif name_score(signer, proprietor) >= NAME_PASS:
                checks.append(_check("SIGNATORY_MATCH", "PASS", "The ID belongs to the proprietor.",
                                     "ID मालिक (प्रोप्राइटर) की ही है।", doc="signatory_id"))
            else:
                checks.append(_check("SIGNATORY_MATCH", "FAIL",
                                     f"The ID is for “{signer}”, but the proprietor is “{proprietor}”.",
                                     f"ID “{signer}” की है, पर मालिक (प्रोप्राइटर) “{proprietor}” हैं।",
                                     ("Upload the proprietor's own ID.", "मालिक (प्रोप्राइटर) की अपनी ID अपलोड करें।"),
                                     "signatory_id"))
        else:
            kind = constitution or "firm"
            checks.append(_check("SIGNATORY_MATCH", "WARN",
                                 f"This business is a {kind}. These documents can't prove that “{signer}” may sign "
                                 "for it, so our team may ask for an authorisation letter.",
                                 f"यह व्यवसाय एक {kind} है। इन दस्तावेज़ों से यह साबित नहीं होता कि “{signer}” इसके लिए "
                                 "हस्ताक्षर कर सकते हैं, इसलिए हमारी टीम एक अधिकार-पत्र माँग सकती है।", doc="signatory_id"))
        checks += [c for c in per_doc["signatory_id"] if c.code == "ID_VALID"]

    # 6. address proof: recent, and at the GST address
    bill = ok.get("address_proof")
    if bill:
        checks += [c for c in per_doc["address_proof"] if c.code == "ADDRESS_RECENT"]
        supply = bill.fields.get("supply_address")
        gst_address = (gst_doc.fields.get("address") if gst_doc else None) or (reg.address if reg else None)
        checks.append(_address_match_check(supply, gst_address))

    fields_masked = _masked_summary(ok)
    return Outcome(verdict=verdict_for(checks), checks=checks, gst_products_blocked=blocked, fields_masked=fields_masked)


def _address_match_check(supply: str | None, gst_address: str | None) -> Check:
    doc: DocType = "address_proof"
    if not supply or not gst_address:
        return _check("ADDRESS_MATCH", "WARN", "We couldn't compare the bill's address with your GST address.",
                      "हम बिल का पता आपके GST पते से नहीं मिला पाए।", doc=doc)
    pin_b, pin_g = address_pin(supply), address_pin(gst_address)
    city_b, city_g = _city_in(supply), _city_in(gst_address)
    same_city = bool(city_b and city_g and compact(city_b) == compact(city_g))
    if pin_b and pin_b == pin_g and (same_city or not (city_b and city_g)):
        return _check("ADDRESS_MATCH", "PASS", "The bill is for your GST business address.",
                      "बिल आपके GST वाले व्यावसायिक पते का है।", doc=doc)
    if same_city:
        return _check("ADDRESS_MATCH", "WARN", f"The bill is in {city_b}, but the PIN code differs from your GST address.",
                      f"बिल {city_b} का है, पर उसका PIN कोड आपके GST पते से अलग है।", doc=doc)
    return _check("ADDRESS_MATCH", "FAIL", "The bill's address doesn't match your GST business address.",
                  "बिल का पता आपके GST वाले व्यावसायिक पते से मेल नहीं खाता।",
                  ("Upload a bill for the address on your GST certificate.",
                   "अपने GST प्रमाणपत्र वाले पते का बिल अपलोड करें।"), doc)


def masked_fields(doc: ParsedDoc) -> dict[str, str]:
    """What we show back to the owner after an upload: identifiers masked, nothing we don't need."""
    f = doc.fields
    keep = {
        "gst_certificate": ["gstin", "legal_name", "trade_name", "constitution", "address", "liability_date"],
        "udyam_certificate": ["udyam_number", "enterprise_name", "enterprise_type", "major_activity", "city", "state",
                              "registration_date"],
        "signatory_id": ["name", "designation", "business_name", "id_number", "valid_till"],
        "address_proof": ["holder_name", "supply_address", "bill_date"],
    }[doc.detected_type or doc.doc_type]
    out = {}
    for k in keep:
        v = f.get(k)
        if not v:
            continue
        if k == "gstin":
            v = mask.mask_gstin(v)
        elif k == "udyam_number":
            v = mask.mask_udyam(v)
        elif k == "id_number":
            v = mask.mask_id(v)
        out[k] = v
    return out


def _masked_summary(ok: dict[DocType, ParsedDoc]) -> dict[str, str]:
    """What we keep with the KYC result: masked identifiers and names only (no addresses, no ID details)."""
    out: dict[str, str] = {}
    g = ok.get("gst_certificate")
    if g:
        out.update({"gstin": mask.mask_gstin(g.fields.get("gstin")), "legal_name": g.fields.get("legal_name", ""),
                    "trade_name": g.fields.get("trade_name", ""), "constitution": g.fields.get("constitution", "")})
    u = ok.get("udyam_certificate")
    if u:
        out["udyam_number"] = mask.mask_udyam(u.fields.get("udyam_number"))
    s = ok.get("signatory_id")
    if s:
        out.update({"signatory_name": s.fields.get("name", ""), "signatory_id": mask.mask_id(s.fields.get("id_number")),
                    "id_valid_till": s.fields.get("valid_till", "")})
    b = ok.get("address_proof")
    if b:
        out["bill_date"] = b.fields.get("bill_date", "")
    return {k: v for k, v in out.items() if v}
