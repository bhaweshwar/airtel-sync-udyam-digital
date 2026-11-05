"""Deterministic fallback parser for English, Hindi (Devanagari) and Hinglish.

Used whenever no LLM answered (no key, timeout, invalid JSON, 429). Also run on every turn to fill what the LLM
missed and to catch things that must never depend on a model: typed GSTINs, product names the owner asks for,
and requests for a person.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .. import data
from ..common import gstin as gst

INTENTS = ("answer", "accept", "change", "ask_why", "handoff", "other")
NEED_CODES = (
    "internet", "backup", "payments_pos", "whatsapp", "sms", "email", "cloud_backup", "website",
    "security", "wifi", "cctv", "telephony", "tollfree", "iot", "fleet", "static_ip", "sdwan",
)
INTERNET_CODES = ("none", "mobile_hotspot", "home_broadband", "business_broadband", "mixed", "leased_line")


@dataclass
class Extraction:
    """What one owner message told us. Empty fields mean "not mentioned"."""
    business_type: Optional[str] = None
    segment: Optional[str] = None
    city: Optional[str] = None          # canonical name of a served city
    city_tier: Optional[int] = None
    state: Optional[str] = None
    unknown_city: Optional[str] = None  # a place we don't have in the city list
    city_size: Optional[str] = None     # metro / big_city / small_town (answer to the tier question)
    employees: Optional[int] = None
    sites: Optional[int] = None
    has_gstin: Optional[bool] = None
    gstin: Optional[str] = None
    current_internet: Optional[str] = None
    needs_add: list[str] = field(default_factory=list)
    needs_remove: list[str] = field(default_factory=list)
    products_asked: list[str] = field(default_factory=list)   # product ids the owner named ("Fibre 1G")
    products_removed: list[str] = field(default_factory=list)
    budget_monthly_inr: Optional[int] = None
    cheaper: bool = False
    intent: str = "other"
    language: Optional[str] = None

    def understood(self) -> bool:
        """True if the message gave us anything we can use."""
        return any([
            self.business_type, self.city, self.unknown_city, self.city_size, self.employees, self.sites,
            self.has_gstin is not None, self.gstin, self.current_internet, self.needs_add, self.needs_remove,
            self.products_asked, self.products_removed, self.budget_monthly_inr, self.cheaper,
        ]) or self.intent in ("accept", "ask_why", "handoff", "change")


# ---------------------------------------------------------------- numbers

_WORD_NUMBERS: dict[str, int] = {
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "twenty five": 25, "thirty": 30, "forty": 40,
    "fifty": 50, "hundred": 100, "a couple of": 2, "a dozen": 12, "single": 1,
    # Hinglish
    "ek": 1, "do": 2, "teen": 3, "tin": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "chhah": 6,
    "che": 6, "saat": 7, "sat": 7, "aath": 8, "ath": 8, "nau": 9, "das": 10, "gyarah": 11, "barah": 12, "baarah": 12,
    "pandrah": 15, "bees": 20, "bis": 20, "pachees": 25, "pachchis": 25, "tees": 30, "chalis": 40, "chaalis": 40,
    "pachas": 50, "pachaas": 50, "sau": 100,
    # Devanagari
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6, "छः": 6, "छे": 6, "सात": 7, "आठ": 8,
    "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "पंद्रह": 15, "बीस": 20, "पच्चीस": 25, "तीस": 30, "चालीस": 40,
    "पचास": 50, "सौ": 100,
}
# "do" and "sat" are also ordinary words; only trust them next to a counting noun (see _count_before).
_AMBIGUOUS_WORDS = {"do", "sat", "tin", "che", "ath", "single"}
_NUM_WORD_RE = "|".join(sorted((re.escape(w) for w in _WORD_NUMBERS), key=len, reverse=True))
_NUM = rf"(\d[\d,]*|{_NUM_WORD_RE})"


def _to_int(token: str) -> Optional[int]:
    token = token.strip().lower()
    if token in _WORD_NUMBERS:
        return _WORD_NUMBERS[token]
    digits = token.replace(",", "")
    if digits.isdigit():
        try:
            return int(digits)  # int() also reads Devanagari digits
        except ValueError:
            return None
    return None


def _count_before(text: str, nouns: str) -> Optional[int]:
    """'3 staff', 'teen log', 'तीन कर्मचारी', 'staff of 12', 'employees: 12'."""
    m = re.search(rf"(?<![\w]){_NUM}\s*(?:\+\s*)?(?:{nouns})(?![\w])", text)
    if m:
        return _to_int(m.group(1))
    m = re.search(rf"(?<![\w])(?:{nouns})\s*(?:of|are|is|hai|hain|है|हैं|:|-|=)?\s*{_NUM}(?![\w])", text)
    if m and m.group(1).lower() not in _AMBIGUOUS_WORDS:
        return _to_int(m.group(1))
    return None


def _bare_number(text: str) -> Optional[int]:
    """A reply that is just a number: '3', 'teen', '20+', 'just me', 'only one'."""
    t = text.strip().lower().rstrip(".!+ ")
    if re.fullmatch(r"(just|only)\s+(me|myself)|sirf\s+main|bas\s+main|केवल\s+मैं|सिर्फ़?\s+मैं|akela|अकेला|अकेले", t):
        return 1
    t = re.sub(r"^(about|around|approx\.?|roughly|lagbhag|लगभग|करीब|kareeb|just|only|sirf|bas|सिर्फ़?|केवल)\s+", "", t)
    t = re.sub(r"\s+(hi|ही|people|log|लोग|hai|hain|है|हैं)$", "", t)
    m = re.fullmatch(r"(\d+)\s*[-–to]+\s*(\d+)", t)  # a range: take the upper end
    if m:
        return int(m.group(2))
    m = re.fullmatch(r"(?:more than|over|above|zyada|ज़्यादा|से ज़्यादा)?\s*" + _NUM + r"\s*(?:se zyada|से ज़्यादा|or more|plus)?", t)
    if m:
        return _to_int(m.group(1))
    return None


_EMPLOYEE_NOUNS = (r"staff|people|persons|employees?|workers?|members?|log|logon|aadmi|karmchari|kaamgar|"
                   r"लोग|लोगों|कर्मचारी|कर्मचारियों|आदमी|कामगार|स्टाफ़?")
_SITE_NOUNS = (r"sites?|branch(?:es)?|outlets?|locations?|shops|stores|clinics|offices|restaurants|factories|units|"
               r"godowns?|warehouses?|jagah|jagahon|branches|dukaane|dukanein|शाखा(?:एँ|एं|ओं)?|ब्रांच|जगह(?:ों)?|"
               r"आउटलेट|दुकानें|दुकानों")


# ---------------------------------------------------------------- cities

_CITY_ALIASES = {
    "bangalore": "bengaluru", "bengalooru": "bengaluru", "bombay": "mumbai", "calcutta": "kolkata", "madras": "chennai",
    "vizag": "visakhapatnam", "mysore": "mysuru", "baroda": "vadodara", "new delhi": "delhi", "cochin": "kochi",
    "poona": "pune",
    "मुंबई": "mumbai", "मुम्बई": "mumbai", "दिल्ली": "delhi", "पुणे": "pune", "कोच्चि": "kochi", "कोचि": "kochi",
    "लुधियाना": "ludhiana", "जयपुर": "jaipur", "लखनऊ": "lucknow", "पटना": "patna", "इंदौर": "indore", "भोपाल": "bhopal",
    "नागपुर": "nagpur", "सूरत": "surat", "अहमदाबाद": "ahmedabad", "बेंगलुरु": "bengaluru", "बैंगलोर": "bengaluru",
    "हैदराबाद": "hyderabad", "चेन्नई": "chennai", "कोलकाता": "kolkata", "नासिक": "nashik", "वडोदरा": "vadodara",
    "कोयंबटूर": "coimbatore", "मैसूर": "mysuru", "मैसूरु": "mysuru", "विशाखापत्तनम": "visakhapatnam",
}

_NOT_PLACES = {
    "english", "hindi", "hinglish", "a", "the", "my", "our", "india", "business", "town", "city", "village",
    "total", "all", "one", "two", "three", "future", "addition", "case", "cash", "budget",
}


def lookup_city(name: str) -> Optional[dict]:
    """Served city by name or alias, else None."""
    key = name.strip().lower()
    key = _CITY_ALIASES.get(key, key)
    return data.city_tiers().get(key)


def _find_city(text_lower: str) -> Optional[dict]:
    keys = list(data.city_tiers().keys()) + list(_CITY_ALIASES.keys())
    for key in sorted(keys, key=len, reverse=True):
        if re.search(rf"(?<![\w]){re.escape(key)}(?![\w])", text_lower):
            return lookup_city(key)
    return None


def _find_unknown_place(text: str) -> Optional[str]:
    """'my shop is in Rampur', 'from Kasauli', 'Rampur mein', 'रामपुर में'."""
    m = re.search(r"\b(?:in|at|from|near)\s+([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})?)", text)
    if not m:
        m = re.search(r"\b([A-Z][a-zA-Z]{2,})\s+(?:mein|se)\b", text)
    if not m:
        m = re.search(r"([ऀ-ॿ]{3,})\s+(?:में|से)(?:\s|$|[,.।])", text)
    if m and m.group(1).lower() not in _NOT_PLACES:
        return m.group(1).strip()
    return None


def _city_size(text_lower: str) -> Optional[str]:
    if re.search(r"\bmetro\b|मेट्रो|mahanagar|महानगर", text_lower):
        return "metro"
    if re.search(r"small town|chhota|chota|छोटा|village|gaon|gaanv|गाँव|गांव|kasba|qasba|कस्बा|tehsil|तहसील", text_lower):
        return "small_town"
    if re.search(r"big city|large city|bada shahar|bada sheher|bada shehar|बड़ा शहर|बडा शहर|\bcity\b|शहर", text_lower):
        return "big_city"
    return None


# ---------------------------------------------------------------- business types

# (pattern, canonical business type as in the leads data). Checked in order: specific before generic.
_BUSINESS_PATTERNS: list[tuple[str, str]] = [
    (r"restaurant chain|chain of restaurants|restaurants|रेस्टोरेंट चेन|रेस्टोरेंट्स", "Restaurant chain"),
    (r"bakery chain|bakeries|बेकरी चेन", "Bakery chain"),
    (r"pharmacy chain|chemist chain|medical stores|फार्मेसी चेन", "Pharmacy chain"),
    (r"gym chain|gyms|जिम चेन", "Gym chain"),
    (r"apparel (?:retail )?chain|clothing chain|garment (?:store )?chain|कपड़ों की चेन", "Apparel retail chain"),
    (r"electronics (?:retail )?chain|electronics stores|इलेक्ट्रॉनिक्स चेन", "Electronics retail chain"),
    (r"pre-?school chain|play ?schools|प्ले ?स्कूल", "Pre-school chain"),
    (r"hotels|hotel group|budget hotel|lodges|होटल", "Budget hotel group"),
    (r"dental|dentist|teeth|daant|दाँत|दांत|डेंटल|डेंटिस्ट", "Dental clinic"),
    (r"diagnostic|pathology|path lab|\blab\b|लैब|पैथोलॉजी", "Diagnostic lab"),
    (r"physio|फिजियो", "Physiotherapy clinic"),
    (r"\bca firm\b|chartered accountant|\bca office\b|accountancy|सीए फर्म|चार्टर्ड अकाउंटेंट", "CA firm"),
    (r"law (?:office|firm)|lawyer|advocate|legal|vakil|वकील|लॉ फर्म", "Law office"),
    (r"architect|आर्किटेक्ट", "Architecture studio"),
    (r"real estate|property dealer|broker|प्रॉपर्टी|रियल एस्टेट", "Real estate agency"),
    (r"travel agen|tours? and travels|ट्रैवल", "Travel agency"),
    (r"insurance|बीमा|इंश्योरेंस", "Insurance agency"),
    (r"coaching|tuition|classes|institute|कोचिंग|ट्यूशन", "Coaching centre"),
    (r"auto[- ]?parts|automobile parts|spare parts|ऑटो पार्ट्स", "Auto-parts unit"),
    (r"textile|weaving|power ?loom|कपड़ा मिल|टेक्सटाइल", "Textile unit"),
    (r"plastic|moulding|molding|प्लास्टिक", "Plastic moulding unit"),
    (r"packaging|पैकेजिंग", "Packaging unit"),
    (r"food processing|namkeen factory|फूड प्रोसेसिंग", "Food processing unit"),
    (r"furniture|carpent|फर्नीचर", "Furniture workshop"),
    (r"printing|press\b|प्रिंटिंग", "Printing press"),
    (r"kirana|grocery|general store|provision store|किराना|किराने", "Kirana store"),
    (r"bakery|बेकरी", "Bakery"),
    (r"sweet|mithai|halwai|मिठाई|हलवाई", "Sweet shop"),
    (r"pharmacy|chemist|medical store|dawai|dawa|दवा|फार्मेसी|मेडिकल स्टोर", "Pharmacy"),
    (r"salon|parlou?r|barber|सैलून|पार्लर", "Salon"),
    (r"boutique|बुटीक", "Boutique"),
    (r"optician|optical|spectacles|chashma|चश्मा|ऑप्टिकल", "Optician"),
    (r"stationery|स्टेशनरी", "Stationery shop"),
    (r"hardware|हार्डवेयर", "Hardware store"),
    (r"mobile (?:repair|shop)|phone repair|मोबाइल रिपेयर|मोबाइल की दुकान", "Mobile repair shop"),
    (r"restaurant|cafe|café|dhaba|eatery|रेस्टोरेंट|ढाबा|कैफ़े", "Restaurant"),
    (r"\bgym\b|fitness|जिम", "Gym"),
    (r"\bhotel\b", "Budget hotel group"),
]
# Generic words: give a segment even when the exact type is unknown.
_GENERIC_PATTERNS: list[tuple[str, str, str]] = [
    (r"factory|manufactur|workshop|\bunit\b|plant|karkhana|फैक्ट्री|कारखाना|उत्पादन", "Manufacturing unit", "mfg"),
    (r"clinic|doctor|hospital|nursing|क्लिनिक|डॉक्टर|अस्पताल", "Clinic", "prof"),
    (r"office|consult|agency|firm|studio|ऑफ़िस|ऑफिस|दफ़्तर|दफ्तर", "Office", "prof"),
    (r"shop|store|dukaan|dukan|दुकान|स्टोर", "Shop", "micro"),
]
_MICRO_TYPES_WITHOUT_ROW = {"restaurant": "micro", "gym": "micro"}


def canonical_business(text: str) -> tuple[Optional[str], Optional[str]]:
    """Free text -> (business type, segment). Works on owner messages and on an LLM's business_type string."""
    t = text.lower()
    segments = data.business_type_segments()
    if t.strip() in segments:
        name = t.strip()
        return name[:1].upper() + name[1:], segments[name]
    for pattern, name in _BUSINESS_PATTERNS:
        if re.search(pattern, t):
            seg = segments.get(name.lower()) or _MICRO_TYPES_WITHOUT_ROW.get(name.lower(), "micro")
            return name, seg
    for pattern, name, seg in _GENERIC_PATTERNS:
        if re.search(pattern, t):
            return name, seg
    return None, None


