"""Airspace feature'ının AIXM 5.2 yazıcısı — data-airspace'in TÜM üreticileri
bu modülü kullanır (yedi kaynak da aynı feature tipini yazar).

Üretici kendi ham verisini `AirspaceRecord`'a çevirir; bu modül onu XSD
sırasında AIXM'e yazar:

    Airspace
      gml:identifier
      timeSlice/AirspaceTimeSlice
        gml:validTime, interpretation, sequenceNumber, correctionNumber
        type, designator, localType, name, designatorICAO, controlType
        class/AirspaceLayerClass/classification              (varsa)
        geometryComponent/AirspaceGeometryComponent
          operation=BASE, operationSequence=1
          theAirspaceVolume/AirspaceVolume
            upperLimit(+uom), upperLimitReference,
            lowerLimit(+uom), lowerLimitReference,
            horizontalProjection/aixm:Surface (PolygonPatch'ler)
        activation/AirspaceActivation (activity, status)     (varsa)
        annotation/Note …
        extension/ibosoftais:AirspaceExtension               (varsa)
        extension/ibosoftais:AirspaceDataProvenance          (her zaman)

Geometri, antimeridyene karşı güvenli MultiPolygon olarak yazılır (her
poligon bir `gml:PolygonPatch`). Koordinatlar `repr(float)` ile yazılır: ham
değer bit düzeyinde geri okunur.

`gml:validTime` başlangıcı **bilinmiyor** (`indeterminatePosition="unknown"`)
yazılır: kaynakların `data_effectivity` değeri VERİ SETİNİN geçerliliğidir,
feature'ın kendi yürürlüğü değildir (ATS Jeppesen üreticisindeki kullanıcı
kararıyla aynı gerekçe). Veri setinin geçerliliği provenance kutusundadır.
"""

import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from data_build_common import provenance
from data_build_common.aixm_reader import (NS_AIXM, NS_GML, NS_IBOSOFTAIS,
                                           NS_MESSAGE, NS_XLINK)
from data_build_common.aixm_writer import (HEADER_COMMENT, root_open_tag,
                                           strip_ns_declarations)

from airspace_geo import antimeridian_safe

SRS_NAME = "urn:ogc:def:crs:EPSG::4326"

#: ATS üreticileriyle aynı UUID5 namespace'i; `kind` önekleri farklı olduğu
#: için kaynaklar ve projeler arasında çakışma olmaz.
UUID_NAMESPACE = uuid.UUID("6f1c3b52-9d4a-5e77-b8c1-2a0e94f7d310")

for _prefix, _uri in (("message", NS_MESSAGE), ("aixm", NS_AIXM),
                      ("gml", NS_GML), ("xlink", NS_XLINK),
                      ("ibosoftais", NS_IBOSOFTAIS)):
    ET.register_namespace(_prefix, _uri)


def _a(tag):
    return f"{{{NS_AIXM}}}{tag}"


def _g(tag):
    return f"{{{NS_GML}}}{tag}"


def _i(tag):
    return f"{{{NS_IBOSOFTAIS}}}{tag}"


def feature_uuid(kind: str, key: str) -> str:
    """Feature türü + anahtar için deterministik UUID5 (büyük harf)."""
    return str(uuid.uuid5(UUID_NAMESPACE, f"{kind}:{key}")).upper()


def ncname(text: str) -> str:
    """gml:id için geçerli NCName (harf/alt çizgi ile başlar)."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", (text or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or not re.match(r"[A-Za-z_]", cleaned):
        cleaned = "X" + cleaned
    return cleaned


# ── AIXM metin tipleri ─────────────────────────────────────────────────────

#: AIXM `TextNameType` (name, localType): 1-60 karakter, yalnız ASCII harf,
#: rakam ve belirli işaretler (`AIXM_DataTypes.xsd` TextNameBaseType deseni).
_TEXT_NAME_RE = re.compile(
    r"([A-Z]|[a-z]|[0-9]|[, !\"&#$%'\(\)\*\+\-\./:;<=>\?@\[\\\]\^_\|\{\}])*")

#: Kullanıcı kararı: Türkçe harfler ASCII karşılığına çevrilir, her dönüşüm
#: loglanır.
_TR_ASCII = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")


def text_name(value, log, gml_id, field_name):
    """TextNameType alanı: Türkçe harf dönüşümü + desen/uzunluk denetimi.

    Dönüşüm sonrası hâlâ geçersizse değer DEĞİŞTİRİLMEDEN döner ve hata
    loglanır — XSD doğrulaması da yakalar (kırpma/uydurma yapılmaz).
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    converted = value.translate(_TR_ASCII)
    if converted != value:
        log.warning("Airspace", gml_id, field_name, value,
                    f"turkce_harf_ascii_donusturuldu -> {converted}")
    if len(converted) > 60 or not _TEXT_NAME_RE.fullmatch(converted):
        log.error("Airspace", gml_id, field_name, converted,
                  "aixm_textname_kuralina_uymuyor")
    return converted


