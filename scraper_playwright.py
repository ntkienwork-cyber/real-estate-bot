"""
Real Estate Scraper v2 — Playwright (bypass bot detection)
Nguồn: mogi.vn + alonhadat.vn
"""
import json
import os
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
    handover_year: Optional[str] = None
    legal_status: Optional[str] = None


def parse_price_vn(text: str) -> Optional[float]:
    text = text.lower().replace("\xa0", " ").replace(",", ".").strip()
    # "3 tỷ 600 triệu" combined format
    m = re.search(r"([\d.]+)\s*tỷ\s+([\d.]+)\s*triệu", text)
    if m:
        return float(m.group(1)) + float(m.group(2)) / 1000
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


def extract_handover_year(text: str) -> Optional[str]:
    t = text.lower()
    # "bàn giao Q2/2026", "bàn giao 2026", "giao nhà 2026", "hoàn thành 2026"
    m = re.search(r"(?:bàn\s*giao|giao\s*nhà|hoàn\s*thành)\s*(?:q\d/?-?)?(20[2-3]\d)", t)
    if m:
        return m.group(1)
    # fallback: any 202x/203x year mentioned
    m = re.search(r"\b(20[2-3]\d)\b", t)
    if m:
        return m.group(1)
    return None


def extract_legal_status(text: str) -> Optional[str]:
    t = text.lower()
    if "vĩnh viễn" in t:
        return "Sổ hồng vĩnh viễn"
    if "50 năm" in t or "50năm" in t:
        return "Sổ hồng 50 năm"
    if "sổ hồng" in t:
        return "Sổ hồng"
    if "sổ đỏ" in t:
        return "Sổ đỏ"
    return None


def normalize_legal(raw: str) -> Optional[str]:
    if not raw or raw in ("---", "_", ""):
        return None
    return extract_legal_status(raw) or raw.strip()


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


