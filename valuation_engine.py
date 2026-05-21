"""
Valuation Engine — BDS TP.HCM
Tính toán định giá tài chính nâng cao cho từng bất động sản.
Tất cả hằng số là module-level, không hardcode per-property.
"""

from typing import Optional

# ─── Module-level Assumptions ─────────────────────────────────────────────────
LTV_RATIO       = 0.70   # 70% loan-to-value (ngân hàng VN tiêu chuẩn)
LOAN_TERM_YEARS = 20
INTEREST_RATE   = 0.095  # 9.5% — lãi suất ưu đãi thực tế T5/2026 (tăng từ 8.5%)
VACANCY_RATE    = 0.10   # 10% tỷ lệ trống
OPEX_RATIO      = 0.15   # 15% chi phí vận hành / effective gross income
MANAGEMENT_FEE  = 0.08   # 8% phí quản lý / gross rent

# ─── Legal risk scores (thấp = an toàn) ─────────────────────────────────────
LEGAL_RISK = {
    "Sổ hồng":              5,
    "Sổ đỏ":                5,
    "Sổ hồng vĩnh viễn":    3,
    "Hợp đồng mua bán":    35,
    "Hợp đồng góp vốn":    50,
    None:                  40,   # không có / không xác định = rủi ro
}

# ─── Developer tiers ─────────────────────────────────────────────────────────
# TIER1: Clean, actively trustworthy developers
TIER1_DEVS = [
    "Vingroup", "Masterise", "CapitaLand", "KeppelLand", "Nam Long",
    "Phú Mỹ Hưng", "Gamuda",
]
# TIER2: Known brands but require extra scrutiny (legal/financial issues)
TIER2_DEVS = [
    "Novaland", "Hưng Thịnh", "Khang Điền", "An Gia", "Đất Xanh",
]

import math as _math

# ─── Transaction & Exit Cost Constants ──────────────────────────────────────
HOLDING_YEARS      = 5
BROKER_EXIT_FEE    = 0.020   # 2% of exit price
TRANSFER_TAX       = 0.020   # 2% personal income tax on transfer
MAINTENANCE_RATIO  = 0.010   # 1% of property value/year maintenance reserve
ENTRY_COST_RATIO   = 0.010   # 1% entry costs (stamp duty + legal)
LEASING_FRICTION   = 0.50    # months lost per vacancy event

LIQUIDITY_HAIRCUT = {
    "can-ho-chung-cu": 0.020,
    "nha-rieng":       0.030,
    "dat-nen":         0.050,
}

# ─── Macro Regime — update each quarter ─────────────────────────────────────
# Q1-Q2 2026: rates 9.5%, buyers cautious, developers stressed
MACRO_REGIME = {
    "mode":              "tightening",   # "bullish" | "neutral" | "tightening"
    "mortgage_rate":     0.095,
    "credit_tightness":  0.65,           # 0=loose → 1=tight
    "sentiment":         0.45,           # 0=fear → 1=greed
    "developer_stress":  0.55,           # 0=none → 1=systemic
    "bull_app_mult":     1.40,
    "base_app_mult":     1.00,
    "bear_app_mult":     0.30,
    "bull_vacancy_mult": 0.75,
    "base_vacancy_mult": 1.00,
    "bear_vacancy_mult": 1.50,
}


# ─── Safe helpers ─────────────────────────────────────────────────────────────

def safe_number(v, default=None):
    """Trả về float hoặc default nếu v không hợp lệ."""
    if v is None:
        return default
    try:
        f = float(v)
        if f != f:   # NaN
            return default
        return f
    except (TypeError, ValueError):
        return default


def safe_divide(a, b, default=None):
    """Trả về a/b hoặc default nếu b == 0 / None."""
    a = safe_number(a)
    b = safe_number(b)
    if a is None or b is None or b == 0:
        return default
    return a / b


def clamp(v, lo, hi):
    """Giới hạn v trong [lo, hi]."""
    if v is None:
        return lo
    return max(lo, min(hi, v))


def clamp_score(v):
    """Giới hạn điểm trong [0, 100]."""
    return clamp(v, 0, 100)


# ─── Helper: monthly mortgage payment (annuity formula) ──────────────────────

def _monthly_mortgage(principal: float) -> float:
    """Tính khoản trả góp hàng tháng theo công thức niên kim."""
    r = INTEREST_RATE / 12
    n = LOAN_TERM_YEARS * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def _remaining_mortgage_balance(
    principal: float,
    annual_rate: float,
    loan_term_years: int,
    years_elapsed: int,
) -> float:
    """PV of remaining annuity payments = correct remaining mortgage balance."""
    r = annual_rate / 12
    n_total = loan_term_years * 12
    n_rem   = (loan_term_years - years_elapsed) * 12
    if r == 0:
        return principal * n_rem / n_total
    monthly_pmt = principal * r * (1 + r)**n_total / ((1 + r)**n_total - 1)
    return monthly_pmt * (1 - (1 + r)**(-n_rem)) / r


# ─── Legal status extractor (mirrors app.py prop_legal logic) ────────────────

def _get_legal_status(prop: dict) -> Optional[str]:
    v = prop.get("legal_status")
    if v:
        return v
    note = (prop.get("note") or "").lower()
    if "vĩnh viễn" in note:
        return "Sổ hồng vĩnh viễn"
    if "sổ hồng" in note:
        return "Sổ hồng"
    if "sổ đỏ" in note:
        return "Sổ đỏ"
    if "hợp đồng mua bán" in note:
        return "Hợp đồng mua bán"
    if "hợp đồng góp vốn" in note:
        return "Hợp đồng góp vốn"
    return None


def _developer_risk(developer: Optional[str]) -> float:
    """Trả về mức rủi ro chủ đầu tư (thấp = tốt)."""
    if not developer or str(developer).strip() == "":
        return 40.0
    dev = str(developer)
    for t1 in TIER1_DEVS:
        if t1.lower() in dev.lower():
            return 8.0
    for t2 in TIER2_DEVS:
        if t2.lower() in dev.lower():
            return 22.0
    return 32.0


