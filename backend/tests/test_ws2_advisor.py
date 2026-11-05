"""WS2 advisor: rules parser, number guard, rules-mode endpoint. No real LLM calls (conftest blanks the keys)."""
from __future__ import annotations

import pytest

from app.advisor import extract, llm, templates
from app.advisor.rules_parser import parse


@pytest.mark.parametrize("text,pending,expected", [
    ("I run a kirana store in Ludhiana, 3 people, no GST", None,
     {"business_type": "Kirana store", "segment": "micro", "city_tier": 2, "employees": 3, "has_gstin": False}),
    ("मेरा डेंटल क्लिनिक कोच्चि में है, बारह लोग काम करते हैं", None,
     {"segment": "prof", "city": "Kochi", "employees": 12, "language": "hi"}),
    ("Humari restaurant chain hai, 4 outlets Pune mein, 30 log, GST hai", None,
     {"segment": "multi", "sites": 4, "employees": 30, "has_gstin": True, "city_tier": 1, "language": "hi"}),
    ("teen", "employees", {"employees": 3}),
    ("हाँ", "has_gstin", {"has_gstin": True}),
    ("GST nahi hai", None, {"has_gstin": False}),
    ("व्हाट्सऐप और बिलिंग चाहिए", None, {"needs_add": ["whatsapp", "payments_pos"]}),
    ("CCTV nahi chahiye", None, {"needs_remove": ["cctv"], "intent": "change"}),
    ("mujhe kisi insaan se baat karni hai", None, {"intent": "handoff"}),
    ("My budget is ₹800 a month", None, {"budget_monthly_inr": 800}),
    ("Can I get Fibre 1G?", None, {"products_asked": ["P03"]}),
    ("Rampur", "city", {"unknown_city": "Rampur"}),
    ("27QHJXK0658U1ZL", "has_gstin", {"gstin": "27QHJXK0658U1ZL", "has_gstin": True}),
])
def test_rules_parser(text, pending, expected):
    ex = parse(text, pending)
    for k, v in expected.items():
        assert getattr(ex, k) == v, (k, getattr(ex, k))


@pytest.mark.parametrize("text,bad", [
    ("Here is a plan that fits your clinic.", False),
    ("यह प्लान आपके व्यवसाय के हिसाब से है।", False),
    ("Only 999 a month!", True),
    ("Just ₹ a month", True),
    ("Costs Rs. less than others", True),
    ("We added P23 for you", True),
    ("सिर्फ़ ९९९ में", True),
])
def test_number_guard(text, bad):
    assert templates.has_numbers(text) is bad
    assert templates.safe_text(text, "TEMPLATE") == ("TEMPLATE" if bad else text)


def test_llm_json_is_validated():
    ex = extract.from_llm({"business_type": "dental clinic", "city": "Kochi", "employees": "12", "needs_add": ["email", "rocket"],
                           "intent": "buy_now", "current_internet": "satellite", "language": "hi"})
    assert ex is not None
    assert (ex.segment, ex.city_tier, ex.employees, ex.needs_add, ex.intent, ex.current_internet) == \
        ("prof", 2, 12, ["email"], "other", None)


def test_endpoint_rules_mode_full_conversation(client, monkeypatch):
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: pytest.fail("LLM must not be called without keys"))
    r = client.post("/api/advisor/message", json={"text": "I run a kirana store in Ludhiana", "language": "en"}).json()
    assert r["mode"] == "rules" and r["stage"] == "asking" and r["missing_fields"][0] == "employees"
    assert 3 <= len(r["quick_replies"]) <= 5
    sid = r["session_id"]
    for text in ["3", "Just one", "No GST", "Mobile hotspot", "Billing & UPI"]:
        r = client.post("/api/advisor/message", json={"session_id": sid, "text": text}).json()
    assert r["stage"] == "recommended" and r["quote"] and r["mode"] == "rules"
    assert not templates.has_numbers(r["reply_text"])
    h = client.post("/api/advisor/handoff", json={"session_id": sid, "reason": "Owner tapped Talk to a person"}).json()
    assert h["handoff_id"].startswith("H-")
    status = client.get("/api/llm-status").json()
    assert status["active"] is None and all(not p["configured"] for p in status["providers"])


def test_llm_intro_with_digits_is_replaced(client, monkeypatch):
    monkeypatch.setattr(llm, "any_configured", lambda: True)

    def fake(system, user):
        if system == extract.REPHRASE_SYSTEM:
            return {"text": "Your plan is just ₹1,649 a month!"}, "groq"
        return {"business_type": "salon", "city": "Indore", "employees": 3, "sites": 1, "has_gstin": False,
                "current_internet": "mobile_hotspot", "needs_add": ["internet"], "intent": "answer", "language": "en"}, "groq"

    monkeypatch.setattr(llm, "complete_json", fake)
    r = client.post("/api/advisor/message", json={"text": "Salon in Indore with three of us, one shop, no GST, hotspot"}).json()
    assert r["mode"] == "llm" and r["stage"] == "recommended"
    assert not templates.has_numbers(r["reply_text"])


def test_gstin_is_masked_and_cancelled_explained(client):
    r = client.post("/api/advisor/message", json={"text": "Travel agency in Visakhapatnam, GSTIN 37IHKXV5167L1ZS"}).json()
    assert r["profile"]["gstin_status"] == "Cancelled"
    assert "37IHKXV5167L1ZS" not in r["profile"]["gstin"]
    assert "cancelled" in r["reply_text"].lower()
