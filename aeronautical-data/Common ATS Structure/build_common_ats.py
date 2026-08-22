r"""Common ATS Structure — common builder.

Üç aşama:

  1   KAYNAK ÜRETİCİLERİ   her sağlayıcının ham verisi → kendi başına geçerli
                    AIXM 5.2 dosyası. Yalnızca `run_source_generators` açıkken
                    çalışır; kapalıysa diskte hazır duran dosyalar kullanılır.

  2A  BİRLEŞTİRME   ana kaynaklar (EAD + Jeppesen) → iptal → ek kaynaklar
                    (LT/TRNC, override) → antimeridyen bölme
                    ⇒ common-ats-structure-aixm.xml
                    ⇒ common-ats-structure-provenance.json

  2B  GEOPACKAGE    yalnızca 2A çıktısından, AIXM_to_GeoPackage_Schema_Design.md
                    kurallarıyla ⇒ common_ats_structure.gpkg

Tarife `config.json`'dadır. Kullanım:

    py build_common_ats.py            # (1 →) 2A + 2B
    py build_common_ats.py --sources  # yalnızca 1. aşama
    py build_common_ats.py --merge    # yalnızca 2A
    py build_common_ats.py --gpkg     # yalnızca 2B (mevcut birleşik dosyadan)

`--sources`, config'deki `run_source_generators` kapalı olsa da 1. aşamayı
çalıştırır (ayarı elle geçersiz kılmanın yolu).
"""

import argparse
import copy
import csv
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from merge import aixm_reader as rdr                       # noqa: E402
from merge.aixm_writer import MergedMessageWriter          # noqa: E402
from merge.antimeridian import split_member                # noqa: E402
from merge.exclude import ExcludeRules                     # noqa: E402
from merge.keys import layer_of, natural_fields, override_key   # noqa: E402
from merge.override import (build_override_index,          # noqa: E402
                            prefer_base_layers,
                            prefer_base_originator,
                            proximity_nm)
from pyproj import Geod                                    # noqa: E402

GEOD = Geod(ellps="WGS84")
from merge.provenance import ProvenanceWriter              # noqa: E402
from gpkg.validation_rules import ATS_STATUS_CONFLICTS   # noqa: E402

MESSAGE_ID = "COMMON_ATS_MSG"


class BuildLog:
    """`errored-features.csv` — her iki aşama da buraya yazar."""

    COLUMNS = ("stage", "layer", "record_identifier", "field", "value",
               "violation", "severity")

    def __init__(self, path: Path):
        self._fh = open(path, "w", encoding="utf-8", newline="")
        self._csv = csv.writer(self._fh)
        self._csv.writerow(self.COLUMNS)
        self.counts = Counter()

    def log(self, stage, layer, ident, field, value, violation, severity):
        self.counts[violation] += 1
        self._csv.writerow([stage, layer, ident, field, value, violation, severity])

    def error(self, stage, layer, ident, field, value, violation):
        self.log(stage, layer, ident, field, value, violation, "error")

    def warning(self, stage, layer, ident, field, value, violation):
        self.log(stage, layer, ident, field, value, violation, "warning")

    def info_count(self, violation):
        """Yalnızca sayaç (dosyaya satır yazmaz)."""
        self.counts[violation] += 1

    def summary(self):
        return dict(sorted(self.counts.items()))

    def close(self):
        self._fh.close()


# ── Kaynak yükleme ──────────────────────────────────────────────────────────

def load_source_meta(source: dict, root: Path) -> dict:
    """Kaynağın `data.json`'ı (provider/originator/effectivity)."""
    rel = source.get("data_json")
    if not rel:
        return {}
    path = root / rel
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def load_originators(source: dict, root: Path) -> dict:
    """Per-kayıt originator yan dosyası (`gml:id → originator`)."""
    rel = source.get("originators_file")
    if not rel:
        return {}
    path = root / rel
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def index_source(path: Path):
    """Kaynağın `uuid → {designator, type, location_designator, kind}` indeksi.

    Yalnızca referans verilebilen feature'lar indekslenir (nokta türleri ve
    Route) — rota segmentlerinin doğal anahtarı bunların designator'larından
    kurulur. Bellek için sade sözlükler kullanılır.
    """
    index = {}
    for member in rdr.iter_members(path):
        feature = rdr.feature_of(member)
        if feature is None:
            continue
        kind = rdr.local(feature.tag)
        if kind not in rdr.POINT_FEATURES and kind != "Route":
            continue
        uid = rdr.uuid_of(feature)
        if not uid:
            continue
        info = rdr.describe(feature)
        index[uid] = {
            "kind": kind,
            "designator": info.get("designator"),
            "type": info.get("type"),
            "location_designator": info.get("location_designator"),
        }
    return index


def collect_features(path: Path, meta: dict, originators: dict):
    """Ek kaynağın feature özetleri — override indeksini kurmak için.

    Ek kaynaklar küçüktür (LT 4.368), bellekte tutulabilir.
    """
    out = []
    for member in rdr.iter_members(path):
        feature = rdr.feature_of(member)
        if feature is None:
            continue
        info = rdr.describe(feature)
        originator = originators.get(info["gml_id"], meta.get("data_originator", ""))
        out.append((info, originator))
    return out


# ── AŞAMA 1 ─────────────────────────────────────────────────────────────────

