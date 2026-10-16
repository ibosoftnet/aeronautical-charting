"""VFR kaynak okuyucu: VFRPOINT.json / VFRSEGMENT.json.

Her iki dosyada da bilgi `pic` alanında HTML olarak gömülüdür; ayrı bir
clicked-info sorgusu gerekmez (doğrulandı: VFRSEGMENT'in 9 etiketi 205/205
kayıtta dolu).
"""

import json
import re

_POS_RE = re.compile(r"Position\s*:\s*</b>(.*?)<br>")
_DESC_RE = re.compile(r"Description\s*:\s*</b>(.*?)(?:<br>|$)")

_SEGMENT_LABELS = {
    "route": r"Route\s*:\s*</b>(.*?)<br>",
    "route_segment": r"Route Segment\s*:\s*</b>(.*?)<br>",
    "start_point": r"Start Point\s*:\s*</b>(.*?)<br>",
    "end_point": r"End Point\s*:\s*</b>(.*?)<br>",
    "distance": r"Distance\s*:\s*</b>(.*?)<br>",
    "calc_start": r"Calc\. Start\s*:\s*</b>(.*?)<br>",
    "calc_end": r"Calc End\s*:\s*</b>(.*?)<br>",
    "magnetic_start": r"Magnetic Start\s*:\s*</b>(.*?)<br>",
    "magnetic_end": r"Magnetic End\s*:\s*</b>(.*?)$",
}
_SEGMENT_RES = {k: re.compile(v) for k, v in _SEGMENT_LABELS.items()}


def _read(raw_dir, name):
    with open(raw_dir / name, encoding="utf-8") as f:
        return json.load(f)


def _degrees(value: str) -> str:
    """"37°" → "37"; boş değer boş kalır."""
    return (value or "").replace("°", "").strip()


def load_points(raw_dir, log):
    """VFR noktalarını döndürür (fix açıklaması ham metin olarak taşınır)."""
    points = []
    for feat in _read(raw_dir, "VFRPOINT.json").get("features", []):
        p = feat["properties"]
        lon, lat = feat["geometry"]["coordinates"]
        desc = _DESC_RE.search(p.get("pic", ""))
        points.append({
            "kid": str(p.get("kid")),
            "name": p.get("hi", "").strip(),
            "description": desc.group(1).strip() if desc else "",
            "lon": lon,
            "lat": lat,
        })
    return points


def load_segments(raw_dir, log):
    """VFR segmentlerini `pic` alanını çözerek döndürür."""
    segments = []
    for feat in _read(raw_dir, "VFRSEGMENT.json").get("features", []):
        p = feat["properties"]
        pic = p.get("pic", "")
        record = {"kid": str(p.get("kid")), "hi": p.get("hi", "").strip()}
        for key, rx in _SEGMENT_RES.items():
            m = rx.search(pic)
            if m is None:
                log.error("RouteSegment(VFR)", record["kid"], key, "-",
                          "pic_alani_cozulemedi")
                record[key] = ""
            else:
                record[key] = m.group(1).strip()

        for key in ("calc_start", "calc_end", "magnetic_start", "magnetic_end"):
            record[key] = _degrees(record[key])
        # "10.8 NM" → "10.8" (birim envanteri 205/205 NM, doğrulandı)
        record["distance"] = record["distance"].replace("NM", "").strip()

        coords = feat["geometry"]["coordinates"]
        record["start_coord"] = tuple(coords[0])
        record["end_coord"] = tuple(coords[-1])
        segments.append(record)
    return segments
