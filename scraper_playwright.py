"""
Real Estate Scraper v2 — Playwright (bypass bot detection)
Nguồn: mogi.vn + alonhadat.vn
"""
import json
import time
import re
from dataclasses import dataclass, asdict
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


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
    property_type: str
    source: str


def parse_price_vn(text: str) -> Optional[float]:
    text = text.lower().replace("\xa0", " ").replace(",", ".").strip()
    m = re.search(r"([\d.]+)\s*tỷ", text)
    if m:
        return float(m.group(1))
    m = re.search(r"([\d.]+)\s*triệu", text)
    if m:
        return float(m.group(1)) / 1000
    return None


def parse_area_vn(text: str) -> Optional[float]:
    m = re.search(r"([\d.,]+)\s*m[²2]", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def extract_district(location: str) -> str:
    patterns = [
        (r"quận\s*(\d+)", lambda m: f"Quận {m.group(1)}"),
        (r"(bình thạnh|gò vấp|phú nhuận|tân bình|tân phú|bình tân|thủ đức|nhà bè|hóc môn|củ chi|bình chánh)",
         lambda m: m.group(1).title()),
    ]
    loc = location.lower()
    for pattern, fmt in patterns:
        m = re.search(pattern, loc)
        if m:
            return fmt(m)
    return "Khác"


def scrape_mogi(page, prop_type: str = "can-ho") -> list[Property]:
    """Scrape mogi.vn"""
    type_map = {
        "can-ho": ("can-ho-chung-cu", "căn hộ"),
        "nha-rieng": ("nha-rieng", "nhà riêng"),
        "dat": ("dat-nen", "đất nền"),
    }
    slug, label = type_map.get(prop_type, ("can-ho-chung-cu", "căn hộ"))

    # mogi URL filter: gia_tu=3000000000&gia_den=5000000000
    url = (
        f"https://mogi.vn/tp-hcm/ban-{prop_type}"
        f"?gia_tu=3000000000&gia_den=5000000000"
    )
    print(f"  → mogi.vn [{label}]: {url}")

    results = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        cards = page.query_selector_all("div.prop-info, div.item-info, li.prop-item")
        print(f"    Tìm được {len(cards)} cards")

        for card in cards[:20]:
            try:
                title_el  = card.query_selector("h2, h3, .prop-name, .item-title")
                price_el  = card.query_selector(".price, .prop-price, span[class*=price]")
                area_el   = card.query_selector(".area, .prop-area, span[class*=area]")
                loc_el    = card.query_selector(".location, .prop-location, span[class*=addr]")
                link_el   = card.query_selector("a[href]")

                if not title_el or not price_el:
                    continue

                title    = title_el.inner_text().strip()
                price    = parse_price_vn(price_el.inner_text())
                area     = parse_area_vn(area_el.inner_text()) if area_el else None
                location = loc_el.inner_text().strip() if loc_el else "TP.HCM"
                href     = link_el.get_attribute("href") if link_el else ""
                full_url = f"https://mogi.vn{href}" if href.startswith("/") else href

                if price is None or not (3.0 <= price <= 5.0):
                    continue

                district     = extract_district(location)
                price_per_m2 = round(price * 1000 / area, 1) if area and area > 0 else None

                results.append(Property(
                    title=title, price_billion=price, area_m2=area,
                    price_per_m2_million=price_per_m2, location=location,
                    district=district, bedrooms=None, url=full_url,
                    property_type=slug, source="mogi.vn",
                ))
            except Exception:
                continue

    except PlaywrightTimeout:
        print("    Timeout — bỏ qua")

    return results


def scrape_alonhadat(page, prop_type: str = "can-ho-chung-cu") -> list[Property]:
    """Scrape alonhadat.com.vn"""
    type_map = {
        "can-ho-chung-cu": "can-ho-chung-cu",
        "nha-rieng": "nha-rieng-biet-thu",
        "dat-nen": "dat-nen-du-an",
    }
    slug = type_map.get(prop_type, "can-ho-chung-cu")
    url = f"https://alonhadat.com.vn/ban-{slug}/thanh-pho-ho-chi-minh.html"
    print(f"  → alonhadat [{prop_type}]: {url}")

    results = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        cards = page.query_selector_all("div.content-item, div.item, .ct-item")
        print(f"    Tìm được {len(cards)} cards")

        for card in cards[:20]:
            try:
                title_el  = card.query_selector("h3 a, .title a, .ct-title a")
                price_el  = card.query_selector(".price, .ct-price, span[class*=price]")
                area_el   = card.query_selector(".square, .ct-dt-dt, span[class*=square]")
                loc_el    = card.query_selector(".address, .ct-address, span[class*=addr]")
                link_el   = title_el or card.query_selector("a[href]")

                if not title_el or not price_el:
                    continue

                title    = title_el.inner_text().strip()
                price    = parse_price_vn(price_el.inner_text())
                area     = parse_area_vn(area_el.inner_text()) if area_el else None
                location = loc_el.inner_text().strip() if loc_el else "TP.HCM"
                href     = link_el.get_attribute("href") if link_el else ""
                full_url = f"https://alonhadat.com.vn{href}" if href and href.startswith("/") else href

                if price is None or not (3.0 <= price <= 5.0):
                    continue

                district     = extract_district(location)
                price_per_m2 = round(price * 1000 / area, 1) if area and area > 0 else None

                results.append(Property(
                    title=title, price_billion=price, area_m2=area,
                    price_per_m2_million=price_per_m2, location=location,
                    district=district, bedrooms=None, url=full_url,
                    property_type=prop_type, source="alonhadat.com.vn",
                ))
            except Exception:
                continue

    except PlaywrightTimeout:
        print("    Timeout — bỏ qua")

    return results


def scrape_all() -> list[Property]:
    all_props = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="vi-VN",
        )
        page = ctx.new_page()
        # ẩn dấu hiệu automation
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("\n[mogi.vn]")
        for t in ["can-ho", "nha-rieng", "dat"]:
            props = scrape_mogi(page, t)
            all_props.extend(props)
            print(f"    ✓ {len(props)} listings")
            time.sleep(1.5)

        print("\n[alonhadat.com.vn]")
        for t in ["can-ho-chung-cu", "nha-rieng", "dat-nen"]:
            props = scrape_alonhadat(page, t)
            all_props.extend(props)
            print(f"    ✓ {len(props)} listings")
            time.sleep(1.5)

        browser.close()

    return all_props


if __name__ == "__main__":
    print("=== SCRAPING BĐS TP.HCM 3-5 TỶ (Playwright) ===")
    props = scrape_all()

    out = "real-estate-bot/data.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in props], f, ensure_ascii=False, indent=2)

    print(f"\nTổng: {len(props)} bất động sản → {out}")
    for p in props[:3]:
        print(f"  • {p.title[:50]} | {p.price_billion}tỷ | {p.district} | {p.source}")