# ---------------------------------------------------------------- needs and products

_NEED_PATTERNS: list[tuple[str, str]] = [
    (r"cctv|camera|surveillance|सीसीटीवी|कैमरा|कैमरे|security cam", "cctv"),
    (r"billing|\bpos\b|\bupi\b|card payment|card machine|payments?\b|invoic|बिलिंग|बिल बनाने|पेमेंट|भुगतान", "payments_pos"),
    (r"whats ?app|व्हाट्सऐप|व्हाट्सएप|वॉट्सऐप|वॉट्सएप|व्हाट्सअप", "whatsapp"),
    (r"e-?mails?\b|\bmail id|ईमेल|ई-मेल", "email"),
    (r"failover|backup (?:internet|line|link|connection|sim)|internet backup|4g backup|5g backup|second line|"
     r"never go(?:es)? down|बैकअप इंटरनेट", "backup"),
    (r"cloud backup|data backup|backup of (?:data|files|records)|files? backup|backup|बैकअप", "cloud_backup"),
    (r"antivirus|anti-virus|virus|ransomware|endpoint|cyber|एंटीवायरस|वायरस", "security"),
    (r"firewall|फ़ायरवॉल|फायरवॉल", "security"),
    (r"wi-?fi|wireless for customers|guest network|वाई-?फ़ाई|वाईफाई|वाई फाई", "wifi"),
    (r"website|web site|online presence|domain|वेबसाइट", "website"),
    (r"\bsms\b|text messages|एसएमएस", "sms"),
    (r"toll[- ]?free|1800|टोल[- ]?फ़्री|टोल[- ]?फ्री", "tollfree"),
    (r"\bivr\b|telephony|call cent(?:er|re)|phone lines|landline|call recording|\bsip\b|टेलीफोनी|कॉल सेंटर", "telephony"),
    (r"machine monitoring|\biot\b|sensors?|machine uptime|मशीन", "iot"),
    (r"fleet|vehicles?|gps|delivery vans?|trucks?|गाड़ियाँ|गाड़ियों|वाहन", "fleet"),
    (r"static ip|fixed ip|स्टैटिक आईपी", "static_ip"),
    (r"sd-?wan", "sdwan"),
    (r"internet|broadband|fibre|fiber|net connection|wifi chahiye|इंटरनेट|ब्रॉडबैंड|फ़ाइबर|फाइबर", "internet"),
]

