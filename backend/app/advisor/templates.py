"""Reply templates in English and Hindi, quick replies, and the number guard for LLM text.

Every question the advisor asks comes from here. The LLM may only rephrase the recommendation intro, and its text
is thrown away if it contains a digit, a rupee sign, "Rs" or a product code: prices live only in the quote card.
"""
from __future__ import annotations

import re
from typing import Optional

from ..contracts import BusinessProfile

_NUMBERS = re.compile(r"\d|₹|\bRs\.?(?![a-z])|\bINR\b|\bP\d\d\b|रु\.|रुपये|रुपए", re.IGNORECASE)


def has_numbers(text: str) -> bool:
    """True if text has any digit (ASCII or Devanagari), ₹, Rs, INR or a product code like P07."""
    return bool(_NUMBERS.search(text))


def safe_text(llm_text: Optional[str], template: str) -> str:
    return llm_text if llm_text and not has_numbers(llm_text) else template


def _biz(p: BusinessProfile, lang: str) -> str:
    if lang == "hi":
        return "आपके व्यवसाय"
    return _lower_first(p.business_type or "business")


# slot -> (en, hi). {biz} is the business type in English, or a neutral phrase in Hindi.
QUESTIONS: dict[str, tuple[str, str]] = {
    "business_type": ("What kind of business do you run? For example a shop, a clinic, an office or a factory.",
                      "आपका व्यवसाय किस तरह का है? जैसे दुकान, क्लिनिक, ऑफ़िस या फ़ैक्टरी।"),
    "city": ("Which city or town is your {biz} in?",
             "आपका व्यवसाय किस शहर या कस्बे में है?"),
    "city_size": ("I don't know {place} yet. Is it a metro, a big city or a small town?",
                  "मुझे {place} के बारे में अभी जानकारी नहीं है। क्या यह मेट्रो है, बड़ा शहर है या छोटा कस्बा?"),
    "employees": ("How many people work at your {biz}, including you? You can type the exact number.",
                  "आपके व्यवसाय में आपको मिलाकर कितने लोग काम करते हैं? सही संख्या भी लिख सकते हैं।"),
    "sites": ("How many locations do you have: shops, branches or offices?",
              "आपकी कितनी जगहें हैं: दुकानें, शाखाएँ या ऑफ़िस?"),
    "has_gstin": ("Is your business registered for GST? If you have the GSTIN handy, you can type it.",
                  "क्या आपका व्यवसाय GST में रजिस्टर्ड है? GSTIN पास हो तो लिख दीजिए।"),
    "current_internet": ("What internet do you use at work today?",
                         "अभी काम पर आप कौन-सा इंटरनेट इस्तेमाल करते हैं?"),
    "needs": ("What do you need help with? Pick any, or type in your own words.",
              "आपको किन चीज़ों में मदद चाहिए? कोई भी चुनिए, या अपने शब्दों में लिखिए।"),
}

QUICK_REPLIES: dict[str, tuple[list[str], list[str]]] = {
    "business_type": (["Kirana / shop", "Clinic", "Office", "Restaurant chain", "Factory"],
                      ["किराना / दुकान", "क्लिनिक", "ऑफ़िस", "रेस्टोरेंट चेन", "फ़ैक्टरी"]),
    "city": (["Mumbai", "Delhi", "Bengaluru", "Pune", "Jaipur"], ["मुंबई", "दिल्ली", "बेंगलुरु", "पुणे", "जयपुर"]),
    "city_size": (["Metro", "Big city", "Small town"], ["मेट्रो", "बड़ा शहर", "छोटा कस्बा"]),
    "employees": (["Just me", "3", "5", "10", "25"], ["सिर्फ़ मैं", "3", "5", "10", "25"]),
    "sites": (["Just one", "2", "3", "5"], ["सिर्फ़ एक", "2", "3", "5"]),
    "has_gstin": (["Yes, I have GST", "No GST"], ["हाँ, GST है", "GST नहीं है"]),
    "current_internet": (["No internet", "Mobile hotspot", "Home broadband", "Business broadband", "Leased line"],
                         ["इंटरनेट नहीं", "मोबाइल हॉटस्पॉट", "घर का ब्रॉडबैंड", "बिज़नेस ब्रॉडबैंड", "लीज़्ड लाइन"]),
}

