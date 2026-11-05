"""WS1: eligibility, pricing, recommendation and dependency handling."""
from __future__ import annotations

from app import data, engine, store
from app.contracts import BusinessProfile, Quote, SelectedItem
from app.engine import rules

PRODUCT_NEEDS = {  # products_of_interest in the leads -> the need that asks for them
    "P09": "backup", "P10": "sdwan", "P11": "static_ip", "P12": "telephony", "P13": "tollfree", "P14": "sms",
    "P15": "whatsapp", "P16": "email", "P17": "cloud_backup", "P18": "website", "P19": "payments_pos",
    "P20": "security", "P22": "wifi", "P23": "cctv", "P24": "iot", "P25": "fleet",
}


def _profile(**kw) -> BusinessProfile:
    return BusinessProfile(**kw)


def _ids(q: Quote) -> list[str]:
    return [i.product_id for i in q.items]


def _assert_sound(q: Quote) -> None:
    """No ineligible product, no unmet dependency, totals add up."""
    products = data.products_by_id()
    chosen = set(_ids(q))
    for item in q.items:
        p = products[item.product_id]
        assert rules.ineligibility(p, q.profile) is None, (item.product_id, q.profile)
        assert rules.dependency_met(p, chosen), (item.product_id, chosen)
        assert item.unit_price_inr == (p.price_min_inr + p.price_max_inr + 1) // 2
        assert item.monthly_inr == item.unit_price_inr * item.quantity
    for item in q.addons_available:
        assert item.product_id not in chosen
        assert rules.ineligibility(products[item.product_id], q.profile) is None
        assert rules.dependency_met(products[item.product_id], chosen)
    assert q.monthly_total_inr == sum(i.monthly_inr for i in q.items)
    assert q.one_time_total_inr == sum(i.setup_inr for i in q.items)
    assert q.contract_months == max((i.contract_months for i in q.items), default=0)
    assert abs(q.monthly_total_with_gst_inr - q.monthly_total_inr * 1.18) <= 0.5


def test_sweep_every_lead_gets_a_sound_recommendation():
    reg = data.gstin_registry()
    for r in data.leads().itertuples(index=False):
        gstin = r.gstin.strip().upper()
        needs = sorted({PRODUCT_NEEDS[x] for x in r.products_of_interest.split(";") if x in PRODUCT_NEEDS})
        profile = BusinessProfile(
            business_type=r.business_type, segment=r.segment_code, city=r.city, city_tier=int(r.city_tier),
            employees=max(1, int(r.employee_count)), sites=max(1, int(r.num_sites)), has_gstin=r.has_gstin == "Y",
            gstin_status=reg[gstin]["status"] if gstin in reg else None,
            current_internet=data.CURRENT_INTERNET_CODES.get(r.current_internet), needs=needs)
        q = engine.recommend(profile)
        assert q.items, r.lead_id
        assert sum(1 for pid in _ids(q) if pid in rules.LINKS) == 1, r.lead_id
        _assert_sound(q)


def test_kirana_ludhiana_no_gst():
    q = engine.recommend(_profile(business_type="kirana store", segment="micro", city="Ludhiana", city_tier=2,
                                  employees=3, sites=1, has_gstin=False, current_internet="mobile_hotspot"))
    _assert_sound(q)
    assert _ids(q) == ["P04", "P07"]  # single-site shop on a hotspot -> AirFiber + mobile lines
    assert q.items[1].quantity == 2  # ceil(3 / 2)
    blocked = {i.product_id: i for i in q.ineligible}
    assert blocked["P15"].reason_code == "GSTIN" and blocked["P03"].reason_code == "TIER"
    assert "Ludhiana is tier 2" in blocked["P03"].reason.en
    assert not q.gst_products_blocked


def test_dental_clinic_kochi():
    q = engine.recommend(_profile(business_type="dental clinic", segment="prof", city="Kochi", city_tier=2,
                                  employees=12, sites=1, has_gstin=True, gstin_status="Active",
                                  current_internet="business_broadband"))
    _assert_sound(q)
    ids = _ids(q)
    assert ids[0] == "P02" and "P16" in ids
    email = next(i for i in q.items if i.product_id == "P16")
    assert email.quantity == 12 and email.reason.en.startswith("12 staff, so 12 email accounts")
    assert any(i.product_id == "P03" and i.reason_code == "TIER" for i in q.ineligible)
    assert q.contract_months == 12
    assert q.monthly_total_with_gst_inr == round(q.monthly_total_inr * 1.18)


