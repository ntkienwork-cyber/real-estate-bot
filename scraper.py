"""
Real Estate Scraper - batdongsan.com.vn
Lọc BĐS TP.HCM giá 3-5 tỷ VND
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from dataclasses import dataclass, asdict
from typing import Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9",
}

@dataclass
class Property:
    title: str
    price_billion: float
    area_m2: Optional[float]
    price_per_m2_million: Optional[float]
    location: str
    district: str
    bedrooms: Optional[int]
    url: str
    property_type: str  # can_ho, nha_rieng, dat_nen


def parse_price(text: str) -> Optional[float]:
    """Chuyển chuỗi giá về tỷ VND"""
    text = text.lower().replace(",", ".").strip()
    match_ty = re.search(r"([\d.]+)\s*tỷ", text)
    match_trieu = re.search(r"([\d.]+)\s*triệu", text)
    if match_ty:
        return float(match_ty.group(1))
    if match_trieu:
        return float(match_trieu.group(1)) / 1000
    return None


def parse_area(text: str) -> Optional[float]:
    """Lấy diện tích m²"""
    match = re.search(r"([\d.,]+)\s*m²", text)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def scrape_batdongsan(page: int = 1, loai: str = "can-ho-chung-cu") -> list[Property]:
    """
    Scrape 1 trang từ batdongsan.com.vn
    loai: can-ho-chung-cu | nha-rieng | dat-nen
    """
    url = (
        f"https://batdongsan.com.vn/ban-{loai}-tp-hcm"
        f"/p{page}"
        f"?gia=3-5"  # filter 3-5 tỷ
    )
    print(f"  Scraping: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Lỗi request: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []

    # Selector cho listing cards
    cards = soup.select("div.js__card")
    if not cards:
        cards = soup.select("li.js__card")

    for card in cards:
        try:
            title_el = card.select_one("span.js__card-title, h3.pr-title")
            price_el = card.select_one("span.price, div.re__card-config-price")
            area_el  = card.select_one("span.area, div.re__card-config-area")
            loc_el   = card.select_one("div.location, span.re__card-location")
            link_el  = card.select_one("a[href]")

            if not title_el or not price_el:
                continue

            title = title_el.get_text(strip=True)
            price = parse_price(price_el.get_text(strip=True))
            area  = parse_area(area_el.get_text(strip=True)) if area_el else None
            location = loc_el.get_text(strip=True) if loc_el else "N/A"
            href  = link_el["href"] if link_el else ""
            full_url = f"https://batdongsan.com.vn{href}" if href.startswith("/") else href

            # Lọc theo giá 3-5 tỷ
            if price is None or not (3.0 <= price <= 5.0):
                continue

            district = extract_district(location)
            price_per_m2 = round(price * 1000 / area, 1) if area and area > 0 else None

            # Đếm phòng ngủ
            beds_el = card.select_one("span.bedroom, span[aria-label*='phòng ngủ']")
            bedrooms = None
            if beds_el:
                m = re.search(r"\d+", beds_el.get_text())
                if m:
                    bedrooms = int(m.group())

            results.append(Property(
                title=title,
                price_billion=price,
                area_m2=area,
                price_per_m2_million=price_per_m2,
                location=location,
                district=district,
                bedrooms=bedrooms,
                url=full_url,
                property_type=loai,
            ))
        except Exception:
            continue

    return results


def extract_district(location: str) -> str:
    districts = [
        "Quận 1","Quận 2","Quận 3","Quận 4","Quận 5","Quận 6","Quận 7",
        "Quận 8","Quận 9","Quận 10","Quận 11","Quận 12",
        "Bình Thạnh","Gò Vấp","Phú Nhuận","Tân Bình","Tân Phú","Bình Tân",
        "Thủ Đức","Bình Dương","Nhà Bè","Hóc Môn","Củ Chi","Cần Giờ",
    ]
    for d in districts:
        if d.lower() in location.lower():
            return d
    return "Khác"


def scrape_all(pages: int = 3) -> list[Property]:
    all_props = []
    types = ["can-ho-chung-cu", "nha-rieng", "dat-nen"]
    for loai in types:
        print(f"\n[{loai}]")
        for page in range(1, pages + 1):
            props = scrape_batdongsan(page, loai)
            all_props.extend(props)
            print(f"  Trang {page}: {len(props)} listings")
            time.sleep(1.5)  # rate limiting
    return all_props


def save_json(props: list[Property], path: str = "data.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in props], f, ensure_ascii=False, indent=2)
    print(f"\nLưu {len(props)} listings -> {path}")


if __name__ == "__main__":
    print("=== SCRAPING BĐS TP.HCM 3-5 TỶ ===")
    props = scrape_all(pages=2)
    save_json(props, "real-estate-bot/data.json")
    print(f"\nTổng: {len(props)} bất động sản")
