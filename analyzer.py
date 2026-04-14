"""
Real Estate Analyzer - áp dụng framework từ real-estate-analyzer skill
Phân tích & recommend BĐS 3-5 tỷ tại TP.HCM (kết hợp phân tích hạ tầng)
"""
import json
from dataclasses import dataclass
from typing import Optional
from collections import defaultdict
from infrastructure import get_infra_score, get_infra_momentum, infra_multiplier, INFRA_PROJECTS, Status


# ──────────────────────────────────────────────
# Dữ liệu thị trường tham chiếu TP.HCM (2024-2025)
# Nguồn: CBRE, Savills, VARS reports
# ──────────────────────────────────────────────
MARKET_DATA = {
    "can-ho-chung-cu": {
        # Nội thành
        "Quận 1":    {"avg_price_per_m2": 120, "rental_yield": 3.5, "growth_yoy": 8},
        "Quận 3":    {"avg_price_per_m2": 90,  "rental_yield": 3.8, "growth_yoy": 7},
        "Quận 4":    {"avg_price_per_m2": 72,  "rental_yield": 4.2, "growth_yoy": 9},
        "Quận 5":    {"avg_price_per_m2": 65,  "rental_yield": 4.0, "growth_yoy": 7},
        "Quận 6":    {"avg_price_per_m2": 46,  "rental_yield": 5.0, "growth_yoy": 10},
        "Quận 8":    {"avg_price_per_m2": 52,  "rental_yield": 4.8, "growth_yoy": 12},
        "Quận 10":   {"avg_price_per_m2": 62,  "rental_yield": 4.3, "growth_yoy": 8},
        "Quận 11":   {"avg_price_per_m2": 52,  "rental_yield": 4.8, "growth_yoy": 9},
        "Quận 12":   {"avg_price_per_m2": 38,  "rental_yield": 5.8, "growth_yoy": 13},
        # Mở rộng
        "Quận 7":    {"avg_price_per_m2": 65,  "rental_yield": 4.5, "growth_yoy": 9},
        "Bình Thạnh":{"avg_price_per_m2": 62,  "rental_yield": 4.8, "growth_yoy": 10},
        "Gò Vấp":    {"avg_price_per_m2": 48,  "rental_yield": 5.2, "growth_yoy": 11},
        "Tân Bình":  {"avg_price_per_m2": 56,  "rental_yield": 5.0, "growth_yoy": 9},
        "Tân Phú":   {"avg_price_per_m2": 48,  "rental_yield": 5.2, "growth_yoy": 10},
        "Bình Tân":  {"avg_price_per_m2": 42,  "rental_yield": 5.5, "growth_yoy": 11},
        "Thủ Đức":   {"avg_price_per_m2": 55,  "rental_yield": 5.2, "growth_yoy": 13},
        # Ngoại thành
        "Nhà Bè":    {"avg_price_per_m2": 38,  "rental_yield": 5.0, "growth_yoy": 11},
        "Bình Chánh":{"avg_price_per_m2": 34,  "rental_yield": 5.2, "growth_yoy": 12},
        "Hóc Môn":   {"avg_price_per_m2": 28,  "rental_yield": 5.0, "growth_yoy": 10},
    },
}

