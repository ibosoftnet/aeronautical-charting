"""ATS kaynak okuyucu: lats / lrnav / uats / urnav geojson + *_info.json.

Noktalar 4 dosyada tekrarlanır; `kid` ile tekilleştirilir (doğrulandı: aynı
kid her dosyada aynı isim, tip ve koordinatı taşıyor).
"""

import json
import re

ATS_FILES = ["lats", "lrnav", "uats", "urnav"]

_DESIGNATOR_RE = re.compile(r"DESIGNATOR\s*:\s*</b>(.*?)<br>")
_NAME_RE = re.compile(r"NAME\s*:\s*</b>(.*?)<br>")
_TYPE_RE = re.compile(r"TYPE\s*:\s*</b>(.*?)(?:<br>|$)")


def _read(raw_dir, name):
    with open(raw_dir / name, encoding="utf-8") as f:
        return json.load(f)


def load_points(raw_dir, log):
    """DP ve navaid noktalarını kid ile tekilleştirerek döndürür.

    Döner: (designated_points, navaids) — her biri kayıt listesi.
    """
    dps, navaids = {}, {}
    for stem in ATS_FILES:
        for feat in _read(raw_dir, f"{stem}.json").get("features", []):
            if feat.get("geometry", {}).get("type") != "Point":
                continue
            p = feat["properties"]
            kid = p.get("kid")
            lon, lat = feat["geometry"]["coordinates"]
            pic = p.get("pic", "")

            if p.get("type") == "DP":
                m = _TYPE_RE.search(pic)
                record = {
                    "kid": kid,
                    "designator": p.get("hi", "").strip(),
                    "type": m.group(1).strip() if m else "",
                    "lon": lon,
                    "lat": lat,
                }
                _merge(dps, kid, record, log, "DesignatedPoint")
            else:
                md, mn, mt = (
                    _DESIGNATOR_RE.search(pic),
                    _NAME_RE.search(pic),
                    _TYPE_RE.search(pic),
                )
                record = {
                    "kid": kid,
                    "designator": md.group(1).strip() if md else "",
                    # `hi` ile pic/NAME birebir aynı (doğrulandı, 65/65).
                    "name": p.get("hi", "").strip(),
                    "type": mt.group(1).strip() if mt else p.get("type", ""),
                    "lon": lon,
                    "lat": lat,
                }
                if mn and mn.group(1).strip() != record["name"]:
                    log.warning("Navaid", kid, "name", record["name"],
                                "hi_ile_pic_NAME_uyusmuyor")
                _merge(navaids, kid, record, log, "Navaid")

    return list(dps.values()), list(navaids.values())


def _merge(store, kid, record, log, feature):
    """Aynı kid farklı içerikle gelirse loglar; ilk kayıt korunur."""
    existing = store.get(kid)
    if existing is None:
        store[kid] = record
    elif existing != record:
        log.error(feature, kid, "-", "-", "ayni_kid_farkli_icerik")


def load_segments(raw_dir, log):
    """Tüm *_info.json kayıtlarını tek listede döndürür."""
    segments = []
    for stem in ATS_FILES:
        path = raw_dir / f"{stem}_info.json"
        if not path.exists():
            log.error("RouteSegment", stem, "-", str(path), "info_dosyasi_yok")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for kid, info in data.items():
            record = dict(info)
            record["kid"] = kid
            record["source"] = stem
            segments.append(record)
    return segments