def _overall_risk_level(legal_risk: float, dev_risk: float, supply_risk: float) -> str:
    combined = (legal_risk * 0.45 + dev_risk * 0.35 + supply_risk * 0.20)
    if combined < 15:
        return "Low"
    if combined < 30:
        return "Medium"
    if combined < 50:
        return "High"
    return "Very High"


def _transaction_velocity(absorption: Optional[float]) -> str:
    if absorption is None:
        return "Medium"
    if absorption >= 0.85:
        return "High"
    if absorption >= 0.65:
        return "Medium"
    return "Low"


# ─── IRR: Newton-Raphson ─────────────────────────────────────────────────────

def _compute_irr(cash_flows: list, guess: float = 0.10) -> Optional[float]:
    """Newton-Raphson IRR. Returns None if no convergence or nonsensical result."""
    rate = guess
    for _ in range(120):
        try:
            npv  = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
            dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
            if abs(dnpv) < 1e-12:
                break
            rate -= npv / dnpv
            if abs(npv) < 1.0:
                break
        except (ZeroDivisionError, OverflowError):
            break
    return rate if -0.50 < rate < 5.0 else None


# ─── Net Rental Yield ────────────────────────────────────────────────────────

def _net_rental_yield(
    gross_yield_pct: float,
    vacancy: float,
    mgmt_fee: float,
    maint_ratio: float,
    price_vnd: float,
) -> float:
    """Net yield after vacancy, management fee, maintenance reserve, leasing friction."""
    if not gross_yield_pct or not price_vnd or price_vnd <= 0:
        return 0.0
    gross_annual  = price_vnd * gross_yield_pct / 100
    eff_rent      = gross_annual * (1 - vacancy)
    after_mgmt    = eff_rent * (1 - mgmt_fee)
    maint         = price_vnd * maint_ratio
    lease_loss    = (gross_annual / 12) * LEASING_FRICTION * vacancy
    net           = after_mgmt - maint - lease_loss
    return round(max(net / price_vnd * 100, 0.0), 2)


# ─── Scenario Engine ─────────────────────────────────────────────────────────

def _scenario_roi(
    price_vnd: float,
    gross_yield_pct: float,
    growth_base_pct: float,
    prop_type: str,
    macro_regime: dict,
) -> dict:
    """
    Bear / Base / Bull scenario engine.
    Returns IRR, equity ROI, net yield, exit price, payback per scenario.
    All costs: entry, maintenance, vacancy, mgmt fee, broker exit, transfer tax, haircut.
    """
    if not price_vnd or price_vnd <= 0:
        return {}
    equity       = price_vnd * (1 - LTV_RATIO)
    entry_cost   = price_vnd * ENTRY_COST_RATIO
    deployed     = equity + entry_cost
    haircut      = LIQUIDITY_HAIRCUT.get(prop_type, 0.03)
    base_app     = growth_base_pct / 100

    defs = {
        "bear": (macro_regime.get("bear_app_mult", 0.30),
                 macro_regime.get("bear_vacancy_mult", 1.50), 1.50, "Xấu"),
        "base": (macro_regime.get("base_app_mult", 1.00),
                 macro_regime.get("base_vacancy_mult", 1.00), 1.00, "Cơ sở"),
        "bull": (macro_regime.get("bull_app_mult", 1.40),
                 macro_regime.get("bull_vacancy_mult", 0.75), 0.80, "Tốt"),
    }
    out = {}
    for sc, (app_m, vac_m, maint_m, label) in defs.items():
        app_rate  = base_app * app_m
        vacancy   = min(VACANCY_RATE * vac_m, 0.30)
        maint     = MAINTENANCE_RATIO * maint_m
        net_yld   = _net_rental_yield(gross_yield_pct, vacancy, MANAGEMENT_FEE, maint, price_vnd)
        net_ann   = price_vnd * net_yld / 100 if net_yld > 0 else 0.0

        exit_raw  = price_vnd * (1 + app_rate) ** HOLDING_YEARS
        exit_proc = exit_raw * (1 - BROKER_EXIT_FEE - TRANSFER_TAX - haircut)

        cap_gain   = exit_proc - price_vnd
        total_inc  = net_ann * HOLDING_YEARS
        roi        = (cap_gain + total_inc) / deployed * 100

        loan_rem = _remaining_mortgage_balance(
            principal=price_vnd * LTV_RATIO,
            annual_rate=INTEREST_RATE,
            loan_term_years=LOAN_TERM_YEARS,
            years_elapsed=HOLDING_YEARS,
        )
        cfs = [-deployed] + [net_ann] * (HOLDING_YEARS - 1) + [net_ann + exit_proc - loan_rem]
        irr = _compute_irr(cfs)

        payback = round(equity / net_ann, 1) if net_ann > 0 and equity / net_ann < 50 else None

        out[sc] = {
            "label":          label,
            "roi":            round(roi, 1),
            "irr":            round(irr * 100, 1) if irr else None,
            "net_yield_pct":  net_yld,
            "net_annual_m":   round(net_ann / 1e6, 1),
            "exit_price_b":   round(exit_raw / 1e9, 2),
            "app_rate_pct":   round(app_rate * 100, 1),
            "payback_years":  payback,
        }
    out["meta"] = {
        "holding_years":    HOLDING_YEARS,
        "entry_cost_pct":   ENTRY_COST_RATIO * 100,
        "broker_exit_pct":  BROKER_EXIT_FEE * 100,
        "transfer_tax_pct": TRANSFER_TAX * 100,
        "haircut_pct":      haircut * 100,
        "base_growth_pct":  round(growth_base_pct, 1),
        "macro_mode":       macro_regime.get("mode", "neutral"),
    }
    return out


# ─── Liquidity Score v2 ──────────────────────────────────────────────────────