# Products an owner may ask for by name. Checked in order, so specific names come first.
_PRODUCT_PATTERNS: list[tuple[str, str]] = [
    (r"\b1\s?g(?:bps)?\b|1000\s?mbps|gigabit|fib(?:re|er) 1g", "P03"),
    (r"leased line 100|100\s?mbps leased", "P06"),
    (r"leased[- ]?line|dedicated (?:internet|line)|\bill\b|लीज़्ड लाइन|लीज्ड लाइन", "P05"),
    (r"air ?fib(?:re|er)|5g fwa|5g broadband", "P04"),
    (r"fib(?:re|er) 300|300\s?mbps", "P02"),
    (r"fib(?:re|er) 100|100\s?mbps", "P01"),
    (r"whats ?app (?:business )?api|whatsapp business|व्हाट्सऐप बिज़नेस|व्हाट्सऐप एपीआई", "P15"),
    (r"sd-?wan", "P10"),
    (r"static ip|fixed ip", "P11"),
    (r"firewall|फ़ायरवॉल|फायरवॉल", "P21"),
    (r"toll[- ]?free", "P13"),
]

# Which product a need points at, so "remove CCTV" can take P23 out of the quote. Same map as the engine's add-ons.
NEED_PRODUCTS = {
    "cctv": "P23", "payments_pos": "P19", "whatsapp": "P15", "email": "P16", "backup": "P09", "security": "P20",
    "wifi": "P22", "website": "P18", "cloud_backup": "P17", "telephony": "P12", "tollfree": "P13", "sms": "P14",
    "static_ip": "P11", "iot": "P24", "fleet": "P25", "sdwan": "P10",
}

