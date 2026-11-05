"""Run the 12 sample applicants through the Smart KYC pipeline (real OCR) and compare with the expected verdicts.

Usage: backend/.venv/bin/python scripts/kyc_eval.py [-v]
Exits non-zero on any mismatch. -v also prints every non-PASS check.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.kyc import pipeline  # noqa: E402

# Hand-checked against the images and the mock registries (docs/WORKSTREAMS.md, WS3 item 8).
EXPECTED = {
    "K01": ("REJECTED", "Cancelled GSTIN; blank Udyam number"),
    "K02": ("VERIFIED", "tilted scan; GSTIN contains the letter O"),
    "K03": ("VERIFIED", "clean"),
    "K04": ("ACTION_REQUIRED", "blurred GST certificate"),
    "K05": ("ACTION_REQUIRED", "no Udyam certificate"),
    "K06": ("REJECTED", "certificate GSTIN fails the checksum"),
    "K07": ("MANUAL_REVIEW", "legal name 'Shri' vs 'Neelgiri' elsewhere"),
    "K08": ("VERIFIED", "GSTIN letter O"),
    "K09": ("VERIFIED", "clean"),
    "K10": ("VERIFIED", "LLP signatory is only a WARN"),
    "K11": ("ACTION_REQUIRED", "bill 257 days old"),
    "K12": ("VERIFIED", "clean"),
}


def main() -> int:
    verbose = "-v" in sys.argv
    mismatches = 0
    print(f"{'ID':<4} {'Expected':<16} {'Got':<16} {'':<2} {'Failing / warning checks':<60} {'s':>5}")
    print("-" * 108)
    for applicant, (expected, why) in EXPECTED.items():
        t0 = time.monotonic()
        docs = pipeline.process_sample(applicant)
        outcome = pipeline.evaluate(docs)
        secs = time.monotonic() - t0
        ok = outcome.verdict == expected
        mismatches += not ok
        flagged = [f"{c.code}:{c.status}" for c in outcome.checks if c.status != "PASS"]
        print(f"{applicant:<4} {expected:<16} {outcome.verdict:<16} {'ok' if ok else 'XX':<2} "
              f"{', '.join(flagged) or '-':<60} {secs:5.1f}")
        if verbose or not ok:
            print(f"       expected because: {why}")
            for c in outcome.checks:
                if c.status != "PASS":
                    print(f"       {c.status} {c.code} [{c.doc_type or '-'}] {c.message.en}")
    print("-" * 108)
    print(f"{len(EXPECTED) - mismatches}/{len(EXPECTED)} match")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
