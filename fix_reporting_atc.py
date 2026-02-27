"""
Mevcut *_enriched.json dosyalarındaki LineString ais_START/END_POINT_NAME
değerlerini kullanarak Point feature'larına ais_REPORTING_ATC ekler.
Yeniden web çekimi yapmaz, sadece dosyaları işler.
"""

import json
from pathlib import Path

JSON_FILES = [
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\L Conv\LT\lats_enriched.json"),
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\L RNAV\LT\lrnav_enriched.json"),
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\U Conv\LT\uats_enriched.json"),
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\U RNAV\LT\urnav_enriched.json"),
]

for json_path in JSON_FILES:
    if not json_path.exists():
        print(f"YOK, atlanıyor: {json_path.name}")
        continue

    print(f"\n{'='*60}")
    print(f"İşleniyor: {json_path.name}")

    with open(json_path, encoding="utf-8") as f:
        geojson = json.load(f)

    features = geojson["features"]

    # Point adı → indeks listesi
    point_index: dict[str, list[int]] = {}
    for i, feat in enumerate(features):
        if feat["geometry"]["type"] == "Point":
            name = feat["properties"].get("hi", "").strip()
            if name:
                point_index.setdefault(name, []).append(i)

    linestrings = [f for f in features if f["geometry"]["type"] == "LineString"]
    updated_points = set()
    skipped = 0

    def apply_atc(pt_name: str, atc_value: str):
        if not pt_name or not atc_value:
            return
        for pi in point_index.get(pt_name, []):
            existing = features[pi]["properties"].get("ais_REPORTING_ATC")
            if existing is None:
                features[pi]["properties"]["ais_REPORTING_ATC"] = atc_value
            elif existing != atc_value and atc_value not in existing.split("/"):
                features[pi]["properties"]["ais_REPORTING_ATC"] = existing + "/" + atc_value
            updated_points.add(pi)

    for ls in linestrings:
        props = ls["properties"]
        start_name = props.get("ais_START_POINT_NAME", "").strip()
        end_name   = props.get("ais_END_POINT_NAME", "").strip()
        start_atc  = props.get("ais_START_POINT_REPORTING_ATC", "").strip()
        end_atc    = props.get("ais_END_POINT_REPORTING_ATC", "").strip()

        if not start_name and not end_name:
            skipped += 1
            continue

        apply_atc(start_name, start_atc)
        apply_atc(end_name, end_atc)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"  LineString: {len(linestrings)}  |  Güncellenen nokta: {len(updated_points)}  |  Atlanan LS: {skipped}")
    print(f"  → Kaydedildi: {json_path.name}")

    # Örnek kontrol
    sample = [features[i]["properties"] for i in list(updated_points)[:3]]
    for s in sample:
        print(f"    {s.get('hi')} → {s.get('ais_REPORTING_ATC')}")

print("\nTamamlandı.")
