"""COP (change over point) kaynak okuyucu.

Girdi: ../COP/turkiye_enr31_changeover_points.json — AIP TÜRKİYE **ENR 3.1**
(Conventional Navigation Routes) tablolarındaki "Change over point BTN"
satırlarından çıkarılmış 100 kayıt.

Kayıt biçimi:

    { "ilişkili_ats_yolu": "A4", "vor_1": "BUK", "vor_1_mesafe_nm": 80,
                                 "vor_2": "SIV", "vor_2_mesafe_nm": 97 }

Rota kodu kaynakta **boşluksuz** ("A4"), ham rota verisinde ise boşukludur
("A 4"); eşleme `generate_aixm.py` tarafında normalize edilerek yapılır.
"""

import json

#: Rota kodu anahtarı Türkçe karakter taşıyor ("ilişkili_ats_yolu"). Anahtar
#: elle yazılmaz; dosyadaki gerçek ad sondan eşleşmeyle bulunur — böylece
#: kaynak dosyadaki kodlama/yazım farkları sessizce eşleşmeyi bozamaz.
_ROUTE_KEY_SUFFIX = "ats_yolu"


def _distance(value, log, ident, field):
    """Mesafeyi sayıya çevirir. Boş/çözülemeyen değer None döner.

    Kaynak notu bu alanların null olabileceğini söylüyor (bu dosyada hiç
    yok, ölçüldü) — bu yüzden None bir hata değil, yalnızca "yazılmaz"dır.
    Sayıya çevrilemeyen bir değer ise gerçek hatadır ve loglanır.
    """
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        log.error("ChangeOverPoint", ident, field, value,
                  "cop_mesafesi_sayiya_cevrilemedi")
        return None


def load(path, log):
    """COP kayıtlarını normalize edilmiş sözlük listesi olarak döndürür.

    Döner: [{route, vor_1, distance_1, vor_2, distance_2}] — sırası kaynaktaki
    sırayla aynıdır.
    """
    if not path.exists():
        log.error("ChangeOverPoint", "-", "-", str(path), "cop_dosyasi_yok")
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    raw_records = data.get("changeover_points", [])
    if not raw_records:
        log.error("ChangeOverPoint", "-", "changeover_points", str(path),
                  "cop_dosyasi_bos")
        return []

    route_key = next((k for k in raw_records[0] if k.endswith(_ROUTE_KEY_SUFFIX)),
                     None)
    if route_key is None:
        log.error("ChangeOverPoint", "-", "-", str(sorted(raw_records[0])),
                  "cop_rota_anahtari_bulunamadi")
        return []

    records = []
    for raw in raw_records:
        route = (raw.get(route_key) or "").strip()
        vor_1 = (raw.get("vor_1") or "").strip()
        vor_2 = (raw.get("vor_2") or "").strip()
        ident = f"{route}_{vor_1}_{vor_2}"

        if not (route and vor_1 and vor_2):
            log.error("ChangeOverPoint", ident, "-", str(raw),
                      "cop_kaydi_eksik_alan")
            continue

        records.append({
            "route": route,
            "vor_1": vor_1,
            "distance_1": _distance(raw.get("vor_1_mesafe_nm"), log, ident,
                                    "vor_1_mesafe_nm"),
            "vor_2": vor_2,
            "distance_2": _distance(raw.get("vor_2_mesafe_nm"), log, ident,
                                    "vor_2_mesafe_nm"),
        })
    return records