def run_source_generators(cfg: dict, root: Path, log: BuildLog) -> dict:
    """Kaynak üreticilerini config'deki SIRAYLA çalıştırır.

    Sıra önemlidir ve config'den gelir: EAD üreticisi, NDB uç noktaları için
    Jeppesen'in çıktısına (`jeppesen-ndb-index.json`) bakar — bu yüzden
    Jeppesen ondan önce gelmelidir.

    Bir üretici hata verirse zincir **durdurulur**: eksik/yarım bir kaynak
    dosyasıyla birleştirmeye geçmek, sessizce veri kaybı demektir.
    """
    print("=" * 62)
    print("ASAMA 1 — KAYNAK URETICILERI")
    print("=" * 62)

    results = {}
    for entry in cfg.get("source_generators", []):
        name = entry["name"]
        script = entry.get("script")

        if not script:
            print(f"  {name:10} — henuz yok ({entry.get('_durum', 'script tanimsiz')})")
            results[name] = "yok"
            continue
        if not entry.get("enabled", True):
            print(f"  {name:10} — config'de kapali, atlandi")
            results[name] = "kapali"
            continue

        path = root / script
        if not path.exists():
            print(f"  {name:10} HATA: script bulunamadi ({script})")
            log.error("1", "-", name, "script", script, "script_dosyasi_yok")
            results[name] = "script_yok"
            raise SystemExit(f"1. asama durdu: {name} scripti yok")

        print(f"\n  ── {name} ──  {script}")
        started = time.monotonic()
        completed = subprocess.run([sys.executable, "-X", "utf8", str(path)],
                                   cwd=path.parent)
        elapsed = time.monotonic() - started

        if completed.returncode != 0:
            log.error("1", "-", name, "exit_code", str(completed.returncode),
                      "uretici_hata_verdi")
            raise SystemExit(
                f"\n1. asama durdu: {name} uretici {completed.returncode} "
                f"koduyla cikti. Birlestirmeye gecilmedi.")

        print(f"  {name:10} tamam ({elapsed:.0f} sn)")
        results[name] = "tamam"

    return results


# ── AŞAMA 2A ────────────────────────────────────────────────────────────────