PRODUCT_NEEDS = {pid: need for need, pid in NEED_PRODUCTS.items()}

_NEGATION = (r"\b(?:remove|delete|drop|skip|cancel|without|don'?t|dont|do not|no need|not needed|no more|nahi|nahin|"
             r"mat|hatao|hata do|hata dijiye|nikal|band karo)\b|नहीं|नही|मत|हटा|हटाओ|हटाएँ|हटाएं|निकाल|बिना|^no\b|\bno\s")
_CLAUSE_SPLIT = r"[,.;!?।]|\bbut\b|\band\b|\bbhi\b|\baur\b|\blekin\b|\bpar\b|और|लेकिन|पर\b|भी"


def _needs(text_lower: str) -> tuple[list[str], list[str], list[str], list[str]]:
    add, remove, p_add, p_remove = [], [], [], []
    for clause in re.split(_CLAUSE_SPLIT, text_lower):
        clause = clause.strip()
        if not clause:
            continue
        negative = bool(re.search(_NEGATION, clause))
        # "no internet" / "internet nahi hai" describes the current connection, not a need to remove.
        if negative and re.fullmatch(r".*(?:internet|इंटरनेट).*", clause) and not re.search(r"remove|hata|हटा|drop", clause):
            negative_internet_only = True
        else:
            negative_internet_only = False
        consumed = clause
        for pattern, code in _PRODUCT_PATTERNS:
            if re.search(pattern, consumed):
                (p_remove if negative else p_add).append(code)
                consumed = re.sub(pattern, " ", consumed)
        for pattern, code in _NEED_PATTERNS:
            if re.search(pattern, consumed):
                consumed = re.sub(pattern, " ", consumed)
                if code == "internet" and negative_internet_only:
                    continue
                if negative:
                    remove.append(code)
                elif code not in add:
                    add.append(code)
    return add, [c for c in dict.fromkeys(remove)], list(dict.fromkeys(p_add)), list(dict.fromkeys(p_remove))