# ──────────────────────────────────────────────────────────────────────
# MACRO DATA — Supply Tightness · Credit Growth · Mortgage Growth
# Nguồn: CBRE Q1/2026, SBV banking report 2025, HoREA, VARS
# ──────────────────────────────────────────────────────────────────────
# supply_tightness: 1–10 (10 = cực khan hiếm nguồn cung mới)
#   → Phản ánh tỷ lệ hàng tồn kho / số giao dịch trung bình 12 tháng
# credit_growth_yoy: % tăng trưởng tín dụng toàn nền kinh tế (city-wide)
# mortgage_growth_yoy: % tăng trưởng dư nợ vay mua BĐS (theo quận/khu vực)
# new_supply_units_qtr: số căn mới mở bán Q1/2026 trong khu vực
# absorption_rate: % căn bán được / tổng mở bán (cao = hấp thụ tốt)
MACRO_DATA = {
    # ── Nội thành cũ ─────────────────────────────────────────────────
    "Quận 1":    {"supply_tightness": 9.5, "new_supply_units_qtr": 0,   "absorption_rate": 0.95, "mortgage_growth_yoy": 14},
    "Quận 3":    {"supply_tightness": 9.0, "new_supply_units_qtr": 120, "absorption_rate": 0.92, "mortgage_growth_yoy": 13},
    "Quận 4":    {"supply_tightness": 8.8, "new_supply_units_qtr": 80,  "absorption_rate": 0.90, "mortgage_growth_yoy": 15},
    "Quận 5":    {"supply_tightness": 8.5, "new_supply_units_qtr": 60,  "absorption_rate": 0.88, "mortgage_growth_yoy": 12},
    "Quận 6":    {"supply_tightness": 7.0, "new_supply_units_qtr": 300, "absorption_rate": 0.75, "mortgage_growth_yoy": 11},
    "Quận 8":    {"supply_tightness": 7.2, "new_supply_units_qtr": 450, "absorption_rate": 0.78, "mortgage_growth_yoy": 13},
    "Quận 10":   {"supply_tightness": 8.2, "new_supply_units_qtr": 100, "absorption_rate": 0.85, "mortgage_growth_yoy": 12},
    "Quận 11":   {"supply_tightness": 8.0, "new_supply_units_qtr": 90,  "absorption_rate": 0.83, "mortgage_growth_yoy": 11},
    "Quận 12":   {"supply_tightness": 6.0, "new_supply_units_qtr": 800, "absorption_rate": 0.70, "mortgage_growth_yoy": 14},
    # ── Mở rộng ──────────────────────────────────────────────────────
    "Quận 7":    {"supply_tightness": 7.5, "new_supply_units_qtr": 600, "absorption_rate": 0.80, "mortgage_growth_yoy": 16},
    "Bình Thạnh":{"supply_tightness": 7.8, "new_supply_units_qtr": 350, "absorption_rate": 0.82, "mortgage_growth_yoy": 14},
    "Gò Vấp":    {"supply_tightness": 6.8, "new_supply_units_qtr": 500, "absorption_rate": 0.73, "mortgage_growth_yoy": 12},
    "Tân Bình":  {"supply_tightness": 7.5, "new_supply_units_qtr": 280, "absorption_rate": 0.80, "mortgage_growth_yoy": 13},
    "Tân Phú":   {"supply_tightness": 6.5, "new_supply_units_qtr": 420, "absorption_rate": 0.72, "mortgage_growth_yoy": 12},
    "Bình Tân":  {"supply_tightness": 5.8, "new_supply_units_qtr": 900, "absorption_rate": 0.65, "mortgage_growth_yoy": 11},
    "Thủ Đức":   {"supply_tightness": 6.2, "new_supply_units_qtr":2800, "absorption_rate": 0.68, "mortgage_growth_yoy": 18},
    # ── Ngoại thành ──────────────────────────────────────────────────
    "Nhà Bè":    {"supply_tightness": 7.0, "new_supply_units_qtr": 400, "absorption_rate": 0.72, "mortgage_growth_yoy": 15},
    "Bình Chánh":{"supply_tightness": 5.5, "new_supply_units_qtr":1200, "absorption_rate": 0.60, "mortgage_growth_yoy": 12},
    "Hóc Môn":   {"supply_tightness": 5.0, "new_supply_units_qtr": 600, "absorption_rate": 0.58, "mortgage_growth_yoy": 10},
    "Củ Chi":    {"supply_tightness": 4.0, "new_supply_units_qtr": 300, "absorption_rate": 0.50, "mortgage_growth_yoy":  9},
    # ── City-wide macro (áp dụng nếu không tìm thấy quận) ────────────
    "_citywide": {"supply_tightness": 6.5, "new_supply_units_qtr": 500, "absorption_rate": 0.72, "mortgage_growth_yoy": 13},
}

# Credit growth toàn TP.HCM (SBV, áp dụng chung — không phân theo quận)
CREDIT_GROWTH_YOY = 14.5   # % — Q4/2025, target 2026: 16%
MORTGAGE_RATE_CURRENT = 8.5  # % — lãi suất vay mua nhà hiện tại (giảm từ 12% năm 2023)
MORTGAGE_RATE_TREND = "decreasing"  # "decreasing" | "stable" | "increasing"

def get_macro(district: str) -> dict:
    return MACRO_DATA.get(district, MACRO_DATA["_citywide"])