def _liquidity_score_v2(
    prop_type: str,
    area_m2: Optional[float],
    price_per_sqm_m: Optional[float],
    avg_price_per_sqm_m: Optional[float],
    absorption: Optional[float],
    supply_tightness: Optional[float],
    developer_rating: int = 3,
) -> float:
    """
    Multi-factor liquidity 0-100.
    Weights: absorption 35% · tightness 15% · price premium 20%
             area sweet-spot 15% · property type 10% · dev rating 5%
    """
    a = absorption or 0.0
    if a >= 0.85:   abs_sc = 90.0
    elif a >= 0.70: abs_sc = 60 + (a - 0.70) / 0.15 * 30
    elif a >= 0.55: abs_sc = 35 + (a - 0.55) / 0.15 * 25
    elif a >= 0.40: abs_sc = 15 + (a - 0.40) / 0.15 * 20
    else:           abs_sc = max(0, a / 0.40 * 15)

    tight_sc = clamp_score((supply_tightness or 5) / 10 * 100)

    if price_per_sqm_m and avg_price_per_sqm_m and avg_price_per_sqm_m > 0:
        r = price_per_sqm_m / avg_price_per_sqm_m
        if r <= 0.90:   prem_sc = 100
        elif r <= 1.05: prem_sc = 80
        elif r <= 1.15: prem_sc = 55
        elif r <= 1.30: prem_sc = 30
        else:           prem_sc = 10
    else:
        prem_sc = 50

    if prop_type == "can-ho-chung-cu" and area_m2:
        if 50 <= area_m2 <= 80:                          area_sc = 100
        elif 40 <= area_m2 < 50 or 80 < area_m2 <= 100: area_sc = 70
        else:                                             area_sc = 40
    else:
        area_sc = 60

    type_sc = {"can-ho-chung-cu": 85, "nha-rieng": 65, "dat-nen": 40}.get(prop_type, 55)
    dev_sc  = clamp_score((developer_rating - 1) / 4 * 100)

    return clamp_score(
        abs_sc  * 0.35 + tight_sc * 0.15 + prem_sc * 0.20 +
        area_sc * 0.15 + type_sc  * 0.10 + dev_sc  * 0.05
    )


# ─── Property Quality Score ──────────────────────────────────────────────────

def _property_quality_score(prop: dict, dev_info: Optional[dict]) -> dict:
    """
    Micro property quality 0-100.
    Components: developer (25%) · building status (20%) · size efficiency (20%)
                bed/bath utility (15%) · project tier (20%)
    """
    if dev_info:
        rating = dev_info.get("rating", 3)
        legal  = dev_info.get("legal_status", "clean")
        a_sc   = rating / 5 * 80
        if legal in ("warning", "red"):   a_sc *= 0.55
        elif legal == "caution":          a_sc *= 0.80
    else:
        a_sc = 38.0

    status = (prop.get("building_status") or "").lower()
    if any(k in status for k in ("đã bàn giao", "hoàn thành", "sổ hồng", "bàn giao")):
        b_sc = 85
    elif any(k in status for k in ("đang xây", "xây dựng", "thi công")):
        b_sc = 50
    elif any(k in status for k in ("mở bán", "off-plan", "sắp mở")):
        b_sc = 30
    else:
        b_sc = 60

    area = safe_number(prop.get("area_m2"))
    beds = safe_number(prop.get("bedrooms")) or 1
    if area:
        mpb = area / max(beds, 1)
        if 20 <= mpb <= 35:             c_sc = 90
        elif 15 <= mpb < 20 or 35 < mpb <= 45: c_sc = 70
        elif mpb < 15:                  c_sc = 40
        else:                           c_sc = 58
    else:
        c_sc = 50

    baths = safe_number(prop.get("bathrooms")) or 1
    bbr = beds / max(baths, 1)
    if 1.0 <= bbr <= 2.0: d_sc = 85
    elif bbr < 1.0:       d_sc = 70
    else:                 d_sc = 48

    district = prop.get("district", "")
    premium  = {"Quận 1", "Quận 3", "Quận 7", "Bình Thạnh", "Thủ Đức"}
    dr       = dev_info.get("rating", 0) if dev_info else 0
    ops      = dev_info.get("operations", 0) if dev_info else 0
    if district in premium and dr >= 4:  e_sc = 90
    elif district in premium or dr >= 4: e_sc = 70
    elif ops >= 4:                       e_sc = 60
    else:                                e_sc = 40

    composite = clamp_score(a_sc*0.25 + b_sc*0.20 + c_sc*0.20 + d_sc*0.15 + e_sc*0.20)
    label = "Cao" if composite >= 72 else ("Trung bình" if composite >= 50 else "Thấp")
    return {
        "score": round(composite, 1), "label": label,
        "breakdown": {
            "developer":        round(a_sc, 1),
            "building_status":  round(b_sc, 1),
            "size_efficiency":  round(c_sc, 1),
            "bed_bath_utility": round(d_sc, 1),
            "project_tier":     round(e_sc, 1),
        },
    }


# ─── Model Confidence ────────────────────────────────────────────────────────

def _model_confidence(
    prop: dict,
    market: dict,
    macro: dict,
    liquidity_sc: float,
) -> dict:
    """Confidence score 0-100 reflecting data richness and consistency."""
    score = 50.0
    fields = [prop.get("price_per_m2_million"), prop.get("area_m2"),
              prop.get("developer"), prop.get("bedrooms"), market.get("avg_price_per_m2")]
    score += (sum(1 for f in fields if f is not None) - 2) * 5
    if macro.get("absorption_rate") is not None:
        score += 5
    score += (liquidity_sc - 50) * 0.20
    p   = safe_number(prop.get("price_per_m2_million"))
    avg = safe_number(market.get("avg_price_per_m2"))
    if p and avg and avg > 0:
        r = p / avg
        if 0.70 <= r <= 1.30:    score += 8
        elif r < 0.50 or r > 2.0: score -= 15
        else:                     score -= 5
    ls = _get_legal_status(prop)
    lr = float(LEGAL_RISK.get(ls, LEGAL_RISK[None]))
    if lr <= 5:    score += 5
    elif lr >= 35: score -= 10
    score = clamp_score(score)
    label = ("Cao" if score >= 72 else "Trung bình" if score >= 52
             else "Thấp" if score >= 38 else "Rất thấp")
    return {"score": round(score, 1), "label": label}