_NEEDS_QR: dict[str, tuple[list[str], list[str]]] = {
    "micro": (["Fast internet", "Billing & UPI", "CCTV", "WhatsApp for business", "Just internet"],
              ["तेज़ इंटरनेट", "बिलिंग और UPI", "CCTV", "बिज़नेस व्हाट्सऐप", "बस इंटरनेट"]),
    "prof": (["Email", "Data backup", "Virus protection", "Wi-Fi for visitors", "Just internet"],
             ["ईमेल", "डेटा बैकअप", "वायरस से सुरक्षा", "ग्राहकों के लिए वाई-फ़ाई", "बस इंटरनेट"]),
    "multi": (["Billing & UPI", "CCTV", "Backup internet", "SD-WAN", "Toll-free number"],
              ["बिलिंग और UPI", "CCTV", "बैकअप इंटरनेट", "SD-WAN", "टोल-फ़्री नंबर"]),
    "mfg": (["Leased line", "Machine monitoring", "CCTV", "Email", "Fleet tracking"],
            ["लीज़्ड लाइन", "मशीन मॉनिटरिंग", "CCTV", "ईमेल", "गाड़ियों की ट्रैकिंग"]),
}

AFTER_QUOTE_QR = (["Why this?", "Make it cheaper", "Talk to a person"], ["यह क्यों?", "सस्ता करें", "किसी व्यक्ति से बात करें"])


def question(slot: str, p: BusinessProfile, lang: str, place: str = "") -> str:
    en, hi = QUESTIONS[slot]
    return (hi if lang == "hi" else en).format(biz=_biz(p, lang), place=place)


def quick_replies(slot: str, p: BusinessProfile, lang: str) -> list[str]:
    if slot == "needs":
        en, hi = _NEEDS_QR.get(p.segment or "micro", _NEEDS_QR["micro"])
    else:
        en, hi = QUICK_REPLIES.get(slot, ([], []))
    out = list(hi if lang == "hi" else en)
    if slot == "current_internet" and (p.sites or 1) >= 2:
        out.append("हर जगह अलग कनेक्शन" if lang == "hi" else "Different at each site")
    return out


def after_quote_quick_replies(lang: str) -> list[str]:
    return list(AFTER_QUOTE_QR[1] if lang == "hi" else AFTER_QUOTE_QR[0])


def T(lang: str, en: str, hi: str, **kw: object) -> str:
    return (hi if lang == "hi" else en).format(**kw)


# ---------------------------------------------------------------- fixed sentences

def _lower_first(name: str) -> str:
    """'Dental clinic' -> 'dental clinic', but 'CA firm' stays."""
    return name if name[1:2].isupper() else name[:1].lower() + name[1:]


def greeting_ack(p: BusinessProfile, lang: str) -> str:
    if p.business_type and p.city:
        biz = _lower_first(p.business_type)
        article = "An" if biz[:1].lower() in "aeiou" else "A"
        return T(lang, "{article} {biz} in {city}, got it.", "ठीक है, {city} में आपका व्यवसाय।", article=article, biz=biz, city=p.city)
    return T(lang, "Thanks.", "धन्यवाद।")


def intro(p: BusinessProfile, lang: str) -> str:
    return T(lang,
             "Here is a plan that fits your {biz}. The reason for each item is in the card. You can switch extras on or off in the full quote.",
             "यह प्लान आपके व्यवसाय के हिसाब से है। हर चीज़ की वजह कार्ड में लिखी है। पूरे कोटेशन में आप अतिरिक्त सेवाएँ चालू या बंद कर सकते हैं।",
             biz=_biz(p, lang))


def updated(lang: str) -> str:
    return T(lang, "I've updated your plan.", "मैंने आपका प्लान बदल दिया है।")


def accepted(lang: str) -> str:
    return T(lang, "Great. Tap “See full quote” to check the details and confirm your order.",
             "बढ़िया। ब्योरा देखने और ऑर्डर पक्का करने के लिए “पूरा कोटेशन देखें” दबाइए।")


