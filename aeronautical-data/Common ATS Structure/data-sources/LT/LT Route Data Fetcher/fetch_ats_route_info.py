"""
DHMI AIS Portal - LT Route Data Fetcher

1) 6 GeoJSON dosyasını (urnav, lrnav, uats, lats, VFRSEGMENT, VFRPOINT) geojsonpages'ten
   herkese açık, login gerekmeden raw-data/ altına indirir.
2) ATS rota segmentleri (lats/lrnav/uats/urnav) için, her LineString feature'ın kid'i ile
   routesegmentclickedinfo.aspx sayfasını (Selenium login sonrası) sorgular, HTML'i parse
   eder ve sonucu <isim>_info.json olarak (kid -> alan sözlüğü) raw-data/ altına yazar.
   VFRSEGMENT/VFRPOINT bu adıma girmez: VFRSEGMENT'in "pic" alanı zaten aynı bilgiyi
   HTML olarak taşıyor, VFRPOINT ise Point olduğu için clicked-info sorgusu yok.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw-data"

BASE_URL  = "https://ais.dhmi.gov.tr"
LOGIN_URL = f"{BASE_URL}/account/login"
INFO_URL  = f"{BASE_URL}/clickedinfos/routesegmentclickedinfo.aspx?id={{kid}}"
# Girdi GeoJSON'ları buradan indirilir (herkese açık, login gerekmez).
# Uzak dosya adı, yerel dosya adıyla aynıdır.
GEOJSON_BASE = f"{BASE_URL}/geojsonpages/"

# Herkese açık indirilecek tüm dosyalar.
SOURCE_FILES = [
    "urnav.json",
    "lrnav.json",
    "uats.json",
    "lats.json",
    "VFRSEGMENT.json",
    "VFRPOINT.json",
]

# Sadece bu dosyalar ek-bilgi (Selenium/login) adımına girer.
ATS_FILES = ["lats.json", "lrnav.json", "uats.json", "urnav.json"]

CAPTCHA_WAIT_SECONDS = 120
PAGE_LOAD_TIMEOUT    = 20
DELAY_BETWEEN_PAGES  = 0.6
# ─────────────────────────────────────────────────────────────────────────────


def parse_segment_page(html: str) -> dict:
    """Parse route segment info HTML and return a flat dict of field→value."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}

    # Strategy 1 – label/value CSS class names.
    # Gerçek sayfa "tooltipHeader"/"tooltipValue" kullanıyor; "label" eski
    # havaalanı sayfası deseni için korunuyor.
    label_cells = soup.find_all("td", class_=re.compile(r"label|tooltipHeader", re.I))
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


def parse_route_designator(html: str) -> str:
    """Sayfa başlığındaki rota kodunu döndürür (örn. "UT 54").

    Gerçek yapı:
        <span id="labelRouteSegmentInfo">
          <span class="routeName">UT 54</span><br>
          <table>…</table>
    Rota kodu label/value tablosunda yer almadığı için ayrıca çekilir; AIXM
    Route elemanlarının oluşturulabilmesi için zorunludur.
    """
    soup = BeautifulSoup(html, "html.parser")
    span = soup.find("span", class_="routeName")
    return span.get_text(strip=True) if span else ""


def download_inputs(attempts: int = 3, timeout: int = 120):
    """Girdi GeoJSON dosyalarını geojsonpages'ten raw-data/ altına indirir (herkese açık).

    Uzak dosya adı yerel dosya adıyla aynıdır. Login'den önce çağrılır.
    Ağ geçici olarak yavaş/kesik olabildiği için her dosya için yeniden denenir.
    """
    print(">>> Girdi GeoJSON dosyaları indiriliyor…")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in SOURCE_FILES:
        url = GEOJSON_BASE + name
        json_path = RAW_DIR / name
        last_ex = None
        for attempt in range(1, attempts + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                data = json.loads(raw.decode("utf-8"))  # geçerli JSON mu?
                n = len(data.get("features", []))
                json_path.write_bytes(raw)
                print(f"    ✓ {name}  ({len(raw):,} bayt, {n} feature)")
                last_ex = None
                break
            except Exception as ex:
                last_ex = ex
                print(f"    ! {name} deneme {attempt}/{attempts} başarısız: {ex}")
                if attempt < attempts:
                    time.sleep(3 * attempt)
        if last_ex is not None:
            print(f"    ✗ {name} indirilemedi: {url}")
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


def fetch_segment_info(driver, json_path: Path) -> dict:
    """Bir ATS dosyasındaki her LineString segmenti için ek bilgiyi çeker.

    Döner: {kid: {field: value, ...}, ...} — alan adlarında önek yok.
    """
    with open(json_path, encoding="utf-8") as f:
        geojson = json.load(f)

    linestrings = [
        feat for feat in geojson.get("features", [])
        if feat.get("geometry", {}).get("type") == "LineString"
    ]
    print(f"  Toplam feature: {len(geojson.get('features', []))}  |  LineString: {len(linestrings)}")

    info_by_kid: dict[str, dict] = {}
    failed = []
    no_designator = []
    for count, feature in enumerate(linestrings, 1):
        kid = feature.get("properties", {}).get("kid", "")
        if not kid:
            continue

        url = INFO_URL.format(kid=kid)
        print(f"  [{count}/{len(linestrings)}] {kid}", end="  ", flush=True)

        try:
            driver.get(url)
            time.sleep(DELAY_BETWEEN_PAGES)
            html = driver.page_source
            raw_info = parse_segment_page(html)
            if raw_info:
                info = {
                    re.sub(r"\W+", "_", k).strip("_"): v
                    for k, v in raw_info.items()
                }
                designator = parse_route_designator(html)
                info["ROUTE_DESIGNATOR"] = designator
                if not designator:
                    no_designator.append(kid)
                info_by_kid[kid] = info
                start_name = info.get("START_POINT_NAME", "")
                end_name = info.get("END_POINT_NAME", "")
                print(f"✓ {len(info)} alan | {designator or '?'} | start={start_name} end={end_name}")
            else:
                print("⚠ boş")
                failed.append(kid)
        except Exception as ex:
            print(f"✗ {ex}")
            failed.append(kid)

    print(f"  Başarılı: {len(linestrings) - len(failed)}/{len(linestrings)}")
    if failed:
        print(f"  Başarısız ({len(failed)}): {failed[:3]}…")
    if no_designator:
        print(f"  ⚠ Rota kodu okunamayan segment ({len(no_designator)}): {no_designator[:3]}…")

    return info_by_kid


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

        # ── ATS dosyaları için ek bilgi çek ──────────────────────────────────────
        for name in ATS_FILES:
            json_path = RAW_DIR / name
            output_path = RAW_DIR / (json_path.stem + "_info.json")
            print(f"\n{'='*60}")
            print(f"Dosya: {name}")

            info_by_kid = fetch_segment_info(driver, json_path)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(info_by_kid, f, ensure_ascii=False, indent=2)
            print(f"  → Kaydedildi: {output_path}")

        print(f"\n{'='*60}")
        print("Tüm dosyalar tamamlandı.")

    finally:
        input("\nBitirmek için Enter'a basın (Chrome kapanacak)…")
        driver.quit()


if __name__ == "__main__":
    main()
