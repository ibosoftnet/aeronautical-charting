"""ChangeOverPoint (COP) yazıcı.

XSD sırası (`ChangeOverPointPropertyGroup` + TimeSlice'ın `extension`'ı):
  distance, <konum choice (6 seçenek)>, applicableRoutePortion,
  annotation, extension

`RoutePortion` sırası:
  start_*, intermediatePoint_*, referencedRoute, end_*, annotation

Gerekçeler ve ölçümler: `docs/AIXM_ChangeOverPoint_Attributes.md` §7.

İki karar bu modülde görünür hale gelir:

1. **Konum yazılmaz.** `location_*` choice'ının tamamı opsiyoneldir ve AIP
   TÜRKİYE ENR 3.1, COP'un koordinatını yayımlamaz — yalnızca iki VOR'a olan
   DME mesafelerini verir. Koordinat hesaplayıp yazmak, kaynağın söylemediği
   bir şeyi söylemek olurdu. Konum, `distance` + `RoutePortion` üçlüsüyle
   zaten tek anlamlı biçimde tariflidir ("A4 üzerinde, BUK'tan 80 NM").

2. **İkinci mesafe extension'a yazılır.** Çekirdek AIXM 5.2'de `distance`
   TEKİLDİR ve yalnızca `RoutePortion.start`'tan ölçülür; `end`'den ölçülen
   tamamlayıcı mesafe için alan yoktur (XSD'den doğrulandı). Oysa haritada
   COP sembolünde her iki VOR'un da DME değeri gösterilir. Bu yüzden ikinci
   mesafe, AIXM'in kendi resmi genişletme mekanizmasıyla
   (`AbstractChangeOverPointExtension` ikame grubu) taşınır.
"""

import xml.etree.ElementTree as ET

from .writer import NS_GML, aixm, ibosoftais, q, sub, xlink_ref

#: Mesafelerin birimi — kaynak alan adı da (`*_mesafe_nm`) NM diyor.
#: "DME" bir uom DEĞİLDİR; mesafenin DME ile okunduğu, referans alınan
#: navaid'in tipinden ima edilir (bkz. doküman §3).
UOM = "NM"


def write(builder, log, gml_id, feature_uuid, *, distance=None,
          start_navaid_uuid=None, route_uuid=None, end_navaid_uuid=None,
          distance_from_end=None):
    """Tek bir ChangeOverPoint feature'ı yazar.

    distance          : `RoutePortion.start`'tan (VOR 1) COP'a mesafe — çekirdek alan
    distance_from_end : `RoutePortion.end`'den (VOR 2) COP'a mesafe — extension alanı
    """
    ts = builder.add_feature("ChangeOverPoint", gml_id, feature_uuid)

    if distance is None:
        # Kaynakta ilk mesafe yoksa feature yine yazılır: rota aralığı
        # (hangi iki VOR arasında) tek başına da bilgidir. Sessiz geçilmez.
        log.warning("ChangeOverPoint", gml_id, "distance", None,
                    "cop_ilk_mesafe_kaynakta_yok")
    else:
        sub(ts, aixm("distance"), _number(distance), uom=UOM)

    # location_* BİLİNÇLİ olarak yazılmaz — modül docstring'i (1).

    portion = ET.SubElement(ts, aixm("applicableRoutePortion"))
    rp = ET.SubElement(portion, aixm("RoutePortion"))
    rp.set(q(NS_GML, "id"), gml_id + "_RP")
    # intermediatePoint_* yazılmaz: yalnızca rota dallanıyorsa gerekir ve
    # COP kaynağında dallanma bilgisi yok.
    if start_navaid_uuid:
        xlink_ref(rp, aixm("start_navaidSystem"), start_navaid_uuid)
    if route_uuid:
        xlink_ref(rp, aixm("referencedRoute"), route_uuid)
    if end_navaid_uuid:
        xlink_ref(rp, aixm("end_navaidSystem"), end_navaid_uuid)

    if distance_from_end is not None:
        extension = ET.SubElement(ts, aixm("extension"))
        cop_ext = ET.SubElement(extension,
                                ibosoftais("ChangeOverPointExtension"))
        # `AbstractExtensionType` -> `AbstractAIXMObjectType`; orada
        # `gml:id` use="required" (resmi XSD'den doğrulandı).
        cop_ext.set(q(NS_GML, "id"), gml_id + "_EXT")
        sub(cop_ext, ibosoftais("distanceFromEnd"),
            _number(distance_from_end), uom=UOM)
    else:
        log.warning("ChangeOverPoint", gml_id, "distanceFromEnd", None,
                    "cop_ikinci_mesafe_kaynakta_yok")

    return ts


def _number(value):
    """80.0 → "80" ; 79.5 → "79.5" — gereksiz ondalık kuyruğu yazılmaz."""
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)
