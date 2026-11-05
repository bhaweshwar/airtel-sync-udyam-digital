"""One-line reasons for each line item (EN + HI), citing the owner's profile, plus quote notices."""
from __future__ import annotations

from ..common.i18n_server import lt
from ..contracts import BusinessProfile, LocalText, Product
from . import rules

_INTERNET_EN = {"none": "no internet", "mobile_hotspot": "a mobile hotspot"}
_INTERNET_HI = {"none": "बिना इंटरनेट", "mobile_hotspot": "मोबाइल हॉटस्पॉट"}


def inr(amount: int) -> str:
    """₹ with Indian digit grouping: 123456 -> ₹1,23,456."""
    s = str(abs(amount))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-₹" if amount < 0 else "₹") + s


def reason(p: Product, qty: int, profile: BusinessProfile) -> LocalText:
    emp, n = rules.employees(profile), rules.sites(profile)
    at_en = "your premises" if n == 1 else f"each of your {n} sites"
    at_hi = "आपकी जगह पर" if n == 1 else f"आपकी सभी {n} जगहों पर"
    s_en = "1 site" if n == 1 else f"{n} sites"
    q_en = "s" if qty != 1 else ""
    staff = f"{emp} staff"
    cur_en = _INTERNET_EN.get(profile.current_internet or "", "a patchy connection")
    cur_hi = _INTERNET_HI.get(profile.current_internet or "", "कमज़ोर कनेक्शन")
    r = {
        "P01": (f"Fibre at {at_en}: 100 Mbps is plenty for billing, UPI and {staff}.",
                f"{at_hi} फ़ाइबर: बिलिंग, UPI और {emp} लोगों के लिए 100 Mbps काफ़ी है।"),
        "P02": (f"300 Mbps fibre at {at_en}, so {staff} can work and video-call at the same time.",
                f"{at_hi} 300 Mbps फ़ाइबर, ताकि {emp} लोग एक साथ काम और वीडियो कॉल कर सकें।"),
        "P03": (f"1 Gbps fibre with priority support at {at_en}, for heavy files and {staff}.",
                f"{at_hi} प्रायोरिटी सपोर्ट के साथ 1 Gbps फ़ाइबर, बड़ी फ़ाइलों और {emp} लोगों के लिए।"),
        "P04": (f"You're on {cur_en} today. 5G AirFiber plugs in and gives 100 Mbps in about 2 days, no digging.",
                f"अभी आप {cur_hi} पर हैं। 5G AirFiber प्लग करते ही लगभग 2 दिन में 100 Mbps देता है, कोई खुदाई नहीं।"),
        "P05": (f"A dedicated 20 Mbps line with 99.5% uptime for {staff} and your machines.",
                f"{emp} लोगों और आपकी मशीनों के लिए 99.5% अपटाइम वाली अलग 20 Mbps लाइन।"),
        "P06": (f"A dedicated 100 Mbps line with 99.9% uptime for a team of {emp}.",
                f"{emp} लोगों की टीम के लिए 99.9% अपटाइम वाली अलग 100 Mbps लाइन।"),
        "P07": (f"{staff}, so {qty} business mobile line{q_en} with unlimited calls.",
                f"{emp} कर्मचारी, इसलिए अनलिमिटेड कॉल वाली {qty} बिज़नेस मोबाइल लाइन।"),
        "P08": (f"{staff}, so {qty} business line{q_en} with more data and roaming for people on the move.",
                f"{emp} कर्मचारी, इसलिए बाहर काम करने वालों के लिए ज़्यादा डेटा और रोमिंग वाली {qty} लाइन।"),
        "P09": (f"If the main line drops, a 4G/5G backup keeps billing and calls running at {at_en}.",
                f"मुख्य लाइन बंद हो तो {at_hi} 4G/5G बैकअप से बिलिंग और कॉल चलते रहें।"),
        "P10": (f"One dashboard to manage the internet at all {s_en}, with priority for billing apps.",
                f"सभी {n} जगहों का इंटरनेट एक डैशबोर्ड से संभालें, बिलिंग ऐप को प्राथमिकता के साथ।"),
        "P11": ("A fixed IP so you can reach CCTV, servers or software from outside.",
                "फ़िक्स्ड IP, ताकि CCTV, सर्वर या सॉफ़्टवेयर बाहर से भी खोल सकें।"),
        "P12": (f"{staff}, so {qty} phone channel{q_en} with IVR and call recording.",
                f"{emp} कर्मचारी, इसलिए IVR और कॉल रिकॉर्डिंग वाले {qty} फ़ोन चैनल।"),
        "P13": ("A free-to-call 1800 number for your customers.",
                "आपके ग्राहकों के लिए मुफ़्त 1800 नंबर।"),
        "P14": ("10,000 SMS a month for order alerts, reminders and offers.",
                "ऑर्डर अलर्ट, रिमाइंडर और ऑफ़र के लिए हर महीने 10,000 SMS।"),
        "P15": ("A verified WhatsApp channel with your catalogue, for customer chats.",
                "ग्राहकों से बात के लिए आपके कैटलॉग के साथ वेरिफ़ाइड WhatsApp चैनल।"),
        "P16": (f"{staff}, so {qty} email account{q_en} on your own domain.",
                f"{emp} कर्मचारी, इसलिए आपके अपने डोमेन पर {qty} ईमेल अकाउंट।"),
        "P17": ("Automatic backup of your PCs and phones, so a broken laptop loses nothing.",
                "PC और फ़ोन का अपने-आप बैकअप, ताकि लैपटॉप ख़राब होने पर कुछ न खोए।"),
        "P18": ("A domain and a simple website, so customers find you online.",
                "डोमेन और एक आसान वेबसाइट, ताकि ग्राहक आपको ऑनलाइन ढूँढ सकें।"),
        "P19": (f"GST-ready billing with UPI and card payments at {qty} counter{q_en}, one per site.",
                f"हर जगह एक, कुल {qty} काउंटर पर UPI और कार्ड पेमेंट के साथ GST-तैयार बिलिंग।"),
        "P20": (f"{staff}, so virus and ransomware protection for {qty} device{q_en}.",
                f"{emp} कर्मचारी, इसलिए {qty} डिवाइस के लिए वायरस और रैनसमवेयर से सुरक्षा।"),
        "P21": (f"A managed firewall at {at_en} keeps the network of {staff} safe.",
                f"{at_hi} मैनेज्ड फ़ायरवॉल, ताकि {emp} लोगों का नेटवर्क सुरक्षित रहे।"),
        "P22": (f"Managed Wi-Fi at {at_en}, with a separate guest network for customers.",
                f"{at_hi} मैनेज्ड Wi-Fi, ग्राहकों के लिए अलग गेस्ट नेटवर्क के साथ।"),
        "P23": ((f"{qty} HD camera{q_en} with 30 days of cloud recording you can watch on your phone." if n == 1 else
                 f"{qty} HD camera{q_en}, two at each of your {n} sites, with 30 days of cloud recording on your phone."),
                (f"{qty} HD कैमरे, फ़ोन पर देखने के लिए 30 दिन की क्लाउड रिकॉर्डिंग के साथ।" if n == 1 else
                 f"आपकी {n} जगहों पर हर जगह दो, कुल {qty} HD कैमरे, फ़ोन पर 30 दिन की क्लाउड रिकॉर्डिंग।")),
        "P24": (f"Sensor kits on {qty} machine{q_en} to track uptime and power use.",
                f"{qty} मशीनों पर सेंसर किट, ताकि चलने का समय और बिजली खर्च दिखे।"),
        "P25": ("GPS tracking for your vehicle with a live dashboard.",
                "लाइव डैशबोर्ड के साथ आपकी गाड़ी की GPS ट्रैकिंग।"),
    }.get(p.product_id, (p.description, p.description))
    return lt(*r)


