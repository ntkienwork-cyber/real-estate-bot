"""
Xuất báo cáo phân tích BĐS ra file bds.md
"""
import json, sys, os
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from analyzer import analyze, AnalysisResult
from infrastructure import get_infra_score, INFRA_PROJECTS, Status
from collections import defaultdict

DATA_FILE = os.path.join(os.path.dirname(__file__), "data_sample.json")
with open(DATA_FILE, encoding="utf-8") as f:
    PROPS = json.load(f)

RESULTS: list[AnalysisResult] = analyze(PROPS)

def verdict_icon(v):
    return {"BUY": "🟢", "HOLD": "🟡", "SKIP": "🔴"}.get(v, "⚪")

def value_icon(v):
    return {"UNDERVALUED": "📉 Thấp hơn TT", "OVERVALUED": "📈 Cao hơn TT", "FAIR": "✅ Hợp lý"}.get(v, "—")

def infra_label(s):
    if s >= 50: return "🔥 BÙNG NỔ"
    if s >= 30: return "🚀 TĂNG MẠNH"
    if s >= 15: return "📊 TIỀM NĂNG"
    return "➡️ Ổn định"

def district_summary():
    by_d = defaultdict(list)
    for r in RESULTS:
        by_d[r.property["district"]].append(r)
    rows = []
    for d, res in by_d.items():
        avg_score = sum(r.score for r in res) / len(res)
        ht_sc, _ = get_infra_score(d)
        buy_count = sum(1 for r in res if r.verdict == "BUY")
        rows.append({"district": d, "avg_score": round(avg_score,1),
                     "ht_score": round(ht_sc,1), "buy": buy_count, "total": len(res)})
    rows.sort(key=lambda x: x["avg_score"], reverse=True)
    return rows

# ── BUILD MARKDOWN ─────────────────────────────────────────────────
lines = []

lines += [
    "# Báo Cáo Phân Tích BĐS TP. Hồ Chí Minh",
    f"> Mức giá: **3–5 tỷ VND** · Ngày tạo: **{date.today().strftime('%d/%m/%Y')}** · Tổng listings: **{len(RESULTS)}**",
    "",
    "---",
    "",
]

# ── STATS ──────────────────────────────────────────────────────────
buy   = [r for r in RESULTS if r.verdict == "BUY"]
hold  = [r for r in RESULTS if r.verdict == "HOLD"]
skip  = [r for r in RESULTS if r.verdict == "SKIP"]

lines += [
    "## Tổng Quan",
    "",
    f"| Verdict | Số lượng | Tỷ lệ |",
    f"|---------|----------|-------|",
    f"| 🟢 BUY  | {len(buy)} | {len(buy)*100//len(RESULTS)}% |",
    f"| 🟡 HOLD | {len(hold)} | {len(hold)*100//len(RESULTS)}% |",
    f"| 🔴 SKIP | {len(skip)} | {len(skip)*100//len(RESULTS)}% |",
    "",
]

# ── TOP BUY ────────────────────────────────────────────────────────
lines += [
    "---",
    "",
    "## Top Bất Động Sản Nên Mua",
    "",
]

for i, r in enumerate(buy, 1):
    p = r.property
    lines += [
        f"### #{i} — {p['title']}",
        "",
        f"| Thông tin | Chi tiết |",
        f"|-----------|----------|",
        f"| **Giá** | {p['price_billion']} tỷ VND |",
        f"| **Quận** | {p['district']} |",
        f"| **Diện tích** | {p.get('area_m2') or '—'} m² |",
        f"| **Giá/m²** | {p.get('price_per_m2_million') or '—'} triệu |",
        f"| **Loại hình** | {p['property_type'].replace('-',' ').title()} |",
        f"| **Score** | **{r.score}/100** |",
        f"| **Verdict** | {verdict_icon(r.verdict)} {r.verdict} |",
        f"| **Định giá** | {value_icon(r.value_vs_market)} |",
        f"| **ROI 5 năm** | {r.roi_5yr or '—'}{'%' if r.roi_5yr else ''} |",
        f"| **Yield** | {r.rental_yield_est or '—'}{'%/năm' if r.rental_yield_est else ''} |",
        f"| **Hạ tầng** | {infra_label(r.infra_score)} ({r.infra_score}/100) |",
        "",
        "**Phân tích:**",
        "",
    ]
    for reason in r.reasons:
        lines.append(f"- {reason}")
    if r.infra_projects:
        lines += ["", "**Dự án hạ tầng liên quan:**", ""]
        for proj in r.infra_projects[:4]:
            lines.append(f"- {proj}")
    lines += ["", "---", ""]