def run_merge(cfg: dict, root: Path, log: BuildLog) -> dict:
    merged_path = root / cfg["merged_aixm"]
    prov_path = root / cfg["merged_provenance"]
    split_enabled = bool(cfg.get("split_antimeridian"))

    base_sources = [s for s in cfg["base_sources"] if s.get("enabled", True)]
    extra_sources = [s for s in cfg["additional_sources"] if s.get("enabled", True)]

    print("=" * 62)
    print("ASAMA 2A — BIRLESTIRME")
    print("=" * 62)

    # -- kaynak hazırlığı --
    prepared = []
    for source in base_sources + extra_sources:
        path = root / source["file"]
        if not path.exists():
            print(f"  ATLANDI  {source['name']}: dosya yok ({source['file']})")
            log.warning("2A", "-", source["name"], "file", source["file"],
                        "kaynak_dosyasi_yok")
            continue
        prepared.append({
            **source,
            "path": path,
            "meta": load_source_meta(source, root),
            "originators": load_originators(source, root),
            "is_base": source in base_sources,
        })

    # -- indeksler (rota segmenti doğal anahtarları için) --
    print("\n[1] Kaynak indeksleri kuruluyor...")
    for source in prepared:
        source["index"] = index_source(source["path"])
        print(f"  {source['name']:10} {len(source['index']):>7} referanslanabilir feature")

    # -- ek kaynakların doğal anahtarları --
    # İki mod var ve kaynak başına seçilir:
    #   override_enabled     → ek kaynak kazanır (ana kaynak kaydı yazılmaz)
    #   prefer_base_on_match → ANA KAYNAK kazanır (ek kaynağın kaydı yazılmaz,
    #                          ona referans veren her şey ana kayda yönlendirilir)
    print("\n[2] Ek kaynak anahtarlari cikariliyor...")
    for source in prepared:
        if source["is_base"] or not (source.get("override_enabled")
                                     or source.get("prefer_base_on_match")):
            source["features"] = []
            continue
        source["features"] = collect_features(
            source["path"], source["meta"], source["originators"])
        mode = "override" if source.get("override_enabled") else "prefer_base"
        print(f"  {source['name']:10} {len(source['features']):>6} feature  mod={mode}")
    overrides = build_override_index(
        [s for s in prepared if not s["is_base"]], log)
    print(f"  override anahtari: {len(overrides)}")

    # -- iptal kuralları --
    excludes = ExcludeRules.load(root / cfg["excludes_dir"], log)
    print(f"\n[3] Iptal kurallari: {len(excludes)}")

    # -- ön tarama: hangi ana kaynak kaydı override edilecek --
    # Bir ana kaynak kaydı override edilince ona referans veren DİĞER ana kaynak
    # feature'ları boşta kalır. Bu yüzden yazımdan önce bir tarama yapılır ve
    # `remap` kurulur: eski UUID → yerine geçen ek kaynak UUID'si. Yazım
    # sırasında tüm `xlink:href` değerleri bu tabloya göre çevrilir.
    print("\n[4] On tarama (referans yonlendirmesi icin)...")
    remap: dict[str, str] = {}
    base_by_key: dict = {}
    # Yakınlık eşleştirmesi için konumlu dizin:
    #   (katman, type, designator) → [(kaynak_adi, gml_id, uuid, (lat, lon)), …]
    # Originator anahtarı tutmadığında (Jeppesen'de originator hiç yok, EAD'de
    # farklı yazılabiliyor) aday bu dizinden çıkarılır ve mesafeyle ayıklanır.
    by_designator: dict = {}
    # Yakınlıkla override edilen ANA KAYNAK kayıtları: gml_id → yerine geçen uuid
    proximity_drop: dict = {}
    # Navaid düşünce boşta kalacak ekipmanı bulmak için:
    #   ekipman uuid → {o ekipmanı kullanan Navaid gml_id, …}
    equipment_users: dict = {}
    equipment_gml_id: dict = {}

    def dizine_ekle(source_name, info, fields):
        pos = info.get("position")
        if not pos or not fields.get("designator"):
            return
        by_designator.setdefault(
            (fields["layer"], fields.get("type"), fields["designator"]), []
        ).append((source_name, info["gml_id"], info["uuid"], pos))

    def yakin_aday(fields, info, hedef_kaynaklar, esik_nm):
        """Hedef kaynaklarda aynı tip+designator taşıyan, eşik içindeki tek aday.

        Birden fazla aday eşiğe giriyorsa SEÇİM YAPILMAZ (None döner) — yanlış
        tesise bağlamak sessiz veri hatası olur.
        """
        pos = info.get("position")
        if not (pos and esik_nm and hedef_kaynaklar and fields.get("designator")):
            return None, 0
        adaylar = by_designator.get(
            (fields["layer"], fields.get("type"), fields["designator"]), [])
        yakin = []
        for kaynak, gml_id, uuid_value, aday_pos in adaylar:
            if kaynak not in hedef_kaynaklar:
                continue
            _, _, mesafe = GEOD.inv(pos[1], pos[0], aday_pos[1], aday_pos[0])
            if mesafe / 1852.0 <= esik_nm:
                yakin.append((gml_id, uuid_value))
        return (yakin[0] if len(yakin) == 1 else None), len(yakin)

    # Tipsiz ek kaynak navaid'leri için gevşek eşleşme tablosu:
    #   (designator, originator) → [ana kaynak uuid, …]
    base_navaid_by_designator: dict = {}
    for source in (s for s in prepared if s["is_base"]):
        for member in rdr.iter_members(source["path"]):
            feature = rdr.feature_of(member)
            if feature is None:
                continue
            info = rdr.describe(feature)
            originator = source["originators"].get(
                info["gml_id"], source["meta"].get("data_originator", ""))
            fields = natural_fields(info, originator, source["index"])
            key = override_key(fields)

            # Navaid → bağlı ekipman feature'ları. Bir Navaid düşerse ona bağlı
            # ekipman boşta kalır; hangi ekipmanın hangi Navaid'lerce
            # kullanıldığı burada toplanır (EAD'de bir ekipman birden fazla
            # Navaid tarafından paylaşılabiliyor).
            # DİKKAT: ekipman feature'larının doğal anahtarı yoktur
            # (`override_key` None döner), bu yüzden toplama aşağıdaki
            # `key is None` elemesinin ÜSTÜNDE yapılmalıdır.
            if info["kind"] == "Navaid":
                ts_el = rdr.time_slice(feature)
                for holder in (ts_el.findall(rdr.A + "navaidEquipment")
                               if ts_el is not None else []):
                    comp = holder.find(rdr.A + "NavaidComponent")
                    if comp is None:
                        continue
                    eq_uuid = rdr.href_of(comp.find(rdr.A + "theNavaidEquipment"))
                    if eq_uuid:
                        equipment_users.setdefault(eq_uuid, set()).add(
                            info["gml_id"])
            elif info["kind"] in rdr.EQUIPMENT_FEATURES and info["uuid"]:
                equipment_gml_id[info["uuid"]] = info["gml_id"]

            if key is None or not info["uuid"]:
                continue
            base_by_key.setdefault(key, info["uuid"])
            dizine_ekle(source["name"], info, fields)
            if fields.get("layer") == "navaids" and fields.get("designator"):
                base_navaid_by_designator.setdefault(
                    (fields["designator"], originator), []).append(info["uuid"])
            hit = overrides.peek(key)
            # Doğal anahtar (designator+originator) tutmadıysa yakınlık
            # yedeği denenir (bkz. merge/override.OverrideIndex.proximity_lookup).
            if not hit and fields.get("layer") == "designatedPoints" and info.get("position"):
                aday, adet = overrides.proximity_lookup(
                    fields["layer"], fields.get("designator"),
                    info["position"], GEOD)
                if aday:
                    hit = aday
                elif adet > 1:
                    log.warning("2A", "designatedPoints", info["gml_id"],
                                "position",
                                f'{fields.get("designator")} ({adet} aday)',
                                "yakinlik_esiginde_birden_fazla_aday")
            if hit and hit[2]:
                remap[info["uuid"]] = hit[2]          # ana kaynak → ek kaynak
    print(f"  ana kaynak dogal anahtari: {len(base_by_key)}")
    print(f"  override ile yonlendirilecek: {len(remap)}")

    # `prefer_base_on_match`: ek kaynağın eşleşen kaydı YAZILMAZ; ona referans
    # veren her şey **o ana kadar yazılmaya karar verilmiş** kaydın UUID'sine
    # yönlendirilir. Yalnızca `prefer_base_on_match_layers` katmanlarında
    # geçerlidir; kaynağın diğer katmanlarında override yönü (ek kaynak kazanır)
    # korunur.
    #
    # Karşılaştırma tablosu ana kaynakla sınırlı DEĞİLDİR: ek kaynaklar config
    # sırasıyla işlenir ve her kaynağın yazılacak kayıtları tabloya eklenir.
    # Böylece sonraki bir ek kaynak, kendisinden önce okunmuş bir ek kaynağa da
    # devredebilir. İstenen akış:
    #   1) ana kaynak kaydı oluşur
    #   2) LT kendi noktalarını override eder (LT kazanır)
    #   3) TRNC, LT'den sonra okunduğu için LT'nin noktalarını override etmez;
    #      LT'de de bulunan noktalarda LT'nin kaydı geçerli kalır
    # Tabloya önce ana kaynağın YAZILACAK kayıtları girer: override edilecek
    # olanlar (yerlerini bir ek kaynak alacak) dışarıda bırakılır.
    written_by_key = {}
    for key, uuid_value in base_by_key.items():
        hit = overrides.peek(key)
        if hit and hit[2]:
            continue
        written_by_key[key] = uuid_value
    # Tipsiz navaid gevşek eşleşmesi de aynı şekilde birikir.
    written_navaid_by_designator = {k: list(v) for k, v
                                    in base_navaid_by_designator.items()}

    for source in (s for s in prepared if not s["is_base"]):
        layers = prefer_base_layers(source)
        skip = set()
        gevsek = belirsiz = 0
        yakinlik_devir = yakinlik_override = 0
        # Yakınlık eşleştirmesinin hedefleri KAYNAK ADIYLA verilir:
        #   prefer_base_sources → bu kaynakların kaydı kazanır (buraya devredilir)
        #   override_sources    → bu kaynakların kaydı düşer (bu kaynak kazanır)
        esik = proximity_nm(source)
        defer_kaynaklar = frozenset(source.get("prefer_base_sources") or ())
        override_kaynaklar = frozenset(source.get("override_sources") or ())
        base_originator = source.get("override_base_originator")
        # Devretme yönünde aranacak originator, override yönündekinden farklı
        # olabilir (bkz. merge/override.prefer_base_originator).
        defer_originator = prefer_base_originator(source)
        for info, _originator in source["features"]:
            fields = natural_fields(info, base_originator, source["index"])
            key = override_key(fields)

            if layer_of(info["kind"]) not in layers:
                # Bu katmanda ek kaynak kazanıyor → kaydı tabloya ekle ki
                # SONRAKİ ek kaynaklar buna devredebilsin.
                if key and info["uuid"]:
                    written_by_key[key] = info["uuid"]
                continue

            defer_key = (override_key(natural_fields(
                info, defer_originator, source["index"]))
                if defer_originator != base_originator else key)
            base_uuid = written_by_key.get(defer_key) if defer_key else None

            # Tipsiz navaid (LT'nin `fix` referansından türetilmiş stub kaydı)
            # tam anahtarla eşleşemez — `type` anahtarın parçası. Bu durumda
            # designator + originator ile gevşek eşleşme denenir. Birden fazla
            # ana kaynak adayı varsa SEÇİM YAPILMAZ: kayıt korunur ve belirsizlik
            # loglanır (yanlış navaid'e yönlendirme sessiz veri hatası olur).
            if (base_uuid is None and fields.get("layer") == "navaids"
                    and not fields.get("type") and fields.get("designator")):
                adaylar = written_navaid_by_designator.get(
                    (fields["designator"], base_originator), [])
                if len(adaylar) == 1:
                    base_uuid = adaylar[0]
                    gevsek += 1
                elif len(adaylar) > 1:
                    belirsiz += 1
                    log.warning("2A", "navaids", info["gml_id"], "type",
                                f'{fields["designator"]} / {base_originator} '
                                f'({len(adaylar)} aday)',
                                "tipsiz_navaid_birden_fazla_ana_kaynak_adayi")

            # Originator anahtarı tutmadıysa YAKINLIK eşleştirmesi. Hedef
            # kaynaklar ADIYLA belirtilir — Jeppesen'de originator alanı hiç
            # yoktur, EAD'de ise yazım kaynaktan kaynağa değişir. Aday, aynı
            # tip+designator'ı taşıyan yazılmış kayıtlar arasından mesafeyle
            # ayıklanır (`LU` Jeppesen'de 5 kez geçiyor; yalnızca biri yakın).
            if base_uuid is None and esik:
                aday, adet = yakin_aday(fields, info, defer_kaynaklar, esik)
                if aday:
                    base_uuid = aday[1]
                    yakinlik_devir += 1
                elif adet > 1:
                    log.warning("2A", fields.get("layer"), info["gml_id"],
                                "position", f'{fields.get("designator")} '
                                f'({adet} aday {esik} NM icinde)',
                                "yakinlik_esiginde_birden_fazla_aday")

            if base_uuid and info["uuid"]:
                skip.add(info["gml_id"])
                remap[info["uuid"]] = base_uuid   # ek kaynak → önceki kayıt
            elif key and info["uuid"]:
                # Eşleşme yok → bu kayıt yazılacak, tabloya eklensin.
                written_by_key[key] = info["uuid"]
                if fields.get("layer") == "navaids" and fields.get("designator"):
                    written_navaid_by_designator.setdefault(
                        (fields["designator"], base_originator), []).append(
                            info["uuid"])
                # Bu kayıt yazılacaksa, hedeflenen kaynaklardaki yakın eşi
                # override edilir (ana kaynak kaydı düşer, referanslar buraya).
                if esik and override_kaynaklar:
                    aday, adet = yakin_aday(fields, info, override_kaynaklar, esik)
                    if aday:
                        proximity_drop[aday[0]] = info["uuid"]
                        remap[aday[1]] = info["uuid"]
                        yakinlik_override += 1
                    elif adet > 1:
                        log.warning("2A", fields.get("layer"), info["gml_id"],
                                    "position", f'{fields.get("designator")} '
                                    f'({adet} aday {esik} NM icinde)',
                                    "yakinlik_esiginde_birden_fazla_aday")
                dizine_ekle(source["name"], info, fields)
        source["skip_gml_ids"] = skip
        if gevsek or belirsiz:
            print(f"  {source['name']:10} tipsiz navaid: gevsek_eslesme={gevsek} "
                  f"belirsiz_birakildi={belirsiz}")
        if yakinlik_devir or yakinlik_override:
            print(f"  {source['name']:10} yakinlik ({esik} NM): "
                  f"devredildi={yakinlik_devir} override={yakinlik_override}")
        if layers:
            print(f"  {source['name']:10} onceki kayit kazandi "
                  f"({'/'.join(sorted(layers))}): {len(skip)}")

    # Düşen Navaid'lerin ekipmanı da düşer — ama YALNIZCA o ekipmanı kullanan
    # bütün Navaid'ler düşmüşse. EAD'de bir ekipman birden fazla Navaid
    # tarafından paylaşılabiliyor; hâlâ kullanılan bir ekipmanı düşürmek kırık
    # referans üretirdi. (TRNC'nin GKE NDB'si Jeppesen Navaid'ini düşürünce
    # onun 1:1 bağlı ekipmanı boşta kalıyordu.)
    dusen_navaidler = set(proximity_drop)
    dusen_ekipman = 0
    for eq_uuid, kullananlar in equipment_users.items():
        if kullananlar and kullananlar <= dusen_navaidler:
            gml_id = equipment_gml_id.get(eq_uuid)
            if gml_id and gml_id not in proximity_drop:
                proximity_drop[gml_id] = None
                dusen_ekipman += 1
    if dusen_ekipman:
        print(f"  dusen navaid ile birlikte dusen ekipman: {dusen_ekipman}")

    # Zincir çözümü. İki yön aynı anda işleyince dolaylı yönlendirme oluşabilir:
    # TRNC kaydı LT'ye devreder (TRNC→LT) ve aynı anda EAD'nin Cyprus DCA
    # kaydını override eder (EAD→TRNC). Tek adımlık arama EAD'yi yazılmayan
    # TRNC kaydına gönderirdi; zincir sonuna kadar izlenir (EAD→LT).
    zincir = 0
    for kaynak in list(remap):
        hedef = remap[kaynak]
        gorulen = {kaynak}
        while hedef in remap and hedef not in gorulen:
            gorulen.add(hedef)
            hedef = remap[hedef]
        if hedef != remap[kaynak]:
            remap[kaynak] = hedef
            zincir += 1
    if zincir:
        print(f"  dolayli yonlendirme cozuldu: {zincir}")

    # -- yazım --
    print("\n[5] Birlesik AIXM yaziliyor...")
    writer = MergedMessageWriter(merged_path, MESSAGE_ID)
    prov = ProvenanceWriter(prov_path)
    stats = Counter()

    def apply_remap(member):
        """Override edilmiş hedeflere giden referansları yenisine yönlendirir."""
        if not remap:
            return
        for el in member.iter():
            href = el.get(rdr.X + "href")
            if not href or not href.startswith("urn:uuid:"):
                continue
            new = remap.get(href[len("urn:uuid:"):].strip().upper())
            if new:
                el.set(rdr.X + "href", "urn:uuid:" + new)
                stats["referans_yonlendirildi"] += 1

    def emit(member, info, source):
        """Bir feature'ı (gerekiyorsa antimeridyen bölmesiyle) yazar."""
        apply_remap(member)
        meta = source["meta"]
        originator = source["originators"].get(
            info["gml_id"], meta.get("data_originator", ""))

        pieces = None
        if split_enabled and info["kind"] == "RouteSegment":
            pieces = split_member(member, info)
            if pieces is None and info.get("positions") \
                    and abs(info["positions"][-1][1] - info["positions"][0][1]) > 180:
                stats["antimeridyen_bolunemedi"] += 1
                log.warning("2A", "routeSegments", info["gml_id"], "curveExtent",
                            str(info["positions"]), "antimeridyen_bolunemedi")

        if pieces:
            stats["antimeridyen_bolundu"] += 1
            for piece in pieces:
                piece_feature = rdr.feature_of(piece)
                writer.write_member(piece)
                prov.add(rdr.gml_id_of(piece_feature),
                         meta.get("data_provider", ""), originator,
                         meta.get("data_effectivity", ""))
                stats[f'yazildi_{rdr.local(piece_feature.tag)}'] += 1
        else:
            writer.write_member(member)
            prov.add(info["gml_id"], meta.get("data_provider", ""), originator,
                     meta.get("data_effectivity", ""))
            stats[f'yazildi_{info["kind"]}'] += 1

    # 5a. Ana kaynaklar — override/iptal süzgeciyle
    for source in (s for s in prepared if s["is_base"]):
        written = skipped_ovr = skipped_exc = 0
        for member in rdr.iter_members(source["path"]):
            feature = rdr.feature_of(member)
            if feature is None:
                continue
            info = rdr.describe(feature)
            originator = source["originators"].get(
                info["gml_id"], source["meta"].get("data_originator", ""))
            fields = natural_fields(info, originator, source["index"])

            if excludes.matches(fields):
                skipped_exc += 1
                log.warning("2A", fields.get("layer") or info["kind"],
                            info["gml_id"], "-", "-", "iptal_kuraliyla_cikarildi")
                continue
            hit = overrides.lookup(override_key(fields))
            if not hit and fields.get("layer") == "designatedPoints" and info.get("position"):
                aday, adet = overrides.proximity_lookup(
                    fields["layer"], fields.get("designator"),
                    info["position"], GEOD)
                if aday:
                    hit = aday
                    overrides.consumed[aday[0]] += 1
                elif adet > 1:
                    log.warning("2A", "designatedPoints", info["gml_id"],
                                "position",
                                f'{fields.get("designator")} ({adet} aday)',
                                "yakinlik_esiginde_birden_fazla_aday")
            if hit:
                skipped_ovr += 1
                continue
            # Yakınlıkla override edilmiş ana kaynak kaydı (originator anahtarı
            # tutmadığı için doğal anahtarla yakalanamaz, gml:id ile düşer).
            if info["gml_id"] in proximity_drop:
                skipped_ovr += 1
                stats["yakinlikla_override_edildi"] += 1
                continue

            emit(member, info, source)
            written += 1
        print(f"  {source['name']:10} yazildi={written:>7} "
              f"override_ile_atlandi={skipped_ovr} iptal={skipped_exc}")
        stats["base_yazildi"] += written
        stats["override_ile_atlandi"] += skipped_ovr
        stats["iptal_edildi"] += skipped_exc

    # 5b. Ek kaynaklar — `prefer_base_on_match` ile eşleşenler hariç
    for source in (s for s in prepared if not s["is_base"]):
        skip = source.get("skip_gml_ids") or set()
        written = skipped = 0
        for member in rdr.iter_members(source["path"]):
            feature = rdr.feature_of(member)
            if feature is None:
                continue
            info = rdr.describe(feature)
            if info["gml_id"] in skip:
                skipped += 1
                continue
            emit(member, info, source)
            written += 1
        print(f"  {source['name']:10} yazildi={written:>7} "
              f"ana_kaynak_kazandi={skipped} (ek kaynak)")
        stats["ek_yazildi"] += written
        stats["ana_kaynak_kazandi"] += skipped

    writer.close()
    prov.close()

    size_mb = merged_path.stat().st_size / 1024 / 1024
    print(f"\nCikti: {merged_path.name} ({size_mb:.1f} MB, {writer.count} feature)")
    print(f"       {prov_path.name} ({prov.count} provenance kaydi)")
    for key in sorted(stats):
        print(f"  {key:34} {stats[key]}")
    if excludes.hits:
        print("  iptal kurali isabetleri:", excludes.summary())
    if overrides.consumed:
        print("  override tuketimi:", dict(overrides.consumed))

    return {"features": writer.count, "provenance": prov.count, "stats": stats}


