"""GSTIN and Udyam number validation. Phase 0 owns this file.

GSTIN layout (15 chars): 2-digit state code, 10-char PAN (5 letters, 4 digits, 1 letter), entity number
(1-9 or A-Z), the letter Z, and a mod-36 check character. The case data uses 'X' as the PAN's 4th character
(not a real entity type), which this format check accepts because it is a letter.
"""
from __future__ import annotations

import re

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")

STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}


def normalize(value: str) -> str:
    """Upper-case and drop spaces, dashes and dots (people type GSTINs in many ways)."""
    return re.sub(r"[\s\-.]", "", value or "").upper()


def check_char(first14: str) -> str:
    """Mod-36 check character for the first 14 characters of a GSTIN."""
    total = 0
    for i, ch in enumerate(first14):
        product = ALPHABET.index(ch) * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return ALPHABET[(36 - total % 36) % 36]


def format_valid(gstin: str) -> bool:
    return bool(GSTIN_RE.match(gstin))


def checksum_valid(gstin: str) -> bool:
    if len(gstin) != 15 or any(c not in ALPHABET for c in gstin):
        return False
    return check_char(gstin[:14]) == gstin[14]


def is_valid(gstin: str) -> bool:
    return format_valid(gstin) and checksum_valid(gstin)


def state_for(gstin: str) -> str | None:
    return STATE_CODES.get(gstin[:2]) if len(gstin) >= 2 else None


def udyam_format_valid(number: str) -> bool:
    return bool(UDYAM_RE.match(number))


def normalize_udyam(value: str) -> str:
    """'udyam kl 00 3078801' or 'UDYAMKL003078801' -> 'UDYAM-KL-00-3078801'. Unparseable input is just upper-cased."""
    compact = re.sub(r"[^A-Z0-9]", "", (value or "").upper())
    m = re.fullmatch(r"UDYAM([A-Z]{2})([0-9]{2})([0-9]{7})", compact)
    return f"UDYAM-{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else (value or "").strip().upper()