# Điểm hấp dẫn đầu tư theo quận (infrastructure, quy hoạch, tăng trưởng dân số)
DISTRICT_SCORE = {
    "Thủ Đức": 9.2,   # TP mới, Metro số 1, hạ tầng bùng nổ
    "Quận 7":  8.8,   # Phú Mỹ Hưng, expat area, quy hoạch tốt
    "Quận 4":  8.5,   # Gần Q1, nguồn cung hạn chế, giá tăng ổn
    "Bình Thạnh": 8.5, # Trung tâm mở rộng, sát Q1
    "Quận 1":  8.0,   # Trung tâm, premium, tăng chậm nhưng ổn định
    "Quận 3":  7.8,   # Nội thành cũ, giá cao nhưng ổn định
    "Gò Vấp":  7.8,   # Dân số đông, hạ tầng cải thiện
    "Tân Bình": 7.8,  # Gần sân bay, kết nối tốt
    "Quận 8":  7.5,   # Đang tái cơ cấu, hạ tầng Q8 đang mạnh, tiềm năng cao
    "Quận 10": 7.5,   # Nội thành cũ, khan hiếm nguồn cung mới
    "Quận 11": 7.2,   # Nội thành, ổn định
    "Tân Phú": 7.5,   # Dân số đông, giá hợp lý
    "Bình Tân": 7.0,  # Công nhân, yield tốt, tăng trưởng ổn
    "Quận 6":  7.0,   # Kết nối Q5-Q11-Bình Tân
    "Quận 5":  7.2,   # Cộng đồng Hoa, ổn định
    "Quận 12": 7.5,   # Hạ tầng đang cải thiện
    "Nhà Bè":  7.8,   # Vành đai 3, hạ tầng tiềm năng
    "Bình Chánh": 7.3, # Nguồn cung lớn, Vành đai 3
    "Hóc Môn": 6.8,
    "Củ Chi":  6.0,
    "Cần Giờ": 6.5,
    "Khác": 6.0,
}


def invest_recommendation(yield_pct: float, infra_sc: float, infra_projs: list[str]) -> tuple[str, str, str, str]:
    """
    Trả về (verdict, color, bg, detail) dựa thuần trên:
      - Tỷ suất sinh lời = yield_pct (tiền thuê hàng năm / giá trị tài sản)
      - Tiềm năng hạ tầng = infra_sc + danh sách dự án gần đó
    """
    # --- Yield score (0-3) ---
    if yield_pct >= 5.5:
        y_pts, y_label = 3, f"Yield {yield_pct}% ✦ Xuất sắc"
    elif yield_pct >= 4.5:
        y_pts, y_label = 2, f"Yield {yield_pct}% ✦ Tốt"
    elif yield_pct >= 3.5:
        y_pts, y_label = 1, f"Yield {yield_pct}% ✦ Chấp nhận"
    else:
        y_pts, y_label = 0, f"Yield {yield_pct}% ✦ Thấp"

    # --- Infra score (0-3) ---
    active_projs = [p for p in infra_projs if any(
        kw in p for kw in ["đang thi công", "đã duyệt", "Đang", "UNDER", "APPROVED"]
    )]
    if infra_sc >= 35:
        i_pts, i_label = 3, f"HT Bùng nổ ({infra_sc:.0f}đ)"
    elif infra_sc >= 20:
        i_pts, i_label = 2, f"HT Tiềm năng ({infra_sc:.0f}đ)"
    elif infra_sc >= 10:
        i_pts, i_label = 1, f"HT Khởi sắc ({infra_sc:.0f}đ)"
    else:
        i_pts, i_label = 0, f"HT Ổn định ({infra_sc:.0f}đ)"

    total = y_pts + i_pts

    if total >= 5:
        verdict, color, bg = "MUA NGAY",  "#14532d", "#dcfce7"
    elif total >= 4:
        verdict, color, bg = "NÊN MUA",   "#166534", "#bbf7d0"
    elif total >= 3:
        verdict, color, bg = "CÂN NHẮC",  "#92400e", "#fef3c7"
    elif total >= 2:
        verdict, color, bg = "CHỜ THÊM",  "#9a3412", "#ffedd5"
    else:
        verdict, color, bg = "TRÁNH",     "#7f1d1d", "#fee2e2"

    detail = f"{y_label}\n{i_label}"
    return verdict, color, bg, detail


@dataclass
class AnalysisResult:
    property: dict
    score: float
    verdict: str          # BUY / HOLD / SKIP
    value_vs_market: str  # UNDERVALUED / FAIR / OVERVALUED
    rental_yield_est: Optional[float]
    roi_5yr: Optional[float]
    reasons: list[str]
    explanations: list[str] = None   # Giải thích thân thiện cho KH
    infra_score: float = 0.0
    infra_projects: list[str] = None
    infra_momentum: dict = None      # Chi tiết momentum: active_projects, investment, timeline
    # Macro signals
    supply_tightness: float = 0.0
    absorption_rate: float = 0.0
    mortgage_growth: float = 0.0
    # Gợi ý đầu tư thuần từ yield + hạ tầng
    invest_verdict: str = ""
    invest_color: str = "#374151"
    invest_bg: str = "#f3f4f6"
    invest_detail: str = ""