# ── AŞAMA 2B ────────────────────────────────────────────────────────────────

#: `depictionCompulsory` bayraginin aradigi AIXM CodeATCReportingType degeri.
_REPORT_MAIN = "COMPULSORY"

#: AIXM CodeNavigationType degerleri (`aircraftCapability/navigationType`).
_NAV_CONVENTIONAL = frozenset(["CONV", "TACAN"])
_NAV_PBN = "PBN"

_ATS_STATUS_SET = (
    ' "atsStatus_isElementOfRouteSegment"=?,'
    ' "atsStatus_associatedLevelUpper"=?,'
    ' "atsStatus_associatedLevelLower"=?,'
    ' "atsStatus_associatedLevelBoth"=?,'
    ' "atsStatus_associatedLevelOther"=?,'
    ' "atsStatus_reportingAssociation"=?,'
    ' "atsStatus_depictionCompulsory"=?,'
    ' "atsStatus_depictionNav"=?,'
    ' "atsStatus_depictionSIGPointBasicFunc"=?')


def depiction_nav(layer, point_type, nav_types):
    """`atsStatus_depictionNav` — seyrusefer gosterim sinifi (kullanici kurallari).

    SIRALI karar zinciri:

      1. CONV        — bagli ATS rotalarindan biri `CONV` veya `TACAN` ise.
                       ANCAK `type=COORD` olan DesignatedPoint CONV OLAMAZ:
                       koordinattan turetilmis nokta klasik seyrusefer
                       yardimcisiyla tanimlanmaz. Navaid'de bu istisna yoktur.
      2. RNAVFlyBy   — `type=COORD` DesignatedPoint KOSULSUZ; ayrica DP/Navaid'de
                       bagli rotalardan biri `PBN` ise.
      3. RNAVFlyOver — su an bir kosula BAGLANMADI: fly-over / fly-by ayrimini
                       verecek kaynak alani henuz yok. Ileride kullanilacak;
                       uydurma siniflandirma yapilmaz, bilerek uretilmiyor.
      4. OTHER       — son fallback.
    """
    is_coord = layer == "designatedPoints" and point_type == "COORD"

    if not is_coord and (nav_types & _NAV_CONVENTIONAL):
        return "CONV"
    if is_coord:
        return "RNAVFlyBy"
    if _NAV_PBN in nav_types:
        return "RNAVFlyBy"
    return "OTHER"


