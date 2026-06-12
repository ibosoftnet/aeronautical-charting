"""
DHMI AIS Portal - ATS Route Segment Info Fetcher
4 JSON dosyasındaki LineString feature'larını uuid/kid ile sorgular,
gelen HTML'i parse edip ais_ önekiyle property olarak ekler.
Sonuçları _enriched.json olarak kaydeder.
"""

import json
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
# İndirilen girdiler ve ara (_enriched) dosyalar temp/ altına yazılır.
# Sonuç dosyaları (lmerged.json / umerged.json) ana dizinde kalır.
# Tier (lower/upper) dosya adının ilk harfinden anlaşılır: l* → lmerged, u* → umerged.
TEMP_DIR = BASE_DIR / "temp"
JSON_FILES = [
    TEMP_DIR / "lats.json",
    TEMP_DIR / "lrnav.json",
    TEMP_DIR / "uats.json",
    TEMP_DIR / "urnav.json",
]

BASE_URL     = "https://ais.dhmi.gov.tr"
LOGIN_URL    = f"{BASE_URL}/account/login"
INFO_URL     = f"{BASE_URL}/clickedinfos/routesegmentclickedinfo.aspx?id={{kid}}"
# Girdi GeoJSON'ları buradan indirilir (herkese açık, login gerekmez).
# Uzak dosya adı, yerel dosya adıyla aynıdır (lats.json, lrnav.json, uats.json, urnav.json).
GEOJSON_BASE = f"{BASE_URL}/geojsonpages/"

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