# ─── Macro Regime Modifier ───────────────────────────────────────────────────

def _macro_modifier(macro_regime: dict) -> dict:
    mode = macro_regime.get("mode", "neutral")
    if mode == "bullish":    return {"rec_bias": +6,  "liq_mult": 1.08}
    if mode == "tightening": return {"rec_bias": -6,  "liq_mult": 0.90}
    return                          {"rec_bias":  0,  "liq_mult": 1.00}


# ─── Recommendation Engine v2 ────────────────────────────────────────────────

def _recommendation_v2(
    composite: float,
    liquidity_sc: float,
    confidence: float,
    dev_legal_status: str,
    quality_score: float,
    scenarios: dict,
    macro_regime: dict,
) -> dict:
    """BUY / HOLD / SPECULATIVE / SKIP with explanation."""
    mod      = _macro_modifier(macro_regime)
    adj      = composite + mod["rec_bias"]
    base_irr = (scenarios.get("base") or {}).get("irr") or 0
    bear_roi = (scenarios.get("bear") or {}).get("roi") or -999

    if dev_legal_status == "red":
        return {"verdict": "SKIP", "color": "#7f1d1d", "bg": "#fee2e2",
                "reason": "Pháp lý nguy hiểm — bỏ qua"}
    # Warning developer → capped at SPECULATIVE regardless of score
    if dev_legal_status == "warning":
        if quality_score < 48 or adj < 48:
            return {"verdict": "SKIP", "color": "#7f1d1d", "bg": "#fee2e2",
                    "reason": "Cảnh báo pháp lý CĐT — rủi ro cao"}
        flags = [f"pháp lý CĐT ⚠️ (đang điều tra)"]
        if liquidity_sc < 44:  flags.append(f"thanh khoản {liquidity_sc:.0f}/100")
        if bear_roi < -10:     flags.append(f"bear ROI {bear_roi:.0f}%")
        return {"verdict": "SPECULATIVE", "color": "#5b21b6", "bg": "#ede9fe",
                "reason": "Tiềm năng nhưng: " + " · ".join(flags)}
    if adj >= 67 and liquidity_sc >= 55 and base_irr >= 11 and bear_roi >= 0:
        return {"verdict": "BUY", "color": "#14532d", "bg": "#dcfce7",
                "reason": f"Điểm {adj:.0f} · IRR {base_irr:.1f}% · Kịch bản xấu vẫn dương"}
    if adj >= 57 and liquidity_sc >= 44 and base_irr >= 7:
        return {"verdict": "BUY", "color": "#166534", "bg": "#bbf7d0",
                "reason": f"Điểm {adj:.0f} · IRR {base_irr:.1f}%"}
    risky = (liquidity_sc < 44 or confidence < 48 or quality_score < 48 or bear_roi < -15)
    if adj >= 49 and risky:
        flags = []
        if liquidity_sc < 44:   flags.append(f"thanh khoản {liquidity_sc:.0f}/100")
        if confidence < 48:     flags.append("dữ liệu mỏng")
        if quality_score < 48:  flags.append(f"chất lượng thấp {quality_score:.0f}/100")
        if bear_roi < -15:      flags.append(f"bear ROI {bear_roi:.0f}%")
        return {"verdict": "SPECULATIVE", "color": "#5b21b6", "bg": "#ede9fe",
                "reason": "Tiềm năng nhưng: " + " · ".join(flags)}
    if adj >= 41:
        return {"verdict": "HOLD", "color": "#92400e", "bg": "#fef3c7",
                "reason": f"Điểm {adj:.0f}/100 · Chờ tín hiệu"}
    return {"verdict": "SKIP", "color": "#7f1d1d", "bg": "#fee2e2",
            "reason": f"Điểm {adj:.0f}/100 · Không đủ hấp dẫn"}


# ─── Main valuation function ──────────────────────────────────────────────────