# ── HOLD ───────────────────────────────────────────────────────────
lines += [
    "## Danh Sách HOLD (Chờ Thêm)",
    "",
    "| # | Tên BĐS | Giá | Quận | Score | Định giá | Lý do chính |",
    "|---|---------|-----|------|-------|----------|-------------|",
]
for i, r in enumerate(hold, 1):
    p = r.property
    main_reason = r.reasons[0][:55] if r.reasons else "—"
    lines.append(f"| {i} | {p['title'][:45]} | {p['price_billion']}tỷ | {p['district']} | {r.score} | {value_icon(r.value_vs_market)} | {main_reason} |")

lines += ["", "---", ""]

# ── SKIP ───────────────────────────────────────────────────────────
lines += [
    "## Danh Sách SKIP (Bỏ Qua)",
    "",
    "| # | Tên BĐS | Giá | Quận | Score | Lý do |",
    "|---|---------|-----|------|-------|-------|",
]
for i, r in enumerate(skip, 1):
    p = r.property
    main_reason = r.reasons[0][:60] if r.reasons else "—"
    lines.append(f"| {i} | {p['title'][:45]} | {p['price_billion']}tỷ | {p['district']} | {r.score} | {main_reason} |")

lines += ["", "---", ""]

# ── DISTRICT RANKING ───────────────────────────────────────────────
lines += [
    "## Xếp Hạng Quận — Kết Hợp Thị Trường + Hạ Tầng",
    "",
    "| Quận | Avg Score | HT Score | BUY/Tổng | Đánh giá HT |",
    "|------|-----------|----------|----------|-------------|",
]
for row in district_summary():
    lines.append(
        f"| {row['district']} | {row['avg_score']}/100 | {row['ht_score']}/100 | "
        f"{row['buy']}/{row['total']} | {infra_label(row['ht_score'])} |"
    )

lines += ["", "---", ""]

# ── INFRA PROJECTS ─────────────────────────────────────────────────
lines += [
    "## Dự Án Hạ Tầng TP.HCM Đang Triển Khai",
    "",
    "> Các dự án đang thi công hoặc đã được phê duyệt — sẽ hiện thực hóa trong 5 năm tới.",
    "",
]

active = [p for p in INFRA_PROJECTS if p.status in (Status.UNDER_CONST, Status.APPROVED)]
active.sort(key=lambda x: x.price_impact_pct, reverse=True)

for p in active:
    status_icon = "🔨" if p.status == Status.UNDER_CONST else "✅"
    lines += [
        f"### {status_icon} {p.name}",
        "",
        f"| | |",
        f"|--|--|",
        f"| Trạng thái | {p.status.value} |",
        f"| Hoàn thành | {p.expected_completion} |",
        f"| Tác động giá | **+{p.price_impact_pct}%** |",
        f"| Quận hưởng lợi | {', '.join(p.districts_affected)} |",
        f"| Nguồn | {p.source} |",
        "",
        f"{p.description}",
        "",
    ]

# ── CONCLUSION ─────────────────────────────────────────────────────
lines += [
    "---",
    "",
    "## Kết Luận & Chiến Lược",
    "",
    "### Thời Điểm Mua (Q2/2025)",
    "",
    "- Lãi suất cho vay đang giảm về ~8–9% → cửa sổ mua thuận lợi",
    "- Thị trường phục hồi sau điều chỉnh 2022–2023",
    "- **Vành đai 3** sắp hoàn thành (2026) → mua trước khi giá phản ánh đủ",
    "- **Metro số 1** đã vận hành → khu vực Thủ Đức đang được re-rate",
    "",
    "### Ưu Tiên Theo Loại Hình",
    "",
    "| Ưu tiên | Loại hình | Lý do |",
    "|---------|-----------|-------|",
    "| ⭐⭐⭐ | Căn hộ 2PN 60–75m² gần ga Metro | Thanh khoản cao, yield tốt, hạ tầng rõ |",
    "| ⭐⭐ | Đất nền ven Vành đai 3 | Upside lớn khi đường thông |",
    "| ⭐ | Nhà phố hẻm xe hơi Gò Vấp/Tân Bình | Giá còn mềm, dân số đông |",
    "| ❌ | Đất nền vùng xa không quy hoạch | Thanh khoản kém, rủi ro pháp lý |",
    "",
    "### Top Quận Nên Tập Trung",
    "",
]
for i, row in enumerate(district_summary()[:4], 1):
    lines.append(f"{i}. **{row['district']}** — Avg Score: {row['avg_score']}, HT: {infra_label(row['ht_score'])}")

lines += [
    "",
    "---",
    f"*Báo cáo được tạo tự động bởi BDS Analyzer Bot · {date.today().strftime('%d/%m/%Y')}*",
]

# ── WRITE FILE ─────────────────────────────────────────────────────
out_path = os.path.join(os.path.dirname(__file__), "bds.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Đã xuất báo cáo → {out_path}")
print(f"  {len(lines)} dòng · {len(buy)} BUY · {len(hold)} HOLD · {len(skip)} SKIP")