def depiction_sig_point(layer, point_type, nav_types, all_pbn, nav_class):
    """`atsStatus_depictionSIGPointBasicFunc` — onemli nokta temel islevi.

      * NAVAID  — `navaids` katmanindaki HER satir. DesignatedPoint asla almaz.
      * VFR_REP — DesignatedPoint `type=VRP` ise.
      * WPT     — `depictionNav` CONV DEGILSE ve (`type=COORD` kosulsuz, ya da
                  bagli TUM rota segmentleri PBN ise).
      * INT     — `type=BRG_DIST` ise, ya da bagli rotalardan biri CONV/TACAN ise.
      * OTHER   — DesignatedPoint icin son fallback.
    """
    if layer == "navaids":
        return "NAVAID"
    if point_type == "VRP":
        return "VFR_REP"

    if nav_class != "CONV":
        if point_type == "COORD":
            return "WPT"
        if all_pbn:
            return "WPT"

    if point_type == "BRG_DIST":
        return "INT"
    if nav_types & _NAV_CONVENTIONAL:
        return "INT"
    return "OTHER"


def compute_ats_status(con, log=None):
    """`designatedPoints`/`navaids` icin `atsStatus_*` alanlarini turetir.

    AIXM'de bu alanlarin karsiligi YOKTUR — bir noktanin ATS rota agindaki
    rolu, ona referans veren `routeSegments` satirlarindan cikarilir. Bu yuzden
    rota segmentleri yazildiktan SONRA, ayri bir gecis olarak hesaplanir.
    `navaidComponents` rota ucu olarak cozumlenmedigi icin kapsam disidir.

    Iki alan grubu vardir:

      * KAPIYA BAGLI (`associatedLevel*`, `reportingAssociation`,
        `depictionCompulsory`): nokta hicbir segmente bagli degilse **NULL**
        kalir — `0`/bos dize degil. "Bagli degil" ile "bagli ama bilgi yok"
        ayrimi korunur (kullanici karari).
      * KAPIDAN BAGIMSIZ (`depictionNav`, `depictionSIGPointBasicFunc`): HER
        satirda doldurulur. Tip tabanli kurallari (COORD / VRP / BRG_DIST,
        navaid olmak) rota baglantisi olmadan da anlamlidir; bagli olmayan
        noktada rota kosullari bos kume ile calisir ve fallback'e duser.

    Diger kurallar:
      * `associatedLevelUpper/Lower/Both/Other`: her biri BAGIMSIZ bayraktir —
        "iliskili segmentlerden EN AZ BIRI bu seviyede mi". `Both` yalnizca ham
        `level=BOTH` varsa 1 olur, UPPER+LOWER birlesiminden turetilmez;
        `Other` yalnizca gercek `OTHER`/`OTHER:<kod>` varsa 1 olur.
      * `reportingAssociation`: yalnizca raporlama turu isaretlenmis uclar
        listelenir; `role` (START/END) ayri alan olarak tasinir.
      * Tutarlilik denetimi: `depictionNav=CONV` ile
        `depictionSIGPointBasicFunc=WPT` BIRLIKTE OLAMAZ. WPT kurali zaten CONV
        disliyor, yine de savunma amacli denetlenir ve ihlal loglanir.
    """
    cur = con.cursor()
    acc = {"designatedPoints": {}, "navaids": {}}

    def bucket(layer, row_id):
        if layer not in acc or row_id is None:
            return None
        return acc[layer].setdefault(row_id, {
            "levels": set(), "reports": [], "nav": set(),
            "segs": set(), "segs_pbn": set()})

    cur.execute(
        'SELECT id, routeSegments_level, routeSegments_aircraftCapability,'
        ' routeSegments_startPointLayer, routeSegments_startPointId,'
        ' routeSegments_startReportingATC,'
        ' routeSegments_endPointLayer, routeSegments_endPointId,'
        ' routeSegments_endReportingATC'
        ' FROM routeSegments')
    for (seg_id, level, capability, s_layer, s_id, s_rep,
         e_layer, e_id, e_rep) in cur.fetchall():
        nav_types = set()
        if capability:
            try:
                for item in json.loads(capability):
                    if isinstance(item, dict) and item.get("navigationType"):
                        nav_types.add(item["navigationType"])
            except ValueError:
                pass
        for layer, row_id, report, role in ((s_layer, s_id, s_rep, "START"),
                                            (e_layer, e_id, e_rep, "END")):
            target = bucket(layer, row_id)
            if target is None:
                continue
            if level:
                target["levels"].add(level)
            target["nav"] |= nav_types
            # Segment kimligi KUME olarak tutulur: bir nokta ayni segmentin hem
            # basi hem sonu olabilir, "tum segmentler PBN mi" sayimi bozulmasin.
            target["segs"].add(seg_id)
            if _NAV_PBN in nav_types:
                target["segs_pbn"].add(seg_id)
            if report:
                target["reports"].append(
                    {"segmentId": seg_id, "role": role, "reportingATC": report})

    ihlal = 0
    for layer, rows in acc.items():
        type_col = f"{layer}_type"
        cur.execute(f'SELECT id, "{type_col}", gmlId FROM "{layer}"')
        payload = []
        bagli = 0
        for row_id, point_type, gml_id in cur.fetchall():
            info = rows.get(row_id)
            if info is not None:
                bagli += 1
                levels, nav_types = info["levels"], info["nav"]
                reports, segs = info["reports"], info["segs"]
                all_pbn = bool(segs) and segs == info["segs_pbn"]
            else:
                # Rota agina bagli olmayan nokta: TUM turetilmis alanlar NULL.
                # `depictionNav` / `depictionSIGPointBasicFunc` de kapiya
                # BAGLIDIR (kullanici karari) — tip tabanli kurallari
                # (COORD/VRP/NAVAID) bagimsiz calisabilirdi, ama bir noktanin
                # rota gosterim sinifi ancak bir ATS rotasinin parcasiysa
                # anlamlidir.
                payload.append((0,) + (None,) * 8 + (row_id,))
                continue

            nav_class = depiction_nav(layer, point_type, nav_types)
            sig_func = depiction_sig_point(
                layer, point_type, nav_types, all_pbn, nav_class)

            # Alanlar arasi tutarlilik: kural listesi tek yerde tutulur
            # (gpkg/validation_rules.ATS_STATUS_CONFLICTS). Bu alanlar satir
            # yazildiktan SONRA UPDATE ile doldugu icin validate_row gormez,
            # denetim burada yapilir.
            secim = {"atsStatus_depictionNav": nav_class,
                     "atsStatus_depictionSIGPointBasicFunc": sig_func}
            for a_col, a_val, b_col, b_val, kod in ATS_STATUS_CONFLICTS:
                if secim.get(a_col) == a_val and secim.get(b_col) == b_val:
                    ihlal += 1
                    if log:
                        log.error("2B", layer, gml_id, a_col,
                                  f"{a_val} + {b_val}", kod)

            kinds = {r["reportingATC"] for r in reports}
            payload.append((
                1,
                1 if "UPPER" in levels else 0,
                1 if "LOWER" in levels else 0,
                1 if "BOTH" in levels else 0,
                1 if any(v == "OTHER" or v.startswith("OTHER:")
                         for v in levels) else 0,
                json.dumps(reports, ensure_ascii=False) if reports else None,
                1 if _REPORT_MAIN in kinds else 0,
                nav_class, sig_func, row_id))

        cur.executemany(
            f'UPDATE "{layer}" SET' + _ATS_STATUS_SET + ' WHERE id=?', payload)
        print(f"  {layer:18} satir={len(payload)} rota ile iliskili={bagli}")
    if ihlal:
        print(f"  TUTARSIZLIK depictionNav=CONV + WPT: {ihlal}")
    con.commit()


