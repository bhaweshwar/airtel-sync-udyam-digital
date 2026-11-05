#!/usr/bin/env python3
"""Twelve scripted advisor conversations through the API, each checking the final stage and key products.

Usage (from the repo root):
  backend/.venv/bin/python scripts/advisor_scenarios.py          # rules mode: LLM keys blanked
  backend/.venv/bin/python scripts/advisor_scenarios.py --llm    # use the GROQ/GEMINI keys from .env
  backend/.venv/bin/python scripts/advisor_scenarios.py -v       # print every turn

Stage and text checks always count. Product checks need the real rules engine (WS1): while app.engine is still the
Phase 0 stub they are reported as "pending" and don't fail the run.
Exits non-zero if any counted check fails.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


@dataclass
class Scenario:
    name: str
    turns: list[str]
    stage: str
    language: str = "en"
    has: list[str] = field(default_factory=list)      # product ids that must be in quote.items
    lacks: list[str] = field(default_factory=list)    # product ids that must not be in quote.items
    text_has: list[str] = field(default_factory=list)  # substrings (case-insensitive) somewhere in the replies
    profile: dict = field(default_factory=dict)       # expected profile fields at the end
    blocked: bool | None = None                       # expected quote.gst_products_blocked (engine check)
    engine_text: list[str] = field(default_factory=list)  # reply substrings that come from engine reasons


SCENARIOS = [
    Scenario("English kirana, no GST",
             ["I run a kirana store in Ludhiana", "3", "Just one", "No GST", "Mobile hotspot", "Billing & UPI"],
             "recommended", has=["P19"], lacks=["P15", "P05"],
             profile={"segment": "micro", "city_tier": 2, "employees": 3, "has_gstin": False}),
    Scenario("Hindi dental clinic types a GSTIN",
             ["मेरा डेंटल क्लिनिक कोच्चि में है", "बारह लोग", "सिर्फ़ एक", "मेरा GSTIN 32TTNXB7384T1ZW है", "घर का ब्रॉडबैंड",
              "ईमेल और डेटा बैकअप चाहिए"],
             "recommended", language="hi", has=["P16"], lacks=["P03"], text_has=["सक्रिय"],
             profile={"segment": "prof", "employees": 12, "gstin_status": "Active", "state": "Kerala"}),
    Scenario("Hinglish restaurant chain, 4 sites",
             ["Humari restaurant chain hai Pune mein, 4 outlets aur 30 log", "GST hai", "har branch alag hai",
              "billing aur CCTV chahiye"],
             "recommended", language="hi", has=["P19", "P23"],
             profile={"segment": "multi", "sites": 4, "employees": 30, "city_tier": 1}),
    Scenario("Manufacturer, 40 staff, wants a leased line",
             ["We have an auto parts factory in Pune with 40 staff and we want a leased line", "Just one",
              "Yes, I have GST", "Business broadband"],
             "recommended", has=["P05"], profile={"segment": "mfg", "employees": 40}),
    Scenario("Tier-2 city asks for Fibre 1G",
             ["Dental clinic in Kochi, 8 staff, one site, GST registered, we use business broadband. Can I get Fibre 1G?"],
             "recommended", lacks=["P03"], engine_text=["tier 1"], profile={"city_tier": 2}),
    Scenario("Shop with no GST asks for WhatsApp API",
             ["I have a boutique in Jaipur with 2 people, one shop, no GST, mobile hotspot. I want WhatsApp Business API"],
             "recommended", lacks=["P15"], engine_text=["GST"], profile={"has_gstin": False}),
    Scenario("Cancelled GSTIN typed",
             ["Travel agency in Visakhapatnam, 4 people, one office", "37IHKXV5167L1ZS", "Home broadband", "Email"],
             "recommended", text_has=["cancelled"], lacks=["P15", "P13"], blocked=True,
             profile={"gstin_status": "Cancelled", "has_gstin": True}),
    Scenario("Budget of ₹800",
             ["Salon in Indore, 3 staff, one site, no GST, mobile hotspot, just internet. My budget is ₹800 a month"],
             "recommended", text_has=["budget"], profile={"budget_monthly_inr": 800}),
    Scenario("Owner changes their mind: remove CCTV",
             ["Bakery in Mumbai, 5 staff, one shop, GST hai, mobile hotspot", "CCTV and billing", "Actually remove CCTV"],
             "recommended", has=["P19"], lacks=["P23"]),
    Scenario("Unknown small town hands off",
             ["I have a kirana shop in Rampur", "Small town"], "handoff", profile={"city_tier": 3}),
    Scenario("Hinglish: asks for a person",
             ["mujhe kisi insaan se baat karni hai"], "handoff", language="hi"),
    Scenario("One-shot full description",
             ["We are a CA firm in Bengaluru with 8 staff in one office, GST registered, on home broadband, and we need "
              "email and backup"],
             "recommended", has=["P16"], profile={"segment": "prof", "employees": 8, "city_tier": 1}),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="use the LLM keys from .env instead of rules mode")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="udyam-scen-"), "scen.db")
    if not args.llm:
        os.environ["GROQ_API_KEY"] = ""
        os.environ["GEMINI_API_KEY"] = ""

    from fastapi.testclient import TestClient

    from app import engine
    from app.main import app

    stub_engine = "STUB" in (engine.recommend.__doc__ or "")
    failures = pending = 0
    rows = []
    with TestClient(app) as client:
        if args.llm:
            print("LLM status:", client.get("/api/llm-status", params={"probe": True}).json())
        for sc in SCENARIOS:
            sid, replies, last, modes = None, [], None, set()
            for text in sc.turns:
                r = client.post("/api/advisor/message", json={"session_id": sid, "text": text, "language": sc.language})
                r.raise_for_status()
                last = r.json()
                sid = last["session_id"]
                replies.append(last["reply_text"])
                modes.add(last["mode"])
                if args.verbose:
                    print(f"  > {text}\n  < [{last['stage']}/{last['mode']}] {last['reply_text']}")
            assert last is not None
            problems, soft = [], []
            if last["stage"] != sc.stage:
                problems.append(f"stage {last['stage']} != {sc.stage}")
            if last["profile"]["language"] != sc.language:
                problems.append(f"language {last['profile']['language']} != {sc.language}")
            joined = "\n".join(replies).lower()
            for s in sc.text_has:
                if s.lower() not in joined:
                    problems.append(f"reply lacks '{s}'")
            for k, v in sc.profile.items():
                if last["profile"].get(k) != v:
                    problems.append(f"profile.{k}={last['profile'].get(k)!r} != {v!r}")
            quote = last.get("quote")
            items = {i["product_id"] for i in quote["items"]} if quote else set()
            for pid in sc.has:
                if pid not in items:
                    soft.append(f"missing {pid}")
            for pid in sc.lacks:
                if pid in items:
                    soft.append(f"has {pid}")
            for s in sc.engine_text:
                if s.lower() not in joined:
                    soft.append(f"reply lacks '{s}'")
            if sc.blocked is not None and quote and quote.get("gst_products_blocked") != sc.blocked:
                soft.append(f"gst_products_blocked != {sc.blocked}")
            if sc.stage == "recommended" and not quote:
                problems.append("no quote")
            if soft and stub_engine:
                pending += 1
            else:
                problems += soft
                soft = []
            failures += bool(problems)
            status = "FAIL" if problems else ("pending" if soft else "ok")
            rows.append((sc.name, len(sc.turns), last["stage"], "/".join(sorted(modes)), status, "; ".join(problems + soft)))

    w = max(len(r[0]) for r in rows)
    print(f"{'scenario':<{w}}  turns  stage        mode       result")
    for name, turns, stage, mode, status, note in rows:
        print(f"{name:<{w}}  {turns:>5}  {stage:<11}  {mode:<9}  {status}{'  (' + note + ')' if note else ''}")
    print(f"\n{len(rows) - failures}/{len(rows)} passed"
          + (f"; {pending} with product checks pending (engine is still the Phase 0 stub)" if pending else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
