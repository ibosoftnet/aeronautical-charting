"""
DHMI AIS Portal - Airport Info Fetcher
Reads AIRPORT.json, queries airportinfo.aspx for each feature (by uuid/kid),
parses the result HTML and adds all data as extra properties.

Workflow:
  1. Opens Chrome via Selenium
  2. Fills in username + password
  3. Waits up to 120 s for you to solve the CAPTCHA and finish logging in
  4. Scrapes every airport page
  5. Saves enriched GeoJSON next to the original file
"""

import json
import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ── Configuration ────────────────────────────────────────────────────────────
GEOJSON_PATH = Path(
    r"d:\ibosoft\aeronautical-charting\aeronautical-data\AD-HP\Designated AD-HP\LT\AIRPORT.json"
)
OUTPUT_PATH = GEOJSON_PATH.parent / "AIRPORT_enriched.json"

BASE_URL = "https://ais.dhmi.gov.tr"
LOGIN_URL = f"{BASE_URL}/account/login"
INFO_URL  = f"{BASE_URL}/clickedinfos/airportinfo.aspx?id={{kid}}"

USERNAME = ""  # runtime'da sorulacak
PASSWORD = ""  # runtime'da sorulacak

CAPTCHA_WAIT_SECONDS = 120   # max time to wait for you to solve the CAPTCHA
PAGE_LOAD_TIMEOUT    = 20    # seconds per airport page
DELAY_BETWEEN_PAGES  = 1.0   # polite delay between requests
# ─────────────────────────────────────────────────────────────────────────────


def parse_airport_page(html: str) -> dict:
    """Parse the airport info HTML page and return a flat dict of field→value."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}

    # The page uses a GridView / table layout: each row has a label cell and a
    # value cell.  The labels are rendered as <span> items or plain text inside
    # <td class="labelCellStyle"> and values in <td class="valueCellStyle">.
    # Fall back to any two-column table if those class names change.

    # Strategy 1 – look for explicit label/value class names
    label_cells = soup.find_all("td", class_=re.compile(r"label", re.I))
    for lc in label_cells:
        raw_label = lc.get_text(strip=True).rstrip(":")
        vc = lc.find_next_sibling("td")
        if vc:
            value = vc.get_text(strip=True)
            if raw_label:
                data[raw_label] = value

    # Strategy 2 – if strategy 1 found nothing, parse all 2-col table rows
    if not data:
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2:
                label = tds[0].get_text(strip=True).rstrip(":")
                value = tds[1].get_text(strip=True)
                if label and not label.lower().startswith("show") and \
                   not label.lower().startswith("metar"):
                    data[label] = value

    # Strategy 3 – RadGrid / Telerik grid spans
    if not data:
        spans = soup.find_all("span", id=re.compile(r"lbl", re.I))
        for span in spans:
            span_id = span.get("id", "")
            key = span_id.split("_")[-1].replace("lbl", "")
            value = span.get_text(strip=True)
            if key and value:
                data[key] = value

    return data


def wait_for_login(driver, timeout: int):
    """Block until the login form disappears (user completed login)."""
    print(f"\n>>> CAPTCHA çözüp Giriş Yap butonuna basın. "
          f"{timeout} saniye beklenecek …")
    end = time.time() + timeout
    while time.time() < end:
        try:
            driver.find_element(By.ID, "MainContent_loginControl_UserName")
            time.sleep(1)
        except Exception:
            print(">>> Giriş başarılı, devam ediliyor …\n")
            return True
    print(">>> UYARI: Süre doldu, login tamamlanamadı olabilir.")
    return False


def main():
    # ── Load GeoJSON ──────────────────────────────────────────────────────────
    print(f"GeoJSON okunuyor: {GEOJSON_PATH}")
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        geojson = json.load(f)

    features = geojson.get("features", [])
    print(f"Toplam {len(features)} feature bulundu.\n")

    # ── Launch Selenium Chrome ────────────────────────────────────────────────
    options = Options()
    options.add_argument("--start-maximized")
    # Do NOT use headless – user needs to see and solve the CAPTCHA
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    try:
        # ── Login ─────────────────────────────────────────────────────────────
        import getpass
        username = input("Kullanıcı adı: ").strip()
        password = getpass.getpass("Şifre: ")

        print(f"Login sayfası açılıyor: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        time.sleep(2)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "MainContent_loginControl_UserName")
                )
            )
            driver.find_element(
                By.ID, "MainContent_loginControl_UserName"
            ).send_keys(username)
            driver.find_element(
                By.ID, "MainContent_loginControl_Password"
            ).send_keys(password)
            print("Kullanıcı adı ve şifre girildi.")
        except Exception as e:
            print(f"UYARI: Giriş formu doldurulamadı: {e}")

        wait_for_login(driver, CAPTCHA_WAIT_SECONDS)

        # ── Scrape each feature ───────────────────────────────────────────────
        failed = []
        for i, feature in enumerate(features, 1):
            kid = feature.get("properties", {}).get("kid", "")
            if not kid:
                print(f"[{i}/{len(features)}] kid yok, atlanıyor.")
                continue

            url = INFO_URL.format(kid=kid)
            print(f"[{i}/{len(features)}] {kid}  →  {url}")

            try:
                driver.get(url)
                time.sleep(DELAY_BETWEEN_PAGES)
                html = driver.page_source
                info = parse_airport_page(html)
                if info:
                    # Add all fetched fields under "ais_" prefix to avoid
                    # collisions with existing properties
                    for k, v in info.items():
                        safe_key = "ais_" + re.sub(r"\W+", "_", k).strip("_")
                        feature["properties"][safe_key] = v
                    print(f"         ✓ {len(info)} alan eklendi: "
                          f"{list(info.keys())[:5]} …")
                else:
                    print("         ⚠ Veri ayrıştırılamadı / boş sayfa.")
                    failed.append(kid)
            except Exception as ex:
                print(f"         ✗ Hata: {ex}")
                failed.append(kid)

        # ── Save output ───────────────────────────────────────────────────────
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"Enriched GeoJSON kaydedildi:\n  {OUTPUT_PATH}")
        print(f"Başarılı: {len(features) - len(failed)}/{len(features)}")
        if failed:
            print(f"Başarısız ({len(failed)}): {failed[:5]}")

    finally:
        input("\nBitirmek için Enter'a basın (Chrome kapanacak)…")
        driver.quit()


if __name__ == "__main__":
    main()
