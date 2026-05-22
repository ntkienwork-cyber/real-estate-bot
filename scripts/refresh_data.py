"""
BDS Data Refresh Script
Gọi Anthropic API với web search để tìm listings mới nhất,
cập nhật data.json và MARKET_DATA_UPDATED trong analyzer.py.

Chạy: python scripts/refresh_data.py
Hoặc: GitHub Actions tự chạy mỗi 5 ngày.
"""

import anthropic
import json
import re
import os
import sys
from datetime import date
from collections import Counter

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(REPO_ROOT, "data.json")
ANALYZER    = os.path.join(REPO_ROOT, "analyzer.py")
SAMPLE_PATH = os.path.join(REPO_ROOT, "data_sample.json")

VALID_DISTRICTS = [
    "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 6", "Quận 7", "Quận 8",
    "Quận 10", "Quận 11", "Quận 12", "Bình Thạnh", "Gò Vấp", "Phú Nhuận",
    "Tân Bình", "Tân Phú", "Bình Tân", "Thủ Đức", "Nhà Bè", "Bình Chánh",
    "Hóc Môn", "Củ Chi", "Cần Giờ",
]

TODAY      = date.today()
MONTH_YEAR = f"T{TODAY.month}/{TODAY.year}"

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT = f"""Bạn là chuyên gia phân tích BĐS TP.HCM. Nhiệm vụ: dùng web search để tìm ~40 tin đăng bán BĐS MỚI NHẤT tại TP.HCM, giá 3–5 tỷ VND, tổng hợp thành JSON.

## Thực hiện các tìm kiếm sau (theo thứ tự):
1. "site:batdongsan.com.vn bán căn hộ TP.HCM 3 tỷ 4 tỷ 5 tỷ 2026"
2. "site:mogi.vn bán căn hộ chung cư TP.HCM 2026 mới nhất"
3. "site:batdongsan.com.vn bán nhà riêng TP.HCM 3-5 tỷ 2026"
4. "site:batdongsan.com.vn bán đất nền TP.HCM sổ hồng 3-5 tỷ 2026"
5. "batdongsan.com.vn Thủ Đức Bình Thạnh Quận 7 căn hộ 2PN 2026 giá tốt"

## Output yêu cầu
Trả về DUY NHẤT một JSON array, không có text nào khác, không có markdown, không có giải thích.

Schema mỗi object:
{{
  "title": "Tên dự án + loại căn + diện tích + quận",
  "price_billion": 3.8,
  "area_m2": 68,
  "price_per_m2_million": 55.9,
  "location": "Địa chỉ chi tiết, Phường, Quận, TP.HCM",
  "district": "Tên quận/huyện",
  "bedrooms": 2,
  "url": "https://batdongsan.com.vn/... hoặc https://mogi.vn/...",
  "property_type": "can-ho-chung-cu",
  "building_status": "existing",
  "developer": "Tên chủ đầu tư",
  "year_built": 2021,
  "note": "Mô tả ngắn điểm nổi bật — giá {MONTH_YEAR}",
  "quy_hoach": null,
  "foreign_eligible": null,
  "legal_status": "Sổ hồng"
}}

## Quy tắc bắt buộc:
- price_billion: từ 3.0 đến 5.0 (inclusive)
- district: chỉ dùng đúng một trong các giá trị: {', '.join(VALID_DISTRICTS)}
- property_type: chỉ "can-ho-chung-cu" | "nha-rieng" | "dat-nen"
- building_status: chỉ "existing" | "under_construction"
- price_per_m2_million = price_billion * 1000 / area_m2 (làm tròn 1 chữ số thập phân)
- note: PHẢI kết thúc bằng "— giá {MONTH_YEAR}"
- legal_status: chỉ điền nếu chắc chắn ("Sổ hồng" / "Sổ đỏ" / "Hợp đồng mua bán"); bỏ qua field nếu không rõ
- bedrooms: 0 cho đất nền
- year_built: null cho dự án chưa xây
- Ít nhất 8 quận/huyện khác nhau
- Tỷ lệ: ~75% căn hộ, ~15% nhà riêng, ~10% đất nền
- Số lượng: 35–45 properties
- Không trùng title
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def validate(props: list) -> tuple[list, list]:
    valid, errors = [], []
    seen_titles = set()
    for i, p in enumerate(props):
        tag = f"[{i}] '{p.get('title','?')[:40]}'"

        # Required fields
        for f in ["title", "price_billion", "area_m2", "district", "property_type"]:
            if f not in p:
                errors.append(f"{tag}: missing field '{f}'"); break
        else:
            pass

        # Price range
        pb = float(p.get("price_billion", 0))
        if not (3.0 <= pb <= 5.0):
            errors.append(f"{tag}: price {pb} out of [3.0, 5.0]"); continue

        # District
        if p.get("district") not in VALID_DISTRICTS:
            errors.append(f"{tag}: invalid district '{p.get('district')}'"); continue

        # Property type
        if p.get("property_type") not in ("can-ho-chung-cu", "nha-rieng", "dat-nen"):
            errors.append(f"{tag}: invalid property_type '{p.get('property_type')}'"); continue

        # Duplicate title
        t = p.get("title", "")
        if t in seen_titles:
            errors.append(f"{tag}: duplicate title"); continue
        seen_titles.add(t)

        # Recalculate price_per_m2 to guarantee correctness
        area = float(p.get("area_m2") or 0)
        if area > 0:
            p["price_per_m2_million"] = round(pb * 1000 / area, 1)

        valid.append(p)
    return valid, errors


def extract_json(text: str) -> list:
    """Try several strategies to extract a JSON array from model output."""
    # Strategy 1: entire text is valid JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Strategy 2: find first [ ... ] block
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass

    # Strategy 3: strip markdown code fence
    stripped = re.sub(r'```(?:json)?', '', text).strip()
    try:
        return json.loads(stripped)
    except Exception:
        pass

    raise ValueError("Cannot extract JSON array from model response")


def update_dates_in_analyzer():
    with open(ANALYZER, encoding="utf-8") as f:
        content = f.read()
    new_date = f"_dt.date({TODAY.year}, {TODAY.month}, {TODAY.day})"
    content = re.sub(
        r'MARKET_DATA_UPDATED\s*=\s*_dt\.date\([^)]+\)',
        f'MARKET_DATA_UPDATED = {new_date}', content,
    )
    content = re.sub(
        r'MACRO_DATA_UPDATED\s*=\s*_dt\.date\([^)]+\)',
        f'MACRO_DATA_UPDATED = {new_date}', content,
    )
    with open(ANALYZER, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Updated MARKET_DATA_UPDATED → {TODAY}")


def print_report(props: list, errors: list):
    prices    = [p["price_billion"] for p in props]
    districts = Counter(p["district"] for p in props)
    types     = Counter(p["property_type"] for p in props)
    statuses  = Counter(p.get("building_status", "?") for p in props)

    print(f"\n{'='*55}")
    print(f"  BDS REFRESH REPORT — {TODAY}")
    print(f"{'='*55}")
    print(f"  Properties written : {len(props)}")
    print(f"  Price range        : {min(prices):.1f} – {max(prices):.1f} tỷ")
    print(f"  Districts ({len(districts):2d})     : {dict(districts.most_common(5))}")
    print(f"  Types              : {dict(types)}")
    print(f"  Status             : {dict(statuses)}")
    if errors:
        print(f"\n  Validation issues  : {len(errors)}")
        for e in errors[:10]:
            print(f"    • {e}")
    print(f"{'='*55}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"→ Calling Claude with web search ({MONTH_YEAR})…")
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 10,
        }],
        messages=[{"role": "user", "content": PROMPT}],
    )

    # Collect text blocks
    raw_text = "".join(
        block.text for block in response.content
        if hasattr(block, "text")
    )

    print(f"→ Received {len(raw_text)} chars from model")

    try:
        raw_props = extract_json(raw_text)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("First 800 chars of response:", raw_text[:800], file=sys.stderr)
        sys.exit(1)

    valid_props, errors = validate(raw_props)

    if len(valid_props) < 20:
        print(
            f"ERROR: Only {len(valid_props)} valid properties (need ≥ 20). Aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Write data.json
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(valid_props, f, ensure_ascii=False, indent=2)
    print(f"✓ Wrote {len(valid_props)} properties → data.json")

    # Update analyzer.py dates
    if os.path.exists(ANALYZER):
        update_dates_in_analyzer()

    print_report(valid_props, errors)


if __name__ == "__main__":
    main()