def _current_internet(text_lower: str, pending: Optional[str]) -> Optional[str]:
    t = text_lower
    if re.search(r"no internet|internet nahi|internet nahin|koi internet nahi|इंटरनेट नहीं|कोई इंटरनेट नहीं|"
                 r"don'?t have (?:any )?internet|without internet", t):
        return "none"
    if re.search(r"hotspot|mobile data|phone (?:ka|se) (?:net|internet|data)|phone se chalate|jio|हॉटस्पॉट|मोबाइल डेटा|"
                 r"फ़ोन से|फोन से|dongle", t):
        return "mobile_hotspot"
    if re.search(r"home (?:broadband|wifi|wi-fi|connection|internet)|ghar ka|घर का|घर वाला", t):
        return "home_broadband"
    if re.search(r"different (?:per|in each|at each) (?:site|branch)|mixed|har (?:jagah|branch) alag|अलग-अलग", t):
        return "mixed"
    if pending == "current_internet":
        if re.fullmatch(r"\s*(?:none|nothing|no|nahi|nahin|kuch nahi|कुछ नहीं|नहीं)\s*", t):
            return "none"
        if re.search(r"leased|लीज़्ड|लीज्ड", t):
            return "leased_line"
        if re.search(r"business broadband|broadband|fib(?:re|er)|wifi|wi-fi|ब्रॉडबैंड|फ़ाइबर|फाइबर|वाईफाई", t):
            return "business_broadband"
    elif re.search(r"(?:we|currently|already|abhi|filhal) (?:use|have|using|hai)?\s*(?:a |an )?(?:business )?broadband|"
                   r"business broadband", t):
        return "business_broadband"
    return None


