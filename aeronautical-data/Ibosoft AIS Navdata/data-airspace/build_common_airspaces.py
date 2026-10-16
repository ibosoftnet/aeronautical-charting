r"""Common Airspaces — birleştirici (data-airspace).

ATS ile aynı üç aşama:

  1   KAYNAK ÜRETİCİLERİ   her kaynağın ham verisi → kendi AIXM 5.2 dosyası
                           (her feature kendi provenance kutusunu taşır)
  2A  BİRLEŞTİRME          ana kaynaklar (Jeppesen, ICAO-FIR-UIR) → iptal
                           kuralları → ek kaynaklar (LT, LH, TRNC, tailored-LT,
                           ibosoft) ⇒ navdata/ibosoft-ais-navdata-airspaces-aixm.xml
  2B  GEOPACKAGE           yalnızca 2A çıktısından ⇒ navdata/ibosoft-ais-navdata-airspaces.gpkg

Kullanım:
    py build_common_airspaces.py            # (1 →) 2A + 2B
    py build_common_airspaces.py --sources  # yalnızca 1. aşama
    py build_common_airspaces.py --merge    # yalnızca 2A
    py build_common_airspaces.py --gpkg     # yalnızca 2B

Davranış ayrıntısı: Common_Builder_Behaviour.md
"""

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR.parent / "common"))       # data_build_common

from data_build_common import aixm_reader as rdr           # noqa: E402
from data_build_common import gpkg_writer, provenance      # noqa: E402
from data_build_common.aixm_writer import MergedMessageWriter  # noqa: E402
from data_build_common.build_log import BuildLog           # noqa: E402
from data_build_common.exclude import ExcludeRules         # noqa: E402
from data_build_common.override import OverrideIndex       # noqa: E402

import gpkg_airspace                                       # noqa: E402
from airspace_geometry import (GeometryError, airspace_geometry,  # noqa: E402
                               orient_member)

MESSAGE_ID = "COMMON_AIRSPACES_MSG"
LAYER = "airspaces"


# ── Ortak: feature özeti ────────────────────────────────────────────────────

def describe(feature):
    """Birleştirme için doğal alanlar + geometri merkezi.

    Merkez, 2B'nin kullandığı geometri hesabıyla (bileşenler sırayla,
    antimeridyen güvenli) bulunur; eski Common Airspaces kodundaki
    `antimeridian_safe(geom).centroid` ile aynı yöntem.
    """
    ts = rdr.time_slice(feature)
    prov = provenance.require(feature)
    fields = {
        "layer": LAYER,
        "kind": rdr.local(feature.tag),
        "provider": prov["data_provider"],
        "originator": prov["data_originator"] or "",
        "type": rdr.text_of(ts, "type"),
        "designator": rdr.text_of(ts, "designator"),
        "name": rdr.text_of(ts, "name"),
    }
    try:
        geometry, _ = airspace_geometry(ts)
        centroid = geometry.centroid
        location = (centroid.x, centroid.y)
    except GeometryError:
        location = None
    return fields, location


def override_key(fields, originator):
    """Override anahtarı: tip + designator + (ana kaynaktaki) originator.

    Designator'ı olmayan saha eşleştirilemez (None).
    """
    if not fields.get("designator"):
        return None
    return (fields.get("type"), fields["designator"], originator)


# ── AŞAMA 1 ─────────────────────────────────────────────────────────────────

def run_source_generators(cfg, root, log):
    print("=" * 62)
    print("ASAMA 1 — KAYNAK URETICILERI")
    print("=" * 62)
    for entry in cfg.get("source_generators", []):
        name, script = entry["name"], entry.get("script")
        if not entry.get("enabled", True):
            print(f"  {name:12} — config'de kapali, atlandi")
            continue
        path = root / script
        if not path.exists():
            log.error("1", "-", name, "script", script, "script_dosyasi_yok")
            raise SystemExit(f"1. asama durdu: {name} scripti yok")
        print(f"\n  ── {name} ──  {script}")
        started = time.monotonic()
        done = subprocess.run([sys.executable, "-X", "utf8", str(path)],
                              cwd=path.parent)
        if done.returncode != 0:
            log.error("1", "-", name, "exit_code", str(done.returncode),
                      "uretici_hata_verdi")
            raise SystemExit(f"1. asama durdu: {name} uretici "
                             f"{done.returncode} koduyla cikti.")
        print(f"  {name:12} tamam ({time.monotonic() - started:.0f} sn)")


