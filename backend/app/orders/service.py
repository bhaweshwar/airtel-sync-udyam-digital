"""Orders + tracker logic (WS4): create, PIN check, transitions, timeline, ETAs and install slots.

Dates shown to the owner run on the demo clock: anything that happened "now" happened on settings.today.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import date, timedelta
from typing import Any, Optional

from cryptography.fernet import Fernet

from .. import engine, store
from ..common.i18n_server import lt
from ..common.mask import mask_phone
from ..config import settings
from ..contracts import (
    CreateOrderRequest, CreateOrderResponse, InstallSlot, ItemEta, LocalText, Order, OrderStatus, OrderTotals,
    SelectedItem, TimelineStep,
)
from .state import NEXT_STATUS, check_transition

WINDOWS = ("10-13", "14-18")
WINDOW_TEXT = {"10-13": ("10 am to 1 pm", "सुबह 10 से दोपहर 1 बजे"), "14-18": ("2 pm to 6 pm", "दोपहर 2 से शाम 6 बजे")}

# ---------------------------------------------------------------- secrets

_PIN_ITERATIONS = 60_000


def hash_pin(pin: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), _PIN_ITERATIONS).hex()
    return f"pbkdf2${salt}${digest}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", (pin or "").encode(), bytes.fromhex(salt), _PIN_ITERATIONS).hex()
    return hmac.compare_digest(candidate, digest)


def encrypt_phone(phone: str) -> str:
    return Fernet(settings.fernet_key.encode()).encrypt(phone.encode()).decode()


def decrypt_phone(token: str) -> str:
    return Fernet(settings.fernet_key.encode()).decrypt(token.encode()).decode()


# ---------------------------------------------------------------- PIN attempts (in memory)

MAX_FAILED_PER_MINUTE = 10
_failures: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def reset_attempts() -> None:
    with _lock:
        _failures.clear()


class TooManyTries(Exception):
    """Raised by authorise() while an order ID is locked after too many wrong PINs."""


def authorise(order_id: str, pin: Optional[str]) -> Optional[dict[str, Any]]:
    """The order row if the PIN matches, else None. Wrong PINs for the same ID (real or not) are counted;
    after 10 failures in a minute every attempt raises TooManyTries until the window clears, so the PIN can't be brute-forced
    and the answer never reveals whether the order exists. Correct PINs don't count, so 10 s polling is fine."""
    now = time.monotonic()
    with _lock:
        q = _failures[order_id]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= MAX_FAILED_PER_MINUTE:
            # Locked IDs answer the same way whether the order exists or not, so this reveals nothing.
            raise TooManyTries(order_id)
    row = store.get_order(order_id)
    if row and pin and verify_pin(pin, row["pin_hash"]):
        return row
    with _lock:
        _failures[order_id].append(now)
    return None


# ---------------------------------------------------------------- create + transitions

def new_order_id() -> str:
    return f"UD-{settings.today:%y%m%d}-{store.count_orders() + 1:04d}"


def create_order(req: CreateOrderRequest) -> Optional[CreateOrderResponse]:
    """None when the quote doesn't exist. The quote is re-priced so client-side numbers are never trusted."""
    quote = store.get_quote(req.quote_id)
    if quote is None:
        return None
    selected = [SelectedItem(product_id=i.product_id, quantity=i.quantity) for i in quote.items]
    priced = engine.price(quote.profile, selected)
    store.save_quote(priced)

    order_id, pin = new_order_id(), f"{secrets.randbelow(10_000):04d}"
    store.create_order(order_id, quote_id=priced.quote_id, pin_hash=hash_pin(pin), contact_name=req.contact_name.strip(),
                       phone_enc=encrypt_phone(req.phone.strip()), phone_masked=mask_phone(req.phone),
                       status="QUOTE_ACCEPTED")
    store.add_event(order_id, "QUOTE_ACCEPTED", lt("You accepted the quote and placed your order.",
                                                    "आपने कोटेशन स्वीकार करके ऑर्डर कर दिया।"))
    transition(order_id, "KYC_PENDING", lt("Next: upload your business documents for a quick check.",
                                           "आगे: जल्दी जाँच के लिए अपने व्यवसाय के दस्तावेज़ अपलोड करें।"))
    return CreateOrderResponse(order_id=order_id, pin=pin)


def transition(order_id: str, target: OrderStatus, text: LocalText, slot: InstallSlot | None = None) -> None:
    """Moves the order to `target` (raises IllegalTransition otherwise) and writes an event."""
    row = store.get_order(order_id)
    if row is None:
        raise KeyError(order_id)
    check_transition(row["status"], target)
    store.update_order(order_id, status=target, slot=slot)
    store.add_event(order_id, target, text)