def compute_valuation(
    prop: dict,
    market: dict,
    district: str,
    infra_momentum: dict,
    macro: dict,
    dev_info: Optional[dict] = None,
    macro_regime: Optional[dict] = None,
) -> dict:
    if macro_regime is None:
        macro_regime = MACRO_REGIME
    """
    Tính toán định giá tài chính nâng cao.

    Parameters
    ----------
    prop            : dict — thông tin bất động sản
    market          : dict — dữ liệu thị trường (avg_price_per_m2, rental_yield, growth_yoy)
    district        : str  — quận/huyện
    infra_momentum  : dict — kết quả từ infrastructure.get_infra_momentum()
    macro           : dict — kết quả từ analyzer.get_macro()

    Returns
    -------
    dict theo cấu trúc chuẩn định nghĩa trong spec.
    """
    prop_type = prop.get("property_type", "can-ho-chung-cu")
    is_dat_nen = (prop_type == "dat-nen")

    # ── Raw inputs ─────────────────────────────────────────────────────────────
    price_billion      = safe_number(prop.get("price_billion"))
    area_m2            = safe_number(prop.get("area_m2"))
    price_per_m2_input = safe_number(prop.get("price_per_m2_million"))  # triệu VND/m²
    avg_price_per_m2   = safe_number(market.get("avg_price_per_m2"))    # triệu VND/m²
    rental_yield_pct   = safe_number(market.get("rental_yield"), 0.0)
    growth_yoy         = safe_number(market.get("growth_yoy"), 8.0)

    # Macro / supply
    absorption         = safe_number(macro.get("absorption_rate"))
    new_supply         = safe_number(macro.get("new_supply_units_qtr"), 500)
    supply_tightness   = safe_number(macro.get("supply_tightness"), 6.5)

    # Convert prices to VND
    price_vnd          = price_billion * 1e9 if price_billion is not None else None
    avg_price_vnd_per_m2 = avg_price_per_m2 * 1e6 if avg_price_per_m2 is not None else None  # VND/m²

    # ── Data quality tracking ──────────────────────────────────────────────────
    dq_price_per_sqm = "User provided" if price_per_m2_input is not None else (
        "Estimated" if (price_vnd and area_m2) else "Missing"
    )
    dq_fmv = "Benchmark based" if avg_price_vnd_per_m2 is not None else "Missing"

    # ── Derived price_per_m2 (VND/m²) ─────────────────────────────────────────
    if price_per_m2_input is not None:
        price_per_sqm_vnd = price_per_m2_input * 1e6
    elif price_vnd is not None and area_m2 is not None:
        price_per_sqm_vnd = safe_divide(price_vnd, area_m2)
    else:
        price_per_sqm_vnd = None

    # ── Fair Market Value ──────────────────────────────────────────────────────
    fair_market_value = None
    if avg_price_vnd_per_m2 is not None and area_m2 is not None:
        fair_market_value = avg_price_vnd_per_m2 * area_m2

    # ── Valuation Gap ─────────────────────────────────────────────────────────
    valuation_gap_pct = None
    valuation_label   = "UNKNOWN"
    if fair_market_value is not None and price_vnd is not None and price_vnd > 0:
        valuation_gap_pct = (fair_market_value - price_vnd) / price_vnd * 100
        if valuation_gap_pct > 10:
            valuation_label = "UNDERVALUED"
        elif valuation_gap_pct < -10:
            valuation_label = "OVERVALUED"
        else:
            valuation_label = "FAIR"

    # ── Projected 5Y ROI ──────────────────────────────────────────────────────
    projected_5y_roi = None
    if growth_yoy is not None:
        capital_gain = ((1 + growth_yoy / 100) ** 5 - 1) * 100
        if not is_dat_nen and rental_yield_pct and rental_yield_pct > 0:
            effective_yield = rental_yield_pct * (1 - VACANCY_RATE) * (1 - MANAGEMENT_FEE)
            rental_5yr = effective_yield * 5
            projected_5y_roi = round(capital_gain + rental_5yr, 1)
        else:
            projected_5y_roi = round(capital_gain, 1)

    # ── Income Metrics ────────────────────────────────────────────────────────
    monthly_rent_est   = None
    gross_rental_yield = None
    egi                = None   # effective gross income
    opex               = None
    noi                = None
    cap_rate           = None
    coc_return         = None
    dscr               = None
    break_even_occ     = None

    if not is_dat_nen and rental_yield_pct and rental_yield_pct > 0 and price_vnd:
        gross_annual_rent  = price_vnd * rental_yield_pct / 100
        monthly_rent_est   = gross_annual_rent / 12
        gross_rental_yield = rental_yield_pct

        # After vacancy & management fee
        net_annual_rent = gross_annual_rent * (1 - VACANCY_RATE) * (1 - MANAGEMENT_FEE)
        egi = gross_annual_rent * (1 - VACANCY_RATE)
        opex = egi * OPEX_RATIO
        noi  = egi - opex

        # Cap rate
        cap_rate = safe_divide(noi, price_vnd, None)
        if cap_rate is not None:
            cap_rate = cap_rate * 100   # as %

        # Debt service
        loan_amount = price_vnd * LTV_RATIO
        down_payment = price_vnd * (1 - LTV_RATIO)
        monthly_pmt = _monthly_mortgage(loan_amount)
        annual_debt_service = monthly_pmt * 12

        # Cash-on-cash
        annual_pre_tax_cf = noi - annual_debt_service
        coc_return = safe_divide(annual_pre_tax_cf, down_payment, None)
        if coc_return is not None:
            coc_return = coc_return * 100  # as %

        # DSCR
        dscr = safe_divide(noi, annual_debt_service, None)

        # Break-even occupancy: opex + debt_service / potential gross
        potential_gross = gross_annual_rent  # 100% occupied
        break_even_occ = safe_divide(opex + annual_debt_service, potential_gross, None)
        if break_even_occ is not None:
            break_even_occ = break_even_occ * 100  # as %

    # Dat nen debt values (no income)
    if price_vnd:
        loan_amount_val      = price_vnd * LTV_RATIO
        down_payment_val     = price_vnd * (1 - LTV_RATIO)
        monthly_pmt_val      = _monthly_mortgage(loan_amount_val)
        annual_debt_val      = monthly_pmt_val * 12
    else:
        loan_amount_val = down_payment_val = monthly_pmt_val = annual_debt_val = None

    # Use computed values for debt section
    if not is_dat_nen and price_vnd:
        _loan = price_vnd * LTV_RATIO
        _down = price_vnd * (1 - LTV_RATIO)
        _mpmt = _monthly_mortgage(_loan)
        _ads  = _mpmt * 12
    else:
        _loan = loan_amount_val
        _down = down_payment_val
        _mpmt = monthly_pmt_val
        _ads  = annual_debt_val

    # ── Interest rate sensitivity ──────────────────────────────────────────────
    if is_dat_nen:
        irs = "High"
    elif dscr is None:
        irs = "High"
    elif dscr > 1.5:
        irs = "Low"
    elif dscr >= 1.1:
        irs = "Medium"
    else:
        irs = "High"

    # ── Market Metrics ────────────────────────────────────────────────────────
    momentum_score = safe_number(infra_momentum.get("momentum_score"), 0.0)

    # Liquidity score based on absorption
    dev_rating   = dev_info.get("rating", 3) if dev_info else 3
    liquidity_sc = _liquidity_score_v2(
        prop_type         = prop_type,
        area_m2           = area_m2,
        price_per_sqm_m   = price_per_m2_input,
        avg_price_per_sqm_m = avg_price_per_m2,
        absorption        = absorption,
        supply_tightness  = supply_tightness,
        developer_rating  = dev_rating,
    )
    liquidity_sc = clamp_score(liquidity_sc * _macro_modifier(macro_regime).get("liq_mult", 1.0))

    # Supply pipeline risk: high new supply + low absorption = high risk
    supply_risk_raw = 0.0
    if new_supply is not None and absorption is not None:
        # Normalise supply: 3000 units = 100 risk, 0 = 0 risk
        supply_norm = clamp(new_supply / 3000 * 100, 0, 100)
        # Low absorption amplifies risk
        absorption_penalty = clamp((1 - absorption) * 100, 0, 100)
        supply_risk_raw = clamp_score((supply_norm * 0.6 + absorption_penalty * 0.4))
    elif new_supply is not None:
        supply_risk_raw = clamp_score(new_supply / 3000 * 100)

    district_benchmark = avg_price_per_m2  # already in million VND/m²

    # ── Risk Metrics ──────────────────────────────────────────────────────────
    legal_status = _get_legal_status(prop)
    legal_risk_score = float(LEGAL_RISK.get(legal_status, LEGAL_RISK[None]))

    developer = prop.get("developer")
    dev_risk_score = _developer_risk(developer)

    overall_risk = _overall_risk_level(legal_risk_score, dev_risk_score, supply_risk_raw)

    # ── Scoring ───────────────────────────────────────────────────────────────

    # A. Valuation Attractiveness (weight 25%)
    if valuation_gap_pct is not None:
        if valuation_gap_pct > 15:
            va_base = 90.0
        elif valuation_gap_pct >= 5:
            va_base = 70 + (valuation_gap_pct - 5) / 10 * 19
        elif valuation_gap_pct >= -5:
            va_base = 45 + (valuation_gap_pct + 5) / 10 * 24
        elif valuation_gap_pct >= -15:
            va_base = 20 + (valuation_gap_pct + 15) / 10 * 24
        else:
            va_base = max(0, 19 + (valuation_gap_pct + 15) / 10 * 10)
    else:
        va_base = 50.0  # no data — neutral

    # Adjust by price vs benchmark
    if price_per_sqm_vnd is not None and avg_price_vnd_per_m2 is not None and avg_price_vnd_per_m2 > 0:
        ratio = price_per_sqm_vnd / avg_price_vnd_per_m2
        benchmark_adj = clamp((1 - ratio) * 50, -10, 10)  # ±10 pts
    else:
        benchmark_adj = 0.0

    valuation_attractiveness_score = clamp_score(va_base + benchmark_adj)

    # B. Cashflow Quality (weight 20%)
    if is_dat_nen:
        cf_base = 10.0
    elif gross_rental_yield is None or gross_rental_yield == 0:
        cf_base = 10.0
    elif gross_rental_yield >= 6:
        cf_base = 85 + clamp((gross_rental_yield - 6) / 2 * 15, 0, 15)
    elif gross_rental_yield >= 5:
        cf_base = 70 + (gross_rental_yield - 5) * 15
    elif gross_rental_yield >= 4:
        cf_base = 50 + (gross_rental_yield - 4) * 20
    elif gross_rental_yield >= 3:
        cf_base = 25 + (gross_rental_yield - 3) * 25
    else:
        cf_base = max(0, gross_rental_yield / 3 * 24)

    # DSCR adjustment
    dscr_adj = 0.0
    if dscr is not None:
        if dscr >= 1.2:
            dscr_adj = 10.0
        elif dscr >= 1.0:
            dscr_adj = 5.0
        else:
            dscr_adj = -10.0

    cashflow_quality_score = clamp_score(cf_base + dscr_adj)

    # C. Growth Potential (weight 25%)
    # Infra momentum 0-100 → 0-60 pts base
    infra_contribution = clamp(momentum_score / 100 * 60, 0, 60)

    # ROI contribution
    if projected_5y_roi is not None:
        if projected_5y_roi > 80:
            roi_contribution = 30.0
        elif projected_5y_roi >= 50:
            roi_contribution = 20 + (projected_5y_roi - 50) / 30 * 10
        elif projected_5y_roi >= 30:
            roi_contribution = 10 + (projected_5y_roi - 30) / 20 * 10
        else:
            roi_contribution = 0.0
    else:
        roi_contribution = 0.0

    growth_potential_score = clamp_score(infra_contribution + roi_contribution)

    # D. Liquidity & Exit Risk (weight 15%)
    # Area sweet spot bonus (50-80m² can-ho)
    area_bonus = 0.0
    if prop_type == "can-ho-chung-cu" and area_m2 is not None:
        if 50 <= area_m2 <= 80:
            area_bonus = 10.0

    # Property type liquidity ordering
    type_bonus = 0.0
    if prop_type == "can-ho-chung-cu":
        type_bonus = 5.0
    elif prop_type == "nha-rieng":
        type_bonus = 0.0
    else:   # dat-nen
        type_bonus = -10.0

    liquidity_exit_score = clamp_score(liquidity_sc + area_bonus + type_bonus)

    # E. Risk Adjustment (weight 15%)
    # Start at 80, subtract risk contributions
    risk_start = 80.0

    # Legal risk: 0 (very safe) to 50 (very risky) — subtract proportionally
    legal_penalty = legal_risk_score * 0.6   # max 30 pts deduction

    # Developer risk: 8 to 40
    dev_penalty = dev_risk_score * 0.375     # max 15 pts deduction

    # Supply pipeline: 0-100
    supply_penalty = supply_risk_raw * 0.1   # max 10 pts deduction

    risk_adj_score = clamp_score(risk_start - legal_penalty - dev_penalty - supply_penalty)

    # Composite score (weighted)
    composite_score = clamp_score(
        valuation_attractiveness_score * 0.25 +
        cashflow_quality_score         * 0.20 +
        growth_potential_score         * 0.25 +
        liquidity_exit_score           * 0.15 +
        risk_adj_score                 * 0.15
    )

    # ── Net Rental Yield ──────────────────────────────────────────────────────
    net_yield_pct = _net_rental_yield(
        gross_yield_pct = gross_rental_yield or 0,
        vacancy         = VACANCY_RATE,
        mgmt_fee        = MANAGEMENT_FEE,
        maint_ratio     = MAINTENANCE_RATIO,
        price_vnd       = price_vnd or 0,
    ) if not is_dat_nen and price_vnd else 0.0

    # ── Scenario Engine ───────────────────────────────────────────────────────
    scenarios = _scenario_roi(
        price_vnd       = price_vnd or 0,
        gross_yield_pct = gross_rental_yield or 0,
        growth_base_pct = growth_yoy or 8.0,
        prop_type       = prop_type,
        macro_regime    = macro_regime,
    ) if price_vnd else {}

    # ── Property Quality Score ────────────────────────────────────────────────
    quality = _property_quality_score(prop, dev_info)

    # ── Model Confidence ──────────────────────────────────────────────────────
    confidence_obj = _model_confidence(prop, market, macro, liquidity_sc)

    # ── Recommendation v2 ─────────────────────────────────────────────────────
    dev_legal_status = (dev_info or {}).get("legal_status", "clean")
    recommendation = _recommendation_v2(
        composite        = composite_score,
        liquidity_sc     = liquidity_sc,
        confidence       = confidence_obj["score"],
        dev_legal_status = dev_legal_status,
        quality_score    = quality["score"],
        scenarios        = scenarios,
        macro_regime     = macro_regime,
    )

    # ── Vietnamese Explanations ───────────────────────────────────────────────
    explanations = []

    # 1. Giá so với thị trường
    if valuation_gap_pct is not None and price_per_m2_input is not None and avg_price_per_m2 is not None:
        gap_str = f"{abs(valuation_gap_pct):.1f}%"
        if valuation_gap_pct > 10:
            explanations.append(
                f"Giá so với thị trường: BĐS đang được định giá THẤP HƠN thị trường {gap_str} "
                f"(giá hiện tại {price_per_m2_input:.0f} tr/m² vs benchmark {avg_price_per_m2:.0f} tr/m²). "
                f"Biên an toàn tốt, có dư địa tăng giá rõ ràng."
            )
        elif valuation_gap_pct < -10:
            explanations.append(
                f"Giá so với thị trường: BĐS đang định giá CAO HƠN thị trường {gap_str} "
                f"({price_per_m2_input:.0f} tr/m² vs benchmark {avg_price_per_m2:.0f} tr/m²). "
                f"Cần thương lượng hoặc chờ điều chỉnh giá."
            )
        else:
            explanations.append(
                f"Giá so với thị trường: Giá hợp lý, sát mặt bằng khu vực "
                f"({price_per_m2_input:.0f} tr/m² vs {avg_price_per_m2:.0f} tr/m²). "
                f"Chênh lệch {gap_str} — nằm trong vùng FAIR VALUE."
            )
    elif avg_price_per_m2 is not None:
        explanations.append(
            f"Giá so với thị trường: Benchmark {district} là {avg_price_per_m2:.0f} triệu/m². "
            f"Không đủ dữ liệu để so sánh chính xác."
        )

    # 2. Dòng tiền cho thuê
    if is_dat_nen:
        explanations.append(
            "Dòng tiền cho thuê: Đất nền không có thu nhập cho thuê. "
            "Lợi nhuận hoàn toàn đến từ tăng giá vốn dài hạn."
        )
    elif gross_rental_yield and monthly_rent_est:
        monthly_m = round(monthly_rent_est / 1e6, 1)
        if gross_rental_yield >= 5.5:
            grade = "xuất sắc"
        elif gross_rental_yield >= 4.5:
            grade = "tốt"
        elif gross_rental_yield >= 3.5:
            grade = "chấp nhận được"
        else:
            grade = "thấp"
        explanations.append(
            f"Dòng tiền cho thuê: Yield {gross_rental_yield:.1f}%/năm ({grade}), "
            f"ước tính ~{monthly_m} triệu/tháng. "
            f"NOI sau chi phí vận hành: {round((noi or 0)/1e6, 1)} triệu/năm."
        )
    else:
        explanations.append("Dòng tiền cho thuê: Không đủ dữ liệu để ước tính.")

    # 3. Tiềm năng tăng giá
    if projected_5y_roi is not None:
        if projected_5y_roi >= 80:
            roi_label = "rất cao"
        elif projected_5y_roi >= 50:
            roi_label = "tốt"
        elif projected_5y_roi >= 30:
            roi_label = "khá"
        else:
            roi_label = "hạn chế"
        explanations.append(
            f"Tiềm năng tăng giá: ROI 5 năm ước tính {projected_5y_roi:.1f}% ({roi_label}). "
            f"Tăng trưởng giá khu vực {growth_yoy:.0f}%/năm. "
            f"Điểm hạ tầng momentum: {momentum_score:.0f}/100."
        )

    # 4. Rủi ro pháp lý
    legal_str = legal_status or "Không xác định"
    if legal_risk_score <= 5:
        explanations.append(
            f"Rủi ro pháp lý: THẤP — {legal_str}. "
            f"Pháp lý sạch, ít rủi ro tranh chấp hay vướng quy hoạch."
        )
    elif legal_risk_score <= 20:
        explanations.append(
            f"Rủi ro pháp lý: TRUNG BÌNH — {legal_str}. "
            f"Cần kiểm tra kỹ hồ sơ pháp lý trước khi ký hợp đồng."
        )
    else:
        explanations.append(
            f"Rủi ro pháp lý: CAO — {legal_str}. "
            f"Khuyến nghị tham khảo luật sư bất động sản và kiểm tra kỹ các ràng buộc pháp lý."
        )

    # 5. Khả năng trả nợ (DSCR)
    if is_dat_nen:
        explanations.append(
            f"Khả năng trả nợ: Đất nền không có thu nhập cho thuê. "
            f"Khoản vay LTV {int(LTV_RATIO*100)}%: trả góp "
            f"~{round((_mpmt or 0)/1e6, 1)} triệu/tháng cần được bù đắp từ nguồn khác."
        )
    elif dscr is not None:
        mpmt_m = round((_mpmt or 0) / 1e6, 1)
        if dscr >= 1.2:
            dscr_label = "dòng tiền dương, an toàn vay vốn"
        elif dscr >= 1.0:
            dscr_label = "vừa đủ trả nợ, ít dư địa rủi ro"
        else:
            dscr_label = "KHÔNG đủ trả nợ từ tiền thuê — cần bổ sung từ thu nhập khác"
        explanations.append(
            f"Khả năng trả nợ (DSCR): {dscr:.2f} — {dscr_label}. "
            f"Trả góp hàng tháng ước tính ~{mpmt_m} triệu/tháng "
            f"(LTV {int(LTV_RATIO*100)}%, lãi suất {INTEREST_RATE*100:.1f}%/năm, {LOAN_TERM_YEARS} năm)."
        )
    else:
        explanations.append("Khả năng trả nợ: Không đủ dữ liệu để tính DSCR.")

    # 6. Thanh khoản khi thoát vốn
    abs_str = f"{round((absorption or 0)*100)}%" if absorption else "N/A"
    if liquidity_sc >= 80:
        liq_label = "rất tốt"
    elif liquidity_sc >= 60:
        liq_label = "tốt"
    elif liquidity_sc >= 40:
        liq_label = "trung bình"
    else:
        liq_label = "hạn chế"
    explanations.append(
        f"Thanh khoản khi thoát vốn: {liq_label} (điểm {liquidity_sc:.0f}/100). "
        f"Tỷ lệ hấp thụ khu vực {abs_str}. "
        f"Loại BĐS: {'căn hộ — thanh khoản cao nhất' if prop_type=='can-ho-chung-cu' else 'nhà riêng — thanh khoản tốt' if prop_type=='nha-rieng' else 'đất nền — thanh khoản phụ thuộc hạ tầng'}."
    )

    # 7. Chủ đầu tư
    dev_name = (developer or "Không rõ")
    if dev_risk_score <= 8:
        explanations.append(
            f"Chủ đầu tư: Tier-1 uy tín ({dev_name}). "
            f"Rủi ro thấp về tiến độ, pháp lý và chất lượng xây dựng."
        )
    elif dev_risk_score <= 22:
        explanations.append(
            f"Chủ đầu tư: Tier-2 — thương hiệu biết đến nhưng cần thẩm định kỹ ({dev_name}). "
            f"Kiểm tra tình trạng pháp lý dự án và tiến độ bàn giao trước khi quyết định."
        )
    elif dev_risk_score <= 32:
        explanations.append(
            f"Chủ đầu tư: Có thông tin ({dev_name}) nhưng không thuộc nhóm uy tín. "
            f"Nên kiểm tra lịch sử dự án trước."
        )
    else:
        explanations.append(
            f"Chủ đầu tư: Không rõ hoặc ít thông tin. "
            f"Cần xác minh năng lực và uy tín trước khi quyết định."
        )

    # 8. Composite summary
    if composite_score >= 75:
        cs_label = "hấp dẫn đầu tư"
    elif composite_score >= 60:
        cs_label = "tiềm năng tốt"
    elif composite_score >= 45:
        cs_label = "trung bình, cân nhắc kỹ"
    else:
        cs_label = "nhiều rủi ro, nên thận trọng"
    explanations.append(
        f"Tổng điểm đánh giá: {composite_score:.1f}/100 — {cs_label}. "
        f"(Định giá {valuation_attractiveness_score:.0f} · Dòng tiền {cashflow_quality_score:.0f} · "
        f"Tăng trưởng {growth_potential_score:.0f} · Thanh khoản {liquidity_exit_score:.0f} · "
        f"Rủi ro {risk_adj_score:.0f})"
    )

    # ── Assemble result ────────────────────────────────────────────────────────
    return {
        "valuation": {
            "pricePerSqm":         price_per_sqm_vnd,
            "listingPriceVND":     price_vnd,
            "fairMarketValue":     fair_market_value,
            "valuationGapPct":     round(valuation_gap_pct, 2) if valuation_gap_pct is not None else None,
            "valuationLabel":      valuation_label,
            "projected5YROI":      projected_5y_roi,
            "dataQuality": {
                "pricePerSqm":     dq_price_per_sqm,
                "fairMarketValue": dq_fmv,
            },
        },
        "income": {
            "grossRentalYield":    gross_rental_yield,
            "monthlyRentEstimate": monthly_rent_est,
            "effectiveGrossIncome": egi,
            "operatingExpenses":   opex,
            "NOI":                 noi,
            "capRate":             round(cap_rate, 3) if cap_rate is not None else None,
            "cashOnCashReturn":    round(coc_return, 3) if coc_return is not None else None,
            "DSCR":                round(dscr, 3) if dscr is not None else None,
            "breakEvenOccupancy":  round(break_even_occ, 2) if break_even_occ is not None else None,
        },
        "debt": {
            "assumedLTV":              LTV_RATIO,
            "loanAmount":              _loan,
            "downPayment":             _down,
            "monthlyMortgagePayment":  _mpmt,
            "annualDebtService":       _ads,
            "interestRateSensitivity": irs,
        },
        "market": {
            "infrastructureMomentumScore":   momentum_score,
            "liquidityScore":                round(liquidity_sc, 1),
            "supplyPipelineRiskScore":        round(supply_risk_raw, 1),
            "districtBenchmarkPricePerSqm":  district_benchmark,
            "transactionVelocity":           _transaction_velocity(absorption),
        },
        "risks": {
            "legalRiskScore":    legal_risk_score,
            "developerRiskScore": dev_risk_score,
            "overallRiskLevel":  overall_risk,
        },
        "scores": {
            "valuationAttractivenessScore": round(valuation_attractiveness_score, 1),
            "cashflowQualityScore":         round(cashflow_quality_score, 1),
            "growthPotentialScore":         round(growth_potential_score, 1),
            "liquidityExitScore":           round(liquidity_exit_score, 1),
            "riskAdjustedScore":            round(risk_adj_score, 1),
            "compositeScore":               round(composite_score, 1),
        },
        "explanations":   explanations,
        "scenarios":      scenarios,
        "netYield":       net_yield_pct,
        "quality":        quality,
        "confidence":     confidence_obj,
        "recommendation": recommendation,
    }
