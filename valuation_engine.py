"""
Valuation Engine — BDS TP.HCM
Tính toán định giá tài chính nâng cao cho từng bất động sản.
Tất cả hằng số là module-level, không hardcode per-property.
"""

from typing import Optional

# ─── Module-level Assumptions ─────────────────────────────────────────────────
LTV_RATIO       = 0.70   # 70% loan-to-value (ngân hàng VN tiêu chuẩn)
LOAN_TERM_YEARS = 20
INTEREST_RATE   = 0.085  # 8.5% — từ analyzer.MORTGAGE_RATE_CURRENT
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
TIER1_DEVS = [
    "Vingroup", "Masterise", "CapitaLand", "KeppelLand", "Nam Long",
    "Phú Mỹ Hưng", "Novaland", "Gamuda", "Hưng Thịnh",
]


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
        return 40.0   # không rõ chủ đầu tư
    dev = str(developer)
    for t1 in TIER1_DEVS:
        if t1.lower() in dev.lower():
            return 8.0
    return 20.0   # biết tên nhưng không phải tier-1


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


# ─── Main valuation function ──────────────────────────────────────────────────

def compute_valuation(
    prop: dict,
    market: dict,
    district: str,
    infra_momentum: dict,
    macro: dict,
) -> dict:
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
    valuation_label   = "Unknown"
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
    if absorption is not None:
        if absorption >= 0.85:
            liquidity_sc = clamp_score(85 + (absorption - 0.85) * 100)
        elif absorption >= 0.70:
            liquidity_sc = clamp_score(60 + (absorption - 0.70) / 0.15 * 24)
        elif absorption >= 0.55:
            liquidity_sc = clamp_score(35 + (absorption - 0.55) / 0.15 * 24)
        else:
            liquidity_sc = clamp_score(absorption / 0.55 * 34)
    else:
        liquidity_sc = 50.0  # default

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
    elif dev_risk_score <= 20:
        explanations.append(
            f"Chủ đầu tư: Có thông tin ({dev_name}) nhưng không phải tier-1. "
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
        "explanations": explanations,
    }