def download_inputs(attempts: int = 3, timeout: int = 120):
    """Gerekli GeoJSON girdi dosyalarını geojsonpages'ten indirir (herkese açık).

    Uzak dosya adı yerel dosya adıyla aynıdır. Login'den önce çağrılır.
    Ağ geçici olarak yavaş/kesik olabildiği için her dosya için yeniden denenir.
    """
    print(">>> Girdi GeoJSON dosyaları indiriliyor…")
    for json_path in JSON_FILES:
        url = GEOJSON_BASE + json_path.name
        json_path.parent.mkdir(parents=True, exist_ok=True)
        last_ex = None
        for attempt in range(1, attempts + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                data = json.loads(raw.decode("utf-8"))  # geçerli JSON mu?
                n = len(data.get("features", []))
                json_path.write_bytes(raw)
                print(f"    ✓ {json_path.name}  ({len(raw):,} bayt, {n} feature)")
                last_ex = None
                break
            except Exception as ex:
                last_ex = ex
                print(f"    ! {json_path.name} deneme {attempt}/{attempts} başarısız: {ex}")
                if attempt < attempts:
                    time.sleep(3 * attempt)
        if last_ex is not None:
            print(f"    ✗ {json_path.name} indirilemedi: {url}")
            raise last_ex


def _safe_url(driver) -> str:
    """current_url'i güvenli oku; ağır sayfa yüklenirken oluşan geçici hatalarda boş döndür."""
    try:
        return (driver.current_url or "").lower()
    except Exception:
        return ""


def wait_for_login(driver, timeout: int):
    print(f"\n>>> Kullanıcı adı ve şifrenizi girin, CAPTCHA'yı çözüp Giriş Yap'a tıklayın. ({timeout}s bekleniyor…)")
    end = time.time() + timeout

    # 1. Adım: Giriş formu kaybolana kadar bekle
    while time.time() < end:
        try:
            driver.find_element(By.ID, "MainContent_loginControl_UserName")
            time.sleep(1)
        except Exception:
            break
    else:
        print(">>> UYARI: Süre doldu (giriş formu bekleniyor).")
        return False

    # 2. Adım: SMS doğrulama sayfasındaysa tamamlanana kadar bekle.
    # current_url, login sonrası ağır harita sayfası yüklenirken TimeoutException
    # atabildiği için _safe_url ile sarılır (önceki sürüm burada çöküyordu).
    sms_end = time.time() + 300  # SMS için 5 dakika
    sms_prompted = False
    while time.time() < sms_end:
        url = _safe_url(driver)
        if not url:
            time.sleep(2)              # sayfa yükleniyor / geçici hata → beklemeye devam
            continue
        if "smsconfirmation" in url:
            if not sms_prompted:
                print(">>> SMS doğrulama ekranı tespit edildi. Kodu girip Onayla'ya tıklayın…")
                sms_prompted = True
            time.sleep(2)
        elif "account/login" in url:
            time.sleep(2)              # hâlâ login sayfasında (henüz giriş yapılmadı)
        else:
            print(">>> Giriş başarılı, devam ediliyor…\n")
            return True

    print(">>> UYARI: SMS doğrulama süresi doldu.")
    return False


# ── Merge yardımcıları (eski Lower/Upper merge.py araçlarından dahil edildi) ──────
def deduplicate_points(features):
    """Aynı isim (hi) + aynı koordinata sahip Point'leri teke indirir; çizgiler korunur."""
    seen = set()
    out = []
    for feat in features:
        geom = feat.get("geometry", {})
        if geom.get("type") != "Point":
            out.append(feat)
            continue
        key = (feat.get("properties", {}).get("hi"), tuple(geom.get("coordinates", [])))
        if key in seen:
            continue
        seen.add(key)
        out.append(feat)
    return out


def enrich_points_from_lines(features):
    """LineString'lerdeki REPORTING_ATC / NAVIGATION_TYPE bilgisini eşleşen Point'lere işler."""
    updates = defaultdict(lambda: {"ais_REPORTING_ATC": set(), "ais_NAVIGATION_TYPE": set()})
    for feat in features:
        if feat.get("geometry", {}).get("type") != "LineString":
            continue
        props = feat.get("properties", {})
        nav = props.get("ais_NAVIGATION_TYPE")
        for name_key, atc_key in (("ais_START_POINT_NAME", "ais_START_POINT_REPORTING_ATC"),
                                  ("ais_END_POINT_NAME", "ais_END_POINT_REPORTING_ATC")):
            name = props.get(name_key)
            if not name:
                continue
            if props.get(atc_key):
                updates[name]["ais_REPORTING_ATC"].add(props[atc_key])
            if nav:
                updates[name]["ais_NAVIGATION_TYPE"].add(nav)

    for feat in features:
        if feat.get("geometry", {}).get("type") != "Point":
            continue
        props = feat.get("properties", {})
        upd = updates.get(props.get("hi"))
        if not upd:
            continue
        rep = sorted(upd["ais_REPORTING_ATC"])
        nav = sorted(upd["ais_NAVIGATION_TYPE"])
        if rep:
            props["ais_REPORTING_ATC"] = "/".join(rep)
        if nav:
            props["ais_NAVIGATION_TYPE"] = "/".join(nav)
    return features


def merge_and_enrich(geojsons):
    """Birden çok enriched GeoJSON'u birleştirir, noktaları tekilleştirir ve zenginleştirir."""
    features = []
    for gj in geojsons:
        features.extend(gj.get("features", []))
    features = deduplicate_points(features)
    features = enrich_points_from_lines(features)
    return {"type": "FeatureCollection", "features": features}


def main():
    # ── Girdi dosyalarını indir (herkese açık, login öncesi) ───────────────────
    download_inputs()

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
        print(f"Login: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        time.sleep(2)

        if not wait_for_login(driver, CAPTCHA_WAIT_SECONDS):
            print(">>> Giriş tamamlanamadı, işlem yapılmadan çıkılıyor.")
            return

        # ── Process each file ─────────────────────────────────────────────────
        enriched_by_tier: dict[str, list] = {}  # tier harfi ('l'/'u') → enriched geojson listesi
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

            tier = json_path.name[0].lower()  # 'l' (lower) / 'u' (upper)
            enriched_by_tier.setdefault(tier, []).append(geojson)

            print(f"\n  → Kaydedildi: {output_path}")
            print(f"  Başarılı: {len(linestrings) - len(failed)}/{len(linestrings)}")
            if failed:
                print(f"  Başarısız ({len(failed)}): {failed[:3]}…")

        # ── Merge: her tier için tek sonuç dosyası (lmerged.json / umerged.json) ──
        print(f"\n{'='*60}")
        print("Birleştiriliyor (merge + nokta tekilleştirme + çizgilerden zenginleştirme)…")
        for tier, geojsons in enriched_by_tier.items():
            merged = merge_and_enrich(geojsons)
            out_name = tier + "merged.json"  # l→lmerged, u→umerged
            out_path = BASE_DIR / out_name
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            pts = sum(1 for ft in merged["features"] if ft.get("geometry", {}).get("type") == "Point")
            lns = sum(1 for ft in merged["features"] if ft.get("geometry", {}).get("type") == "LineString")
            print(f"  → {out_name}  ({len(merged['features'])} feature: {pts} nokta, {lns} çizgi)")

        print(f"\n{'='*60}")
        print("Tüm dosyalar tamamlandı.")

    finally:
        input("\nBitirmek için Enter'a basın (Chrome kapanacak)…")
        driver.quit()


if __name__ == "__main__":
    main()
