"""
Merkezi hava sahası GeoPackage oluşturucu.

config.json'daki kaynak modüllerini (sources/*.py) sırayla çalıştırır, her
kaydı ortak `airspaces` tablosuna + RTree'ye ekler, sonda tüm sütun index'lerini
kurar. Şema: AIXM_to_GeoPackage_Schema_Design.md.
"""
import importlib
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from common import schema  # noqa: E402


def main():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    out = os.path.join(BASE, cfg["output"])
    print(f"Output : {out}")
    g = schema.create_gpkg(out)
    g.commit()
    cur = g.cursor()

    total = 0
    for name in cfg["sources_enabled"]:
        mod = importlib.import_module(f"sources.{name}")
        ins = skip = 0
        for rec in (mod.load(cfg, BASE) or []):
            if schema.insert_record(cur, rec):
                ins += 1
            else:
                skip += 1
        g.commit()
        total += ins
        print(f"  {name}: inserted={ins}  skipped={skip}")

    n = schema.build_indexes(g)
    print(f"  indexes: {n} sütun + RTree spatial index")
    print(f"Done. {out}  ({os.path.getsize(out):,} bytes)  total={total}")
    g.close()


if __name__ == "__main__":
    main()
