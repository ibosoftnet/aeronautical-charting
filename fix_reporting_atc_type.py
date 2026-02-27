"""
ais_REPORTING_ATC değerlerini normalize eder:
  list  → elemanları "/" ile birleştirir  (örn. "COMPULSORY/ON_REQUEST")
  str   → olduğu gibi bırakır
Tüm _enriched.json dosyalarını yerinde günceller.
"""
import json
from pathlib import Path

FILES = [
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\L Conv\LT\lats.json"),
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\L RNAV\LT\lrnav.json"),
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\U Conv\LT\uats.json"),
    Path(r"d:\ibosoft\aeronautical-charting\aeronautical-data\ATS Routes\U RNAV\LT\urnav.json"),
]

for fp in FILES:
    with open(fp, encoding="utf-8") as f:
        geojson = json.load(f)

    fixed = 0
    for feat in geojson["features"]:
        val = feat["properties"].get("ais_REPORTING_ATC")
        if isinstance(val, list):
            feat["properties"]["ais_REPORTING_ATC"] = "/".join(val)
            fixed += 1

    with open(fp, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"{fp.name}: {fixed} dizi → string'e çevrildi")

print("Tamamlandı.")
