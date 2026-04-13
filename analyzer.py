"""
Real Estate Analyzer - áp dụng framework từ real-estate-analyzer skill
Phân tích & recommend BĐS 3-5 tỷ tại TP.HCM (kết hợp phân tích hạ tầng)
"""
import json
from dataclasses import dataclass
from typing import Optional
from collections import defaultdict
from infrastructure import get_infra_score, infra_multiplier, INFRA_PROJECTS, Status


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


@dataclass
class AnalysisResult:
    property: dict
    score: float
    verdict: str          # BUY / HOLD / SKIP
    value_vs_market: str  # UNDERVALUED / FAIR / OVERVALUED
    rental_yield_est: Optional[float]
    roi_5yr: Optional[float]
    reasons: list[str]
    infra_score: float = 0.0
    infra_projects: list[str] = None


def get_market_ref(prop_type: str, district: str) -> Optional[dict]:
    type_data = MARKET_DATA.get(prop_type, {})
    return type_data.get(district) or type_data.get("Khác")


def calc_score(prop: dict, market: dict, district: str) -> tuple[float, list[str]]:
    score = 50.0
    reasons = []

    price_per_m2 = prop.get("price_per_m2_million")
    avg = market.get("avg_price_per_m2", 0)

    # 1. So sánh giá với thị trường
    if price_per_m2 and avg:
        ratio = price_per_m2 / avg
        if ratio < 0.85:
            score += 20
            reasons.append(f"Giá thấp hơn thị trường {round((1-ratio)*100)}% → tiềm năng tăng giá tốt")
        elif ratio < 0.95:
            score += 10
            reasons.append(f"Giá hợp lý, thấp hơn mặt bằng ~{round((1-ratio)*100)}%")
        elif ratio > 1.15:
            score -= 15
            reasons.append(f"Giá cao hơn thị trường {round((ratio-1)*100)}% → rủi ro đỉnh giá")
        else:
            reasons.append("Giá sát mặt bằng thị trường")

    # 2. Rental yield
    yield_pct = market.get("rental_yield", 0)
    if yield_pct >= 5:
        score += 15
        reasons.append(f"Rental yield ước tính {yield_pct}% → dòng tiền tốt")
    elif yield_pct >= 4:
        score += 8
        reasons.append(f"Rental yield {yield_pct}% — chấp nhận được")
    elif yield_pct < 3:
        score -= 10
        reasons.append(f"Rental yield thấp ({yield_pct}%) — phù hợp đầu tư dài hạn hơn cho thuê")

    # 3. Tăng trưởng khu vực
    growth = market.get("growth_yoy", 0)
    if growth >= 12:
        score += 15
        reasons.append(f"Khu vực tăng trưởng mạnh {growth}%/năm")
    elif growth >= 8:
        score += 8
        reasons.append(f"Tăng trưởng ổn định {growth}%/năm")

    # 4. Điểm hấp dẫn quận
    d_score = DISTRICT_SCORE.get(district, 6.0)
    if d_score >= 8.5:
        score += 10
        reasons.append(f"Vị trí chiến lược (điểm quận: {d_score}/10)")
    elif d_score >= 7.5:
        score += 5

    # 5. Diện tích hợp lý (căn hộ 50-80m² dễ thanh khoản nhất)
    area = prop.get("area_m2")
    if area and prop.get("property_type") == "can-ho-chung-cu":
        if 50 <= area <= 80:
            score += 5
            reasons.append(f"Diện tích {area}m² — thanh khoản cao")
        elif area < 40:
            score -= 5
            reasons.append(f"Diện tích nhỏ ({area}m²) — khó cho thuê")

    # 6. Hạ tầng tiềm năng
    infra_sc, infra_projects = get_infra_score(district)
    if infra_sc >= 50:
        score += 20
        reasons.append(f"Hạ tầng BÙNG NỔ (điểm {infra_sc:.0f}/100) — {len(infra_projects)} dự án lớn")
    elif infra_sc >= 30:
        score += 12
        reasons.append(f"Hạ tầng TĂNG MẠNH (điểm {infra_sc:.0f}/100) — {len(infra_projects)} dự án")
    elif infra_sc >= 15:
        score += 6
        reasons.append(f"Hạ tầng TIỀM NĂNG (điểm {infra_sc:.0f}/100)")

    # Áp dụng multiplier hạ tầng lên toàn bộ score
    score = score * infra_multiplier(district)

    return min(max(score, 0), 100), reasons


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

        score, reasons = calc_score(prop, market, district)

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

        results.append(AnalysisResult(
            property=prop,
            score=round(score, 1),
            verdict=verdict,
            value_vs_market=value_assessment(prop.get("price_per_m2_million"), market["avg_price_per_m2"]),
            rental_yield_est=yield_pct,
            roi_5yr=roi_5yr,
            reasons=reasons,
            infra_score=round(infra_sc, 1),
            infra_projects=infra_projs,
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