# ── Kayıt ──────────────────────────────────────────────────────────────────

@dataclass
class Limit:
    value: str | None = None          # sayı ya da UNL/GND/FLOOR/CEILING
    uom: str | None = None            # FT/M/FL/SM
    reference: str | None = None      # SFC/MSL/W84/STD


@dataclass
class AirspaceRecord:
    gml_id: str
    uuid: str
    geometry: object                  # shapely Polygon/MultiPolygon (lon, lat)
    provider: str
    effectivity: str
    originator: str | None = None
    type: str | None = None
    designator: str | None = None
    name: str | None = None
    local_type: str | None = None
    designator_icao: str | None = None
    control_type: str | None = None
    classification: str | None = None
    upper: Limit = field(default_factory=Limit)
    lower: Limit = field(default_factory=Limit)
    activity: str | None = None
    status: str | None = None
    #: [(purpose, metin)] — purpose: DESCRIPTION/REMARK/WARNING/DISCLAIMER
    notes: list = field(default_factory=list)
    region_icao: str | None = None
    region_sup_proc: str | None = None


# ── Yazıcı ─────────────────────────────────────────────────────────────────

def _sub(parent, tag, text=None, **attrs):
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    for key, value in attrs.items():
        if value is not None:
            el.set(key, str(value))
    return el


def _opt(parent, tag, value, **attrs):
    if value is None or str(value).strip() == "":
        return None
    return _sub(parent, tag, str(value).strip(), **attrs)


def _limit(parent, name, limit: Limit):
    if limit.value not in (None, ""):
        el = _sub(parent, _a(name), limit.value)
        if limit.uom:
            el.set("uom", limit.uom)
    _opt(parent, _a(name + "Reference"), limit.reference)


def _pos_list(coords):
    """shapely (lon, lat) → AIXM/GML posList (enlem boylam)."""
    return " ".join(f"{lat!r} {lon!r}" for lon, lat in coords)


def _surface(parent, gml_id, geometry):
    surface = _sub(parent, _a("Surface"))
    surface.set(_g("id"), gml_id)
    surface.set("srsName", SRS_NAME)
    patches = _sub(surface, _g("patches"))
    for polygon in geometry.geoms:
        patch = _sub(patches, _g("PolygonPatch"))
        ring = _sub(_sub(patch, _g("exterior")), _g("LinearRing"))
        _sub(ring, _g("posList"), _pos_list(polygon.exterior.coords))
        for hole in polygon.interiors:
            ring = _sub(_sub(patch, _g("interior")), _g("LinearRing"))
            _sub(ring, _g("posList"), _pos_list(hole.coords))


def _note(parent, gml_id, purpose, text):
    ann = _sub(parent, _a("annotation"))
    note = _sub(ann, _a("Note"))
    note.set(_g("id"), gml_id)
    _sub(note, _a("purpose"), purpose)
    ling = _sub(_sub(note, _a("translatedNote")), _a("LinguisticNote"))
    ling.set(_g("id"), gml_id + "_LN")
    _sub(ling, _a("note"), text)