# ---------------------------------------------------------------- yes / no, GST, budget, intent, language

_YES = r"\s*(?:yes|yeah|yep|haan|haa|ha|han|ji|ji haan|haan ji|hai|हाँ|हां|जी|जी हाँ|हाँ जी|है|sure|of course|y)\s*[.!]*\s*"
_NO = r"\s*(?:no|nope|nahi|nahin|nai|na|नहीं|नही|ना|n)\s*[.!]*\s*"
_GSTIN_RE = re.compile(r"(?<![0-9A-Za-z])([0-9]{2}\s?[A-Za-z]{5}\s?[0-9]{4}\s?[A-Za-z][0-9A-Za-z][Zz][0-9A-Za-z])(?![0-9A-Za-z])")


def find_gstin(text: str) -> Optional[str]:
    m = _GSTIN_RE.search(text)
    return gst.normalize(m.group(1)) if m else None


def _has_gstin(text_lower: str, pending: Optional[str]) -> Optional[bool]:
    t = text_lower
    gst_word = r"(?:gst|gstin|जीएसटी)"
    if re.search(rf"(?:no|not|without|don'?t have|do not have|bina|बिना)\s+(?:a\s+|any\s+)?(?:registered\s+)?(?:for\s+)?{gst_word}|"
                 rf"{gst_word}\s*(?:number\s*)?(?:nahi|nahin|nai|na|नहीं|नही|is not|not)|not (?:gst )?registered|"
                 rf"unregistered", t):
        return False
    if re.search(rf"{gst_word}\s*(?:number\s*)?(?:hai|he|है|registered|wala|वाला|yes|हाँ|haan|holder)|"
                 rf"(?:have|got|with|registered under|registered for)\s+(?:a\s+)?{gst_word}|{gst_word} registered", t):
        return True
    if pending == "has_gstin":
        if re.fullmatch(_YES, t):
            return True
        if re.fullmatch(_NO, t):
            return False
    return None


