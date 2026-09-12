"""Feature'ların kaynaktan bağımsız "doğal anahtar" alanları.

Kaynakların UUID uzayları birbirinden bağımsızdır (her üretici kendi
deterministik UUID5'ini üretir), bu yüzden kaynaklar arası karşılaştırma
UUID ile yapılamaz. Hem override eşleştirmesi hem iptal (exclude) kuralları bu
modülün ürettiği alanları kullanır — böylece iki mekanizma aynı sözlüğü konuşur.

Rota segmentinin uç noktaları da UUID ile referans verildiği için, karşılaştırma
uç noktaların **designator**'ları üzerinden yapılır; bunun için kaynağın kendi
`uuid → designator` indeksi gerekir (`build_index`).
"""

from .aixm_reader import EQUIPMENT_FEATURES, POINT_FEATURES

# Feature adı → katman adı. Katman adı, çakışma çözümünün ortak dilidir:
# `config.json`'daki `prefer_base_on_match_layers`, iptal kurallarının `layer`
# alanı ve `override.prefers_base()` hep bu adı konuşur.
#
# Not: buradaki her ad bir GeoPackage katmanına karşılık GELMEK ZORUNDA DEĞİLDİR
# — `routes` de burada vardır ama GeoPackage'da `routes` katmanı yoktur.
LAYER_OF = {
    "DesignatedPoint": "designatedPoints",
    "Navaid": "navaids",
    "RouteSegment": "routeSegments",
    "Route": "routes",
    # COP, kaynaklar arası çakışmaya GİREBİLEN bir feature'dır: aynı fiziksel
    # geçiş noktasını iki kaynak da yayımlayabilir. Bugün yalnızca LT üretiyor
    # (ölçüldü: EAD-SDO 0, Jeppesen 0, TRNC 0), ama katman adı burada tanımlı
    # olduğu için davranış config'den ayarlanabilir — diğer katmanlarla aynı
    # şekilde (kullanıcı kararı).
    "ChangeOverPoint": "changeOverPoints",
}
for _name in EQUIPMENT_FEATURES:
    LAYER_OF[_name] = "navaidComponents"


def layer_of(kind: str) -> str | None:
    return LAYER_OF.get(kind)


def natural_fields(info: dict, originator: str | None, index: dict) -> dict:
    """Bir feature'ın karşılaştırılabilir alanları.

    `index`: aynı kaynağın `uuid → {"designator", "type", "kind"}` sözlüğü;
    rota segmentinin uç nokta ve rota referanslarını çözmek için kullanılır.
    """
    kind = info["kind"]
    fields = {"layer": layer_of(kind), "kind": kind, "originator": originator}

    if kind in POINT_FEATURES or kind in EQUIPMENT_FEATURES:
        fields["designator"] = info.get("designator")
        fields["type"] = info.get("type")
        position = info.get("position")
        if position:
            # Konum, designator'ı olmayan noktalar için ayırt edici alan.
            fields["position"] = (round(position[0], 6), round(position[1], 6))

    elif kind == "Route":
        fields["designator"] = info.get("designator")
        fields["locationDesignator"] = info.get("location_designator")

    elif kind == "RouteSegment":
        route = index.get(info.get("route_uuid") or "", {})
        start = index.get(info.get("start_uuid") or "", {})
        end = index.get(info.get("end_uuid") or "", {})
        fields["route"] = route.get("designator")
        fields["routeLocationDesignator"] = route.get("location_designator")
        fields["start"] = start.get("designator")
        fields["end"] = end.get("designator")

    elif kind == "ChangeOverPoint":
        # RouteSegment ile aynı desen: referanslar UUID, karşılaştırma
        # designator üzerinden. Uçlar Navaid ya da DesignatedPoint olabilir;
        # `index` ikisini de taşır (`POINT_FEATURES`).
        route = index.get(info.get("route_uuid") or "", {})
        start = index.get(info.get("start_uuid") or "", {})
        end = index.get(info.get("end_uuid") or "", {})
        fields["route"] = route.get("designator")
        fields["routeLocationDesignator"] = route.get("location_designator")
        fields["start"] = start.get("designator")
        fields["end"] = end.get("designator")

    return fields


def override_key(fields: dict):
    """Override eşleştirmesinde kullanılan anahtar (yoksa None).

    Plandaki kurallar:
      * RouteSegment  → rota kimliği + start/end kombinasyonu + originator
      * DesignatedPoint → designator + originator
      * Navaid        → type + ident + originator
      * ChangeOverPoint → rota kimliği + SIRASIZ uç çifti + originator
    `navaidComponents` ve `Route` override edilmez (ek kaynaklarda ekipman
    ayrıntısı yok; Route'lar segmentleriyle birlikte gelir).
    """
    layer = fields.get("layer")
    originator = fields.get("originator")

    if layer == "routeSegments":
        if not (fields.get("start") and fields.get("end")):
            return None          # uç noktası çözülmemiş segment eşleştirilemez
        return ("routeSegments", fields.get("route"),
                fields["start"], fields["end"], originator)

    if layer == "changeOverPoints":
        if not (fields.get("start") and fields.get("end")):
            return None          # ucu çözülmemiş COP eşleştirilemez
        # Uç çifti SIRALANIR (kullanıcı kararı): iki VOR arasında geçiş noktası
        # fizikî olarak tektir; bir kaynak BUK→SIV, diğeri SIV→BUK yazmışsa
        # bunlar AYNI noktadır ve eşleşmelidir. RouteSegment'te sıra korunur
        # çünkü orada yön kaydın kendi anlamının parçasıdır — COP'ta değildir.
        return ("changeOverPoints", fields.get("route"),
                *sorted((fields["start"], fields["end"])), originator)

    if layer == "designatedPoints":
        if not fields.get("designator"):
            return None
        return ("designatedPoints", fields["designator"], originator)

    if layer == "navaids":
        if not fields.get("designator"):
            return None
        return ("navaids", fields.get("type"), fields["designator"], originator)

    return None