# ── AŞAMA 2A ────────────────────────────────────────────────────────────────

def run_merge(cfg, root, log):
    print("=" * 62)
    print("ASAMA 2A — BIRLESTIRME")
    print("=" * 62)
    base = [s for s in cfg["base_sources"] if s.get("enabled", True)]
    extra = [s for s in cfg["additional_sources"] if s.get("enabled", True)]
    for source in base + extra:
        source["path"] = root / source["file"]
        if not source["path"].exists():
            log.error("2A", LAYER, source["name"], "file", source["file"],
                      "kaynak_dosyasi_yok")
            raise SystemExit(f"2A durdu: {source['name']} dosyasi yok "
                             f"({source['file']})")

    # Override: yalnızca `override_enabled` ek kaynaklar. Anahtar, ana
    # kaynakta aranacak originator yazımıyla kurulur (ATS ile aynı ilke).
    overrides = OverrideIndex()
    for source in extra:
        if not source.get("override_enabled"):
            continue
        base_originator = source.get("override_base_originator") or ""
        for member in rdr.iter_members(source["path"]):
            feature = rdr.feature_of(member)
            fields, _ = describe(feature)
            overrides.add(override_key(fields, base_originator), source["name"],
                          rdr.gml_id_of(feature), rdr.uuid_of(feature))
    print(f"\n[1] Override anahtari: {len(overrides)} "
          f"(override acik kaynak: "
          f"{[s['name'] for s in extra if s.get('override_enabled')] or 'yok'})")

    excludes = ExcludeRules.load(root / cfg["excludes_dir"], log)
    print(f"[2] Iptal kurallari: {len(excludes)}")

    writer = MergedMessageWriter(root / cfg["merged_aixm"], MESSAGE_ID)
    stats = Counter()
    print("\n[3] Birlesik AIXM yaziliyor...")
    for source in base:
        written = skipped_exc = skipped_ovr = 0
        for member in rdr.iter_members(source["path"]):
            feature = rdr.feature_of(member)
            fields, location = describe(feature)
            gml_id = rdr.gml_id_of(feature)
            if location is None:
                log.warning("2A", LAYER, gml_id, "geometry", "-",
                            "merkez_hesaplanamadi_konumlu_iptal_kurali_uygulanamaz")
            rule = excludes.matches(fields, location=location)
            if rule:
                skipped_exc += 1
                log.warning("2A", LAYER, gml_id, "-", rule["source"],
                            "iptal_kuraliyla_cikarildi")
                continue
            if overrides.lookup(override_key(fields, fields["originator"])):
                skipped_ovr += 1
                continue
            # Halka yönü RFC 7946'ya göre (dış saat yönünün tersi, delik saat
            # yönü) — kaynak dosyalar değişmez, yalnız birleşik çıktı.
            stats["halka_ters_cevrildi"] += orient_member(feature)
            writer.write_member(member)
            written += 1
        print(f"  {source['name']:12} yazildi={written:>6} iptal={skipped_exc} "
              f"override_ile_atlandi={skipped_ovr}")
        stats["base_yazildi"] += written
        stats["iptal_edildi"] += skipped_exc
        stats["override_ile_atlandi"] += skipped_ovr

    for source in extra:
        written = 0
        for member in rdr.iter_members(source["path"]):
            feature = rdr.feature_of(member)
            provenance.require(feature)                     # kutusuz = hata
            stats["halka_ters_cevrildi"] += orient_member(feature)
            writer.write_member(member)
            written += 1
        mode = "override" if source.get("override_enabled") else "ekleme"
        print(f"  {source['name']:12} yazildi={written:>6} (ek kaynak, mod={mode})")
        stats["ek_yazildi"] += written
    writer.close()

    print(f"\nCikti: {cfg['merged_aixm']} ({writer.count} feature)")
    for key in sorted(stats):
        print(f"  {key:24} {stats[key]}")
    print("  iptal kurali isabetleri:", excludes.summary())
    if any(excludes.excepted):
        print("  istisna ile korunan    :",
              [(r["source"], n) for r, n in zip(excludes.rules, excludes.excepted)])
    if excludes.location_missing:
        print(f"  konumsuz (test edilemedi): {excludes.location_missing}")
    return stats