def _slot_text(slot: InstallSlot) -> tuple[str, str]:
    en, hi = WINDOW_TEXT[slot.window]
    return f"{slot.date:%a %d %b}, {en}", f"{slot.date:%d-%m-%Y}, {hi}"


def book_slot(order_id: str, slot: InstallSlot) -> None:
    """Raises ValueError if the slot isn't offered; IllegalTransition if the order isn't ready for one."""
    if slot not in available_slots():
        raise ValueError("slot not offered")
    row = store.get_order(order_id)
    en, hi = _slot_text(slot)
    if row and row["status"] == "INSTALL_SCHEDULED":  # reschedule: same status, new slot
        store.update_order(order_id, slot=slot)
        store.add_event(order_id, "INSTALL_SCHEDULED", lt(f"Installation moved to {en}.", f"इंस्टॉलेशन {hi} पर बदल दिया गया।"))
        return
    transition(order_id, "INSTALL_SCHEDULED", lt(f"Installation booked for {en}.", f"इंस्टॉलेशन {hi} के लिए बुक हो गया।"), slot=slot)


ADVANCE_TEXT: dict[str, LocalText] = {
    "KYC_PENDING": lt("Order confirmed. Next: document check.", "ऑर्डर पक्का हुआ। आगे: दस्तावेज़ जाँच।"),
    "KYC_VERIFIED": lt("Documents verified by our team.", "हमारी टीम ने दस्तावेज़ सत्यापित कर दिए।"),
    "INSTALLING": lt("Engineer Ravi assigned and on the way to your site.",
                     "इंजीनियर रवि को काम सौंपा गया, वे आपकी साइट पर आ रहे हैं।"),
    "ACTIVE": lt("Fibre line activated. Your services are live.", "फ़ाइबर लाइन चालू हो गई। आपकी सेवाएँ शुरू हो गईं।"),
}


def advance(order_id: str) -> bool:
    """Demo only: one step along the happy path. False when the order is already at the end."""
    row = store.get_order(order_id)
    if row is None or row["status"] not in NEXT_STATUS:
        return False
    target = NEXT_STATUS[row["status"]]
    if target == "INSTALL_SCHEDULED":
        book_slot(order_id, available_slots()[0])
    else:
        transition(order_id, target, ADVANCE_TEXT[target])
    return True


# ---------------------------------------------------------------- slots + ETAs