def get_market_ref(prop_type: str, district: str) -> Optional[dict]:
    type_data = MARKET_DATA.get(prop_type, {})
    return type_data.get(district) or type_data.get("Khác")


def calc_score(prop: dict, market: dict, district: str) -> tuple[float, list[str], list[str]]:
    """
    Returns (score, reasons, explanations)
    - reasons: ngắn gọn cho analyst
    - explanations: giải thích thân thiện cho khách hàng
    """
    score = 50.0
    reasons = []
    explanations = []

    macro = get_macro(district)
    price_per_m2 = prop.get("price_per_m2_million")
    avg = market.get("avg_price_per_m2", 0)

    # 1. So sánh giá với thị trường
    if price_per_m2 and avg:
        ratio = price_per_m2 / avg
        if ratio < 0.85:
            score += 20
            pct = round((1 - ratio) * 100)
            reasons.append(f"Giá thấp hơn thị trường {pct}% → tiềm năng tăng giá tốt")
            explanations.append(
                f"💰 **Giá hời {pct}% so với mặt bằng khu vực** — Giá/m² của căn này là "
                f"{price_per_m2} triệu, trong khi trung bình {district} là {avg} triệu/m². "
                f"Chênh lệch này tạo ra vùng đệm an toàn và dư địa tăng giá tốt."
            )
        elif ratio < 0.95:
            score += 10
            pct = round((1 - ratio) * 100)
            reasons.append(f"Giá hợp lý, thấp hơn mặt bằng ~{pct}%")
            explanations.append(
                f"✅ **Giá hợp lý, nhỉnh hơn trung bình {pct}%** — Không phải bargain nhưng cũng "
                f"không đắt. Mức giá này phù hợp với chất lượng và vị trí của căn hộ."
            )
        elif ratio > 1.15:
            score -= 15
            pct = round((ratio - 1) * 100)
            reasons.append(f"Giá cao hơn thị trường {pct}% → rủi ro đỉnh giá")
            explanations.append(
                f"⚠️ **Giá cao hơn thị trường {pct}%** — Cần thương lượng hoặc chờ điều chỉnh. "
                f"Mua ở mức này tiềm ẩn rủi ro nếu thị trường sideways trong 1–2 năm tới."
            )
        else:
            reasons.append("Giá sát mặt bằng thị trường")
            explanations.append(f"📊 **Giá đúng thị trường** — Giá/m² sát mặt bằng khu vực, không có premium cũng không discount đặc biệt.")

    # 2. Rental yield
    yield_pct = market.get("rental_yield", 0)
    if yield_pct >= 5:
        score += 15
        reasons.append(f"Rental yield ước tính {yield_pct}% → dòng tiền tốt")
        monthly = round(prop.get("price_billion", 4) * 1e9 * yield_pct / 100 / 12 / 1e6, 1)
        explanations.append(
            f"🏠 **Cho thuê ước tính ~{monthly} triệu/tháng (yield {yield_pct}%/năm)** — "
            f"Đây là mức yield tốt so với gửi ngân hàng (~5–6%). Căn hộ tự trang trải được "
            f"phần lớn lãi vay nếu đầu tư có đòn bẩy."
        )
    elif yield_pct >= 4:
        score += 8
        monthly = round(prop.get("price_billion", 4) * 1e9 * yield_pct / 100 / 12 / 1e6, 1)
        reasons.append(f"Rental yield {yield_pct}% — chấp nhận được")
        explanations.append(
            f"🏠 **Cho thuê ước tính ~{monthly} triệu/tháng (yield {yield_pct}%/năm)** — "
            f"Chấp nhận được. Lợi nhuận chính đến từ tăng giá dài hạn, không phải dòng tiền thuê."
        )
    elif yield_pct < 3:
        score -= 10
        reasons.append(f"Rental yield thấp ({yield_pct}%) — phù hợp đầu tư dài hạn hơn cho thuê")
        explanations.append(
            f"📉 **Yield thấp ({yield_pct}%)** — Không phù hợp nếu mục tiêu chính là dòng tiền cho thuê. "
            f"Chỉ nên mua nếu tin vào tăng giá dài hạn của khu vực này."
        )

    # 3. Supply tightness — nguồn cung
    tightness = macro.get("supply_tightness", 6.5)
    absorption = macro.get("absorption_rate", 0.72)
    new_supply = macro.get("new_supply_units_qtr", 500)
    if tightness >= 8.5:
        score += 12
        reasons.append(f"Supply cực khan hiếm ({district}) — tightness {tightness}/10")
        explanations.append(
            f"🔒 **Nguồn cung rất khan hiếm tại {district}** — Khu vực này gần như không còn đất "
            f"để xây mới (tightness {tightness}/10). Chỉ có {new_supply} căn mở bán/quý, "
            f"tỷ lệ hấp thụ {round(absorption*100)}%. Cung thấp + cầu ổn định = giá khó giảm."
        )
    elif tightness >= 7.0:
        score += 6
        reasons.append(f"Nguồn cung hạn chế ({district}) — tightness {tightness}/10")
        explanations.append(
            f"📦 **Nguồn cung kiểm soát được tại {district}** — {new_supply} căn/quý với "
            f"absorption rate {round(absorption*100)}%. Thị trường cân bằng, không có rủi ro "
            f"dư cung gây áp lực giá."
        )
    elif tightness < 5.5:
        score -= 8
        reasons.append(f"Nguồn cung dồi dào ({district}) — rủi ro áp lực giá")
        explanations.append(
            f"⚠️ **Nguồn cung lớn tại {district}** — {new_supply} căn/quý với absorption rate "
            f"chỉ {round(absorption*100)}%. Dư cung có thể tạo áp lực giảm giá ngắn hạn. "
            f"Nên chờ absorption rate cải thiện trước khi xuống tiền."
        )

    # 4. Mortgage growth — tín hiệu nhu cầu vay
    mg = macro.get("mortgage_growth_yoy", 13)
    if mg >= 16:
        score += 8
        reasons.append(f"Mortgage growth {mg}%/năm — nhu cầu mua nhà tăng mạnh")
        explanations.append(
            f"📈 **Tăng trưởng vay mua nhà {mg}%/năm tại {district}** — Đây là tín hiệu nhu cầu "
            f"thực cao. Nhiều người đang vay mua nhà khu vực này = thanh khoản tốt khi bạn cần bán."
        )
    elif mg >= 13:
        score += 4
        reasons.append(f"Mortgage growth {mg}%/năm — nhu cầu ổn định")
        explanations.append(
            f"📊 **Tăng trưởng vay mua nhà {mg}%/năm** — Ổn định. Lãi suất đang giảm về ~{MORTGAGE_RATE_CURRENT}% "
            f"giúp người mua dễ tiếp cận hơn, hỗ trợ thanh khoản thị trường."
        )

    # 5. Tăng trưởng khu vực (giá lịch sử)
    growth = market.get("growth_yoy", 0)
    if growth >= 12:
        score += 15
        reasons.append(f"Khu vực tăng trưởng mạnh {growth}%/năm")
        explanations.append(
            f"🚀 **Tăng trưởng giá {growth}%/năm** — Mức tăng vượt trội. Nếu duy trì, "
            f"căn hộ này sẽ tăng gần gấp đôi sau 5–6 năm (quy tắc 72)."
        )
    elif growth >= 8:
        score += 8
        reasons.append(f"Tăng trưởng ổn định {growth}%/năm")
        explanations.append(
            f"📈 **Tăng trưởng giá lịch sử {growth}%/năm** — Ổn định và bền vững. "
            f"Cao hơn lạm phát trung bình, giúp bảo toàn giá trị tài sản thực."
        )

    # 6. Điểm hấp dẫn quận
    d_score = DISTRICT_SCORE.get(district, 6.0)
    if d_score >= 8.5:
        score += 10
        reasons.append(f"Vị trí chiến lược (điểm quận: {d_score}/10)")
        explanations.append(
            f"📍 **{district} — vị trí chiến lược ({d_score}/10)** — Quận này có hạ tầng hoàn thiện, "
            f"quy hoạch rõ ràng và nhu cầu thuê/mua bền vững từ người có thu nhập cao."
        )
    elif d_score >= 7.5:
        score += 5
        explanations.append(
            f"📍 **{district} — khu vực tốt ({d_score}/10)** — Tiện ích đầy đủ, "
            f"kết nối giao thông ổn và có thanh khoản tốt trên thị trường thứ cấp."
        )

    # 7. Diện tích
    area = prop.get("area_m2")
    if area and prop.get("property_type") == "can-ho-chung-cu":
        if 50 <= area <= 80:
            score += 5
            reasons.append(f"Diện tích {area}m² — thanh khoản cao")
            explanations.append(
                f"📐 **Diện tích {area}m² — sweet spot thị trường** — Căn 50–80m² là phân khúc "
                f"dễ cho thuê và dễ bán lại nhất, đặc biệt với người thuê gia đình nhỏ 2–3 người."
            )
        elif area < 40:
            score -= 5
            reasons.append(f"Diện tích nhỏ ({area}m²) — khó cho thuê")
            explanations.append(
                f"📐 **Diện tích chỉ {area}m²** — Quá nhỏ cho gia đình, hạn chế đối tượng thuê. "
                f"Phù hợp hơn cho người độc thân hoặc studio airbnb."
            )

    # 8. Hạ tầng tiềm năng
    infra_sc, infra_projects = get_infra_score(district)
    if infra_sc >= 50:
        score += 20
        reasons.append(f"Hạ tầng BÙNG NỔ (điểm {infra_sc:.0f}/100) — {len(infra_projects)} dự án lớn")
        explanations.append(
            f"🏗️ **Hạ tầng bùng nổ — điểm {infra_sc:.0f}/100** — Khu vực đang có {len(infra_projects)} "
            f"dự án hạ tầng lớn. Khi các dự án này hoàn thành, giá BĐS thường tăng 20–40% "
            f"so với trước khi dự án hoàn thành."
        )
    elif infra_sc >= 30:
        score += 12
        reasons.append(f"Hạ tầng TĂNG MẠNH (điểm {infra_sc:.0f}/100) — {len(infra_projects)} dự án")
        explanations.append(
            f"🏗️ **Hạ tầng đang được đầu tư mạnh — điểm {infra_sc:.0f}/100** — Có {len(infra_projects)} "
            f"dự án đang triển khai gần khu vực. Đây là tín hiệu tích cực cho tăng giá trung hạn."
        )
    elif infra_sc >= 15:
        score += 6
        reasons.append(f"Hạ tầng TIỀM NĂNG (điểm {infra_sc:.0f}/100)")
        explanations.append(
            f"🏗️ **Hạ tầng có tiềm năng — điểm {infra_sc:.0f}/100** — Một số dự án đang được quy hoạch "
            f"hoặc phê duyệt. Theo dõi tiến độ để có thời điểm mua phù hợp."
        )

    # Áp dụng multiplier hạ tầng lên toàn bộ score
    score = score * infra_multiplier(district)

    return min(max(score, 0), 100), reasons, explanations