def _budget(text_lower: str) -> Optional[int]:
    m = re.search(r"(?:₹|rs\.?|inr|rupees?|rupaye|रुपये|रुपए|budget|बजट|under|within|upto|up to|below|max|tak|तक)\s*(?:of|is|hai|है|:)?\s*"
                  r"(\d[\d,]*)\s*(k\b)?", text_lower)
    if not m:
        m = re.search(r"(\d[\d,]*)\s*(k\b)?\s*(?:rupees?|rupaye|रुपये|रुपए|rs\b|₹|/-|a month budget|budget|tak|तक|"
                      r"per month max|maximum)", text_lower)
    if not m:
        return None
    value = int(m.group(1).replace(",", ""))
    return value * 1000 if m.group(2) else value


def _intent(text_lower: str) -> Optional[str]:
    t = text_lower
    if re.search(r"talk to (?:a |some)?(?:person|human|someone|agent|executive|representative|people)|speak to (?:a |some)?"
                 r"(?:person|human|someone|agent)|real person|call me|callback|call back|"
                 r"insaan|insan|kisi (?:se|aadmi)|kisi vyakti|banda|इंसान|इन्सान|व्यक्ति से|किसी से बात|कॉल कर|फ़ोन कर|"
                 r"human|customer care|agent", t):
        return "handoff"
    if re.search(r"\bwhy\b|kyun|kyon|kyu\b|क्यों|क्यूँ|explain|samjhao|समझा", t):
        return "ask_why"
    if re.fullmatch(r"\s*(?:ok(?:ay)?|okay|fine|great|perfect|looks good|sounds good|go ahead|done|confirm|book it|"
                    r"accept|theek hai|thik hai|sahi hai|chalega|ठीक है|सही है|चलेगा|बढ़िया|हाँ ठीक है|yes,? (?:go ahead|book))"
                    r"[\s.!]*", t):
        return "accept"
    return None


_HINGLISH = re.compile(r"\b(?:hai|hain|nahi|nahin|mera|meri|mere|mujhe|hum|humare|hamara|kitne|kitna|log|dukaan|dukan|"
                       r"chahiye|chaiye|karna|karni|baat|kya|aur|bhi|wala|wali|mein|haan|teen|paanch|sirf|bas|abhi|"
                       r"insaan|kisi|lekin|thoda|sasta)\b")


def detect_language(text: str) -> Optional[str]:
    """'hi' for Devanagari or Hinglish, 'en' for clear English, None when the message is too short to tell."""
    text = _GSTIN_RE.sub(" ", text)
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    words = re.findall(r"[a-zA-Z]+", text.lower())
    markers = len(_HINGLISH.findall(text.lower()))
    if words and (markers >= 2 or markers / len(words) >= 0.25):
        return "hi"
    if len(words) >= 3:
        return "en"
    return None


# ---------------------------------------------------------------- entry point