def run_gpkg(cfg: dict, root: Path, log: BuildLog) -> dict:
    """Birleşik AIXM + provenance → GeoPackage (saf şema eşlemesi)."""
    from gpkg import mapper, schema
    from gpkg.validate import validate_row

    merged_path = root / cfg["merged_aixm"]
    prov_path = root / cfg["merged_provenance"]
    out_path = root / cfg["output_gpkg"]

    print("=" * 62)
    print("ASAMA 2B — GEOPACKAGE")
    print("=" * 62)
    if not merged_path.exists():
        print(f"  HATA: {merged_path.name} yok — once 2A calistirilmali.")
        return {}

    provenance = json.loads(prov_path.read_text(encoding="utf-8")) \
        if prov_path.exists() else {}
    print(f"  provenance kaydi: {len(provenance)}")

    con = schema.create_gpkg(out_path)
    cur = con.cursor()
    counts = Counter()

    # uuid → (katman, satır id, designator) — rota uç noktası çözümlemesi için
    resolved: dict[str, tuple] = {}
    # equipment uuid → (navaid satır id, NavaidComponent elemanı)
    component_links: dict[str, tuple] = {}
    # Route uuid → TimeSlice elemanı (segmentlere devredilecek alanlar için)
    routes: dict[str, object] = {}

    # -- 1. geçiş: designatedPoints, navaids, Route alanları, bileşen bağları --
    print("\n[1] Noktalar ve navaid'ler yaziliyor...")
    for member in rdr.iter_members(merged_path):
        feature = rdr.feature_of(member)
        if feature is None:
            continue
        kind = rdr.local(feature.tag)
        gml_id = rdr.gml_id_of(feature)
        uid = rdr.uuid_of(feature)
        ts = rdr.time_slice(feature)
        entry = provenance.get(gml_id)

        if kind == "DesignatedPoint":
            row, position = mapper.map_designated_point(feature, ts, gml_id, entry)
            row = validate_row("designatedPoints", row, log, gml_id)
            geom = schema.point_blob(position[1], position[0]) if position else None
            row_id = schema.insert_row(cur, "designatedPoints", row, geom)
            resolved[uid] = ("designatedPoints", row_id,
                             row.get("designatedPoints_designator"))
            counts["designatedPoints"] += 1

        elif kind == "Navaid":
            row, position = mapper.map_navaid(feature, ts, gml_id, entry)
            row = validate_row("navaids", row, log, gml_id)
            geom = schema.point_blob(position[1], position[0]) if position else None
            row_id = schema.insert_row(cur, "navaids", row, geom)
            resolved[uid] = ("navaids", row_id, row.get("navaids_designator"))
            counts["navaids"] += 1
            for holder in ts.findall(rdr.A + "navaidEquipment"):
                component = holder.find(rdr.A + "NavaidComponent")
                if component is None:
                    continue
                link = component.find(rdr.A + "theNavaidEquipment")
                equipment_uuid = rdr.href_of(link)
                if equipment_uuid:
                    component_links[equipment_uuid] = (
                        row_id, copy.deepcopy(component))

        elif kind == "Route":
            routes[uid] = copy.deepcopy(ts)

    con.commit()
    print(f"  designatedPoints={counts['designatedPoints']} "
          f"navaids={counts['navaids']} route={len(routes)} "
          f"bilesen_bagi={len(component_links)}")

    # -- 2. geçiş: navaidComponents (ekipman feature'ları) --
    print("\n[2] Navaid bilesenleri yaziliyor...")
    for member in rdr.iter_members(merged_path):
        feature = rdr.feature_of(member)
        if feature is None:
            continue
        kind = rdr.local(feature.tag)
        if kind not in rdr.EQUIPMENT_FEATURES:
            continue
        gml_id = rdr.gml_id_of(feature)
        uid = rdr.uuid_of(feature)
        ts = rdr.time_slice(feature)
        navaid_row_id, component = component_links.get(uid, (None, None))
        if component is None:
            counts["baglanmamis_ekipman"] += 1
            log.warning("2B", "navaidComponents", gml_id, "theNavaidEquipment",
                        "-", "hicbir_navaid_e_bagli_degil")
        row, position = mapper.map_navaid_component(
            component, ts, kind, navaid_row_id, gml_id, provenance.get(gml_id))
        row = validate_row("navaidComponents", row, log, gml_id)
        geom = schema.point_blob(position[1], position[0]) if position else None
        schema.insert_row(cur, "navaidComponents", row, geom)
        counts["navaidComponents"] += 1
    con.commit()
    print(f"  navaidComponents={counts['navaidComponents']} "
          f"(baglanmamis={counts['baglanmamis_ekipman']})")

    # -- 3. geçiş: routeSegments --
    print("\n[3] Rota segmentleri yaziliyor...")
    unresolved = 0
    for member in rdr.iter_members(merged_path):
        feature = rdr.feature_of(member)
        if feature is None or rdr.local(feature.tag) != "RouteSegment":
            continue
        gml_id = rdr.gml_id_of(feature)
        ts = rdr.time_slice(feature)
        route_uuid = rdr.href_of(ts.find(rdr.A + "routeFormed"))
        row, positions = mapper.map_route_segment(
            feature, ts, gml_id, provenance.get(gml_id),
            routes.get(route_uuid or ""), resolved.get)
        row = validate_row("routeSegments", row, log, gml_id)
        for side in ("start", "end"):
            if row.get(f"routeSegments_{side}PointId") is None:
                unresolved += 1
        geom = schema.linestring_blob(positions) if positions else None
        schema.insert_row(cur, "routeSegments", row, geom)
        counts["routeSegments"] += 1
    con.commit()
    print(f"  routeSegments={counts['routeSegments']} "
          f"(cozulmemis uc nokta={unresolved})")

    print("\n[4] atsStatus_* alanlari turetiliyor...")
    compute_ats_status(con, log)

    print("\n[5] Indexler kuruluyor...")
    schema.finalize(con)
    con.close()

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\nCikti: {out_path.name} ({size_mb:.1f} MB)")
    for key in sorted(counts):
        print(f"  {key:26} {counts[key]}")
    return dict(counts)