def value_assessment(price_per_m2: Optional[float], avg: float) -> str:
    if not price_per_m2 or not avg:
        return "UNKNOWN"
    ratio = price_per_m2 / avg
    if ratio < 0.90:
        return "UNDERVALUED"
    if ratio > 1.10:
        return "OVERVALUED"
    return "FAIR"


def analyze(props: list[dict]) -> list[AnalysisResult]:
    results = []
    for prop in props:
        prop_type = prop.get("property_type", "can-ho-chung-cu")
        district  = prop.get("district", "Khác")
        market    = get_market_ref(prop_type, district)

        if not market:
            market = {"avg_price_per_m2": 50, "rental_yield": 4.0, "growth_yoy": 8}

        score, reasons, explanations = calc_score(prop, market, district)

        # Verdict
        if score >= 75:
            verdict = "BUY"
        elif score >= 55:
            verdict = "HOLD"
        else:
            verdict = "SKIP"

        # Ước tính rental yield
        price_b = prop.get("price_billion", 4)
        area    = prop.get("area_m2")
        yield_pct = market.get("rental_yield", 0)
        rental_monthly = (price_b * 1e9 * yield_pct / 100) / 12 if yield_pct else None

        # ROI 5 năm (tăng giá + cho thuê + hạ tầng bonus)
        growth = market.get("growth_yoy", 8) / 100
        infra_sc, infra_projs = get_infra_score(district)
        roi_5yr = None
        if yield_pct:
            capital_gain = ((1 + growth) ** 5 - 1) * 100
            rental_total = yield_pct * 5 * 0.85  # -15% chi phí quản lý
            # Hạ tầng bonus: dự án đang thi công/đã duyệt sẽ hiện thực hóa trong 5 năm
            active_impact = sum(
                p.price_impact_pct * 0.6
                for p in INFRA_PROJECTS
                if district in p.districts_affected
                and p.status in (Status.UNDER_CONST, Status.APPROVED)
            )
            roi_5yr = round(capital_gain + rental_total + active_impact * 0.3, 1)

        # Gợi ý đầu tư: yield + hạ tầng
        iv, ic, ib, id_ = invest_recommendation(yield_pct or 0, infra_sc, infra_projs)

        # Lấy tên các dự án đang thi công / đã duyệt gần quận
        nearby_active = [
            p for p in INFRA_PROJECTS
            if district in p.districts_affected
            and p.status in (Status.UNDER_CONST, Status.APPROVED)
        ]
        nearby_names = [p.name for p in sorted(nearby_active, key=lambda x: x.price_impact_pct, reverse=True)[:3]]
        invest_detail_full = id_
        if nearby_names:
            invest_detail_full += "\n" + " · ".join(nearby_names)

        # Macro signals
        macro = get_macro(district)

        # Infrastructure momentum
        momentum = get_infra_momentum(district)

        results.append(AnalysisResult(
            property=prop,
            score=round(score, 1),
            verdict=verdict,
            value_vs_market=value_assessment(prop.get("price_per_m2_million"), market["avg_price_per_m2"]),
            rental_yield_est=yield_pct,
            roi_5yr=roi_5yr,
            reasons=reasons,
            explanations=explanations,
            infra_score=round(infra_sc, 1),
            infra_projects=infra_projs,
            infra_momentum=momentum,
            supply_tightness=macro.get("supply_tightness", 0),
            absorption_rate=macro.get("absorption_rate", 0),
            mortgage_growth=macro.get("mortgage_growth_yoy", 0),
            invest_verdict=iv,
            invest_color=ic,
            invest_bg=ib,
            invest_detail=invest_detail_full,
        ))

    return sorted(results, key=lambda x: x.score, reverse=True)