# ── AŞAMA 2B ────────────────────────────────────────────────────────────────

def run_gpkg(cfg, root, log):
    print("=" * 62)
    print("ASAMA 2B — GEOPACKAGE")
    print("=" * 62)
    merged = root / cfg["merged_aixm"]
    con = gpkg_writer.create_gpkg(root / cfg["output_gpkg"],
                                  gpkg_airspace.LAYERS, gpkg_airspace.column_type)
    cur = con.cursor()
    counts = Counter()
    for member in rdr.iter_members(merged):
        feature = rdr.feature_of(member)
        if rdr.local(feature.tag) != "Airspace":
            log.error("2B", LAYER, rdr.gml_id_of(feature), "feature",
                      rdr.local(feature.tag), "beklenmeyen_feature_tipi")
            continue
        ts = rdr.time_slice(feature)
        gml_id = rdr.gml_id_of(feature)
        try:
            geometry, base_volume = airspace_geometry(ts)
        except GeometryError as exc:
            counts["geometri_hesaplanamadi"] += 1
            log.error("2B", LAYER, gml_id, "geometryComponent", str(exc),
                      "geometri_hesaplanamadi_satir_yazilmadi")
            continue
        row = gpkg_airspace.map_airspace(feature, ts, gml_id,
                                         rdr.uuid_of(feature),
                                         provenance.require(feature),
                                         base_volume)
        gpkg_writer.insert_row(cur, gpkg_airspace.LAYERS, LAYER, row,
                               gpkg_writer.shapely_blob(geometry))
        counts[LAYER] += 1
    con.commit()
    print(f"  {LAYER}: {counts[LAYER]} satir "
          f"(geometri hesaplanamadi: {counts['geometri_hesaplanamadi']})")
    print("\n[Index]")
    gpkg_writer.finalize(con, gpkg_airspace.LAYERS, log)
    con.close()
    return counts


def main():
    parser = argparse.ArgumentParser(description="Common Airspaces builder")
    parser.add_argument("--sources", action="store_true", help="yalnizca 1. asama")
    parser.add_argument("--merge", action="store_true", help="yalnizca 2A")
    parser.add_argument("--gpkg", action="store_true", help="yalnizca 2B")
    args = parser.parse_args()

    cfg = json.loads((BASE_DIR / "config.json").read_text(encoding="utf-8"))
    (BASE_DIR / "navdata").mkdir(exist_ok=True)
    (BASE_DIR / cfg["error_log"]).parent.mkdir(parents=True, exist_ok=True)
    log = BuildLog(BASE_DIR / cfg["error_log"])
    only = args.sources or args.merge or args.gpkg
    try:
        if args.sources or (not only and cfg.get("run_source_generators")):
            run_source_generators(cfg, BASE_DIR, log)
        if args.merge or not only:
            run_merge(cfg, BASE_DIR, log)
        if args.gpkg or not only:
            run_gpkg(cfg, BASE_DIR, log)
    finally:
        log.close()
    summary = log.summary()
    print(f"\n{cfg['error_log']}: {sum(summary.values())} kayit")
    for key, n in summary.items():
        print(f"  {key:50} {n}")


if __name__ == "__main__":
    main()
