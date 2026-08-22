"""AIXM 5.2 XML yazım çekirdeği (EAD-SDO üreticisi için).

Element sırası XSD'deki <sequence> sırasına birebir uymak ZORUNDA; sıra dışı
yazım şema doğrulamasını kırar. Bu yüzden her yazıcı alanları XSD sırasında
yazar ve boş değerleri atlar.

Not: Üreticiler bilinçli olarak birbirinden bağımsız (self-contained)
araçlardır — LT ve Jeppesen üreticileri de kendi yazıcılarını taşır ki biri
değişince diğeri kırılmasın.
"""

import re
import uuid
import xml.etree.ElementTree as ET

NS_MESSAGE = "http://www.aixm.aero/schema/5.2/message"
NS_AIXM = "http://www.aixm.aero/schema/5.2"
NS_GML = "http://www.opengis.net/gml/3.2"
NS_XLINK = "http://www.w3.org/1999/xlink"

SRS_NAME = "urn:ogc:def:crs:EPSG::4326"

# Bu projeye özgü sabit UUID5 namespace'i (LT/Jeppesen üreticileriyle aynı —
# farklı `kind` önekleri kullanıldığı için kaynaklar arası çakışma olmaz).
UUID_NAMESPACE = uuid.UUID("6f1c3b52-9d4a-5e77-b8c1-2a0e94f7d310")

for _prefix, _uri in (("message", NS_MESSAGE), ("aixm", NS_AIXM),
                      ("gml", NS_GML), ("xlink", NS_XLINK)):
    ET.register_namespace(_prefix, _uri)


def q(ns, tag):
    return f"{{{ns}}}{tag}"


def aixm(tag):
    return q(NS_AIXM, tag)


def gml(tag):
    return q(NS_GML, tag)


def feature_uuid(kind: str, key: str) -> str:
    """Feature türü + anahtar için deterministik UUID5 (büyük harf)."""
    return str(uuid.uuid5(UUID_NAMESPACE, f"{kind}:{key}")).upper()


def _ncname(text: str) -> str:
    """gml:id için geçerli NCName üretir (harf/alt çizgi ile başlar)."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", (text or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or not re.match(r"[A-Za-z_]", cleaned):
        cleaned = "X" + cleaned
    return cleaned


class IdRegistry:
    """Okunabilir gml:id üretir ve benzersizliğini garanti eder.

    `source_prefix` her id'nin başına eklenir (örn. `EAD_RS_001610`) — böylece
    farklı kaynaklardan gelen AIXM dosyaları tek bir GeoPackage'da birleşince
    gml:id'ler karışmaz. Türetilmiş id'ler (`_TS`, `_EP`, `_NC1` …) zaten
    önekli id'den üretildiği için öneki otomatik miras alır.
    """

    def __init__(self, source_prefix: str = ""):
        self._used: set[str] = set()
        self._source = source_prefix.strip("_")

    def make(self, prefix: str, key: str) -> str:
        parts = [p for p in (self._source, prefix, key) if p]
        base = _ncname("_".join(parts))
        candidate = base
        n = 1
        while candidate in self._used:
            n += 1
            candidate = f"{base}_{n}"
        self._used.add(candidate)
        return candidate


def sub(parent, tag, text=None, **attrs):
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    for k, v in attrs.items():
        if v is None:
            continue
        el.set(k, str(v))
    return el


def opt(parent, tag, value, **attrs):
    """Değer boş/None değilse element yazar, aksi halde hiç yazmaz."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    return sub(parent, tag, value, **attrs)


def xlink_ref(parent, tag, uuid_value):
    """Boş içerikli association elementi: <tag xlink:href="urn:uuid:…"/>"""
    el = ET.SubElement(parent, tag)
    el.set(q(NS_XLINK, "href"), f"urn:uuid:{uuid_value}")
    return el


def point(parent, tag, gml_id, lat, lon, elevated=False):
    """aixm:location → aixm:Point veya aixm:ElevatedPoint.

    DesignatedPoint.location = Point, Navaid/NavaidEquipment.location =
    ElevatedPoint (XSD'den teyit edildi). gml:pos ENLEM BOYLAM sırasındadır.
    """
    loc = ET.SubElement(parent, tag)
    el = ET.SubElement(loc, aixm("ElevatedPoint" if elevated else "Point"))
    el.set(q(NS_GML, "id"), gml_id)
    el.set("srsName", SRS_NAME)
    sub(el, gml("pos"), f"{lat} {lon}")
    return el