def print_report(results: list[AnalysisResult], top_n: int = 10):
    buy   = [r for r in results if r.verdict == "BUY"]
    hold  = [r for r in results if r.verdict == "HOLD"]
    skip  = [r for r in results if r.verdict == "SKIP"]

    print("\n" + "="*70)
    print("   BÁO CÁO PHÂN TÍCH BĐS TP.HCM — MỨC GIÁ 3-5 TỶ VND")
    print("="*70)
    print(f"\nTổng listings phân tích: {len(results)}")
    print(f"  BUY  : {len(buy)} ({len(buy)*100//max(len(results),1)}%)")
    print(f"  HOLD : {len(hold)}")
    print(f"  SKIP : {len(skip)}")

    print(f"\n{'─'*70}")
    print(f"  TOP {min(top_n, len(buy))} NÊN MUA NGAY")
    print(f"{'─'*70}")

    for i, r in enumerate(buy[:top_n], 1):
        p = r.property
        infra_label = ""
        if r.infra_score >= 50:   infra_label = " | HT: BÙNG NỔ"
        elif r.infra_score >= 30: infra_label = " | HT: TĂNG MẠNH"
        elif r.infra_score >= 15: infra_label = " | HT: TIỀM NĂNG"

        print(f"\n#{i}  [{r.verdict}]  Score: {r.score}/100  |  {r.value_vs_market}{infra_label}")
        print(f"   {p['title'][:65]}")
        print(f"   Giá: {p['price_billion']} tỷ  |  Quận: {p['district']}")
        if p.get("area_m2"):
            print(f"   Diện tích: {p['area_m2']}m²  |  Giá/m²: {p.get('price_per_m2_million')} triệu")
        if r.roi_5yr:
            print(f"   ROI 5 năm ước tính: {r.roi_5yr}%  |  Yield: {r.rental_yield_est}%/năm")
        print(f"   Phân tích:")
        for reason in r.reasons:
            print(f"     • {reason}")
        if r.infra_projects:
            print(f"   Hạ tầng (điểm {r.infra_score}/100):")
            for proj in r.infra_projects[:3]:
                print(f"     → {proj}")
        if p.get("url"):
            print(f"   Link: {p['url']}")

    # Phân tích theo quận + hạ tầng
    print(f"\n{'─'*70}")
    print("  BẢNG XẾP HẠNG QUẬN — KẾT HỢP THỊ TRƯỜNG + HẠ TẦNG")
    print(f"{'─'*70}")
    by_district: dict[str, list[AnalysisResult]] = defaultdict(list)
    for r in results:
        by_district[r.property["district"]].append(r)

    district_summary = []
    for d, res_list in by_district.items():
        avg_score    = sum(r.score for r in res_list) / len(res_list)
        infra_sc, _  = get_infra_score(d)
        buy_count    = sum(1 for r in res_list if r.verdict == "BUY")
        district_summary.append((d, avg_score, infra_sc, buy_count, len(res_list)))

    district_summary.sort(key=lambda x: x[1], reverse=True)
    print(f"  {'Quận':<15} {'Avg Score':>9}  {'HT Score':>8}  {'BUY/Total':>10}  Nhận xét")
    print(f"  {'─'*62}")
    for d, avg, ht, buys, total in district_summary:
        ht_label = "BÙNG NỔ" if ht >= 50 else ("TĂNG MẠNH" if ht >= 30 else ("TIỀM NĂNG" if ht >= 15 else "Ổn định"))
        print(f"  {d:<15} {avg:>9.1f}  {ht:>8.1f}  {buys:>4}/{total:<5}  {ht_label}")

    print(f"\n{'─'*70}")
    print("  KẾT LUẬN & THỜI ĐIỂM MUA")
    print(f"{'─'*70}")
    # Tìm quận tốt nhất từ data
    top_district = district_summary[0][0] if district_summary else "Thủ Đức"
    top_infra_districts = [d for d, _, ht, _, _ in district_summary if ht >= 30]

    print(f"""
  TIMING (Q2/2025):
  • Lãi suất cho vay đang giảm về ~8-9% → cửa sổ mua tốt
  • Thị trường phục hồi sau điều chỉnh 2022-2023
  • Vành đai 3 sắp hoàn thành (2026) → mua trước khi thị trường phản ánh đủ

  TOP QUẬN NÊN MUA (kết hợp giá + hạ tầng):
  {chr(10).join(f"  {i+1}. {d} — HT score {ht:.0f}/100" for i, (d, _, ht, _, _) in enumerate(district_summary[:4]))}

  CHIẾN LƯỢC:
  • Ưu tiên: Căn hộ 2PN 60-75m² gần ga Metro đang/sắp mở
  • Trung hạn: Đất nền ven Vành đai 3 (mua trước khi đường thông)
  • Tránh: BĐS không có quy hoạch hạ tầng rõ ràng trong 5 năm tới
    """)


