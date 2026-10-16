"""EAD-SDO ham XML okuyucuları + navaid eşleştirme motoru.

Eşleştirme mantığı `Navaids\\EAD-SDO\\build_navaids_gpkg.py` (1339 satır)
dosyasından **birebir** port edilmiştir. Karar kuralları AYNEN korunmuştur;
değişen tek şey çıktının şekli: legacy düz GeoPackage satırı üretiyordu,
burada AIXM `Navaid` + `NavaidComponent` + `AbstractNavaidEquipment` yapısına
dönüştürülecek gruplar üretiliyor.

Port edilen kurallar (legacy satır numaralarıyla):
  * LOC+GP   : GP indeksi (ahp_code_id, fir_code_id, ilz_code_id, originator)
               anahtarlı (369-420); LOC (ahp_code_id, fir_code_id, kendi
               code_id, originator) ile arar, `all([ahp_code_id, originator])`
               şartı aranır (423-481).
  * LOC+DME  : DME'nin `Vor/codeId` alanı BOŞ olmalı, `codeId` LOC'unkiyle
               aynı, `OrgCre/txtName` aynı (469-481).
  * VOR+TACAN: TACAN'ın `Vor/codeId`'si VOR'un `codeId`'sine eşit, originator
               aynı. Ülke (`Org/txtName`) BİLEREK karşılaştırılmaz — aynı
               tesis için VOR ve TACAN farklı ülke etiketi taşıyabiliyor
               (622-633).
  * VOR+DME  : VOR+TACAN ile aynı şekil; yalnızca TACAN eşleşmesi YOKSA
               denenir (676-686).
  * Öncelik  : TACAN, DME'yi yener — bir VOR ya VORTAC ya VOR/DME ya da düz
               VOR olur, asla birden fazlası değil (670-696).
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


# ── Legacy'den birebir port edilen yardımcılar ──────────────────────────────

def read_head_text(path: Path, size: int = 256) -> str:
    try:
        return path.read_bytes()[:size].decode("utf-8", errors="ignore").strip()
    except OSError:
        return ""


def looks_like_xml(path: Path) -> tuple[bool, str | None]:
    if not path.exists():
        return False, "dosya bulunamadı"
    head = read_head_text(path).lstrip("﻿")      # BOM
    if not head:
        return False, "dosya boş"
    if not head.startswith("<"):
        return False, head[:80]
    return True, None


#: GECICI COZUM — pist bilgisi `name` alanina metin olarak yaziliyor.
#:
#: AIXM'de ILS'in pist bagi `Navaid/runwayDirection` ASSOCIATION'idir ve ayri
#: bir `RunwayDirection` feature'ina isaret eder. Bu projenin katmanlarinda
#: `AirportHeliport`/`RunwayDirection` feature'lari HENUZ URETILMIYOR, yani
#: association'in gosterecegi hedef yok. Kaynakta %100 dolu olan pist bilgisi
#: (`Rdn/txtDesig`) tamamen kaybolmasin diye GECICI olarak `name` alanina
#: tasiniyor (kullanici karari).
#:
#: Havaalani/pist feature'lari eklendiginde bu cozum KALDIRILMALI ve yerine
#: gercek `runwayDirection` association'i kurulmalidir.
RUNWAY_NAME_PREFIX = "RWY"


def runway_name(rdn_desig: str | None) -> str | None:
    """`"04R"` → `"RWY 04R"`. Bos/None → None.

    `Rdn/txtDesig` TEK pist YONUNU verir (`04R`); `Rwy/txtDesig` ise fiziksel
    pist CIFTINI (`RWY-04L/22R`). AIXM'in `runwayDirection`'i yone karsilik
    geldigi icin `Rdn` kullanilir.
    """
    text = (rdn_desig or "").strip().upper()
    return f"{RUNWAY_NAME_PREFIX} {text}" if text else None


def append_runway_name(existing: str | None, rdn_desig: str | None) -> str | None:
    """Mevcut adin SONUNA pist bilgisini ekler; adi EZMEZ.

    Ezmeme karari olculmus bir catismadan dogdu: ILS/LOC bileseni 402 DME'nin
    396'si kaynakta kendi `txtName`'ini tasiyor (`BRUSSELS NATIONAL`,
    `QUEEN ALIA`, `PAPA 16` gibi) ve ikisinde pist numarasi bile LOC'unkiyle
    CELISIYOR (`ICV`: LOC `Rdn`=26, DME adi `CRAIOVA DME 27`). Ustune yazmak
    gercek kaynak verisini silerdi (kullanici karari).

    Sonuc: `"BRUSSELS NATIONAL"` + `"25R"` → `"BRUSSELS NATIONAL RWY 25R"`.
    Ad bossa yalnizca `"RWY 25R"`.
    """
    rwy = runway_name(rdn_desig)
    base = (existing or "").strip()
    if rwy is None:
        return base or None
    if not base:
        return rwy
    if _has_runway_token(base, rdn_desig):
        # Ad ZATEN ayni pisti soyluyor — ikinci kez yazmak
        # "ILS/DME NZDN RWY 03 RWY 03" uretirdi. Olculdu: 402 DME'nin 30'u
        # boyle; pist bilgisi ADIN ICINDE kaldigi icin hicbir sey kaybolmaz.
        # FARKLI pist soyleyen tek kayit yok (0/402), yani bastirilan sey her
        # zaman birebir ayni metin.
        return base
    return f"{base} {rwy}"


def _has_runway_token(text: str, rdn_desig: str | None) -> bool:
    """Metin zaten `RWY <rdn>` ikilisini tasiyor mu?

    Token bazli bakilir, duz alt-dize aramasi DEGIL: `"RWY 03"`, `"RWY 03L"`
    icinde gecmis sayilmamalidir.
    """
    rdn = (rdn_desig or "").strip().upper()
    if not rdn:
        return False
    tokens = text.upper().split()
    return any(a == RUNWAY_NAME_PREFIX and b == rdn
               for a, b in zip(tokens, tokens[1:]))


def normalize_code(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().upper()
    return text or None


def parse_coord(coord: str | None, is_lat: bool) -> float | None:
    """EAD koordinat metnini ondalık dereceye çevirir.

    Legacy `build_*_gpkg.py` dosyalarındaki `parse_coord` ile birebir aynı;
    ondalık derece, derece+ondalık dakika ve derece+dakika+ondalık saniye
    biçimlerini destekler.
    """
    if not coord:
        return None

    text = coord.strip().upper().replace(" ", "")
    if not text:
        return None

    sign = 1
    if text[0] in "+-":
        if text[0] == "-":
            sign = -1
        text = text[1:]

    if text and text[-1] in "NSEW":
        if text[-1] in "SW":
            sign *= -1
        text = text[:-1]

    if not text:
        return None

    deg_len = 2 if is_lat else 3
    before, dot, after = text.partition(".")

    if len(before) <= deg_len:                      # ondalık derece
        try:
            return sign * float(text)
        except ValueError:
            return None

    if len(before) <= deg_len + 2:                  # derece + ondalık dakika
        try:
            degrees = int(before[:deg_len])
            minutes = float(before[deg_len:] + (dot + after if dot else ""))
            return sign * (degrees + minutes / 60.0)
        except ValueError:
            return None

    try:                                            # derece + dakika + saniye
        degrees = int(before[:deg_len])
        minutes = int(before[deg_len:deg_len + 2])
        seconds = float(before[deg_len + 2:] + (dot + after if dot else ""))
        return sign * (degrees + minutes / 60.0 + seconds / 3600.0)
    except ValueError:
        return None


def _text(elem, path):
    return (elem.findtext(path) or "").strip() or None


def _coords(elem):
    lat_text = (elem.findtext("geoLat") or "").strip()
    lon_text = (elem.findtext("geoLong") or "").strip()
    return (lat_text, lon_text,
            parse_coord(lat_text, is_lat=True), parse_coord(lon_text, is_lat=False))


# ── Ham kayıt okuyucular (legacy alan listeleri korunarak) ──────────────────

def load_dme_records(xml_path: Path) -> dict[str, dict[str, Any]]:
    """DME XML'i oku → mid → record. (legacy 263-313)"""
    records: dict[str, dict[str, Any]] = {}
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  DME atlandı: {reason}")
        return records

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue
        mid = _text(elem, "mid")
        code_id = normalize_code(elem.findtext("codeId"))
        if not mid or not code_id:
            elem.clear()
            continue
        lat_text, lon_text, lat_dd, lon_dd = _coords(elem)
        if lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        records[mid] = {
            "mid": mid,
            "code_id": code_id,
            "name": _text(elem, "txtName"),
            "country": _text(elem, "Org/txtName"),
            "channel": _text(elem, "codeChannel"),
            "ghost_freq": _text(elem, "valGhostFreq"),
            "uom_ghost_freq": _text(elem, "uomGhostFreq"),
            "datum": _text(elem, "codeDatum"),
            "work_hr": _text(elem, "codeWorkHr"),
            "dt_wef": _text(elem, "dtWef"),
            "created_by": _text(elem, "OrgCre/txtName"),
            "vor_code_id": normalize_code(elem.findtext("Vor/codeId")),
            "lat_text": lat_text, "lon_text": lon_text,
            "lat_dd": lat_dd, "lon_dd": lon_dd,
        }
        elem.clear()

    print(f"  DME okunan: {len(records)}")
    return records