def parse(text: str, pending: Optional[str] = None) -> Extraction:
    """Parse one owner message. `pending` is the slot the advisor just asked about, to read bare answers like '3'."""
    out = Extraction()
    lower = text.lower()
    out.language = detect_language(text)

    g = find_gstin(text)
    if g:
        out.gstin = g
        out.has_gstin = True
        lower = lower.replace(g.lower(), " ")
        text = re.sub(re.escape(g), " ", text, flags=re.I)

    out.budget_monthly_inr = _budget(lower)
    no_money = re.sub(r"(?:₹|rs\.?|inr)\s*\d[\d,]*|\d[\d,]*\s*(?:rupees?|rupaye|रुपये|रुपए|rs\b|/-)|budget\s*(?:of|is)?\s*\d[\d,]*",
                      " ", lower)

    out.employees = _count_before(no_money, _EMPLOYEE_NOUNS)
    out.sites = _count_before(no_money, _SITE_NOUNS)
    if out.sites is None and re.search(r"single (?:site|shop|location|branch|outlet|office)|"
                                       r"(?:one|1) (?:shop|location|branch|outlet|office|clinic|site|store|factory|unit|place)\b|"
                                       r"only one (?:site|shop|place)|ek hi (?:jagah|dukaan|dukan|branch)|एक ही (?:जगह|दुकान)",
                                       no_money):
        out.sites = 1
    if pending in ("employees", "sites") and out.employees is None and out.sites is None:
        n = _bare_number(no_money)
        if n is not None and n >= 1:
            setattr(out, pending, n)
        elif pending == "sites" and re.fullmatch(r"\s*(?:just one|only one|one|single|ek|एक|bas ek|सिर्फ़ एक|ek hi)\s*", no_money):
            out.sites = 1

    out.has_gstin = out.has_gstin or _has_gstin(lower, pending)
    city = _find_city(lower)
    if city:
        out.city, out.city_tier, out.state = str(city["city"]), int(city["tier"]), str(city["state"])  # type: ignore[call-overload]
    out.city_size = _city_size(lower) if pending == "city_size" else None
    if not city and not out.city_size:
        place = _find_unknown_place(text)
        if not place and pending == "city":
            cleaned = re.sub(r"^(?:in|at|from|it'?s|it is|we are in|i am in|main|hum)\s+", "", text.strip(), flags=re.I)
            cleaned = re.sub(r"\s+(?:mein|me|में|से|city|शहर)$", "", cleaned, flags=re.I).strip(" .!")
            if 2 < len(cleaned) <= 30 and not re.search(r"\d", cleaned) and len(cleaned.split()) <= 3:
                place = cleaned
        out.unknown_city = place

    btype, seg = canonical_business(lower)
    if btype:
        out.business_type, out.segment = btype, seg

    out.current_internet = _current_internet(lower, pending)
    out.needs_add, out.needs_remove, out.products_asked, out.products_removed = _needs(lower)
    if out.current_internet and "internet" in out.needs_add and not re.search(r"need|want|chahiye|चाहिए|looking for|just internet|only internet|bas internet|sirf internet", lower):
        out.needs_add.remove("internet")  # "we use home broadband" describes today's connection, not a need
    for pid in out.products_asked:
        need = PRODUCT_NEEDS.get(pid)
        if need and need not in out.needs_add:
            out.needs_add.append(need)
    if out.current_internet == "leased_line" and "P05" in out.products_asked and pending == "current_internet":
        out.products_asked.remove("P05")
    if pending == "needs" and not out.needs_add and re.search(r"just internet|only internet|bas internet|sirf internet|"
                                                              r"nothing else|kuch nahi|बस इंटरनेट|सिर्फ़ इंटरनेट|कुछ नहीं", lower):
        out.needs_add = ["internet"]
    out.cheaper = bool(re.search(r"cheaper|cheap|lower (?:the )?price|too (?:costly|expensive)|reduce|sasta|sasti|kam (?:karo|kijiye)|"
                                 r"सस्ता|सस्ती|कम करो|कम कीजिए|महँगा|महंगा|mehenga|mehnga", lower))

    intent = _intent(lower)
    if intent:
        out.intent = intent
    elif out.needs_remove or out.products_removed or out.cheaper or out.budget_monthly_inr:
        out.intent = "change"
    elif out.understood():
        out.intent = "answer"
    return out