def fetch_listing_details(detail_page, url: str, source: str) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch the full listing page and return (handover_year, legal_status).
    Uses a dedicated page so the listing-grid page is not navigated away from.
    """
    try:
        detail_page.goto(url, wait_until="domcontentloaded", timeout=20000)
        detail_page.wait_for_timeout(1000)

        handover_year = None
        legal_status  = None

        if source == "mogi.vn":
            # Structure: div.info-attr > span[label], span[value]
            attrs = detail_page.evaluate("""() => {
                const out = {};
                document.querySelectorAll('div.info-attr').forEach(div => {
                    const spans = div.querySelectorAll('span');
                    if (spans.length >= 2)
                        out[spans[0].textContent.trim()] = spans[1].textContent.trim();
                });
                return out;
            }""")
            legal_status  = normalize_legal(attrs.get("Pháp lý", ""))
            raw_handover  = attrs.get("Bàn giao", "") or attrs.get("Năm xây", "")
            handover_year = extract_handover_year(raw_handover) if raw_handover else None

            # Fall back to description text if no structured year
            if not handover_year:
                desc_el = detail_page.query_selector("div.prop-description, div.description, div.intro")
                if desc_el:
                    handover_year = extract_handover_year(desc_el.inner_text())

        elif source == "alonhadat.com.vn":
            # Table: <td>Label</td><td>Value</td> pairs (6 cells per row)
            attrs = detail_page.evaluate("""() => {
                const out = {};
                const tds = [...document.querySelectorAll('td')];
                for (let i = 0; i < tds.length - 1; i++) {
                    const key = tds[i].textContent.trim();
                    const val = tds[i+1].textContent.trim();
                    if (key && val) out[key] = val;
                }
                return out;
            }""")
            legal_status  = normalize_legal(attrs.get("Pháp lý", ""))
            raw_handover  = attrs.get("Bàn giao", "") or attrs.get("Năm xây dựng", "")
            handover_year = extract_handover_year(raw_handover) if raw_handover else None

            # Fall back to full body text (description often has "Pháp lý: Sổ hồng riêng")
            if not legal_status or not handover_year:
                body = detail_page.inner_text("body")
                if not legal_status:
                    legal_status  = extract_legal_status(body)
                if not handover_year:
                    handover_year = extract_handover_year(body)

    except Exception as e:
        print(f"      Detail fetch error ({url[-40:]}): {e}")

    return handover_year, legal_status


def scrape_mogi(page, detail_page, prop_type: str = "can-ho") -> list[Property]:
    """Scrape mogi.vn"""
    url_map = {
        "can-ho":    ("can-ho-chung-cu", "căn hộ",   "https://mogi.vn/tp-hcm/mua-can-ho-chung-cu"),
        "nha-rieng": ("nha-rieng",       "nhà riêng", "https://mogi.vn/tp-hcm/mua-nha-rieng"),
        "dat":       ("dat-nen",         "đất nền",   "https://mogi.vn/tp-hcm/mua-dat"),
    }
    slug, label, url = url_map.get(prop_type, url_map["can-ho"])
    print(f"  → mogi.vn [{label}]: {url}")

    results = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("div.prop-info", timeout=10000)

        cards = page.query_selector_all("div.prop-info")
        print(f"    Tìm được {len(cards)} cards")

        for card in cards[:20]:
            try:
                title_el = card.query_selector("h2.prop-title")
                price_el = card.query_selector("div.price")
                area_el  = card.query_selector("ul.prop-attr li:first-child")
                loc_el   = card.query_selector("div.prop-addr")
                link_el  = card.query_selector("a.link-overlay")
                beds_el  = card.query_selector("ul.prop-attr li:nth-child(2)")

                if not title_el or not price_el:
                    continue

                title    = title_el.inner_text().strip()
                price    = parse_price_vn(price_el.inner_text())
                area     = parse_area_vn(area_el.inner_text()) if area_el else None
                location = loc_el.inner_text().strip() if loc_el else "TP.HCM"
                href     = link_el.get_attribute("href") if link_el else ""
                full_url = href if href.startswith("http") else f"https://mogi.vn{href}"

                if price is None or not (3.0 <= price <= 5.0):
                    continue

                district     = extract_district(location)
                price_per_m2 = round(price * 1000 / area, 1) if area and area > 0 else None

                bedrooms = None
                if beds_el:
                    m = re.search(r"\d+", beds_el.inner_text())
                    if m:
                        bedrooms = int(m.group())

                handover_year, legal_status = fetch_listing_details(detail_page, full_url, "mogi.vn")
                print(f"      {title[:40]} → handover={handover_year} legal={legal_status}")

                results.append(Property(
                    title=title, price_billion=price, area_m2=area,
                    price_per_m2_million=price_per_m2, location=location,
                    district=district, bedrooms=bedrooms, url=full_url,
                    property_type=slug, source="mogi.vn",
                    handover_year=handover_year,
                    legal_status=legal_status,
                ))
            except Exception as e:
                print(f"      Parse error: {e}")
                continue

    except PlaywrightTimeout:
        print("    Timeout — bỏ qua")
    except Exception as e:
        print(f"    Error: {e}")

    return results


def scrape_alonhadat(page, detail_page, prop_type: str = "can-ho-chung-cu") -> list[Property]:
    """Scrape alonhadat.com.vn"""
    url_map = {
        "can-ho-chung-cu": "can-ban-can-ho-chung-cu",
        "nha-rieng":       "can-ban-nha",
        "dat-nen":         "can-ban-dat-nen",
    }
    slug = url_map.get(prop_type, "can-ban-can-ho-chung-cu")
    url = f"https://alonhadat.com.vn/{slug}/ho-chi-minh"
    print(f"  → alonhadat [{prop_type}]: {url}")

    results = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("article.property-item", timeout=10000)

        cards = page.query_selector_all("article.property-item")
        print(f"    Tìm được {len(cards)} cards")

        for card in cards[:20]:
            try:
                title_el  = card.query_selector("h3.property-title")
                link_el   = card.query_selector("a.link")
                price_el  = card.query_selector("span[itemprop=price]")
                area_el   = card.query_selector("span.area span[itemprop=value]")
                region_el = card.query_selector("span[itemprop=addressRegion]")
                addr_el   = card.query_selector("p.new-address")
                beds_el   = card.query_selector("span.bedroom span[itemprop=value]")

                if not title_el or not price_el:
                    continue

                # Skip listings outside TP.HCM
                region = region_el.inner_text().strip() if region_el else ""
                if "hồ chí minh" not in region.lower():
                    continue

                title = title_el.inner_text().strip()

                # content attr holds raw VND integer: "4309000000"
                price_vnd = price_el.get_attribute("content")
                price = float(price_vnd) / 1e9 if price_vnd else parse_price_vn(price_el.inner_text())

                area_str = area_el.inner_text().strip() if area_el else None
                area     = float(area_str) if area_str else None
                location = addr_el.inner_text().strip() if addr_el else "TP.HCM"
                href     = link_el.get_attribute("href") if link_el else ""
                full_url = f"https://alonhadat.com.vn{href}" if href.startswith("/") else href

                if price is None or not (3.0 <= price <= 5.0):
                    continue

                district     = extract_district(location)
                price_per_m2 = round(price * 1000 / area, 1) if area and area > 0 else None

                bedrooms = None
                if beds_el:
                    m = re.search(r"\d+", beds_el.inner_text())
                    if m:
                        bedrooms = int(m.group())

                handover_year, legal_status = fetch_listing_details(detail_page, full_url, "alonhadat.com.vn")
                print(f"      {title[:40]} → handover={handover_year} legal={legal_status}")

                results.append(Property(
                    title=title, price_billion=round(price, 3), area_m2=area,
                    price_per_m2_million=price_per_m2, location=location,
                    district=district, bedrooms=bedrooms, url=full_url,
                    property_type=prop_type, source="alonhadat.com.vn",
                    handover_year=handover_year,
                    legal_status=legal_status,
                ))
            except Exception as e:
                print(f"      Parse error: {e}")
                continue

    except PlaywrightTimeout:
        print("    Timeout — bỏ qua")
    except Exception as e:
        print(f"    Error: {e}")

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
        page        = ctx.new_page()
        detail_page = ctx.new_page()
        for p in (page, detail_page):
            p.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("\n[mogi.vn]")
        for t in ["can-ho", "nha-rieng", "dat"]:
            props = scrape_mogi(page, detail_page, t)
            all_props.extend(props)
            print(f"    ✓ {len(props)} listings")
            time.sleep(1.5)

        print("\n[alonhadat.com.vn]")
        for t in ["can-ho-chung-cu", "nha-rieng", "dat-nen"]:
            props = scrape_alonhadat(page, detail_page, t)
            all_props.extend(props)
            print(f"    ✓ {len(props)} listings")
            time.sleep(1.5)

        browser.close()

    return all_props


if __name__ == "__main__":
    print("=== SCRAPING BĐS TP.HCM 3-5 TỶ (Playwright) ===")
    props = scrape_all()

    out = os.path.join(os.path.dirname(__file__), "data.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in props], f, ensure_ascii=False, indent=2)

    print(f"\nTổng: {len(props)} bất động sản → {out}")
    for p in props[:3]:
        print(f"  • {p.title[:50]} | {p.price_billion}tỷ | {p.district} | {p.source}")
        print(f"    handover={p.handover_year}  legal={p.legal_status}")
