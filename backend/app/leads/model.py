"""Lead score: a small logistic regression on intake-time fields only (WS5).

Target: outcome == "Activated". Features are what we know when the lead arrives, so the score can rank a fresh
lead. Stage dates, stage_reached, drop_reason, bundle, value, churn, NPS and outcome columns are never used:
they are only known after the fact and would leak the answer.

Trained once, lazily, on first use (~0.1 s). The reported metrics come from a time split (train before
2026-06-01, test on June); the scoring model is then refit on every row.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import OneHotEncoder

from .. import data

# Raw intake-time columns the features are derived from. Anything else in smb_leads.csv is off limits.
INTAKE_COLUMNS = [
    "lead_source", "segment", "city_tier", "has_gstin", "has_udyam", "employee_count", "num_sites",
    "current_internet", "current_provider", "monthly_telecom_spend_inr", "preferred_language",
]
# Columns known only after the lead has moved through the funnel. Listed so the tests can assert none is used.
LEAKAGE_COLUMNS = [
    "stage_reached", "outcome", "drop_reason", "contacted_date", "needs_assessed_date", "quote_accepted_date",
    "kyc_complete_date", "activated_date", "days_lead_to_activation", "customer_follow_up_calls", "bundle_products",
    "monthly_bundle_value_inr", "one_time_setup_inr", "contract_months", "churned_within_6_months", "nps_score",
    "acquisition_cost_inr",
]
FEATURES = [
    "lead_source", "segment", "city_tier", "has_gstin", "has_udyam", "employee_band", "sites_band",
    "current_internet", "current_provider", "spend_band", "preferred_language",
]
SPLIT_DATE = "2026-06-01"


def employee_band(n: int) -> str:
    return "1-5" if n <= 5 else "6-20" if n <= 20 else "21-50" if n <= 50 else "50+"


def sites_band(n: int) -> str:
    return "1" if n <= 1 else "2-3" if n <= 3 else "4+"


def spend_band(inr: int) -> str:
    return "<1k" if inr < 1000 else "1k-3k" if inr < 3000 else "3k-10k" if inr < 10000 else "10k+"


def features(df: pd.DataFrame) -> pd.DataFrame:
    """Intake-time feature frame (all strings), one row per lead."""
    return pd.DataFrame({
        "lead_source": df["lead_source"],
        "segment": df["segment_code"],
        "city_tier": df["city_tier"].astype(str),
        "has_gstin": df["has_gstin"],
        "has_udyam": df["has_udyam"],
        "employee_band": df["employee_count"].map(employee_band),
        "sites_band": df["num_sites"].map(sites_band),
        "current_internet": df["current_internet"],
        "current_provider": df["current_provider"],
        "spend_band": df["monthly_telecom_spend_inr"].map(spend_band),
        "preferred_language": df["preferred_language"],
    }, index=df.index)


_SEGMENT_PHRASE = {"micro": "is a micro shop or service", "prof": "is a professional office",
                   "multi": "has several sites", "mfg": "is a small manufacturer"}
_INTERNET_PHRASE = {"None": "has no internet today", "Mobile hotspot": "uses a mobile hotspot today",
                    "Home broadband": "uses home broadband today", "Business broadband": "already has business broadband",
                    "Mixed per site": "has mixed connections per site", "Leased line": "already has a leased line"}


def phrase(feature: str, value: str) -> str:
    """Plain words for one one-hot feature, e.g. ('lead_source', 'Referral') -> 'came through a referral'."""
    if feature == "lead_source":
        return {"Field sales": "came through field sales", "Channel partner": "came through a channel partner",
                "Website form": "filled the website form", "Inbound call": "called us",
                "Referral": "came through a referral", "WhatsApp campaign": "came from a WhatsApp campaign"}.get(value, f"source: {value}")
    if feature == "segment":
        return _SEGMENT_PHRASE.get(value, value)
    if feature == "city_tier":
        return f"in a tier-{value} city"
    if feature == "has_gstin":
        return "has a GSTIN" if value == "Y" else "has no GSTIN"
    if feature == "has_udyam":
        return "has Udyam registration" if value == "Y" else "has no Udyam registration"
    if feature == "employee_band":
        return f"has {value.replace('-', '–')} staff"
    if feature == "sites_band":
        return "has one site" if value == "1" else f"has {value.replace('-', '–')} sites"
    if feature == "current_internet":
        return _INTERNET_PHRASE.get(value, value)
    if feature == "current_provider":
        return "no current provider" if value == "None" else f"currently with {value}"
    if feature == "spend_band":
        return {"<1k": "spends under ₹1,000 a month", "1k-3k": "spends ₹1,000–3,000 a month",
                "3k-10k": "spends ₹3,000–10,000 a month", "10k+": "spends ₹10,000+ a month"}[value]
    if feature == "preferred_language":
        return f"prefers {value}"
    return f"{feature}={value}"


def _fit(X: pd.DataFrame, y: np.ndarray) -> tuple[OneHotEncoder, LogisticRegression]:
    enc = OneHotEncoder(handle_unknown="ignore")
    clf = LogisticRegression(class_weight="balanced", max_iter=1000)
    clf.fit(enc.fit_transform(X), y)
    return enc, clf


def top_decile_lift(y: np.ndarray, p: np.ndarray, share: float = 0.1) -> float:
    k = max(1, int(round(len(y) * share)))
    top = np.argsort(-p, kind="stable")[:k]
    return float(y[top].mean() / y.mean()) if y.mean() else 0.0


def capture(y: np.ndarray, p: np.ndarray, share: float = 0.2) -> float:
    k = max(1, int(round(len(y) * share)))
    top = np.argsort(-p, kind="stable")[:k]
    return float(y[top].sum() / y.sum()) if y.sum() else 0.0


@dataclass
class LeadModel:
    auc_time_split: float
    top_decile_lift: float
    top20_capture: float
    train_rows: int
    test_rows: int
    coefficients: list[tuple[str, str, float]]  # (feature, value, weight), sorted by |weight| desc
    scores: pd.Series                            # lead_id -> score in [0, 1]
    hot_cut: float
    warm_cut: float
    top_factors: dict[str, list[str]] = field(default_factory=dict)

    def band(self, score: float) -> str:
        return "HOT" if score >= self.hot_cut else "WARM" if score >= self.warm_cut else "COLD"


def train() -> LeadModel:
    df = data.leads()
    X = features(df)
    y = (df["outcome"] == "Activated").to_numpy(dtype=int)

    # Honest estimate: fit on April–May, test on June.
    is_train = (df["created_date"] < SPLIT_DATE).to_numpy()
    enc, clf = _fit(X[is_train], y[is_train])
    p_test = clf.predict_proba(enc.transform(X[~is_train]))[:, 1]
    y_test = y[~is_train]

    # Scoring model: refit on every row.
    enc, clf = _fit(X, y)
    Xt = enc.transform(X)
    scores = clf.predict_proba(Xt)[:, 1]

    names = [(f, str(v)) for f, cats in zip(FEATURES, enc.categories_) for v in cats]
    w = clf.coef_[0]
    coefs = sorted(((f, v, float(wi)) for (f, v), wi in zip(names, w)), key=lambda c: -abs(c[2]))

    # Top 2 factors per lead: largest positive coefficient × feature contributions (one-hot, so x is 0 or 1).
    contrib = Xt.multiply(w).tocsr()
    factors: dict[str, list[str]] = {}
    for i, lead_id in enumerate(df["lead_id"]):
        row = contrib.getrow(i)
        pairs = sorted(((val, j) for j, val in zip(row.indices, row.data) if val > 0), reverse=True)[:2]
        factors[lead_id] = [phrase(*names[j]) for _, j in pairs]

    return LeadModel(
        auc_time_split=float(roc_auc_score(y_test, p_test)),
        top_decile_lift=top_decile_lift(y_test, p_test),
        top20_capture=capture(y_test, p_test),
        train_rows=int(is_train.sum()),
        test_rows=int((~is_train).sum()),
        coefficients=coefs,
        scores=pd.Series(scores, index=df["lead_id"].to_numpy()),
        hot_cut=float(np.quantile(scores, 0.8)),   # HOT = top 20% of all leads
        warm_cut=float(np.quantile(scores, 0.5)),  # WARM = next 30%
        top_factors=factors,
    )


_lock = threading.Lock()


@lru_cache(maxsize=1)
def _cached() -> LeadModel:
    return train()


def get_model() -> LeadModel:
    with _lock:
        return _cached()
