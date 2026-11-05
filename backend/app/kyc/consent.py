"""The DPDP Act 2023 consent notice for Smart KYC, in English and Hindi."""
from __future__ import annotations

from ..common.i18n_server import lt
from ..contracts import ConsentNotice, ConsentPurpose

NOTICE_VERSION = "2026-07-v1"
REQUIRED_PURPOSE = "kyc_verification"
OPTIONAL_PURPOSE = "service_improvement"


def notice() -> ConsentNotice:
    return ConsentNotice(
        version=NOTICE_VERSION,
        purposes=[
            ConsentPurpose(id=REQUIRED_PURPOSE, required=True, text=lt(
                "Check my business documents for this order.",
                "इस ऑर्डर के लिए मेरे व्यवसाय के दस्तावेज़ जाँचें।")),
            ConsentPurpose(id=OPTIONAL_PURPOSE, required=False, text=lt(
                "Use my anonymised details to improve the service.",
                "सेवा बेहतर करने के लिए मेरी पहचान हटाकर मेरी जानकारी का उपयोग करें।")),
        ],
        body=lt(
            "What we collect: photos of your GST certificate, Udyam certificate, the signatory's ID and a recent "
            "utility bill, and the details we read from them (business names, GSTIN, Udyam number, ID number and "
            "expiry, bill date and address).\n"
            "Why: only to check that the business placing this order is registered and active, and that the person "
            "signing can sign for it. We never ask for your Aadhaar.\n"
            "Who sees it: our KYC system, and our verification team if a check needs a person. Numbers are masked "
            "everywhere we show them. We don't sell or share your details.\n"
            "Your photos are read in memory and never stored.\n"
            "How to withdraw: tap “Withdraw consent” on the KYC page at any time. We then delete your KYC "
            "details straight away. Without consent we can't verify the order.",
            "हम क्या लेते हैं: आपके GST प्रमाणपत्र, उद्यम प्रमाणपत्र, हस्ताक्षरकर्ता की ID और हाल के बिजली/पानी के बिल की "
            "फ़ोटो, और उनसे पढ़ी गई जानकारी (व्यवसाय के नाम, GSTIN, उद्यम नंबर, ID नंबर और उसकी समाप्ति तिथि, बिल की "
            "तारीख़ और पता)।\n"
            "क्यों: सिर्फ़ यह जाँचने के लिए कि ऑर्डर देने वाला व्यवसाय रजिस्टर्ड और सक्रिय है, और हस्ताक्षर करने वाले "
            "व्यक्ति को इसका अधिकार है। हम आपका आधार कभी नहीं माँगते।\n"
            "कौन देखता है: हमारा KYC सिस्टम, और अगर किसी जाँच में इंसान की ज़रूरत हो तो हमारी सत्यापन टीम। नंबर हर जगह "
            "छिपाकर दिखाए जाते हैं। हम आपकी जानकारी न बेचते हैं, न किसी को देते हैं।\n"
            "आपकी फ़ोटो सिर्फ़ मेमोरी में पढ़ी जाती हैं और कभी सहेजी नहीं जातीं।\n"
            "सहमति कैसे वापस लें: KYC पेज पर कभी भी “सहमति वापस लें” दबाएँ। हम आपकी KYC जानकारी तुरंत मिटा "
            "देंगे। सहमति के बिना हम ऑर्डर सत्यापित नहीं कर सकते।",
        ),
        retention=lt(
            "Photos are never stored. Extracted details are kept for 180 days after your service is activated, or "
            "30 days if the order is rejected, and are then deleted.",
            "फ़ोटो कभी सहेजी नहीं जातीं। निकाली गई जानकारी सेवा चालू होने के 180 दिन बाद तक, या ऑर्डर अस्वीकार होने पर "
            "30 दिन तक रखी जाती है, फिर मिटा दी जाती है।",
        ),
    )