def why_header(lang: str) -> str:
    return T(lang, "Why each item is in your plan:", "आपके प्लान में हर चीज़ क्यों है:")


def cheaper(lang: str) -> str:
    return T(lang, "I've kept only the essentials. You can add extras back in the full quote.",
             "मैंने सिर्फ़ ज़रूरी चीज़ें रखी हैं। पूरे कोटेशन में आप अतिरिक्त सेवाएँ वापस जोड़ सकते हैं।")


def already_minimal(lang: str) -> str:
    return T(lang, "This is already the smallest plan that covers what you asked for.",
             "आपने जो माँगा है, उसके लिए यह पहले से सबसे छोटा प्लान है।")


def over_budget(lang: str) -> str:
    return T(lang, "This plan is above the budget you mentioned. Say “make it cheaper” and I'll keep only the essentials.",
             "यह प्लान आपके बताए बजट से ऊपर है। “सस्ता करें” कहिए, मैं सिर्फ़ ज़रूरी चीज़ें रखूँगा।")


def within_budget(lang: str) -> str:
    return T(lang, "It fits within the budget you mentioned.", "यह आपके बताए बजट में है।")


def handoff(reason_code: str, lang: str) -> str:
    texts = {
        "tier3": ("We don't install in your area yet, so a local Accel partner will call you to see what they can set up.",
                  "आपके इलाके में हम अभी इंस्टॉल नहीं करते, इसलिए Accel के स्थानीय पार्टनर आपको कॉल करके बताएँगे कि क्या हो सकता है।"),
        "asked": ("Sure. A person from Accel will call you back during working hours.",
                  "ज़रूर। Accel का एक व्यक्ति कामकाजी समय में आपको कॉल करेगा।"),
        "not_understood": ("Sorry, I'm not getting this right. A person from Accel will call you to help.",
                           "माफ़ कीजिए, मैं ठीक से समझ नहीं पा रहा। Accel का एक व्यक्ति आपको कॉल करके मदद करेगा।"),
    }
    en, hi = texts.get(reason_code, texts["asked"])
    return hi if lang == "hi" else en


def handoff_done(lang: str) -> str:
    return T(lang, "A person from Accel will call you. You can still look at your plan here.",
             "Accel का एक व्यक्ति आपको कॉल करेगा। आप यहाँ अपना प्लान अब भी देख सकते हैं।")


def not_understood(lang: str) -> str:
    return T(lang, "Sorry, I didn't catch that.", "माफ़ कीजिए, मैं समझ नहीं पाया।")


def gstin_found(status: str, name: str, lang: str) -> str:
    if status == "Active":
        return T(lang, "I found your GST registration ({name}). It is active.",
                 "आपका GST रजिस्ट्रेशन ({name}) मिल गया। यह सक्रिय है।", name=name)
    word_en = "cancelled" if status == "Cancelled" else "suspended"
    word_hi = "रद्द" if status == "Cancelled" else "निलंबित"
    return T(lang,
             "I found your GST registration ({name}), but it is {word} in the GST records. Services that need an active GSTIN, "
             "like WhatsApp Business API, leased lines and business SMS, can't be sold until it is active again. "
             "Everything else is still available.",
             "आपका GST रजिस्ट्रेशन ({name}) मिला, लेकिन GST रिकॉर्ड में यह {word_hi} है। जिन सेवाओं के लिए सक्रिय GSTIN चाहिए, "
             "जैसे WhatsApp Business API, लीज़्ड लाइन और बिज़नेस SMS, वे इसके दोबारा सक्रिय होने तक नहीं मिल सकतीं। "
             "बाकी सब कुछ मिल सकता है।",
             name=name, word=word_en, word_hi=word_hi)


def gstin_invalid(lang: str) -> str:
    return T(lang, "That GSTIN doesn't look right: one of the characters may be mistyped. Please check it, or just tell me if you have GST.",
             "यह GSTIN सही नहीं लग रहा, शायद कोई अक्षर गलत लिखा गया है। कृपया जाँच लीजिए, या बस बताइए कि GST है या नहीं।")