def note(parent, gml_id, text, purpose="REMARK"):
    """aixm:annotation → Note (purpose, translatedNote/LinguisticNote/note)."""
    ann = ET.SubElement(parent, aixm("annotation"))
    n = ET.SubElement(ann, aixm("Note"))
    n.set(q(NS_GML, "id"), gml_id)
    sub(n, aixm("purpose"), purpose)
    tn = ET.SubElement(n, aixm("translatedNote"))
    ln = ET.SubElement(tn, aixm("LinguisticNote"))
    ln.set(q(NS_GML, "id"), gml_id + "_LN")
    sub(ln, aixm("note"), text)
    return ann


_NS_DECL_RE = re.compile(r'\s+xmlns:(?:message|aixm|gml|xlink)="[^"]*"')


class MessageBuilder:
    """AIXMBasicMessage zarfı ve feature/timeSlice iskeleti.

    **Akış (streaming) yazıcı**: EAD-SDO ~260.000 feature üretir (yalnızca
    DesignatedPoint 151.710 kayıt); tüm ağacı bellekte tutmak birkaç GB'a
    çıkardı. Bunun yerine her feature tamamlandığında diske yazılıp bellekten
    atılır. Namespace'ler kök elemanda bir kez bildirilir; parçalardaki
    tekrarlanan bildirimler temizlenir.
    """

    def __init__(self, path, message_id, header_comment):
        self._fh = open(path, "w", encoding="utf-8")
        self._fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self._fh.write(f"<!-- {header_comment} -->\n")
        self._fh.write(
            "<message:AIXMBasicMessage\n"
            f'    xmlns:message="{NS_MESSAGE}"\n'
            f'    xmlns:aixm="{NS_AIXM}"\n'
            f'    xmlns:gml="{NS_GML}"\n'
            f'    xmlns:xlink="{NS_XLINK}"\n'
            f'    gml:id="{message_id}">\n'
        )
        self._pending = None
        self.count = 0

    def _flush(self):
        if self._pending is None:
            return
        ET.indent(self._pending, space="  ", level=1)
        text = ET.tostring(self._pending, encoding="unicode", xml_declaration=False)
        self._fh.write("  " + _NS_DECL_RE.sub("", text) + "\n")
        self._pending = None

    def add_feature(self, feature_name, gml_id, uuid_value, valid_time=None):
        """hasMember → Feature → timeSlice → <Feature>TimeSlice döndürür.

        `valid_time`: kaydın kendi `dtWef` değerinden türetilen yürürlük
        başlangıcı (kullanıcı kararı — data.json'daki `data_effectivity` ÜRETİLEN
        veri setinin geçerliliğini anlatır, feature'ın yürürlüğüyle ilgisizdir).
        Kaynakta tarih yoksa `indeterminatePosition="unknown"` yazılır; gml:validTime
        AIXM'de zorunlu olduğu için element yine de üretilmek zorundadır.
        """
        self._flush()
        member = ET.Element(q(NS_MESSAGE, "hasMember"))
        self._pending = member
        feature = ET.SubElement(member, aixm(feature_name))
        feature.set(q(NS_GML, "id"), gml_id)
        ident = sub(feature, gml("identifier"), uuid_value)
        ident.set("codeSpace", "urn:uuid:")

        ts_wrapper = ET.SubElement(feature, aixm("timeSlice"))
        ts = ET.SubElement(ts_wrapper, aixm(f"{feature_name}TimeSlice"))
        ts.set(q(NS_GML, "id"), gml_id + "_TS")

        vt = ET.SubElement(ts, gml("validTime"))
        tp = sub(vt, gml("TimePeriod"))
        tp.set(q(NS_GML, "id"), gml_id + "_TP")
        if valid_time:
            sub(tp, gml("beginPosition"), valid_time)
        else:
            sub(tp, gml("beginPosition"), None, indeterminatePosition="unknown")
        sub(tp, gml("endPosition"), None, indeterminatePosition="unknown")

        sub(ts, aixm("interpretation"), "BASELINE")
        sub(ts, aixm("sequenceNumber"), "1")
        sub(ts, aixm("correctionNumber"), "0")
        self.count += 1
        return ts

    def close(self):
        self._flush()
        self._fh.write("</message:AIXMBasicMessage>\n")
        self._fh.close()