if __name__ == "__main__":
    import sys
    data_file = sys.argv[1] if len(sys.argv) > 1 else "real-estate-bot/data.json"

    try:
        with open(data_file, encoding="utf-8") as f:
            props = json.load(f)
        print(f"Loaded {len(props)} properties từ {data_file}")
    except FileNotFoundError:
        # Demo mode với dữ liệu mẫu
        print("Không tìm thấy data.json — chạy demo với dữ liệu mẫu")
        props = [
            {"title": "Căn hộ Vinhomes Grand Park 2PN", "price_billion": 3.2, "area_m2": 65,
             "price_per_m2_million": 49.2, "location": "Quận 9, TP.HCM", "district": "Thủ Đức",
             "bedrooms": 2, "url": "https://batdongsan.com.vn/...", "property_type": "can-ho-chung-cu"},
            {"title": "Căn hộ Masteri Thảo Điền 2PN view sông", "price_billion": 4.8, "area_m2": 72,
             "price_per_m2_million": 66.7, "location": "Quận 2, TP.HCM", "district": "Thủ Đức",
             "bedrooms": 2, "url": "https://batdongsan.com.vn/...", "property_type": "can-ho-chung-cu"},
            {"title": "Nhà hẻm xe hơi Gò Vấp 3PN 1 lầu", "price_billion": 3.9, "area_m2": 48,
             "price_per_m2_million": 81.2, "location": "Gò Vấp, TP.HCM", "district": "Gò Vấp",
             "bedrooms": 3, "url": "https://batdongsan.com.vn/...", "property_type": "nha-rieng"},
            {"title": "Căn hộ The Sun Avenue 2PN Quận 2", "price_billion": 4.1, "area_m2": 70,
             "price_per_m2_million": 58.6, "location": "Quận 2, TP.HCM", "district": "Thủ Đức",
             "bedrooms": 2, "url": "https://batdongsan.com.vn/...", "property_type": "can-ho-chung-cu"},
            {"title": "Đất nền sổ đỏ Bình Chánh", "price_billion": 3.5, "area_m2": 100,
             "price_per_m2_million": 35.0, "location": "Bình Chánh, TP.HCM", "district": "Bình Chánh",
             "bedrooms": None, "url": "https://batdongsan.com.vn/...", "property_type": "dat-nen"},
            {"title": "Căn hộ Sunrise City Quận 7 2PN", "price_billion": 4.5, "area_m2": 85,
             "price_per_m2_million": 52.9, "location": "Quận 7, TP.HCM", "district": "Quận 7",
             "bedrooms": 2, "url": "https://batdongsan.com.vn/...", "property_type": "can-ho-chung-cu"},
            {"title": "Nhà phố Bình Thạnh 4x12m đường ô tô", "price_billion": 4.8, "area_m2": 48,
             "price_per_m2_million": 100.0, "location": "Bình Thạnh, TP.HCM", "district": "Bình Thạnh",
             "bedrooms": 3, "url": "https://batdongsan.com.vn/...", "property_type": "nha-rieng"},
            {"title": "Căn hộ Charmington Tân Bình 2PN", "price_billion": 3.6, "area_m2": 60,
             "price_per_m2_million": 60.0, "location": "Tân Bình, TP.HCM", "district": "Tân Bình",
             "bedrooms": 2, "url": "https://batdongsan.com.vn/...", "property_type": "can-ho-chung-cu"},
        ]

    results = analyze(props)
    print_report(results)