def gstin_unknown(lang: str) -> str:
    return T(lang, "Thanks. I couldn't find that GSTIN in the records yet; we'll check it with your documents later.",
             "धन्यवाद। यह GSTIN अभी रिकॉर्ड में नहीं मिला; दस्तावेज़ों के साथ हम इसे बाद में जाँच लेंगे।")


def product_unavailable_intro(lang: str) -> str:
    return T(lang, "One thing you asked for isn't possible:", "आपने जो माँगा, उसमें से एक चीज़ नहीं मिल सकती:")


def bad_number(lang: str) -> str:
    return T(lang, "That number doesn't look right. Please count yourself too, and every shop or branch you have.",
             "यह संख्या सही नहीं लग रही। कृपया अपने को भी गिनिए, और अपनी हर दुकान या शाखा भी।")


def assumed_internet(lang: str, mixed: bool) -> str:
    if mixed:
        return T(lang, "I'll take it that each of your sites has its own connection today.",
                 "मैं मान रहा हूँ कि अभी आपकी हर जगह का अपना अलग कनेक्शन है।")
    return T(lang, "I'll take it that you need a new connection.", "मैं मान रहा हूँ कि आपको नया कनेक्शन चाहिए।")


def kept_requested(lang: str) -> str:
    return T(lang, "Everything left in your plan is something you asked for. Tell me what to drop, for example “remove CCTV”.",
             "आपके प्लान में अब वही चीज़ें हैं जो आपने माँगी थीं। बताइए क्या हटाना है, जैसे “CCTV हटा दो”।")


def unsupported(items: list[str], lang: str) -> str:
    names = ", ".join(items)
    return T(lang, "Accel Business doesn't offer {names}, so I've left that out.",
             "Accel Business {names} नहीं देता, इसलिए मैंने उसे शामिल नहीं किया।", names=names)


def plan_changes(added: list[str], removed: list[str], changed: list[str], lang: str) -> str:
    """'Done: added X. Removed Y. Z is now 4.' Names are product names; changed entries already read 'Name: ×4'."""
    lines = []
    if added:
        lines.append(T(lang, "Added: {x}.", "जोड़ा: {x}।", x=", ".join(added)))
    if removed:
        lines.append(T(lang, "Removed: {x}.", "हटाया: {x}।", x=", ".join(removed)))
    if changed:
        lines.append(T(lang, "Changed: {x}.", "बदला: {x}।", x=", ".join(changed)))
    return T(lang, "Done. ", "हो गया। ") + " ".join(lines)


def plan_moved(city: str, lang: str) -> str:
    return T(lang, "I've redone the plan for {city}.", "मैंने {city} के लिए प्लान फिर से बनाया है।", city=city)


def no_change(lang: str) -> str:
    return T(lang, "Your plan stays the same.", "आपका प्लान वैसा ही है।")


def not_in_plan(names: list[str], lang: str) -> str:
    return T(lang, "{x} isn't in your plan, so nothing changed.", "{x} आपके प्लान में नहीं है, इसलिए कुछ नहीं बदला।",
             x=", ".join(names))


def price_line(name: str, monthly: int, unit_price: int, qty: int, setup: int, in_plan: bool, lang: str) -> str:
    """A price answer from the rules engine (never from the LLM)."""
    m, u, s = f"₹{monthly:,}", f"₹{unit_price:,}", f"₹{setup:,}"
    if qty > 1:
        base = T(lang, "{name}: {m} a month ({u} each × {q})", "{name}: {m} महीना ({u} प्रति यूनिट × {q})",
                 name=name, m=m, u=u, q=qty)
    else:
        base = T(lang, "{name}: {m} a month", "{name}: {m} महीना", name=name, m=m)
    if setup:
        base += T(lang, ", plus {s} one-time setup", ", साथ में {s} एक बार का सेटअप", s=s)
    base += T(lang, " (+18% GST).", " (+18% GST)।")
    if not in_plan:
        base += T(lang, " It's not in your plan; say “add it” if you want it.",
                  " यह आपके प्लान में नहीं है; चाहिए तो “जोड़ दो” कहिए।")
    return base


def price_unknown(lang: str) -> str:
    return T(lang, "Every price is in the plan card. Tell me which service you want the price for.",
             "हर कीमत प्लान कार्ड में है। बताइए किस सेवा की कीमत जाननी है।")