def gst_blocked_notice(profile: BusinessProfile) -> LocalText:
    status = (profile.gstin_status or "").lower()
    status_hi = "रद्द" if profile.gstin_status == "Cancelled" else "निलंबित"
    return lt(f"Your GSTIN is {status}, so products that need a GSTIN are left out. Everything else can go ahead now.",
              f"आपका GSTIN {status_hi} है, इसलिए GSTIN वाले प्रोडक्ट इसमें नहीं हैं। बाकी सब अभी लिया जा सकता है।")


def not_served_notice(profile: BusinessProfile) -> LocalText:
    city_en = profile.city or "your city"
    city_hi = profile.city or "आपके शहर"
    return lt(f"We don't serve {city_en} yet, so there is nothing we can quote. A person from our team can call you.",
              f"हम अभी {city_hi} में सेवा नहीं देते, इसलिए कोटेशन नहीं बन सकता। हमारी टीम का कोई व्यक्ति आपको कॉल कर सकता है।")


def budget_notice(total_with_gst: int, budget: int) -> LocalText:
    return lt(f"This comes to {inr(total_with_gst)} a month with GST, above your {inr(budget)} budget. "
              "Switch off add-ons or lower quantities to bring it down.",
              f"GST के साथ यह {inr(total_with_gst)} महीना है, जो आपके {inr(budget)} बजट से ज़्यादा है। "
              "कम करने के लिए ऐड-ऑन बंद करें या संख्या घटाएँ।")


def _names(products: list[Product], conj: str) -> str:
    names = [p.name for p in products]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" {conj} " + names[-1]


def added_prerequisite(added: Product, for_: list[Product]) -> LocalText:
    names = _names(for_, "and")
    verb = "needs" if len(for_) == 1 else "need"
    return lt(f"{added.name} added because {names} {verb} an internet line to work.",
              f"{added.name} जोड़ा गया, क्योंकि {_names(for_, 'और')} को चलने के लिए इंटरनेट लाइन चाहिए।")


def removed_dependant(removed: Product, because: list[Product]) -> LocalText:
    return lt(f"{removed.name} removed because {_names(because, 'and')} was removed.",
              f"{removed.name} हटाया गया, क्योंकि {_names(because, 'और')} हटा दिया गया।")


def removed_ineligible(p: Product, why: LocalText) -> LocalText:
    return lt(f"{p.name} removed. {why.en}", f"{p.name} हटाया गया। {why.hi}")


def unknown_product(pid: str) -> LocalText:
    return lt(f"{pid} isn't in our catalogue, so it was left out.", f"{pid} हमारी सूची में नहीं है, इसलिए छोड़ दिया गया।")


def dependency_ineligible(p: Product, link: Product | None) -> LocalText:
    if link is None:
        return lt(f"{p.name} needs an internet line, and none is available for you.",
                  f"{p.name} के लिए इंटरनेट लाइन चाहिए, जो अभी आपके लिए उपलब्ध नहीं है।")
    return lt(f"{p.name} doesn't work with {link.name}, the line in your quote.",
              f"{p.name} आपके कोटेशन की लाइन {link.name} के साथ नहीं चलता।")