def load_tacan_records(xml_path: Path) -> dict[str, dict[str, Any]]:
    """TACAN XML'i oku → mid → record. (legacy 316-366)"""
    records: dict[str, dict[str, Any]] = {}
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  TACAN atlandı: {reason}")
        return records

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue
        mid = _text(elem, "mid")
        code_id = normalize_code(elem.findtext("codeId"))
        if not mid or not code_id:
            elem.clear()
            continue
        lat_text, lon_text, lat_dd, lon_dd = _coords(elem)
        if lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        records[mid] = {
            "mid": mid,
            "code_id": code_id,
            "name": _text(elem, "txtName"),
            "country": _text(elem, "Org/txtName"),
            "channel": _text(elem, "codeChannel"),
            "datum": _text(elem, "codeDatum"),
            "vor_code_id": normalize_code(elem.findtext("Vor/codeId")),
            "work_hr": _text(elem, "codeWorkHr"),
            "dt_wef": _text(elem, "dtWef"),
            "created_by": _text(elem, "OrgCre/txtName"),
            "lat_text": lat_text, "lon_text": lon_text,
            "lat_dd": lat_dd, "lon_dd": lon_dd,
        }
        elem.clear()

    print(f"  TACAN okunan: {len(records)}")
    return records


def load_gp_records(xml_path: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """GP XML'i oku → (ahp_code_id, fir_code_id, ilz_code_id, originator) indeksi.

    (legacy 369-420 — anahtar yapısı birebir korunmuştur.)
    """
    records: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  ILS-GP atlandı: {reason}")
        return records

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue
        ahp_code_id = normalize_code(elem.findtext("Ahp/codeId"))
        fir_code_id = normalize_code(elem.findtext("Ase/firCodeId"))
        ilz_code_id = normalize_code(elem.findtext("Ilz/codeId"))
        originator = _text(elem, "OrgCre/txtName")

        if not all([ahp_code_id, ilz_code_id, originator]):
            elem.clear()
            continue
        lat_text, lon_text, lat_dd, lon_dd = _coords(elem)
        if lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        key = (ahp_code_id or "", fir_code_id or "", ilz_code_id or "", originator or "")
        records[key] = {
            "mid": _text(elem, "mid"),
            "code_id": ilz_code_id,
            "name": _text(elem, "txtName"),
            "rdn_desig": _text(elem, "Rdn/txtDesig"),
            "created_by": originator,
            "lat_text": lat_text, "lon_text": lon_text,
            "lat_dd": lat_dd, "lon_dd": lon_dd,
            "freq": _text(elem, "valFreq"),
            "uom_freq": _text(elem, "uomFreq"),
            "slope": _text(elem, "valSlope"),
            "elev": _text(elem, "valElev"),
            "uom_dist_ver": _text(elem, "uomDistVer"),
            "rdh": _text(elem, "valRdh"),
            "uom_rdh": _text(elem, "uomRdh"),
            "datum": _text(elem, "codeDatum"),
            "emission": _text(elem, "codeEm"),
            "crc": _text(elem, "valCrc"),
            "work_hr": _text(elem, "codeWorkHr"),
            "geo_accuracy": _text(elem, "valGeoAccuracy"),
            "uom_geo_accuracy": _text(elem, "uomGeoAccuracy"),
            "geoid_undulation": _text(elem, "valGeoidUndulation"),
            "vert_datum": _text(elem, "txtVerDatum"),
            "elev_accuracy": _text(elem, "valElevAccuracy"),
            "dt_wef": _text(elem, "dtWef"),
            "dt_com": _text(elem, "dtCom"),
            "rmk": _text(elem, "txtRmk"),
            "work_hr_rmk": _text(elem, "txtRmkWorkHr"),
        }
        elem.clear()

    print(f"  ILS-GP okunan: {len(records)}")
    return records


# ── Eşleştirme motoru (legacy karar kuralları birebir) ──────────────────────

def load_loc_groups(xml_path: Path, gp_index, dme_records):
    """LOC XML'i oku, GP ve DME ile eşleştir → grup listesi.

    (legacy `load_loc_records`, 423-580 — eşleştirme kuralları birebir.)
    Grup: {"primary": loc, "gp": gp|None, "dme": dme|None, "aixm_type": …}
    """
    groups: list[dict[str, Any]] = []
    dme_consumed_by_ils: set[str] = set()
    pistsiz = 0                       # `Rdn/txtDesig` bos gelen LOC sayisi
    dme_pist_devralan = 0             # pist bilgisi LOC'tan devralan DME

    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  ILS-LOC atlandı: {reason}")
        return groups, dme_consumed_by_ils

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        code_id = normalize_code(elem.findtext("codeId"))
        ahp_code_id = normalize_code(elem.findtext("Ahp/codeId"))
        fir_code_id = normalize_code(elem.findtext("Ase/firCodeId"))
        originator = _text(elem, "OrgCre/txtName")
        lat_text, lon_text, lat_dd, lon_dd = _coords(elem)

        if not code_id or lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        # GP'yi eşleştir (legacy 466-467)
        gp_key = (ahp_code_id or "", fir_code_id or "", code_id, originator or "")
        gp = gp_index.get(gp_key, {}) if all([ahp_code_id, originator]) else {}

        # DME'yi eşleştir: vor_code_id BOŞ + codeId eşleşme + originator eşleşme
        # (legacy 469-481)
        dme = {}
        for dme_mid, dme_rec in dme_records.items():
            if (
                not dme_rec.get("vor_code_id")
                and dme_rec.get("code_id") == code_id
                and dme_rec.get("created_by") == originator
            ):
                dme = dme_rec
                dme_consumed_by_ils.add(dme_mid)
                break

        loc = {
            "mid": _text(elem, "mid"),
            "code_id": code_id,
            "name": _text(elem, "txtName"),
            "ahp_code_id": ahp_code_id,
            "ahp_code_icao": normalize_code(elem.findtext("Ahp/codeIcao")),
            "rwy_desig": _text(elem, "Rwy/txtDesig"),
            "rdn_desig": _text(elem, "Rdn/txtDesig"),
            "freq": _text(elem, "valFreq"),
            "uom_freq": _text(elem, "uomFreq"),
            "mag_brg": _text(elem, "valMagBrg"),
            "true_brg": _text(elem, "valTrueBrg"),
            "course_width": _text(elem, "valWidCourse"),
            "back_course": _text(elem, "codeTypeUseBack"),
            "mag_var": _text(elem, "valMagVar"),
            "mag_var_date": _text(elem, "dateMagVar"),
            "elev": _text(elem, "valElev"),
            "uom_dist_ver": _text(elem, "uomDistVer"),
            "elev_accuracy": _text(elem, "valElevAccuracy"),
            "datum": _text(elem, "codeDatum"),
            "crc": _text(elem, "valCrc"),
            "work_hr": _text(elem, "codeWorkHr"),
            "emission": _text(elem, "codeEm"),
            "fir_code_id": fir_code_id,
            "geo_accuracy": _text(elem, "valGeoAccuracy"),
            "uom_geo_accuracy": _text(elem, "uomGeoAccuracy"),
            "geoid_undulation": _text(elem, "valGeoidUndulation"),
            "vert_datum": _text(elem, "txtVerDatum"),
            "dt_wef": _text(elem, "dtWef"),
            "dt_com": _text(elem, "dtCom"),
            "created_by": originator,
            "rmk": _text(elem, "txtRmk"),
            "work_hr_rmk": _text(elem, "txtRmkWorkHr"),
            "lat_text": lat_text, "lon_text": lon_text,
            "lat_dd": lat_dd, "lon_dd": lon_dd,
        }

        # Bileşik AIXM tipi: GP ve DME eşleşmesine göre.
        if gp and dme:
            aixm_type = "ILS_DME"
        elif gp:
            aixm_type = "ILS"
        elif dme:
            aixm_type = "LOC_DME"
        else:
            aixm_type = "LOC"

        # ── GECICI: pist bilgisi `name` alanina yaziliyor ───────────────────
        # AirportHeliport/RunwayDirection feature'lari henuz uretilmedigi icin
        # `runwayDirection` association'i kurulamiyor (bkz. runway_name).
        # Mevcut ad HICBIR ZAMAN ezilmez, sonuna eklenir.
        if not (loc["rdn_desig"] or "").strip():
            pistsiz += 1
        loc["name"] = append_runway_name(loc.get("name"), loc["rdn_desig"])

        if gp:
            # GP'nin KENDI `Rdn`'si kullanilir, LOC'unki devredilmez. Olculdu:
            # eslesen 522 ciftin 522'sinde iki deger ayni; yine de kaynagin
            # kendi alani esas alinir.
            gp = dict(gp)                      # paylasilan indeks kaydini bozma
            gp["name"] = append_runway_name(gp.get("name"), gp.get("rdn_desig"))

        if dme:
            # `dme.xml`'de pist/havaalani elemani YOK (Rwy/Rdn/Ahp hicbiri) —
            # bu yuzden pist bagli LOC'tan DEVRALINIR. DME'nin kendi
            # `txtName`'i korunur: "BRUSSELS NATIONAL" + "25R" →
            # "BRUSSELS NATIONAL RWY 25R".
            dme = dict(dme)                    # paylasilan kaydi bozma
            dme["name"] = append_runway_name(dme.get("name"), loc["rdn_desig"])
            dme_pist_devralan += 1

        groups.append({"kind": "LOC", "primary": loc, "gp": gp or None,
                       "dme": dme or None, "aixm_type": aixm_type})
        elem.clear()

    matched_gp = sum(1 for g in groups if g["gp"])
    matched_dme = sum(1 for g in groups if g["dme"])
    print(f"  ILS-LOC okunan: {len(groups)}, "
          f"GP eşleşmesi: {matched_gp}, DME eşleşmesi: {matched_dme}")
    print(f"  pist adı (GEÇİCİ) yazılan: LOC={len(groups) - pistsiz}, "
          f"GP={matched_gp}, DME={dme_pist_devralan}"
          + (f"  UYARI pist bilgisi OLMAYAN LOC: {pistsiz}" if pistsiz else ""))
    return groups, dme_consumed_by_ils


def load_vor_groups(xml_path: Path, dme_records, tacan_records):
    """VOR XML'i oku, TACAN'ı DME'ye tercih ederek eşleştir → grup listesi.

    (legacy `load_vor_records`, 583-707 — öncelik ve eşleşme kuralları birebir.)
    """
    groups: list[dict[str, Any]] = []
    dme_consumed_by_vor: set[str] = set()
    tacan_consumed_by_vor: set[str] = set()

    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  VOR atlandı: {reason}")
        return groups, dme_consumed_by_vor, tacan_consumed_by_vor

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        code_id = normalize_code(elem.findtext("codeId"))
        lat_text, lon_text, lat_dd, lon_dd = _coords(elem)
        created_by = _text(elem, "OrgCre/txtName")

        if not code_id or lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        # Önce TACAN eşleştir.
        # Not: country karşılaştırması YAPILMIYOR — VOR ve TACAN aynı tesis için
        # farklı org adları taşıyabiliyor (legacy 622-633'teki gerekçe).
        tacan = {}
        for tacan_mid, tacan_rec in tacan_records.items():
            if (
                tacan_rec.get("vor_code_id") == code_id
                and tacan_rec.get("created_by") == created_by
            ):
                tacan = tacan_rec
                tacan_consumed_by_vor.add(tacan_mid)
                break

        vor = {
            "mid": _text(elem, "mid"),
            "code_id": code_id,
            "name": _text(elem, "txtName"),
            "code_type": _text(elem, "codeType"),
            "freq": _text(elem, "valFreq"),
            "uom_freq": _text(elem, "uomFreq"),
            "north_ref": _text(elem, "codeTypeNorth"),
            "declination": _text(elem, "valDeclination"),
            "mag_var": _text(elem, "valMagVar"),
            "mag_var_date": _text(elem, "dateMagVar"),
            "emission": _text(elem, "codeEm"),
            "datum": _text(elem, "codeDatum"),
            "geo_accuracy": _text(elem, "valGeoAccuracy"),
            "uom_geo_accuracy": _text(elem, "uomGeoAccuracy"),
            "elev": _text(elem, "valElev"),
            "uom_dist_ver": _text(elem, "uomDistVer"),
            "elev_accuracy": _text(elem, "valElevAccuracy"),
            "geoid_undulation": _text(elem, "valGeoidUndulation"),
            "vert_datum": _text(elem, "txtVerDatum"),
            "crc": _text(elem, "valCrc"),
            "work_hr": _text(elem, "codeWorkHr"),
            "work_hr_rmk": _text(elem, "txtRmkWorkHr"),
            "country": _text(elem, "Org/txtName"),
            "created_by": created_by,
            "dt_wef": _text(elem, "dtWef"),
            "dt_com": _text(elem, "dtCom"),
            "rmk": _text(elem, "txtRmk"),
            "lat_text": lat_text, "lon_text": lon_text,
            "lat_dd": lat_dd, "lon_dd": lon_dd,
        }

        if tacan:
            # VORTAC — TACAN eşleşti, DME eşleştirmesi HİÇ denenmez (legacy 670-674).
            groups.append({"kind": "VOR", "primary": vor, "tacan": tacan,
                           "dme": None, "aixm_type": "VORTAC"})
        else:
            # TACAN yok → DME eşleştir (legacy 676-696).
            dme = {}
            for dme_mid, dme_rec in dme_records.items():
                if (
                    dme_rec.get("vor_code_id") == code_id
                    and dme_rec.get("created_by") == created_by
                ):
                    dme = dme_rec
                    dme_consumed_by_vor.add(dme_mid)
                    break

            groups.append({"kind": "VOR", "primary": vor, "tacan": None,
                           "dme": dme or None,
                           "aixm_type": "VOR_DME" if dme else "VOR"})
        elem.clear()

    n_vortac = sum(1 for g in groups if g["aixm_type"] == "VORTAC")
    n_vordme = sum(1 for g in groups if g["aixm_type"] == "VOR_DME")
    n_vor = sum(1 for g in groups if g["aixm_type"] == "VOR")
    print(f"  VOR okunan: {len(groups)} → VOR={n_vor}, "
          f"VOR/DME={n_vordme}, VORTAC={n_vortac}")
    return groups, dme_consumed_by_vor, tacan_consumed_by_vor


def collect_standalone(dme_records, tacan_records, dme_consumed, tacan_consumed):
    """Hiçbir VOR/LOC tarafından tüketilmemiş DME ve TACAN'lar (legacy 1116-1129)."""
    dme_groups = [
        {"kind": "DME", "primary": dme_records[mid], "aixm_type": "DME"}
        for mid in dme_records if mid not in dme_consumed
    ]
    tacan_groups = [
        {"kind": "TACAN", "primary": tacan_records[mid], "aixm_type": "TACAN"}
        for mid in tacan_records if mid not in tacan_consumed
    ]
    print(f"  Standalone DME: {len(dme_groups)}, TACAN: {len(tacan_groups)}")
    return dme_groups, tacan_groups


def load_designated_points(xml_paths: list[Path]) -> list[dict[str, Any]]:
    """DP XML'lerini oku (legacy `load_dp_records`, 257-301)."""
    records: list[dict[str, Any]] = []
    for xml_path in xml_paths:
        valid, reason = looks_like_xml(xml_path)
        if not valid:
            print(f"  DP {xml_path.name} atlandı: {reason}")
            continue
        n = 0
        for _, elem in ET.iterparse(xml_path, events=("end",)):
            if elem.tag != "Record":
                continue
            code_id = normalize_code(elem.findtext("codeId"))
            lat_text, lon_text, lat_dd, lon_dd = _coords(elem)
            if not code_id or lat_dd is None or lon_dd is None:
                elem.clear()
                continue
            records.append({
                "mid": _text(elem, "mid"),
                "code_id": code_id,
                "code_type": normalize_code(elem.findtext("codeType")),
                "name": _text(elem, "txtName"),
                "datum": _text(elem, "codeDatum"),
                "dt_wef": _text(elem, "dtWef"),
                "created_by": _text(elem, "OrgCre/txtName"),
                "lat_text": lat_text, "lon_text": lon_text,
                "lat_dd": lat_dd, "lon_dd": lon_dd,
            })
            n += 1
            elem.clear()
        print(f"  DP {xml_path.name}: {n}")
    return records


def load_route_records(xml_paths: list[tuple[Path, str]]) -> list[dict[str, Any]]:
    """Rota XML'lerini oku. `level` dosya grubundan türetilir (UPPER/LOWER)."""
    records: list[dict[str, Any]] = []
    for xml_path, level in xml_paths:
        valid, reason = looks_like_xml(xml_path)
        if not valid:
            print(f"  Route {xml_path.name} atlandı: {reason}")
            continue
        n = 0
        for _, elem in ET.iterparse(xml_path, events=("end",)):
            if elem.tag != "Record":
                continue
            records.append({
                "mid": _text(elem, "mid"),
                "designator": _text(elem, "Rte/txtDesig"),
                "loc_designator": _text(elem, "Rte/txtLocDesig"),
                "start_code_id": normalize_code(elem.findtext("SpnSta/codeId")),
                "start_code_type": normalize_code(elem.findtext("SpnSta/codeType")),
                "end_code_id": normalize_code(elem.findtext("SpnEnd/codeId")),
                "end_code_type": normalize_code(elem.findtext("SpnEnd/codeType")),
                "upper_limit": _text(elem, "valDistVerUpper"),
                "upper_uom": _text(elem, "uomDistVerUpper"),
                "upper_ref": _text(elem, "codeDistVerUpper"),
                "lower_limit": _text(elem, "valDistVerLower"),
                "lower_uom": _text(elem, "uomDistVerLower"),
                "lower_ref": _text(elem, "codeDistVerLower"),
                "dt_wef": _text(elem, "dtWef"),
                "created_by": _text(elem, "OrgCre/txtName"),
                "level": level,
            })
            n += 1
            elem.clear()
        print(f"  Route {xml_path.name}: {n}")
    return records