class AirspaceMessageWriter:
    """`message:AIXMBasicMessage` — Airspace feature'ları akış modunda yazılır."""

    def __init__(self, path, message_id, log):
        self._fh = open(path, "w", encoding="utf-8")
        self._fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self._fh.write(f"<!-- {HEADER_COMMENT} -->\n")
        self._fh.write(root_open_tag(message_id))
        self.log = log
        self.count = 0

    def write(self, rec: AirspaceRecord) -> bool:
        """Kaydı yazar; geometrisi geçersizse yazmaz, loglar ve False döner."""
        geometry = antimeridian_safe(rec.geometry)
        if geometry is None:
            self.log.error("Airspace", rec.gml_id, "geometry", "-",
                           "gecersiz_ya_da_bos_geometri")
            return False

        member = ET.Element(f"{{{NS_MESSAGE}}}hasMember")
        feature = _sub(member, _a("Airspace"))
        feature.set(_g("id"), rec.gml_id)
        _sub(feature, _g("identifier"), rec.uuid, codeSpace="urn:uuid:")
        ts = _sub(_sub(feature, _a("timeSlice")), _a("AirspaceTimeSlice"))
        ts.set(_g("id"), rec.gml_id + "_TS")

        period = _sub(_sub(ts, _g("validTime")), _g("TimePeriod"))
        period.set(_g("id"), rec.gml_id + "_TP")
        _sub(period, _g("beginPosition"), indeterminatePosition="unknown")
        _sub(period, _g("endPosition"), indeterminatePosition="unknown")
        _sub(ts, _a("interpretation"), "BASELINE")
        _sub(ts, _a("sequenceNumber"), "1")
        _sub(ts, _a("correctionNumber"), "0")

        # AirspacePropertyGroup — XSD sırası
        _opt(ts, _a("type"), rec.type)
        _opt(ts, _a("designator"), rec.designator)
        _opt(ts, _a("localType"),
             text_name(rec.local_type, self.log, rec.gml_id, "localType"))
        _opt(ts, _a("name"), text_name(rec.name, self.log, rec.gml_id, "name"))
        _opt(ts, _a("designatorICAO"), rec.designator_icao)
        _opt(ts, _a("controlType"), rec.control_type)
        if rec.classification:
            layer = _sub(_sub(ts, _a("class")), _a("AirspaceLayerClass"))
            layer.set(_g("id"), rec.gml_id + "_CLS")
            _sub(layer, _a("classification"), rec.classification)

        component = _sub(_sub(ts, _a("geometryComponent")),
                         _a("AirspaceGeometryComponent"))
        component.set(_g("id"), rec.gml_id + "_GC")
        _sub(component, _a("operation"), "BASE")
        _sub(component, _a("operationSequence"), "1")
        volume = _sub(_sub(component, _a("theAirspaceVolume")),
                      _a("AirspaceVolume"))
        volume.set(_g("id"), rec.gml_id + "_AV")
        _limit(volume, "upperLimit", rec.upper)
        _limit(volume, "lowerLimit", rec.lower)
        _surface(_sub(volume, _a("horizontalProjection")),
                 rec.gml_id + "_SF", geometry)

        if rec.activity or rec.status:
            activation = _sub(_sub(ts, _a("activation")),
                              _a("AirspaceActivation"))
            activation.set(_g("id"), rec.gml_id + "_ACT")
            _opt(activation, _a("activity"), rec.activity)
            _opt(activation, _a("status"), rec.status)

        for n, (purpose, text) in enumerate(rec.notes, 1):
            if text and str(text).strip():
                _note(ts, f"{rec.gml_id}_NOTE{n}", purpose, str(text).strip())

        if rec.region_icao or rec.region_sup_proc:
            ext = _sub(_sub(ts, _a("extension")), _i("AirspaceExtension"))
            ext.set(_g("id"), rec.gml_id + "_EXT")
            _opt(ext, _i("regionIcao"), rec.region_icao)
            _opt(ext, _i("regionSupProc"), rec.region_sup_proc)

        provenance.append_box(feature, rec.provider, rec.originator,
                              rec.effectivity)

        ET.indent(member, space="  ", level=1)
        text = ET.tostring(member, encoding="unicode")
        self._fh.write("  " + strip_ns_declarations(text) + "\n")
        self.count += 1
        return True

    def close(self):
        self._fh.write("</message:AIXMBasicMessage>\n")
        self._fh.close()


def generate(records, out_path, message_id, log, label):
    """Üretici ortak gövdesi: kayıtları yazar, özeti basar."""
    writer = AirspaceMessageWriter(out_path, message_id, log)
    read = 0
    for rec in records:
        read += 1
        writer.write(rec)
    writer.close()
    log.close()
    print("=" * 60)
    print(f"{label} -> {out_path.name}")
    print(f"  okunan kayit : {read}")
    print(f"  yazilan      : {writer.count}")
    for key, n in sorted(log.counts.items()):
        print(f"  {key:40} {n}")
    return writer.count


# ── Log ────────────────────────────────────────────────────────────────────

class ErrorLog:
    """`errored-features.log` — her çalıştırmada sıfırlanır (TSV)."""

    def __init__(self, path):
        self._fh = open(path, "w", encoding="utf-8")
        self._fh.write("severity\tfeature\tident\tfield\tvalue\tviolation\n")
        self.counts = {}

    def _log(self, severity, feature, ident, field_name, value, violation):
        key = violation.split(" ->")[0]
        self.counts[key] = self.counts.get(key, 0) + 1
        self._fh.write(f"{severity}\t{feature}\t{ident}\t{field_name}\t"
                       f"{value}\t{violation}\n")

    def error(self, *args):
        self._log("error", *args)

    def warning(self, *args):
        self._log("warning", *args)

    def close(self):
        self._fh.close()