# ── Giriş noktası ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Common ATS Structure builder")
    parser.add_argument("--sources", action="store_true",
                        help="yalnizca 1. asama (kaynak ureticileri)")
    parser.add_argument("--merge", action="store_true", help="yalnizca 2A")
    parser.add_argument("--gpkg", action="store_true", help="yalnizca 2B")
    args = parser.parse_args()

    cfg = json.loads((BASE_DIR / "config.json").read_text(encoding="utf-8"))
    log = BuildLog(BASE_DIR / cfg.get("error_log", "errored-features.csv"))

    only = args.sources or args.merge or args.gpkg
    # `--sources`, config ayari kapali olsa da 1. asamayi calistirir.
    run_1 = args.sources or (not only and bool(cfg.get("run_source_generators")))
    run_2a = args.merge or not only
    run_2b = args.gpkg or not only

    if run_1:
        run_source_generators(cfg, BASE_DIR, log)
        if run_2a or run_2b:
            print()

    if run_2a:
        run_merge(cfg, BASE_DIR, log)

    if run_2b:
        print()
        run_gpkg(cfg, BASE_DIR, log)

    summary = log.summary()
    print(f"\n{cfg.get('error_log')}: {sum(summary.values())} kayit")
    for key, value in summary.items():
        print(f"  {key:38} {value}")
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