def test_restaurant_chain_five_sites():
    q = engine.recommend(_profile(business_type="restaurant chain", segment="multi", city="Mumbai", city_tier=1,
                                  employees=30, sites=5, has_gstin=True, gstin_status="Active",
                                  current_internet="mixed", needs=["payments_pos", "cctv"]))
    _assert_sound(q)
    by = {i.product_id: i for i in q.items}
    assert by["P02"].quantity == 5 and by["P19"].quantity == 5 and by["P23"].quantity == 10
    assert "P10" in by  # 5 sites, 30 staff, active GSTIN -> SD-WAN
    assert q.contract_months == 24


def test_auto_parts_unit_leased_line():
    q = engine.recommend(_profile(business_type="auto-parts unit", segment="mfg", city="Pune", city_tier=1,
                                  employees=40, sites=1, has_gstin=True, gstin_status="Active",
                                  current_internet="business_broadband", needs=["iot"]))
    _assert_sound(q)
    assert _ids(q)[0] == "P05"
    assert "P24" in _ids(q)
    by = {i.product_id: i for i in q.items}
    assert by["P05"].setup_inr == 10000 and by["P24"].quantity == 5


def test_ca_firm_email_and_backup():
    q = engine.recommend(_profile(business_type="ca firm", segment="prof", city="Jaipur", city_tier=2,
                                  employees=8, sites=1, has_gstin=True, gstin_status="Active",
                                  current_internet="home_broadband", needs=["email", "backup"]))
    _assert_sound(q)
    by = {i.product_id: i for i in q.items}
    assert by["P16"].quantity == 8 and "P09" in by
    assert by["P09"].kind == "addon"
    assert any(i.product_id == "P05" and i.reason_code == "EMPLOYEES" for i in q.ineligible)


def test_pharmacy_cctv_without_link_gets_one_added():
    profile = _profile(business_type="pharmacy", segment="micro", city="Delhi", city_tier=1, employees=4, sites=1,
                       has_gstin=True, gstin_status="Active")
    q = engine.price(profile, [SelectedItem(product_id="P23", quantity=2)])
    _assert_sound(q)
    links = [pid for pid in _ids(q) if pid in rules.LINKS]
    assert len(links) == 1 and q.notices and "Cloud CCTV" in q.notices[0].en
    assert next(i for i in q.items if i.product_id == "P23").quantity == 2


def test_removing_prerequisite_removes_dependants():
    profile = _profile(segment="prof", city="Pune", city_tier=1, employees=5, sites=1, has_gstin=True,
                       gstin_status="Active")
    before = engine.price(profile, [SelectedItem(product_id="P02", quantity=1), SelectedItem(product_id="P11", quantity=1)])
    assert set(_ids(before)) == {"P02", "P11"}
    after = engine.price(profile, [SelectedItem(product_id="P11", quantity=1)], before)
    assert _ids(after) == []
    assert after.notices[0].en == "Static IP removed because Biz Fibre 300 was removed."
    assert "P02" in [i.product_id for i in after.addons_available]  # the link can be switched back on


def test_cancelled_gstin_blocks_gst_products_only():
    q = engine.recommend(_profile(segment="prof", city="Delhi", city_tier=1, employees=6, sites=1, has_gstin=True,
                                  gstin_status="Cancelled", needs=["whatsapp", "email"]))
    _assert_sound(q)
    assert q.gst_products_blocked and "cancelled" in q.notices[0].en
    assert "P16" in _ids(q) and "P15" not in _ids(q)
    assert any(i.product_id == "P15" and i.reason_code == "GSTIN" for i in q.ineligible)


def test_api_never_trusts_client_prices(client):
    p = {"segment": "micro", "city": "Delhi", "city_tier": 1, "employees": 2, "sites": 1, "has_gstin": True,
         "gstin_status": "Active", "needs": []}
    r = client.post("/api/quote", json={"profile": p, "selected": [{"product_id": "P01", "quantity": 1,
                                                                    "unit_price_inr": 1}]})
    assert r.status_code == 200
    q = Quote.model_validate(r.json())
    assert q.items[0].unit_price_inr == 1099
    assert store.get_quote(q.quote_id) is not None
    tier3 = client.post("/api/recommend", json={"profile": {**p, "city": "Shimla", "city_tier": 3}}).json()
    assert tier3["items"] == [] and "Shimla" in tier3["notices"][0]["en"]
