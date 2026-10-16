"""ATS birleştiricisinin AIXM 5.2 okuyucusu.

Genel okuma fonksiyonları `data_build_common.aixm_reader`'dadır; burada ATS'ye
özgü olanlar durur. Bu modül birleştirme aşamasının (2A) tek XML okuma yeridir. Kaynak dosyalar
1. aşamada üretilmiş, XSD'ye karşı doğrulanmış AIXM 5.2 mesajlarıdır:
`message:AIXMBasicMessage` → `message:hasMember` → `aixm:<Feature>` →
`gml:identifier` + `aixm:timeSlice` → `aixm:<Feature>TimeSlice`.

Bellek: EAD-SDO dosyası ~461 MB / 274.933 feature. Bu yüzden her şey akış
(streaming) modunda okunur; işlenen eleman hemen bellekten atılır.
"""

# Kaynaktan bağımsız temel okuyucu ortak pakettedir; bu modül onu yeniden
# dışa verir ve üzerine ATS'ye özgü yardımcıları ekler (rota uç noktaları,
# RoutePortion, `describe`). Diğer ATS modülleri `rdr.<ad>` biçimini korur.
from data_build_common.aixm_reader import (  # noqa: F401
    A, G, HAS_MEMBER, I, M, NS_AIXM, NS_GML, NS_IBOSOFTAIS, NS_MESSAGE,
    NS_XLINK, X, feature_of, gml_id_of, href_of, iter_members, local,
    text_of, time_slice, uuid_of)
from data_build_common import provenance

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


def route_portion_refs(ts):
    """ChangeOverPoint'in `RoutePortion` referansları → dict.

    Döner: `{"start_uuid", "start_tag", "end_uuid", "end_tag", "route_uuid"}`.

    `RoutePortion` bir AIXM **Object**'tir (Feature değil) ve `ChangeOverPoint`'in
    TimeSlice'ı içine gömülüdür; bu yüzden referanslar `endpoint_ref`'in baktığı
    yerden bir seviye daha derindedir:

        ChangeOverPointTimeSlice
          └─ applicableRoutePortion
               └─ RoutePortion
                    ├─ start_*          (6 seçenekli choice)
                    ├─ referencedRoute
                    └─ end_*            (6 seçenekli choice)

    Uç noktalar `start_navaidSystem`, `start_fixDesignatedPoint`, … olabildiği
    için eleman adı SABİT DEĞİLDİR; bu yüzden tam ada değil `start_`/`end_`
    ÖNEKİNE bakılır — choice'ın hangi dalı kullanılmış olursa olsun çalışır.
    `tag` alanı hangi dalın kullanıldığını taşır (`endpoint_ref` ile aynı desen).
    """
    out = {"start_uuid": None, "start_tag": None,
           "end_uuid": None, "end_tag": None, "route_uuid": None,
           "intermediate_uuid": None, "intermediate_tag": None}
    if ts is None:
        return out
    portion = ts.find(A + "applicableRoutePortion")
    portion = portion.find(A + "RoutePortion") if portion is not None else None
    if portion is None:
        return out

    for child in portion:
        name = local(child.tag)
        uid = href_of(child)
        if uid is None:
            continue
        if name == "referencedRoute":
            out["route_uuid"] = uid
        elif name.startswith("start_"):
            out["start_uuid"], out["start_tag"] = uid, name
        elif name.startswith("end_"):
            out["end_uuid"], out["end_tag"] = uid, name
        elif name.startswith("intermediatePoint_"):
            # Doğal anahtara GİRMEZ (kimliğin parçası değil), ama 2B'de
            # geometri kurulurken ŞARTTIR: rota dallanıyorsa yolun hangi
            # koldan geçtiğini yalnızca bu alan söyler.
            out["intermediate_uuid"], out["intermediate_tag"] = uid, name
    return out


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

    Döner: `kind`, `gml_id`, `uuid`, `originator` ve türe göre `designator` / `type` /
    `position` / rota segmenti alanları. Doğal anahtar hesaplamaları
    (`override.py`) ve antimeridyen bölme (`antimeridian.py`) bu özeti kullanır.
    """
    kind = local(feature.tag)
    ts = time_slice(feature)
    info = {
        "kind": kind,
        "gml_id": gml_id_of(feature),
        "uuid": uuid_of(feature),
        # Originator feature'ın KENDİ provenance kutusundan okunur (ayrı bir
        # yan dosya yok). Kutu yoksa `ProvenanceError` — build durur, varsayılan
        # değer atanmaz. Yazılmamış originator "" olur: doğal anahtarların
        # karşılaştırdığı değer önceki yan dosya düzeninde de "" idi.
        "originator": provenance.require(feature)["data_originator"] or "",
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

    elif kind == "ChangeOverPoint":
        # Referanslar gömülü `RoutePortion` nesnesinin içindedir — bkz.
        # `route_portion_refs`. Doğal anahtar bunlardan türetilir (keys.py).
        info.update(route_portion_refs(ts))

    return info