def _working_days(start: date, n: int) -> list[date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def available_slots() -> list[InstallSlot]:
    """The next 5 working days after KYC is verified (verification happens on the demo 'today'), two windows each."""
    return [InstallSlot(date=d, window=w) for d in _working_days(settings.today + timedelta(days=1), 5) for w in WINDOWS]


_KYC_DONE = {"KYC_VERIFIED", "INSTALL_SCHEDULED", "INSTALLING", "ACTIVE"}


def install_start(status: str, slot: InstallSlot | None) -> date:
    if slot is not None:
        return slot.date
    if status in _KYC_DONE:
        return settings.today + timedelta(days=1)
    return settings.today + timedelta(days=2)


def item_etas(items: list, status: str, slot: InstallSlot | None) -> list[ItemEta]:
    if status == "REJECTED":
        return [ItemEta(product_id=i.product_id, name=i.name) for i in items]
    start = install_start(status, slot)
    return [ItemEta(product_id=i.product_id, name=i.name, eta=start + timedelta(days=i.install_days)) for i in items]


# ---------------------------------------------------------------- timeline + next action

STEPS = [
    ("ordered", lt("Order placed", "ऑर्डर हो गया")),
    ("kyc", lt("Documents checked", "दस्तावेज़ जाँचे गए")),
    ("install_scheduled", lt("Installation booked", "इंस्टॉलेशन बुक")),
    ("installing", lt("Engineer on site", "इंजीनियर साइट पर")),
    ("active", lt("Services live", "सेवाएँ चालू")),
]

# status -> (index of the current step, is it blocked). Steps before it are done; len(STEPS) means all done.
_CURRENT = {
    "QUOTE_ACCEPTED": (1, False), "KYC_PENDING": (1, False), "KYC_ACTION_REQUIRED": (1, True),
    "KYC_REVIEW": (1, False), "REJECTED": (1, True), "KYC_VERIFIED": (2, False),
    "INSTALL_SCHEDULED": (3, False), "INSTALLING": (4, False), "ACTIVE": (5, False),
}


def timeline(status: str, slot: InstallSlot | None, eta_active: date | None) -> list[TimelineStep]:
    current, blocked = _CURRENT[status]
    etas = {"installing": install_start(status, slot), "active": eta_active} if status != "REJECTED" else {}
    out = []
    last_done = settings.today
    for idx, (key, label) in enumerate(STEPS):
        if idx < current:
            # A done step can't be dated before the step it follows (services go live after the engineer's visit).
            last_done = max(last_done, slot.date if key == "installing" and slot else settings.today)
            out.append(TimelineStep(key=key, label=label, state="done", date=last_done))
        else:
            state = ("blocked" if blocked else "current") if idx == current else "upcoming"
            out.append(TimelineStep(key=key, label=label, state=state, eta=etas.get(key)))
    return out


DOC_RETAKE = {
    "gst_certificate": lt("Retake your GST certificate photo.", "अपने GST प्रमाणपत्र की फ़ोटो दोबारा लें।"),
    "udyam_certificate": lt("Retake your Udyam certificate photo.", "अपने उद्यम प्रमाणपत्र की फ़ोटो दोबारा लें।"),
    "signatory_id": lt("Retake the photo of your ID card.", "अपने पहचान पत्र की फ़ोटो दोबारा लें।"),
    "address_proof": lt("Retake your address proof photo.", "अपने पते के प्रमाण की फ़ोटो दोबारा लें।"),
}


def next_action(order_id: str, status: str, slot: InstallSlot | None) -> Optional[LocalText]:
    if status in ("QUOTE_ACCEPTED", "KYC_PENDING"):
        return lt("Upload your business documents to continue.", "आगे बढ़ने के लिए अपने व्यवसाय के दस्तावेज़ अपलोड करें।")
    if status == "KYC_ACTION_REQUIRED":
        kyc = store.get_kyc_result(order_id)
        failing = [c for c in (kyc["checks"] if kyc else []) if c.status == "FAIL"] or \
                  [c for c in (kyc["checks"] if kyc else []) if c.status == "WARN"]
        for check in failing:
            if check.doc_type in DOC_RETAKE:
                return DOC_RETAKE[check.doc_type]
            if check.fix_hint:
                return check.fix_hint
        return lt("Retake the document photos we flagged.", "जिन दस्तावेज़ों पर निशान लगा है, उनकी फ़ोटो दोबारा लें।")
    if status == "KYC_REVIEW":
        return lt("Nothing to do. Our team is checking your documents and will update you within 1 working day.",
                  "आपको कुछ नहीं करना है। हमारी टीम दस्तावेज़ जाँच रही है और 1 कामकाजी दिन में बताएगी।")
    if status == "KYC_VERIFIED":
        return lt("Pick an installation slot.", "इंस्टॉलेशन के लिए समय चुनें।")
    if status == "INSTALL_SCHEDULED" and slot:
        en, hi = _slot_text(slot)
        return lt(f"Keep someone at the site on {en}.", f"{hi} को साइट पर किसी को मौजूद रखें।")
    if status == "INSTALLING":
        return lt("Our engineer is setting up your services. Keep the site open.",
                  "हमारे इंजीनियर आपकी सेवाएँ लगा रहे हैं। साइट खुली रखें।")
    if status == "REJECTED":
        return lt("We could not verify your business. Call Accel Business support to talk it through.",
                  "हम आपके व्यवसाय का सत्यापन नहीं कर सके। बात करने के लिए Accel Business सहायता को कॉल करें।")
    return None


# ---------------------------------------------------------------- read model

def build_order(row: dict[str, Any]) -> Order:
    quote = store.get_quote(row["quote_id"])
    items = quote.items if quote else []
    status, slot = row["status"], row["slot"]
    etas = item_etas(items, status, slot)
    eta_active = max((e.eta for e in etas if e.eta), default=None)
    return Order(
        order_id=row["order_id"], status=status, contact_name=row["contact_name"], phone_masked=row["phone_masked"],
        items=items,
        totals=OrderTotals(monthly_inr=quote.monthly_total_inr if quote else 0,
                           one_time_inr=quote.one_time_total_inr if quote else 0,
                           monthly_with_gst_inr=quote.monthly_total_with_gst_inr if quote else 0,
                           contract_months=quote.contract_months if quote else 0),
        timeline=timeline(status, slot, eta_active), item_etas=etas, eta_activation_date=eta_active,
        install_slot=slot, events=store.list_events(row["order_id"]), next_action=next_action(row["order_id"], status, slot),
        created_at=row["created_at"],
    )
