"""Jenerik AIXM 5.2 okuyucu — kaynağa özel hiçbir mantık içermez.

Bu modül birleştirme aşamasının (2A) tek XML okuma yeridir. Kaynak dosyalar
1. aşamada üretilmiş, XSD'ye karşı doğrulanmış AIXM 5.2 mesajlarıdır:
`message:AIXMBasicMessage` → `message:hasMember` → `aixm:<Feature>` →
`gml:identifier` + `aixm:timeSlice` → `aixm:<Feature>TimeSlice`.

Bellek: EAD-SDO dosyası ~461 MB / 274.933 feature. Bu yüzden her şey akış
(streaming) modunda okunur; işlenen eleman hemen bellekten atılır.
"""

from pathlib import Path

from lxml import etree

NS_MESSAGE = "http://www.aixm.aero/schema/5.2/message"
NS_AIXM = "http://www.aixm.aero/schema/5.2"
NS_GML = "http://www.opengis.net/gml/3.2"
NS_XLINK = "http://www.w3.org/1999/xlink"

M = "{%s}" % NS_MESSAGE
A = "{%s}" % NS_AIXM
G = "{%s}" % NS_GML
X = "{%s}" % NS_XLINK

HAS_MEMBER = M + "hasMember"

# Rota uç noktası olarak kullanılabilen nokta feature'ları (AIXM'in 6 seçenekli
# pointChoice_* choice'ının bu projede karşılığı olan üçü).
POINT_FEATURES = {"DesignatedPoint", "Navaid", "Point"}

# AbstractNavaidEquipment'ın bu projede üretilen somut alt-türleri.
# `MarkerBeacon` bu kumeye eklenince 2B kendiliginden calisir: `keys.LAYER_OF`
# bu kumeden turetiliyor, `run_gpkg`'nin navaidComponents gecisi bununla
# suzuyor, sahipsiz ekipman denetimi de bunu kullaniyor.
#: AIXM `AbstractNavaidEquipment` ikame grubunun 11 SOMUT alt-turu (XSD'den
#: dogrulandi). Onceki hali yalnizca 7'sini sayiyordu; `SDF`, `Azimuth`,
#: `Elevation`, `DirectionFinder` eksikti ve bu turden bir feature gelse
#: `build_common_ats.run_gpkg` onu SESSIZCE atiyordu — ne bilesen satiri olur,
#: ne de birlestirmedeki "dusen navaid'in ekipmani" mantigi gorurdu.
EQUIPMENT_FEATURES = {"VOR", "DME", "TACAN", "Localizer", "Glidepath", "NDB",
                      "MarkerBeacon", "SDF", "Azimuth", "Elevation",
                      "DirectionFinder"}


def local(tag: str) -> str:
    """'{ns}Name' → 'Name'."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def iter_members(path: Path):
    """`hasMember` elemanlarını akış modunda üretir.

    Her adımda eleman ve önceki kardeşleri bellekten silinir — 461 MB'lik dosya
    birkaç yüz MB RAM ile taranabilir. Tüketici, eleman üzerinde yalnızca kendi
    döngü adımı içinde çalışmalıdır.
    """
    context = etree.iterparse(str(path), events=("end",), tag=HAS_MEMBER)
    for _, member in context:
        yield member
        member.clear()
        while member.getprevious() is not None:
            del member.getparent()[0]


def feature_of(member):
    """`hasMember` → içindeki `aixm:<Feature>` elemanı."""
    return member[0] if len(member) else None


def time_slice(feature):
    """`aixm:<Feature>TimeSlice` elemanı (yoksa None)."""
    wrapper = feature.find(A + "timeSlice")
    return wrapper[0] if wrapper is not None and len(wrapper) else None


def uuid_of(feature) -> str | None:
    el = feature.find(G + "identifier")
    return el.text.strip().upper() if el is not None and el.text else None


def gml_id_of(el) -> str | None:
    return el.get(G + "id")


def text_of(ts, name: str) -> str | None:
    """TimeSlice'ın doğrudan alt elemanının metni (yoksa None)."""
    if ts is None:
        return None
    el = ts.find(A + name)
    return el.text.strip() if el is not None and el.text else None


def href_of(el) -> str | None:
    """`xlink:href="urn:uuid:…"` → UUID (büyük harf)."""
    if el is None:
        return None
    href = el.get(X + "href")
    if not href or not href.startswith("urn:uuid:"):
        return None
    return href[len("urn:uuid:"):].strip().upper()


def position_of(feature):
    """Feature'ın konumu → (lat, lon) veya None.

    `location/Point/gml:pos` veya `location/ElevatedPoint/gml:pos`; `Point`
    feature'ında `location` sarmalayıcısı yoktur, `gml:pos` doğrudan gelir.
    """
    pos = feature.find(".//" + G + "pos")
    if pos is None or not pos.text:
        return None
    parts = pos.text.split()
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def endpoint_ref(ts, side: str):
    """RouteSegment'in `start`/`end` ucundaki nokta referansı → (uuid, tag).

    `tag`, hangi `pointChoice_*` kullanıldığını söyler
    (`pointChoice_fixDesignatedPoint`, `pointChoice_navaidSystem`, …).
    """
    holder = ts.find(A + side)
    if holder is None:
        return None, None
    for child in holder.iter():
        uid = href_of(child)
        if uid:
            return uid, local(child.tag)
    return None, None


def curve_positions(ts):
    """RouteSegment'in `curveExtent` posList'i → [(lat, lon), …] veya None."""
    pl = ts.find(".//" + G + "posList") if ts is not None else None
    if pl is None or not pl.text:
        return None
    v = pl.text.split()
    if len(v) < 4 or len(v) % 2:
        return None
    try:
        nums = [float(x) for x in v]
    except ValueError:
        return None
    return list(zip(nums[0::2], nums[1::2]))


def describe(feature) -> dict:
    """Bir feature'ın birleştirme için gereken özet bilgisi.

    Döner: `kind`, `gml_id`, `uuid` ve türe göre `designator` / `type` /
    `position` / rota segmenti alanları. Doğal anahtar hesaplamaları
    (`override.py`) ve antimeridyen bölme (`antimeridian.py`) bu özeti kullanır.
    """
    kind = local(feature.tag)
    ts = time_slice(feature)
    info = {
        "kind": kind,
        "gml_id": gml_id_of(feature),
        "uuid": uuid_of(feature),
    }

    if kind in POINT_FEATURES or kind in EQUIPMENT_FEATURES:
        info["designator"] = text_of(ts, "designator")
        info["type"] = text_of(ts, "type")
        info["position"] = position_of(feature)

    elif kind == "Route":
        info["designator"] = "".join(filter(None, (
            text_of(ts, "designatorPrefix"),
            text_of(ts, "designatorSecondLetter"),
            text_of(ts, "designatorNumber"),
            text_of(ts, "multipleIdentifier"),
        ))) or text_of(ts, "name")
        info["location_designator"] = text_of(ts, "locationDesignator")

    elif kind == "RouteSegment":
        start_uuid, start_tag = endpoint_ref(ts, "start")
        end_uuid, end_tag = endpoint_ref(ts, "end")
        info.update({
            "start_uuid": start_uuid, "start_tag": start_tag,
            "end_uuid": end_uuid, "end_tag": end_tag,
            "route_uuid": href_of(ts.find(A + "routeFormed")) if ts is not None else None,
            "positions": curve_positions(ts),
        })

    return info
