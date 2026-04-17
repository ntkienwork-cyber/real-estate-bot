"""
Infrastructure Intelligence Module — TP.HCM
Tổng hợp từ nghiên cứu thực tế: VnExpress, Tuoitre, Dantri, VnEconomy, Báo Chính Phủ
Cập nhật: 04/2026 — 45 dự án hạ tầng trên toàn TP.HCM
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class InfraType(str, Enum):
    METRO      = "metro"
    ROAD       = "road"
    BRIDGE     = "bridge"
    EXPRESSWAY = "expressway"
    AIRPORT    = "airport"
    ANTI_FLOOD = "anti_flood"
    URBAN_DEV  = "urban_development"
    INDUSTRIAL = "industrial_park"
    FINANCIAL  = "financial_hub"


class Status(str, Enum):
    PLANNING    = "Quy hoạch"
    APPROVED    = "Đã duyệt"
    UNDER_CONST = "Đang thi công"
    COMPLETED   = "Hoàn thành"


@dataclass
class InfraProject:
    name: str
    infra_type: InfraType
    status: Status
    districts_affected: list[str]
    districts_secondary: list[str]
    expected_completion: str
    price_impact_pct: float
    description: str
    investment_billion_vnd: Optional[float] = None
    source: str = ""


# ═══════════════════════════════════════════════════════════════════
# DATABASE 45 DỰ ÁN HẠ TẦNG TP.HCM — CẬP NHẬT 04/2026
# ═══════════════════════════════════════════════════════════════════
INFRA_PROJECTS: list[InfraProject] = [

    # ──────────────────────────────────────────────────────────────
    # METRO / ĐƯỜNG SẮT ĐÔ THỊ
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Metro số 1 — Bến Thành → Suối Tiên",
        infra_type=InfraType.METRO,
        status=Status.COMPLETED,
        districts_affected=["Quận 1", "Bình Thạnh", "Thủ Đức"],
        districts_secondary=["Quận 2", "Quận 9", "Quận 12"],
        expected_completion="2024",
        price_impact_pct=20,
        investment_billion_vnd=43_700,
        description="19.7km, 14 ga (3 ngầm + 11 trên cao). Khai thác chính thức 22/12/2024. "
                    "BĐS trong bán kính 500m mỗi ga đã tăng 15–25%.",
        source="MAUR / Railway Pro",
    ),
    InfraProject(
        name="Metro số 2 — Bến Thành → Tham Lương",
        infra_type=InfraType.METRO,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 1", "Quận 3", "Tân Bình", "Tân Phú"],
        districts_secondary=["Bình Thạnh", "Quận 10", "Quận 12"],
        expected_completion="2030",
        price_impact_pct=25,
        investment_billion_vnd=47_800,
        description="11.3km, 11 ga đi ngầm. Khởi công 01/2026. Tân Bình và Tân Phú "
                    "hưởng lợi lớn nhất — giá hiện ~52–60tr/m² sẽ được re-rate.",
        source="Quyết định 568/QĐ-TTg / VietGoHan",
    ),
    InfraProject(
        name="Metro số 3A — Bến Thành → Tân Kiên",
        infra_type=InfraType.METRO,
        status=Status.APPROVED,
        districts_affected=["Quận 1", "Quận 5", "Quận 6", "Quận 10", "Quận 11", "Bình Tân"],
        districts_secondary=["Bình Chánh", "Quận 8"],
        expected_completion="2031",
        price_impact_pct=28,
        investment_billion_vnd=67_000,
        description="19.58km (11km Phase 1 + 8.58km Phase 2), 14 ga. Vốn ODA Nhật (STEP). "
                    "Quận 6, 8 lần đầu có Metro — tiềm năng tăng giá 30–50% vùng ga.",
        source="Blog Rever / Taumetro",
    ),
    InfraProject(
        name="Metro số 4 — Thạnh Xuân → Hiệp Phước",
        infra_type=InfraType.METRO,
        status=Status.APPROVED,
        districts_affected=["Quận 12", "Gò Vấp", "Bình Thạnh", "Quận 7", "Nhà Bè"],
        districts_secondary=["Quận 4", "Quận 8"],
        expected_completion="2035",
        price_impact_pct=30,
        investment_billion_vnd=50_000,
        description="36km xuyên suốt Bắc–Nam. Metro 4 tăng tốc (04/2026). "
                    "Quận 7 và Nhà Bè kết nối thẳng lên Gò Vấp, Q12. "
                    "Khu Nam sẽ re-rate mạnh khi dự án được phê duyệt vốn.",
        source="Vietstock 04/2026",
    ),
    InfraProject(
        name="Metro số 5 — Ngã Tư Bảy Hiền → Cầu Sài Gòn",
        infra_type=InfraType.METRO,
        status=Status.PLANNING,
        districts_affected=["Tân Phú", "Tân Bình", "Phú Nhuận", "Bình Thạnh"],
        districts_secondary=["Quận 10", "Quận 11"],
        expected_completion="2035",
        price_impact_pct=22,
        description="23.4km kết nối Tân Phú ↔ Bình Thạnh. "
                    "Phú Nhuận được kết nối toàn diện với toàn mạng lưới.",
        source="Quy hoạch ĐSĐT TP.HCM 2035",
    ),

    # ──────────────────────────────────────────────────────────────
    # VÀNH ĐAI / ĐƯỜNG VÀNH ĐAI
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Vành đai 2 TP.HCM — hoàn chỉnh vòng khép kín",
        infra_type=InfraType.ROAD,
        status=Status.UNDER_CONST,
        districts_affected=["Bình Tân", "Quận 7", "Quận 8", "Quận 12", "Hóc Môn", "Bình Chánh", "Thủ Đức"],
        districts_secondary=["Quận 6", "Gò Vấp"],
        expected_completion="2027",
        price_impact_pct=18,
        investment_billion_vnd=15_000,
        description="70km tổng, ~50km đang khai thác, 14km còn lại đang thi công. "
                    "Đoạn 1 & 2 khởi công 19/12/2025. Quận 8 và Bình Chánh hưởng lợi trực tiếp.",
        source="VnEconomy / HCMC Portal",
    ),
    InfraProject(
        name="Vành đai 3 TP.HCM",
        infra_type=InfraType.ROAD,
        status=Status.UNDER_CONST,
        districts_affected=["Hóc Môn", "Bình Chánh", "Củ Chi", "Thủ Đức"],
        districts_secondary=["Quận 12", "Bình Dương", "Đồng Nai", "Long An"],
        expected_completion="2026",
        price_impact_pct=32,
        investment_billion_vnd=75_000,
        description="76km, 4 tỉnh/thành phố. Thông kỹ thuật 32.6km ngày 30/04/2026, "
                    "thông toàn tuyến 30/06/2026. Đã giải phóng 99.8% mặt bằng. "
                    "Vùng ven tăng 25–40% khi đường thông.",
        source="Nghị quyết 57/2022/QH15 / MSH Group",
    ),
    InfraProject(
        name="Vành đai 4 TP.HCM",
        infra_type=InfraType.ROAD,
        status=Status.APPROVED,
        districts_affected=["Củ Chi", "Hóc Môn", "Bình Chánh"],
        districts_secondary=["Long An", "Bình Dương", "Tây Ninh"],
        expected_completion="2029",
        price_impact_pct=28,
        investment_billion_vnd=120_400,
        description="207km, khởi công Q3/2026. HCMC có 38km. "
                    "Đất ven vành đai 4 đang tích lũy mạnh trước khi giá bùng.",
        source="HCMC Portal / VnEconomy",
    ),

    # ──────────────────────────────────────────────────────────────
    # CAO TỐC / QUỐC LỘ
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Cao tốc Bến Lức — Long Thành",
        infra_type=InfraType.EXPRESSWAY,
        status=Status.COMPLETED,
        districts_affected=["Quận 7", "Nhà Bè", "Bình Chánh"],
        districts_secondary=["Long An", "Đồng Nai"],
        expected_completion="2025",
        price_impact_pct=15,
        investment_billion_vnd=31_000,
        description="57km. Nhánh phía Đông khai thác 28/04/2025. "
                    "Đoạn My Yên–Bình Chánh thông 23/01/2025. "
                    "Q7 và Nhà Bè kết nối sân bay Long Thành trong ~30 phút.",
        source="ADB / Vietnam.vn",
    ),
    InfraProject(
        name="Cao tốc TP.HCM — Mộc Bài",
        infra_type=InfraType.EXPRESSWAY,
        status=Status.UNDER_CONST,
        districts_affected=["Củ Chi"],
        districts_secondary=["Hóc Môn", "Quận 12", "Tây Ninh"],
        expected_completion="2027",
        price_impact_pct=22,
        investment_billion_vnd=19_600,
        description="51km (24.7km HCMC + 26.3km Tây Ninh), 4 làn, 120km/h. "
                    "Khởi công 01/2026. Giải phóng mặt bằng 2,100+ người dân. "
                    "Củ Chi sẽ bứt phá khi thông đường.",
        source="Vietnam.vn / Quyết định 1454/QĐ-TTg",
    ),
    InfraProject(
        name="Cao tốc TP.HCM — Trung Lương — Mỹ Thuận (mở rộng)",
        infra_type=InfraType.EXPRESSWAY,
        status=Status.UNDER_CONST,
        districts_affected=["Bình Chánh"],
        districts_secondary=["Long An"],
        expected_completion="2028",
        price_impact_pct=12,
        investment_billion_vnd=36_200,
        description="96.13km, mở rộng 8 làn (120km/h). Khởi công 19/12/2025. "
                    "Kết nối HCMC ↔ Đồng bằng SCL nhanh hơn, Bình Chánh hưởng lợi.",
        source="Vietnam News",
    ),
    InfraProject(
        name="Cao tốc Biên Hòa — Vũng Tàu",
        infra_type=InfraType.EXPRESSWAY,
        status=Status.UNDER_CONST,
        districts_affected=["Thủ Đức"],
        districts_secondary=["Quận 9", "Đồng Nai"],
        expected_completion="2026",
        price_impact_pct=12,
        description="54km. Đoạn HCMC (Component 3, 19.5km) thông kỹ thuật 30/04/2025. "
                    "Thủ Đức là cửa ngõ phía Đông.",
        source="The Saigon Times",
    ),
    InfraProject(
        name="Quốc lộ 1A mở rộng 10–12 làn (cửa ngõ Tây)",
        infra_type=InfraType.ROAD,
        status=Status.APPROVED,
        districts_affected=["Bình Tân", "Bình Chánh"],
        districts_secondary=["Quận 6", "Quận 8"],
        expected_completion="2028",
        price_impact_pct=15,
        investment_billion_vnd=16_285,
        description="9.6km → 60m mặt cắt, 10–12 làn. Khởi công 2026. "
                    "Cầu Bình Điền thêm 6 làn. Giải tỏa ùn tắc cửa ngõ Tây Nam.",
        source="Tuổi Trẻ 11/2024",
    ),
    InfraProject(
        name="Quốc lộ 50 mở rộng (Bình Chánh)",
        infra_type=InfraType.ROAD,
        status=Status.COMPLETED,
        districts_affected=["Bình Chánh"],
        districts_secondary=["Quận 8"],
        expected_completion="2024",
        price_impact_pct=10,
        investment_billion_vnd=1_400,
        description="Hoàn thành 30/12/2024. 6.3km mở rộng lên 6 làn. "
                    "Kết nối HCMC ↔ Đồng bằng SCL tốt hơn.",
        source="Vietnam News",
    ),

    # ──────────────────────────────────────────────────────────────
    # CẦU
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Cầu Nhơn Trạch (Vành đai 3)",
        infra_type=InfraType.BRIDGE,
        status=Status.COMPLETED,
        districts_affected=["Thủ Đức", "Quận 9"],
        districts_secondary=["Đồng Nai"],
        expected_completion="2025",
        price_impact_pct=15,
        description="Thông chính thức 19/08/2025 (vượt tiến độ 4 tháng). "
                    "Nối Thủ Đức ↔ Nhơn Trạch (Đồng Nai). "
                    "Là một phần Vành đai 3.",
        source="Nhân Dân",
    ),
    InfraProject(
        name="Cầu Bình Khánh (cao tốc Bến Lức – Long Thành)",
        infra_type=InfraType.BRIDGE,
        status=Status.UNDER_CONST,
        districts_affected=["Nhà Bè"],
        districts_secondary=["Cần Giờ"],
        expected_completion="2025",
        price_impact_pct=12,
        investment_billion_vnd=2_800,
        description="2,763m qua sông Soài Rạp, 4 làn. Đạt 92% khối lượng. "
                    "Nối Nhà Bè ↔ khu vực Cần Giờ.",
        source="Huttons Vietnam",
    ),
    InfraProject(
        name="Cầu Cần Giờ",
        infra_type=InfraType.BRIDGE,
        status=Status.APPROVED,
        districts_affected=["Nhà Bè", "Cần Giờ"],
        districts_secondary=["Quận 7"],
        expected_completion="2029",
        price_impact_pct=45,
        investment_billion_vnd=11_087,
        description="7.3km, 6 làn, dây văng. PPP/BOT. Khởi công 2026. "
                    "Thay thế phà Bình Khánh. Đất Cần Giờ đang tăng từ 12.9 → dự báo 25+ tr/m². "
                    "Dự án 2,870ha Vinhomes Green Paradise đã khởi công 04/2025.",
        source="Báo PLO / Vietnam.vn",
    ),
    InfraProject(
        name="Cầu Cát Lái — TP.HCM ↔ Đồng Nai",
        infra_type=InfraType.BRIDGE,
        status=Status.UNDER_CONST,
        districts_affected=["Thủ Đức"],
        districts_secondary=["Quận 9", "Đồng Nai"],
        expected_completion="2029",
        price_impact_pct=18,
        investment_billion_vnd=20_600,
        description="12km (kể cả đường dẫn), 6 làn + 2 làn xe thô sơ, dây văng 450m. "
                    "Khởi công 15/01/2026. PPP. Kết nối thẳng sân bay Long Thành. "
                    "Giải tỏa ùn tắc phà Cát Lái.",
        source="Vietnam.vn",
    ),
    InfraProject(
        name="Cầu Phú Mỹ 2 — TP.HCM ↔ Đồng Nai",
        infra_type=InfraType.BRIDGE,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 7", "Nhà Bè"],
        districts_secondary=["Quận 4"],
        expected_completion="2028",
        price_impact_pct=18,
        investment_billion_vnd=13_000,
        description="6.3km, 8 làn, dây văng (tĩnh không 55m — cao nhất VN). "
                    "Khởi công 15/01/2026. Hành lang quốc tế cho tàu hàng lớn. "
                    "Quận 7 và Nhà Bè kết nối Đồng Nai không qua trung tâm.",
        source="Vietnam.vn",
    ),
    InfraProject(
        name="Cầu Thủ Thiêm 4 (Q7 ↔ Thủ Thiêm)",
        infra_type=InfraType.BRIDGE,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 7", "Thủ Đức"],
        districts_secondary=["Quận 4", "Quận 1"],
        expected_completion="2028",
        price_impact_pct=20,
        investment_billion_vnd=5_063,
        description="8 làn, dây văng, qua sông Sài Gòn. Khởi công Q3/2026. "
                    "Nối Tân Thuận (Q7) ↔ An Khánh (Thủ Thiêm). "
                    "BĐS khu Thủ Thiêm tiếp tục tăng.",
        source="VnEconomy",
    ),
    InfraProject(
        name="Cầu Bình Tiên — Q6, Q8, Bình Chánh",
        infra_type=InfraType.BRIDGE,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 6", "Quận 8", "Bình Chánh"],
        districts_secondary=["Quận 5", "Quận 11"],
        expected_completion="2027",
        price_impact_pct=25,
        investment_billion_vnd=6_285,
        description="Khởi công đầu 2026, hoàn thành Q3/2027. Đường trên cao 4–6 làn. "
                    "Đây là DỰ ÁN HẠ TẦNG QUAN TRỌNG NHẤT của Quận 8 — "
                    "kết nối Khu Nam với trung tâm TP, giải quyết 'điểm nghẽn' lớn nhất.",
        source="Báo PLO 2026",
    ),
    InfraProject(
        name="Cầu đi bộ Sài Gòn (Q1 ↔ Thủ Thiêm)",
        infra_type=InfraType.BRIDGE,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 1", "Thủ Đức"],
        districts_secondary=[],
        expected_completion="2026",
        price_impact_pct=8,
        investment_billion_vnd=1_000,
        description="Cầu đi bộ thiết kế lá dừa nước. Khởi công 29/03/2025, "
                    "hoàn thành 30/04/2026 (kỷ niệm 50 năm thống nhất). "
                    "Nối Bạch Đằng Wharf ↔ công viên ven sông Thủ Thiêm.",
        source="Vietnam.vn",
    ),
    InfraProject(
        name="Cầu Long Kiểng (Nhà Bè ↔ Q7, Q4)",
        infra_type=InfraType.BRIDGE,
        status=Status.COMPLETED,
        districts_affected=["Nhà Bè"],
        districts_secondary=["Quận 7", "Quận 4"],
        expected_completion="2023",
        price_impact_pct=10,
        investment_billion_vnd=589,
        description="Khánh thành 08/09/2023. 318m, 15m rộng. "
                    "Thay thế cầu cũ từ thời Pháp (sập 01/2018 do xe quá tải).",
        source="Báo PLO",
    ),
    InfraProject(
        name="Cầu Cây Khô (Nhà Bè ↔ Bình Chánh)",
        infra_type=InfraType.BRIDGE,
        status=Status.COMPLETED,
        districts_affected=["Nhà Bè", "Bình Chánh"],
        districts_secondary=["Quận 7"],
        expected_completion="2024",
        price_impact_pct=8,
        description="Khai thác 30/08/2024. 485m + 292m đường dẫn. "
                    "Tăng kết nối Nhà Bè ↔ Bình Chánh.",
        source="Vietnam News",
    ),
    InfraProject(
        name="Cầu Rạch Dĩa (Q7 ↔ Nhà Bè) trên Lê Văn Lương",
        infra_type=InfraType.BRIDGE,
        status=Status.COMPLETED,
        districts_affected=["Quận 7", "Nhà Bè"],
        districts_secondary=[],
        expected_completion="2024",
        price_impact_pct=8,
        investment_billion_vnd=500,
        description="Hoàn thành 28/11/2024. Trên đường Lê Văn Lương. "
                    "Kết nối Q7 ↔ Nhà Bè giảm tải cho Q7.",
        source="Vietnam News",
    ),

    # ──────────────────────────────────────────────────────────────
    # SÂN BAY
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Sân bay Long Thành (giai đoạn 1)",
        infra_type=InfraType.AIRPORT,
        status=Status.UNDER_CONST,
        districts_affected=["Thủ Đức"],
        districts_secondary=["Quận 9", "Nhà Bè", "Đồng Nai"],
        expected_completion="2026",
        price_impact_pct=28,
        description="25 triệu khách/năm giai đoạn 1. Khai thác dự kiến 06/2026. "
                    "Thủ Đức là cửa ngõ thành phố tiếp cận sân bay. "
                    "BĐS Thủ Đức và Q9 đang re-rate mạnh.",
        source="ACV / Bộ GTVT",
    ),
    InfraProject(
        name="Nhà ga T3 Tân Sơn Nhất",
        infra_type=InfraType.AIRPORT,
        status=Status.UNDER_CONST,
        districts_affected=["Tân Bình", "Gò Vấp"],
        districts_secondary=["Tân Phú", "Bình Thạnh"],
        expected_completion="2026",
        price_impact_pct=12,
        description="Nâng công suất Tân Sơn Nhất lên 50 triệu khách/năm. "
                    "BĐS bán kính 3km xung quanh sân bay tăng ổn định.",
        source="ACV",
    ),

    # ──────────────────────────────────────────────────────────────
    # CHỐNG NGẬP — ĐẶC BIỆT QUAN TRỌNG CHO Q8, Q4, NHÀ BÈ
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Hệ thống cống kiểm soát triều Phase 1 (chống ngập)",
        infra_type=InfraType.ANTI_FLOOD,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 8", "Quận 4", "Quận 7", "Nhà Bè", "Bình Chánh"],
        districts_secondary=["Quận 1", "Quận 6"],
        expected_completion="2025",
        price_impact_pct=15,
        investment_billion_vnd=10_000,
        description="24 cống kiểm soát triều (40–160m rộng). Tổng 37,000–38,000 tỷ cho 24 dự án. "
                    "Cống Phú Định (Q8) giảm ngập từ 10+ ngày/tháng xuống gần 0. "
                    "Quận 8 lâu nay bị chiết khấu giá vì ngập — sẽ được re-rate sau khi giải quyết.",
        source="Báo PLO 2026",
    ),
    InfraProject(
        name="Cải tạo Kênh Đôi — bờ Bắc (Quận 8)",
        infra_type=InfraType.ANTI_FLOOD,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 8"],
        districts_secondary=["Quận 4"],
        expected_completion="2028",
        price_impact_pct=18,
        investment_billion_vnd=7_300,
        description="4.3km, gói XL-01 và XL-02. Khởi công 11/2025. "
                    "Chống sạt lở, cải thiện thoát nước, chỉnh trang đô thị ven kênh. "
                    "Kết hợp công viên cảnh quan — tương tự hiệu ứng Kênh Nhiêu Lộc.",
        source="Canal renovation — Vietnam.vn",
    ),
    InfraProject(
        name="Cải tạo Kênh Tham Lương — Bến Cát — Nước Lên",
        infra_type=InfraType.ANTI_FLOOD,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 12", "Bình Tân", "Tân Bình", "Gò Vấp"],
        districts_secondary=["Quận 6", "Bình Thạnh"],
        expected_completion="2026",
        price_impact_pct=12,
        investment_billion_vnd=9_000,
        description="Trục thoát nước chính của TP. 10/10 gói thầu đang thi công, "
                    "đạt 58.5% khối lượng. Hạn chót 2026. Bình Tân và Q12 hưởng lợi.",
        source="Vietnam.vn",
    ),
    InfraProject(
        name="Cải tạo Kênh Xuyên Tâm (Bình Thạnh → Gò Vấp)",
        infra_type=InfraType.ANTI_FLOOD,
        status=Status.UNDER_CONST,
        districts_affected=["Bình Thạnh", "Gò Vấp"],
        districts_secondary=["Quận 12"],
        expected_completion="2026",
        price_impact_pct=15,
        description="3 gói (XL-01, 02, 03). Gói XL-03 khởi công 21/05/2025. "
                    "Hoàn thành 11/2026. Cải thiện môi trường và cảnh quan ven kênh.",
        source="Vietnam.vn",
    ),

    # ──────────────────────────────────────────────────────────────
    # KHU ĐÔ THỊ / PHÁT TRIỂN ĐÔ THỊ
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Khu đô thị sáng tạo TP Thủ Đức (phía Đông)",
        infra_type=InfraType.URBAN_DEV,
        status=Status.UNDER_CONST,
        districts_affected=["Thủ Đức"],
        districts_secondary=["Quận 9", "Quận 2"],
        expected_completion="2030",
        price_impact_pct=38,
        description="21,156ha, Quy hoạch duyệt 21/01/2025. 9 hub đổi mới sáng tạo: "
                    "tài chính–công nghệ, trung tâm thể thao quốc gia, sản xuất công nghệ cao, "
                    "giáo dục IT, công nghệ sinh học, startup ecosystem. "
                    "Mục tiêu 300,000+ cư dân trong giai đoạn đầu.",
        source="Báo Chính Phủ 01/2025",
    ),
    InfraProject(
        name="Trung tâm Tài chính Quốc tế Việt Nam (VIFC) TP.HCM",
        infra_type=InfraType.FINANCIAL,
        status=Status.UNDER_CONST,
        districts_affected=["Quận 1", "Quận 4"],
        districts_secondary=["Quận 7", "Thủ Đức", "Bình Thạnh"],
        expected_completion="2030",
        price_impact_pct=22,
        investment_billion_vnd=50_000,
        description="Ra mắt chính thức 11/02/2026. 898ha khu vực lõi CBD. "
                    "Phase 1–2 (2026–2027): chuyển đổi 123 Trương Định và 8 Nguyễn Huệ. "
                    "Phase 3 (2027–2030): xây mới toàn bộ. "
                    "Hub tài chính–hàng hải–hàng không–fintech. Quận 4 hưởng lợi trực tiếp.",
        source="Tuổi Trẻ 02/2026",
    ),
    InfraProject(
        name="Khu đô thị Hiệp Phước (Nhà Bè)",
        infra_type=InfraType.URBAN_DEV,
        status=Status.APPROVED,
        districts_affected=["Nhà Bè"],
        districts_secondary=["Quận 7"],
        expected_completion="2030",
        price_impact_pct=30,
        description="1,354ha, 5 phân khu chức năng, 180,000 cư dân. "
                    "Liên kết KCN Hiệp Phước, cảng và logistics. "
                    "Metro 4 đi qua — tạo hub logistics–cư dân lớn phía Nam.",
        source="khudothi.vn",
    ),
    InfraProject(
        name="Khu đô thị du lịch lấn biển Cần Giờ (Vinhomes Green Paradise)",
        infra_type=InfraType.URBAN_DEV,
        status=Status.UNDER_CONST,
        districts_affected=["Cần Giờ"],
        districts_secondary=["Nhà Bè"],
        expected_completion="2035",
        price_impact_pct=65,
        description="2,870ha (1,357ha mặt nước). Khởi công 04/2025. "
                    "4 phân khu: giải trí, du lịch nghỉ dưỡng, thương mại dịch vụ, resort cao cấp. "
                    "230,000 dân, 8–10 triệu khách/năm. Tàu cao tốc 350km/h 12 phút từ Phú Mỹ Hưng. "
                    "Đất Cần Giờ đang được gom mạnh trước khi cầu hoàn thành.",
        source="Vinhomes / Báo Chính Phủ 04/2025",
    ),
    InfraProject(
        name="Khu Công nghệ cao TP.HCM (SHTP) mở rộng",
        infra_type=InfraType.INDUSTRIAL,
        status=Status.UNDER_CONST,
        districts_affected=["Thủ Đức"],
        districts_secondary=["Quận 9", "Quận 12"],
        expected_completion="2027",
        price_impact_pct=15,
        investment_billion_vnd=17_391,
        description="Mở rộng 194.8ha (85.3% R&D và ươm tạo). Đầu tư 17,391 tỷ. "
                    "161+ dự án đã cấp phép (Intel, Samsung, Nidec). "
                    "Nhu cầu nhà ở kỹ sư, chuyên gia nước ngoài tăng cao.",
        source="Dantri 03/2026",
    ),
    InfraProject(
        name="Khu đô thị Đại học Quốc gia TP.HCM",
        infra_type=InfraType.URBAN_DEV,
        status=Status.UNDER_CONST,
        districts_affected=["Thủ Đức"],
        districts_secondary=["Bình Dương"],
        expected_completion="2030",
        price_impact_pct=12,
        description="643ha, giải phóng mặt bằng 90%. Quy hoạch hoàn thành 2026, "
                    "hạ tầng 2026–2030. 65,000 sinh viên fulltime vào 2030. "
                    "Kéo nhu cầu nhà ở, dịch vụ giáo dục và thương mại xung quanh.",
        source="PLO.vn",
    ),
    InfraProject(
        name="Khu đô thị cảng Sài Gòn — Nhà Rồng Khánh Hội (Q4)",
        infra_type=InfraType.URBAN_DEV,
        status=Status.APPROVED,
        districts_affected=["Quận 4"],
        districts_secondary=["Quận 7", "Quận 1"],
        expected_completion="2030",
        price_impact_pct=25,
        description="Chuyển đổi cảng công nghiệp ven sông thành khu đô thị hỗn hợp cao cấp. "
                    "Waterfront premium — tương tự hiệu ứng Thủ Thiêm. "
                    "Quận 4 lâu nay bị định giá thấp, sẽ được re-rate mạnh khi triển khai.",
        source="Saigon Port / UBND TP.HCM",
    ),
    InfraProject(
        name="Khu đô thị Tây Bắc (Củ Chi — Hóc Môn)",
        infra_type=InfraType.URBAN_DEV,
        status=Status.PLANNING,
        districts_affected=["Củ Chi", "Hóc Môn"],
        districts_secondary=["Quận 12"],
        expected_completion="2040",
        price_impact_pct=20,
        description="9,000ha+ (6,089ha giai đoạn 1). KCN Tây Bắc 381ha "
                    "(cơ khí, điện tử, hóa chất, chế biến thực phẩm). "
                    "Tiến độ chậm nhưng Vành đai 3 & 4 đang mở khóa khu vực.",
        source="khudothi.vn",
    ),
    InfraProject(
        name="14 Khu công nghiệp mới Bình Chánh (2025–2033)",
        infra_type=InfraType.INDUSTRIAL,
        status=Status.APPROVED,
        districts_affected=["Bình Chánh"],
        districts_secondary=["Hóc Môn", "Bình Tân"],
        expected_completion="2033",
        price_impact_pct=20,
        description="Tổng 3,833ha. Phase 1 (2025–2027): KCN Phạm Văn Hải I (379ha), "
                    "Phạm Văn Hải II (289ha), Vĩnh Lộc 3 (200ha), Nhị Xuân. "
                    "Công nghệ cao, sạch, chiến lược. "
                    "Giá đất Bình Chánh hiện rẻ hơn trung tâm 49% — cơ hội lớn.",
        source="Hoang Quan / UBND TP.HCM",
    ),

    # ──────────────────────────────────────────────────────────────
    # NÂNG CẤP HÀNH CHÍNH
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Bình Chánh lên thành phố trực thuộc TP.HCM",
        infra_type=InfraType.URBAN_DEV,
        status=Status.APPROVED,
        districts_affected=["Bình Chánh"],
        districts_secondary=["Bình Tân"],
        expected_completion="2025",
        price_impact_pct=18,
        description="Cải cách hành chính 01/07/2025: toàn TP chuyển sang mô hình 2 cấp (TP–phường). "
                    "Bình Chánh nâng lên thành phố trực thuộc — 12/16 xã thành phường. "
                    "Tâm lý thị trường đánh giá cao BĐS khu vực nâng cấp hành chính.",
        source="Tuổi Trẻ / Vietnam.vn",
    ),
    InfraProject(
        name="Hóc Môn và Nhà Bè đủ tiêu chí lên đô thị",
        infra_type=InfraType.URBAN_DEV,
        status=Status.PLANNING,
        districts_affected=["Hóc Môn", "Nhà Bè"],
        districts_secondary=["Quận 12", "Quận 7"],
        expected_completion="2030",
        price_impact_pct=15,
        description="Hóc Môn đạt 23/30 tiêu chí đô thị. Nhà Bè phát triển hạ tầng sau 2026. "
                    "Sau 2030 đủ điều kiện lên thành phố tương đương Thủ Đức.",
        source="Vietnam.vn",
    ),

    # ──────────────────────────────────────────────────────────────
    # BỆNH VIỆN / TIỆN ÍCH XÃ HỘI
    # ──────────────────────────────────────────────────────────────
    InfraProject(
        name="Bệnh viện Đa khoa 1,500 giường (Củ Chi / Tân Nhựt)",
        infra_type=InfraType.URBAN_DEV,
        status=Status.UNDER_CONST,
        districts_affected=["Củ Chi"],
        districts_secondary=["Hóc Môn", "Bình Chánh"],
        expected_completion="2026",
        price_impact_pct=10,
        investment_billion_vnd=8_800,
        description="16ha, 1,500+ giường — lớn nhất TP.HCM. Đạt 95% hạ tầng chính Q3/2026. "
                    "Trung tâm y tế vùng phía Bắc/Tây TP.HCM.",
        source="Dantri 11/2025",
    ),
    InfraProject(
        name="Mở rộng Bệnh viện Quân Y 175 (Gò Vấp)",
        infra_type=InfraType.URBAN_DEV,
        status=Status.COMPLETED,
        districts_affected=["Gò Vấp"],
        districts_secondary=["Tân Bình", "Bình Thạnh"],
        expected_completion="2024",
        price_impact_pct=8,
        description="1,000 giường đa khoa mới hoàn thành 05/2024. "
                    "Tổng hệ thống 2,500+ giường — tăng sức hút của Gò Vấp.",
        source="HCMCPV",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# SCORING ENGINE — cập nhật với dữ liệu thực
# ═══════════════════════════════════════════════════════════════════

def get_infra_score(district: str) -> tuple[float, list[str]]:
    """Tính điểm hạ tầng cho 1 quận. Trả về (score 0–100, danh sách dự án)."""
    score = 0.0
    impacts: list[str] = []

    for proj in INFRA_PROJECTS:
        if district in proj.districts_affected:
            weight = {
                Status.COMPLETED:   1.00,
                Status.UNDER_CONST: 0.85,
                Status.APPROVED:    0.60,
                Status.PLANNING:    0.30,
            }[proj.status]
            contrib = proj.price_impact_pct * weight / 5
            score += contrib
            impacts.append(
                f"{proj.name} [{proj.status.value}, {proj.expected_completion}] → +{proj.price_impact_pct}%"
            )
        elif district in proj.districts_secondary:
            weight = {
                Status.COMPLETED:   0.50,
                Status.UNDER_CONST: 0.40,
                Status.APPROVED:    0.28,
                Status.PLANNING:    0.12,
            }[proj.status]
            contrib = proj.price_impact_pct * weight / 10
            score += contrib

    # Sort impacts by project status priority
    status_order = {
        Status.UNDER_CONST.value: 0,
        Status.COMPLETED.value: 1,
        Status.APPROVED.value: 2,
        Status.PLANNING.value: 3,
    }
    impacts.sort(key=lambda x: status_order.get(
        next((s.value for s in Status if s.value in x), ""), 4))

    return min(score, 100), impacts


def infra_label(score: float) -> tuple[str, str, str]:
    """Trả về (nhãn, fg_color, bg_color)."""
    if score >= 60:  return "BÙNG NỔ",    "#7c3aed", "#ede9fe"
    if score >= 40:  return "TĂNG MẠNH",  "#dc2626", "#fee2e2"
    if score >= 22:  return "TIỀM NĂNG",  "#d97706", "#fef3c7"
    if score >= 10:  return "Khởi sắc",   "#0369a1", "#e0f2fe"
    return               "Ổn định",       "#374151", "#f3f4f6"


def infra_multiplier(district: str) -> float:
    score, _ = get_infra_score(district)
    if score >= 60: return 1.35
    if score >= 40: return 1.25
    if score >= 22: return 1.15
    if score >= 10: return 1.08
    return 1.0


def get_infra_momentum(district: str) -> dict:
    """
    Phân tích Infrastructure Momentum chi tiết cho 1 quận.
    Momentum = tốc độ và quy mô đầu tư hạ tầng đang diễn ra HIỆN TẠI.

    Trả về dict:
      active_count         — số dự án đang thi công (UNDER_CONST)
      pipeline_count       — số dự án đã duyệt (APPROVED, sắp thi công)
      planning_count       — số dự án quy hoạch (PLANNING)
      total_investment_t   — tổng vốn đầu tư (nghìn tỷ VND)
      max_price_impact_pct — dự án có tác động giá cao nhất
      total_price_impact   — tổng impact giá nếu tất cả hoàn thành
      nearest_completion   — dự án hoàn thành sớm nhất (năm)
      momentum_score       — 0–100, tổng hợp tốc độ + quy mô
      momentum_label       — "Bùng nổ" | "Tăng mạnh" | "Tích cực" | "Ổn định" | "Yếu"
      top_projects         — list[dict] top 3 dự án quan trọng nhất
    """
    active, pipeline, planning = [], [], []

    for proj in INFRA_PROJECTS:
        is_primary = district in proj.districts_affected
        is_secondary = district in proj.districts_secondary
        if not (is_primary or is_secondary):
            continue
        weight = 1.0 if is_primary else 0.5

        if proj.status == Status.UNDER_CONST:
            active.append((proj, weight))
        elif proj.status == Status.APPROVED:
            pipeline.append((proj, weight))
        elif proj.status == Status.PLANNING:
            planning.append((proj, weight))

    # Tổng vốn đầu tư (đang thi công — chắc chắn nhất)
    total_inv = sum(
        (p.investment_billion_vnd or 0) * w / 1_000  # đổi sang nghìn tỷ
        for p, w in active + pipeline
    )

    # Tổng tác động giá tiềm năng (primary only)
    total_impact = sum(
        p.price_impact_pct for p, w in active + pipeline + planning
        if w == 1.0
    )

    # Dự án impact cao nhất
    all_primary = [(p, w) for p, w in active + pipeline + planning if w == 1.0]
    max_impact = max((p.price_impact_pct for p, _ in all_primary), default=0)

    # Năm hoàn thành sớm nhất (active only)
    completions = []
    for p, _ in active:
        try:
            completions.append(int(p.expected_completion[:4]))
        except (ValueError, IndexError):
            pass
    nearest = min(completions) if completions else None

    # ── Momentum score (v2 — chặt hơn, uy tín hơn) ──────────────────
    # Chỉ tính dự án ĐANG THI CÔNG + primary district (không tính quy hoạch / phê duyệt)
    # Investment chia cho số quận hưởng lợi chính → tránh thổi phồng outer districts bởi vành đai
    primary_active = [p for p, w in active if w == 1.0]

    # 1. Active count score — tối đa 5 dự án có trọng số đầy đủ
    active_score = min(len(primary_active) * 8, 40)

    # 2. Investment score — chia đều cho các quận chịu ảnh hưởng chính của từng dự án
    inv_primary = sum(
        (p.investment_billion_vnd or 0) * 0.001 / max(len(p.districts_affected), 1)
        for p in primary_active
    )
    inv_score = min(inv_primary / 6, 25)              # cần 150k tỷ riêng → max 25đ

    # 3. Impact score — chỉ từ active primary (loại bỏ lạm phát điểm từ dự án quy hoạch)
    impact_primary = sum(p.price_impact_pct for p in primary_active)
    impact_score = min(impact_primary / 3.5, 30)      # cần 105% riêng → max 30đ

    momentum_score = round(active_score + inv_score + impact_score, 1)

    # Ngưỡng khắt khe hơn — Bùng nổ chỉ dành cho trung tâm đô thị thực sự đang chuyển mình
    if momentum_score >= 75:   momentum_label = "Bùng nổ 🔥"
    elif momentum_score >= 52: momentum_label = "Tăng mạnh 🚀"
    elif momentum_score >= 32: momentum_label = "Tích cực 📈"
    elif momentum_score >= 15: momentum_label = "Ổn định 📊"
    else:                      momentum_label = "Yếu ➡️"

    # Top 3 dự án quan trọng nhất (primary, sort by impact)
    top_projs = sorted(
        [(p, w) for p, w in active + pipeline if w == 1.0],
        key=lambda x: x[0].price_impact_pct,
        reverse=True
    )[:3]

    return {
        "active_count":          len(active),
        "pipeline_count":        len(pipeline),
        "planning_count":        len(planning),
        "total_investment_t":    round(total_inv, 1),
        "max_price_impact_pct":  max_impact,
        "total_price_impact":    total_impact,
        "nearest_completion":    nearest,
        "momentum_score":        momentum_score,
        "momentum_label":        momentum_label,
        "top_projects": [
            {
                "name":       p.name,
                "status":     p.status.value,
                "completion": p.expected_completion,
                "impact_pct": p.price_impact_pct,
                "type":       p.infra_type.value,
            }
            for p, _ in top_projs
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# STANDALONE REPORT
# ═══════════════════════════════════════════════════════════════════

def print_infra_report():
    ALL_DISTRICTS = [
        "Quận 1","Quận 3","Quận 4","Quận 5","Quận 6","Quận 7","Quận 8",
        "Quận 10","Quận 11","Quận 12",
        "Bình Thạnh","Gò Vấp","Phú Nhuận","Tân Bình","Tân Phú","Bình Tân",
        "Thủ Đức","Nhà Bè","Hóc Môn","Củ Chi","Bình Chánh","Cần Giờ",
    ]
    print("\n" + "="*70)
    print("  HẠ TẦNG TP.HCM — XẾP HẠNG 22 QUẬN/HUYỆN (04/2026)")
    print("="*70)
    print(f"  Tổng dự án cập nhật: {len(INFRA_PROJECTS)}")
    print(f"  {'Quận':<16} {'Score':>7}  {'Nhãn':<12}  Dự án trực tiếp")
    print("  " + "─"*65)

    ranked = []
    for d in ALL_DISTRICTS:
        sc, projs = get_infra_score(d)
        ranked.append((d, sc, projs))
    ranked.sort(key=lambda x: x[1], reverse=True)

    for d, sc, projs in ranked:
        label, _, _ = infra_label(sc)
        print(f"  {d:<16} {sc:>7.1f}  {label:<12}  {len(projs)} dự án")

    print(f"\n  {'─'*65}")
    print("  CHI TIẾT TỪNG QUẬN (TOP 8)")
    print(f"  {'─'*65}")
    for d, sc, projs in ranked[:8]:
        label, _, _ = infra_label(sc)
        print(f"\n  [{label}] {d}  —  {sc:.1f}/100")
        for p in projs[:5]:
            print(f"    • {p[:80]}")

    print(f"\n  {'─'*65}")
    print("  ĐANG THI CÔNG — MUA NGAY ĐỂ BẮT SÓNG")
    print(f"  {'─'*65}")
    active = sorted(
        [p for p in INFRA_PROJECTS if p.status == Status.UNDER_CONST],
        key=lambda x: x.price_impact_pct, reverse=True
    )
    for p in active:
        budget = f"{p.investment_billion_vnd/1000:.0f}k tỷ" if p.investment_billion_vnd else "—"
        print(f"\n  [{p.expected_completion}] {p.name}")
        print(f"    Quận:  {', '.join(p.districts_affected)}")
        print(f"    Tác động: +{p.price_impact_pct}%  |  Đầu tư: {budget}")
        print(f"    → {p.description[:90]}")


if __name__ == "__main__":
    print_infra_report()
