"""
DHMI AIS Portal - ATS Route Segment Info Fetcher
4 JSON dosyasındaki LineString feature'larını uuid/kid ile sorgular,
gelen HTML'i parse edip ais_ önekiyle property olarak ekler.
Sonuçları _enriched.json olarak kaydeder.
"""

import json
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
JSON_FILES = [
    BASE_DIR / "Lower" / "lats.json",
    BASE_DIR / "Lower" / "lrnav.json",
    BASE_DIR / "Upper" / "uats.json",
    BASE_DIR / "Upper" / "urnav.json",
]

BASE_URL     = "https://ais.dhmi.gov.tr"
LOGIN_URL    = f"{BASE_URL}/account/login"
INFO_URL     = f"{BASE_URL}/clickedinfos/routesegmentclickedinfo.aspx?id={{kid}}"

USERNAME = ""  # runtime'da sorulacak
PASSWORD = ""  # runtime'da sorulacak

CAPTCHA_WAIT_SECONDS = 120
PAGE_LOAD_TIMEOUT    = 20
DELAY_BETWEEN_PAGES  = 0.6
# ─────────────────────────────────────────────────────────────────────────────


def parse_segment_page(html: str) -> dict:
    """Parse route segment info HTML and return a flat dict of field→value."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}

    # Strategy 1 – label/value CSS class names (same pattern as airport page)
    label_cells = soup.find_all("td", class_=re.compile(r"label", re.I))
    for lc in label_cells:
        raw_label = lc.get_text(strip=True).rstrip(":").strip()
        vc = lc.find_next_sibling("td")
        if vc:
            value = vc.get_text(strip=True)
            if raw_label:
                data[raw_label] = value

    # Strategy 2 – all 2-column table rows if strategy 1 got nothing
    if not data:
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2:
                label = tds[0].get_text(strip=True).rstrip(":").strip()
                value = tds[1].get_text(strip=True)
                if label:
                    data[label] = value

    # Strategy 3 – <span id="…lbl…"> Telerik-style labels
    if not data:
        for span in soup.find_all("span", id=re.compile(r"lbl", re.I)):
            key = span["id"].split("_")[-1].replace("lbl", "")
            value = span.get_text(strip=True)
            if key and value:
                data[key] = value

    return data


def wait_for_login(driver, timeout: int):
    print(f"\n>>> CAPTCHA'yı çözüp Giriş Yap'a tıklayın. ({timeout}s bekleniyor…)")
    end = time.time() + timeout
    while time.time() < end:
        try:
            driver.find_element(By.ID, "MainContent_loginControl_UserName")
            time.sleep(1)
        except Exception:
            print(">>> Giriş başarılı, devam ediliyor…\n")
            return True
    print(">>> UYARI: Süre doldu.")
    return False


def main():
    # ── Launch Selenium ───────────────────────────────────────────────────────
    options = Options()
    options.add_argument("--start-maximized")
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

        print(f"Login: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        time.sleep(2)

        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "MainContent_loginControl_UserName")
                )
            )
            driver.find_element(By.ID, "MainContent_loginControl_UserName").send_keys(username)
            driver.find_element(By.ID, "MainContent_loginControl_Password").send_keys(password)
            print("Kullanıcı adı ve şifre girildi.")
        except Exception as e:
            print(f"UYARI: Form doldurulamadı: {e}")

        wait_for_login(driver, CAPTCHA_WAIT_SECONDS)

        # ── Process each file ─────────────────────────────────────────────────
        for json_path in JSON_FILES:
            output_path = json_path.parent / (json_path.stem + "_enriched.json")
            print(f"\n{'='*60}")
            print(f"Dosya: {json_path.name}")

            with open(json_path, encoding="utf-8") as f:
                geojson = json.load(f)

            features = geojson.get("features", [])

            # Build name → list of point feature indices for fast lookup
            # (same name may appear multiple times, e.g. shared waypoint)
            point_index: dict[str, list[int]] = {}
            for i, feat in enumerate(features):
                if feat["geometry"]["type"] == "Point":
                    name = feat["properties"].get("hi", "").strip()
                    if name:
                        point_index.setdefault(name, []).append(i)

            linestrings = [
                (i, feat) for i, feat in enumerate(features)
                if feat["geometry"]["type"] == "LineString"
            ]
            print(f"  Toplam feature: {len(features)}  |  LineString: {len(linestrings)}  |  Point: {len(point_index)} unique name")

            failed = []
            for count, (idx, feature) in enumerate(linestrings, 1):
                kid = feature.get("properties", {}).get("kid", "")
                if not kid:
                    continue

                url = INFO_URL.format(kid=kid)
                print(f"  [{count}/{len(linestrings)}] {kid}", end="  ", flush=True)

                try:
                    driver.get(url)
                    time.sleep(DELAY_BETWEEN_PAGES)
                    html = driver.page_source
                    info = parse_segment_page(html)
                    if info:
                        # 1. Add all fields to the LineString
                        for k, v in info.items():
                            safe_key = "ais_" + re.sub(r"\W+", "_", k).strip("_")
                            features[idx]["properties"][safe_key] = v

                        # 2. Propagate REPORTING ATC to matching Point features
                        # Read from already-written ais_ props to avoid key-format issues
                        props = features[idx]["properties"]
                        start_name = props.get("ais_START_POINT_NAME", "").strip()
                        end_name   = props.get("ais_END_POINT_NAME", "").strip()
                        start_atc  = props.get("ais_START_POINT_REPORTING_ATC", "").strip()
                        end_atc    = props.get("ais_END_POINT_REPORTING_ATC", "").strip()

                        def apply_reporting_atc(pt_name: str, atc_value: str):
                            if not pt_name or not atc_value:
                                return
                            for pi in point_index.get(pt_name, []):
                                existing = features[pi]["properties"].get("ais_REPORTING_ATC")
                                if existing is None:
                                    features[pi]["properties"]["ais_REPORTING_ATC"] = atc_value
                                elif existing != atc_value and atc_value not in existing.split("/"):
                                    features[pi]["properties"]["ais_REPORTING_ATC"] = existing + "/" + atc_value

                        apply_reporting_atc(start_name, start_atc)
                        apply_reporting_atc(end_name, end_atc)

                        print(f"✓ {len(info)} alan | start={start_name}({start_atc}) end={end_name}({end_atc})")
                    else:
                        print("⚠ boş")
                        failed.append(kid)
                except Exception as ex:
                    print(f"✗ {ex}")
                    failed.append(kid)

            # Save enriched file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)

            print(f"\n  → Kaydedildi: {output_path}")
            print(f"  Başarılı: {len(linestrings) - len(failed)}/{len(linestrings)}")
            if failed:
                print(f"  Başarısız ({len(failed)}): {failed[:3]}…")

        print(f"\n{'='*60}")
        print("Tüm dosyalar tamamlandı.")

    finally:
        input("\nBitirmek için Enter'a basın (Chrome kapanacak)…")
        driver.quit()


if __name__ == "__main__":
    main()
