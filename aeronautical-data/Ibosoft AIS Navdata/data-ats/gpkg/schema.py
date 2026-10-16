"""AŞAMA 2B — GeoPackage şeması: 4 katmanın sütun listeleri ve DDL.

Sütun adlandırma (plan kararı):
  * `<katman>_<AIXM öznitelik adı, camelCase>`
  * ölçü birimi → `<alan>Uom`, dikey referans → `<alan>Reference`
  * `annotation` → 4 sabit sütun (purpose değerlerine göre), katman ÖNEKİSİZ
  * provenance (`data_provider`/`data_originator`/`data_effectivity`) ve
    `aixm_*` (kimlik + TimeSlice/feature tabanı) de katman ÖNEKİSİZ — bu
    alanlar her katmanda birebir aynı yapıyı taşır (kullanıcı kararı)

`points` katmanı YOKTUR: AIXM `Point` bağımsız bir feature değildir
(`gml:Point` substitution group'unda, `AbstractAIXMFeature` değil), bu yüzden
bağımsız satırları olan bir katman kurulamaz — kullanıcı kararıyla iptal edildi.
"""

from data_build_common import gpkg_writer
from data_build_common.aixm_fields import (  # noqa: F401
    ANNOTATION_COLUMNS, ANNOTATION_PURPOSES, BASE_COLUMNS, IDENTITY_COLUMNS,
    INTEGER_BASE_COLUMNS, PROVENANCE_COLUMNS)
from data_build_common.gpkg_writer import (  # noqa: F401
    SRS_ID, geometry_envelope, linestring_blob, point_blob)

#: `annotation*`, `data_*` (provenance) ve `aixm_*` (kimlik + TimeSlice/feature
#: tabanı) aileleri katman öneksizdir ve iki projede de aynıdır: tanımları
#: `data_build_common.aixm_fields`'tadır. Her katmanın sonunda
#: `IDENTITY_COLUMNS + BASE_COLUMNS` gelir.
AIXM_COLUMNS = IDENTITY_COLUMNS + BASE_COLUMNS

#: `atsStatus_*` — noktanın ATS rota ağındaki rolünün TÜRETİLMİŞ özeti.
#: Yalnızca nokta katmanlarında (`designatedPoints`, `navaids`) bulunur;
#: `navaidComponents` rota uç noktası olarak çözümlenmez, orada anlamsızdır.
#: AIXM'de karşılığı YOKTUR — `routeSegments` tablosu yazıldıktan SONRA ondan
#: türetilir (bkz. build_common_ats.py `compute_ats_status`). Amaç: QGIS'te
#: "yalnızca rota noktaları" gibi filtreleri sanal katman kurmadan, mevcut
#: RTree/B-tree indekslerini bozmadan yapabilmek.
#: Katman öneki taşımazlar (annotation/provenance ile aynı kural).
#:
#: Aile İKİYE ayrılır (emsal: `NAVAID_SYMBOLOGY_COLUMNS` /
#: `NAVAID_SYMBOLOGY_COMPONENT_ONLY_COLUMNS`):
#:   * `ATS_STATUS_ASSOCIATED_COLUMNS` — `designatedPoints`, `navaids` VE
#:     `changeOverPoints`'te ortak yedili (kullanıcı kararı).
#:   * Geri kalanı yalnızca NOKTA katmanlarında. `isElementOfRouteSegment`
#:     COP'ta anlamsız olurdu (COP tanımı gereği bir rota aralığına bağlıdır,
#:     kapı hep 1 olurdu); `reportingAssociation` ve `depiction*` ailesi ise
#:     NOKTA sembolü seçmek içindir — COP'un sembolü `copSymbology_*`'tan gelir.
ATS_STATUS_ASSOCIATED_COLUMNS = [
    # CodeLevelType degerleri, dort BAGIMSIZ bayrak olarak: her biri
    # "iliskili segmentlerden EN AZ BIRI bu seviyede mi". Birbirlerini
    # dislamazlar. `Other` yalnizca gercek `OTHER`/`OTHER:xxx` degeri varsa
    # 1 olur — level tasimayan segmentler icin fallback DEGILDIR.
    "atsStatus_associatedLevelUpper",      # BOOLEAN
    "atsStatus_associatedLevelLower",      # BOOLEAN
    "atsStatus_associatedLevelBoth",       # BOOLEAN
    "atsStatus_associatedLevelOther",      # BOOLEAN — gercek OTHER/OTHER:xxx
    # CodeRouteType degerleri, uc BAGIMSIZ bayrak olarak: her biri
    # "iliskili segmentlerden EN AZ BIRI bu tipte bir rotaya ait mi".
    # Kaynak sutun `route_type` — RouteSegment'in DEGIL, segmentin
    # bagli oldugu Route feature'inin alanidir. `Other` yalnizca gercek
    # `OTHER`/`OTHER:xxx` degeri varsa 1 olur; tip tasimayan segment
    # hicbir bayraga katki vermez.
    "atsStatus_associatedTypeAts",         # BOOLEAN — route_type = ATS
    "atsStatus_associatedTypeNat",         # BOOLEAN — route_type = NAT
    "atsStatus_associatedTypeOther",       # BOOLEAN — gercek OTHER/OTHER:xxx
]

#: Tam aile — sutun SIRASI degismedi: kapi alani basta, ortak yedili ortada.
ATS_STATUS_COLUMNS = [
    "atsStatus_isElementOfRouteSegment",   # BOOLEAN — kapı alanı
] + ATS_STATUS_ASSOCIATED_COLUMNS + [
    "atsStatus_reportingAssociation",      # JSON: [{segmentId, role, reportingATC}]
    "atsStatus_depictionCompulsory",       # BOOLEAN — reportingATC = COMPULSORY
    # Harita gosterimi icin TURETILMIS siniflandirmalar. Diger alanlar gibi
    # KAPIYA BAGLIDIRLAR: nokta rota elemani degilse NULL kalirlar — bir
    # noktanin rota gosterim sinifi ancak bir ATS rotasinin parcasiysa
    # anlamlidir (kullanici karari, bkz. compute_ats_status).
    "atsStatus_depictionNav",              # CONV / RNAVFlyBy / RNAVFlyOver / OTHER
    "atsStatus_depictionSIGPointBasicFunc",  # NAVAID / VFR_REP / WPT / INT / OTHER
    # `depictionNav` + `depictionCompulsory` bileskesi. Tek sutunda hem
    # seyrusefer sinifini hem raporlama zorunlulugunu tasir; QGIS'te tek
    # kategorize alanindan sembol uretmek icin (kullanici karari).
    "atsStatus_depictionNavAndREP",        # <depictionNav>_<Comp|NonComp>
]

#: `atsStatus_depictionNav` enum'u — seyrusefer gosterim sinifi.
DEPICTION_NAV = ("CONV", "RNAVFlyBy", "RNAVFlyOver", "OTHER")

#: `atsStatus_depictionSIGPointBasicFunc` enum'u — onemli nokta temel islevi.
DEPICTION_SIG_POINT = ("NAVAID", "VFR_REP", "WPT", "INT", "OTHER")

#: `atsStatus_depictionNavAndREP` enum'u — `DEPICTION_NAV` degerlerinin
#: `_Comp` / `_NonComp` sonekiyle carpimi. Elle yazilmaz, turetilir ki
#: `DEPICTION_NAV` degisince burasi da otomatik guncellensin.
DEPICTION_NAV_AND_REP = tuple(
    f"{nav}_{suffix}" for suffix in ("Comp", "NonComp") for nav in DEPICTION_NAV)

#: `navaidLabeling_*` — harita etiketi icin TURETILMIS alanlar. AIXM'de
#: karsiligi YOKTUR: AIXM neyin var oldugunu soyler, neyin etiketlenecegini
#: soylemez. Ayrica AIXM'de frekans/kanal Navaid feature'inda degil BAGLI
#: EKIPMANDA durur (`NavaidPropertyGroup`'ta `frequency`/`channel` yok), oysa
#: harita etiketi navaid duzeyinde cizilir — bu yuzden `navaids` satirlarindaki
#: degerler bilesenlerden toplanir (bkz. gpkg/navaid_labeling.py).
#:
#: `have*` bayraklari TIP BAZLIDIR: alan o tip icin gecerliyse deger bos olsa
#: bile 1 kalir ("tanimli fakat bossa true" — kullanici karari). `name`/`ident`
#: bayragi YOKTUR: bu ikisi `NavaidPropertyGroup` ve
#: `NavaidEquipmentPropertyGroup`'ta ortaktir, her tipte tanimlidir.
#:
#: Katman oneki tasimazlar (annotation/provenance/atsStatus ile ayni kural).
NAVAID_LABELING_COLUMNS = [
    "navaidLabeling_name",
    "navaidLabeling_ident",
    "navaidLabeling_freq",          # REAL — NDB kHz, diger her tip MHz
    "navaidLabeling_freqUom",       # "KHZ" | "MHZ"
    "navaidLabeling_channel",       # TEXT — "40X", "18Y", MLS icin "500"
    "navaidLabeling_dmeElev",       # REAL
    "navaidLabeling_dmeElevUom",    # kaynaktaki birim (FT/M) korunur
    # Etiket uretimini QGIS ifadesinden buildera tasiyan iki alan:
    "navaidLabeling_type",          # kartografik tip kisaltmasi (VOR DME, GP, OM)
    "navaidLabeling_morseCode",     # ident'in ITU mors karsiligi
]


#: AIXM `AbstractNavaidEquipment` ikame grubunun 11 SOMUT alt-turu ve her
#: birinin KENDINE OZGU alanlari (ortak taban `NavaidEquipmentPropertyGroup`
#: buraya DAHIL DEGILDIR). XSD'den birebir dogrulandi:
#: `docs/AIXM_Features_annotated.xsd` icindeki `<group name="<AltTur>PropertyGroup">`
#: tanimlari; `docs/aixm-point-types/AIXM_NavaidEquipment_Attributes.md` §2.1-2.11
#: ile ortusuyor.
#:
#: Ayni alan adi birden fazla alt-turde gecebilir (`frequency` 6, `channel` 3,
#: `type` 3 alt-turde) ve bunlarin bir kismi FARKLI enum tasir — `type` icin
#: CodeVORType/CodeDMEType/CodeMLSAzimuthType, `channel` icin
#: CodeDMEChannelType/CodeTACANChannelType/CodeMLSChannelType. Bu yuzden her
#: alt-tur KENDI sutununu alir: `navaidComponents_<AltTur>_<alan>` (kullanici
#: karari). Boylece tek sutunda cakisan enum sorunu ortadan kalkar ve her sutun
#: kendi dogrulama kuralini alabilir.
#:
#: `_uom` soneki: deger+birim tasiyan alanlar icin ayrica `<alan>Uom` sutunu
#: uretilir (bkz. EQUIPMENT_VALUE_UOM).
EQUIPMENT_SUBTYPE_FIELDS = {
    "VOR": ("type", "frequency", "zeroBearingDirection", "declination"),
    "DME": ("type", "channel", "displace", "tuningFrequencyVHF"),
    "TACAN": ("channel", "declination", "tuningFrequencyVHF"),
    "Localizer": ("frequency", "magneticBearing", "trueBearing", "declination",
                  "widthCourse", "backCourseUsable", "signalPerformance",
                  "courseQuality", "integrityLevel"),
    "Glidepath": ("frequency", "slope", "rdh", "signalPerformance",
                  "courseQuality", "integrityLevel"),
    "MarkerBeacon": ("class", "frequency", "axisBearing", "auralMorseCode"),
    "NDB": ("frequency", "class", "emissionBand"),
    "SDF": ("frequency", "magneticBearing", "trueBearing"),
    "Azimuth": ("type", "channel", "trueBearing", "magneticBearing",
                "angleProportionalLeft", "angleProportionalRight",
                "angleCoverLeft", "angleCoverRight"),
    "Elevation": ("angleNominal", "angleMinimum", "angleSpan"),
    "DirectionFinder": ("doppler",),
}

#: Alt-tur alanlarindan deger+birim ciftini `<alan>` + `<alan>Uom` olarak
#: yazilacaklar. (AIXM'de `uom` niteligi tasiyan alanlar.)
EQUIPMENT_VALUE_UOM = frozenset({"frequency", "displace", "tuningFrequencyVHF",
                                 "rdh"})

#: Sayisal olarak saklanacak alt-tur alanlari (digerleri TEXT).
EQUIPMENT_NUMERIC = frozenset({
    "declination", "magneticBearing", "trueBearing", "widthCourse", "slope",
    "axisBearing", "angleProportionalLeft", "angleProportionalRight",
    "angleCoverLeft", "angleCoverRight", "angleNominal", "angleMinimum",
    "angleSpan",
})

#: Ortak taban — 11 alt-turde de AYNI (`NavaidEquipmentPropertyGroup`).
#: Alt-tur oneki ALMAZ. `authority` (0..∞, Organisation agaci) kullanici
#: onayiyla kapsam disidir; `location` asagida alt alanlarina acilir.
EQUIPMENT_COMMON_FIELDS = (
    "designator", "name", "emissionClass", "mobile", "magneticVariation",
    "dateMagneticVariation", "flightChecked",
    "locationElevation", "locationElevationUom", "locationGeoidUndulation",
    "locationVerticalDatum", "locationHorizontalAccuracy",
    "locationHorizontalAccuracyUom",
    "monitoring", "availability",          # JSON liste
)

#: `NavaidComponent`'in (ince Object) kendi alanlari — ekipmana ait degil.
NAVAID_COMPONENT_OWN_FIELDS = ("collocationGroup", "markerPosition",
                               "providesNavigableLocation")


def equipment_column(subtype: str, field: str) -> str:
    """('Glidepath', 'slope') → 'navaidComponents_Glidepath_slope'."""
    return f"navaidComponents_{subtype}_{field}"


def _equipment_subtype_columns():
    """Alt-tur alanlarindan sutun listesi URETIR — elle yazilmaz.

    `EQUIPMENT_SUBTYPE_FIELDS` degisirse sutun listesi kendiliginden guncellenir.
    """
    columns = []
    for subtype, fields in EQUIPMENT_SUBTYPE_FIELDS.items():
        for field in fields:
            columns.append(equipment_column(subtype, field))
            if field in EQUIPMENT_VALUE_UOM:
                columns.append(equipment_column(subtype, field + "Uom"))
    return columns


#: Navaid → bilesen TERS bagi. Her alt-tur icin bir sutun; deger, o navaid'in
#: ilgili tipteki bilesenlerinin `navaidComponents.id` listesidir (virgullu),
#: bilesen yoksa NULL. Liste olmasinin sebebi: bir navaid ayni tipten birden
#: fazla bilesen tasiyabiliyor — olculdu, 31 ILS'te ikiser MarkerBeacon var
#: (OUTER + MIDDLE). Katman oneki tasimaz.
ASSOCIATED_COMPONENT_COLUMNS = [
    f"associatedComponent_{subtype}" for subtype in EQUIPMENT_SUBTYPE_FIELDS]

#: Bilesen → navaid bagi. `navaidId` (tek FK) YERINE gecer: bir ekipman birden
#: fazla Navaid tarafindan paylasilabiliyor (olculdu: 275 ekipman 2-7 navaid'e
#: ait, 230 DME + 45 TACAN) ve tek FK bunlardan yalnizca birini kaydediyordu.
#: Iki sutun AYNI SIRADA hizalidir: n. id'nin tipi n. tiptir.
ASSOCIATED_NAVAID_COLUMNS = ["associatedNavaid", "associatedNavaidType"]

#: `navaidSymbology_*` — sembol GEOMETRISI icin turetilmis alanlar.
#: `navaidLabeling_*`'tan AYRIDIR: o etiket METNI uretir, bu sembolun
#: cizimini besler. Katman oneki tasimaz (annotation/provenance/atsStatus/
#: navaidLabeling ile ayni kural).
#:
#: `declination`: pusula gulu (compass rose) sembolunun DONDURME ACISI.
#: Yalnizca VOR/TACAN bilesenlerinin AIXM'de kendi `declination` alani
#: vardir (bkz. EQUIPMENT_SUBTYPE_FIELDS); deger o bilesenin KENDI
#: sutunundan devralinir. `navaids` duzeyinde yalnizca VOR/VOR_DME/TACAN/
#: VORTAC turlerinde doldurulur, digerlerinde NULL kalir (kullanici karari).
#: Hem `navaids` hem `navaidComponents`'te bulunur (bkz. gpkg/navaid_symbology.py).
NAVAID_SYMBOLOGY_COLUMNS = [
    "navaidSymbology_declination",
]

#: `GPAssociatedLOCTrueBrg`: Glidepath sembolu haritada bir HUZME olarak
#: cizilir ve yonu olmalidir, ama `GlidepathPropertyGroup`'ta yon alani
#: YOKTUR. Yon ayni ILS'in Localizer bileseninde durur; bu sutun o degeri
#: Glidepath satirina tasir (bkz. gpkg/navaid_symbology.py). Yalnizca
#: `navaidComponents`'te anlamlidir (Glidepath ancak bilesen duzeyinde var).
NAVAID_SYMBOLOGY_COMPONENT_ONLY_COLUMNS = [
    "navaidSymbology_GPAssociatedLOCTrueBrg",
]


#: `changeOverPoints` — COP'un AIXM referanslarinin COZULMUS hali.
#: Dort referans var: `RoutePortion`'in start/end/intermediatePoint'i ve
#: COP'un kendi `location`'i. Hepsi ayni dort temel alani tasir; UC NOKTALAR
#: ayrica ad ve tip alir (kullanici karari).
#:
#: `Layer` hedefin hangi gpkg katmaninda oldugunu soyler (`navaids` /
#: `designatedPoints`) — satir id'si tek basina belirsiz olurdu, hangi tabloya
#: join edilecegi bilinmeli. `routeSegments_startPoint*` ile ayni desen.
#:
#: `Uuid` semada YENI bir bilgi: bugune kadar iliskiler yalnizca gpkg satir
#: id'si olarak tutuluyordu. Kural: `…Id` = gpkg satir id, `…Uuid` = AIXM
#: `gml:identifier` (kullanici karari, AIXM<->gpkg eslestirmesi icin).
_COP_REFERENCE_FIELDS = ["Layer", "Id", "Uuid", "Designator"]
_COP_ENDPOINT_FIELDS = _COP_REFERENCE_FIELDS + ["Name", "Type"]

#: Bagli Route. IKI aileye ayrilir (kullanici karari):
#:
#:  * `route_*`            — Route'tan DEVRALINAN oznitelikler. `routeSegments`
#:                           katmanindaki `route_*` ailesiyle ayni ad ve ayni
#:                           anlam, boylece iki katman ayni dili konusur.
#:  * `associatedRoute_uuid` — ILISKININ kendisi, yani Route'un kimligi.
#:                           `routeSegments`'te boyle bir sutun yoktur; COP'ta
#:                           kimlik gerektigi icin semanin iliski ailesi olan
#:                           `associated…` altinda durur.
#:
#: `route_uuid` gibi bir ad kullanilmaz — hicbir katmanda `<katman>_uuid`
#: biciminde sutun yok, satirin kendi kimligi her yerde `aixm_uuid`.
ROUTE_INHERITED_COLUMNS = [
    "route_designatorPrefix",
    "route_designatorSecondLetter",
    "route_designatorNumber",
    "route_multipleIdentifier",
    # Route'un adi. `routeSegments`'takiyle BIREBIR ayni ad, boylece iki
    # katmanda ayni QGIS ifadesi calisir.
    "route_name",
    #
    # `designatorSuffix` BILEREK YOK. Gerekce yapisal: AIXM'de bu alan
    # `Route`'un degil `RouteSegment`'in oznitelligidir, dolayisiyla
    # "Route'tan devralinan" bu ailenin uyesi olamaz. Ayrica COP bir
    # `RoutePortion`'a (segment ARALIGINA) baglidir ve aralikta yer alan
    # segmentler farkli suffix degerleri tasiyabilir - tek sutuna
    # indirgenemez (kullanici karari).
]

ASSOCIATED_ROUTE_COLUMNS = ["associatedRoute_uuid"] + ROUTE_INHERITED_COLUMNS

#: Rota araligini olusturan segmentler. AIXM'de COP'un boyle bir alani YOKTUR —
#: rota grafigi yurunerek turetilir (bkz. gpkg/route_portion.py). Ikisi de
#: virgullu liste ve AYNI SIRADA: zincirin start->end sirasi.
ASSOCIATED_ROUTE_SEGMENT_COLUMNS = [
    "associatedRouteSegment_id",      # gpkg satir id'leri
    "associatedRouteSegment_uuid",    # AIXM uuid'leri
]

#: `copSymbology_*` — COP sembolunun cizime hazir hali.
#: QGIS sembolu CIZGI BOYUNCA bir yuzdeyle kaydirdigi icin payda cizginin
#: kendi uzunlugudur; `distanceFromEnd` bu hesaba GIRMEZ.
#: Cizgi uzunlugu ve segment sayisi ayri sutun olarak yazilmaz: birincisini
#: QGIS `length($geometry)` ile, ikincisini `associatedRouteSegment_id`
#: listesinin eleman sayisiyla zaten hesaplar (kullanici karari).
COP_SYMBOLOGY_COLUMNS = [
    "copSymbology_offsetPercent",
]


#: Liste tasiyan sutunlarin ayiricisi.
LIST_SEPARATOR = ","


#: GeoPackage'da BOOLEAN yoktur; 0/1 INTEGER olarak saklanır (GDAL bunu
#: mantıksal alan olarak tanır). Sütun adıyla açıkça listelenir — son ek
#: tahminine bırakmak kırılgan olurdu.
BOOLEAN_COLUMNS = frozenset([
    "atsStatus_isElementOfRouteSegment",
    "atsStatus_associatedLevelUpper",
    "atsStatus_associatedLevelLower",
    "atsStatus_associatedLevelBoth",
    "atsStatus_associatedLevelOther",
    "atsStatus_associatedTypeAts",
    "atsStatus_associatedTypeNat",
    "atsStatus_associatedTypeOther",
    "atsStatus_depictionCompulsory",
])


# ── designatedPoints ────────────────────────────────────────────────────────
DESIGNATED_POINTS = (
    ["designatedPoints_designator", "designatedPoints_type",
     "designatedPoints_name", "designatedPoints_codeICAOCountry",
     "designatedPoints_fix"]                      # JSON: PointReference[]
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + ATS_STATUS_COLUMNS
    + AIXM_COLUMNS
)

# ── navaids ─────────────────────────────────────────────────────────────────
NAVAIDS = (
    ["navaids_type", "navaids_designator", "navaids_name",
     "navaids_flightChecked", "navaids_purpose", "navaids_signalPerformance",
     "navaids_courseQuality", "navaids_integrityLevel",
     "navaids_codeICAOCountry",
     # location → ElevatedPoint alt alanları (geometri ayrı sütunda)
     "navaids_locationElevation", "navaids_locationElevationUom",
     "navaids_locationGeoidUndulation", "navaids_locationVerticalDatum",
     "navaids_locationHorizontalAccuracy", "navaids_locationHorizontalAccuracyUom",
     "navaids_availability"]                      # JSON: NavaidOperationalStatus[]
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + ATS_STATUS_COLUMNS
    + NAVAID_LABELING_COLUMNS
    + NAVAID_SYMBOLOGY_COLUMNS
    + ASSOCIATED_COMPONENT_COLUMNS
    + AIXM_COLUMNS
)

# ── navaidComponents ────────────────────────────────────────────────────────
# NavaidComponent (ince Object) + bağlı AbstractNavaidEquipment tek satırda.
#
# Sütun adlandırması (kullanıcı kararı):
#   * ortak taban ve NavaidComponent'in kendi alanları → `navaidComponents_<alan>`
#   * alt-türe özgü her alan  → `navaidComponents_<AltTür>_<alan>`
# Alt-tür sütunları `EQUIPMENT_SUBTYPE_FIELDS`'ten TÜRETİLİR, elle yazılmaz.
# Tablo bilinçli olarak seyrektir: her satırda yalnızca kendi alt-türünün
# sütunları dolar. Karşılığında hangi alanın hangi alt-türe ait olduğu sütun
# adından okunur ve çakışan enum'lar (`type`, `class`, `channel`) ayrışır.
NAVAID_COMPONENTS = (
    ["navaidComponents_equipmentType"]           # 11 somut alt-türden hangisi
    + ASSOCIATED_NAVAID_COLUMNS                  # ebeveyn bağı (liste)
    + [f"navaidComponents_{f}" for f in NAVAID_COMPONENT_OWN_FIELDS]
    + [f"navaidComponents_{f}" for f in EQUIPMENT_COMMON_FIELDS]
    + _equipment_subtype_columns()               # <AltTür>_<alan>
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + NAVAID_LABELING_COLUMNS
    + NAVAID_SYMBOLOGY_COLUMNS
    + NAVAID_SYMBOLOGY_COMPONENT_ONLY_COLUMNS
    + AIXM_COLUMNS
)

# ── routeSegments ───────────────────────────────────────────────────────────
_SEGMENT_POINT_FIELDS = [
    "PointLayer", "PointId", "PointDesignator",   # çözülen referans
    "ReportingATC", "FlyOver", "Waypoint", "RadarGuidance",
    "FacilityMakeup",                             # JSON: PointReference[]
    "RoleFreeFlight", "RoleRVSM",
    "TurnRadius", "TurnRadiusUom", "RoleMilitaryTraining",
]

ROUTE_SEGMENTS = (
    ["routeSegments_level",
     "routeSegments_upperLimit", "routeSegments_upperLimitUom",
     "routeSegments_upperLimitReference",
     "routeSegments_lowerLimit", "routeSegments_lowerLimitUom",
     "routeSegments_lowerLimitReference",
     "routeSegments_minimumObstacleClearanceAltitude",
     "routeSegments_minimumObstacleClearanceAltitudeUom",
     "routeSegments_pathType",
     "routeSegments_trueTrack", "routeSegments_magneticTrack",
     "routeSegments_reverseTrueTrack", "routeSegments_reverseMagneticTrack",
     "routeSegments_length", "routeSegments_lengthUom",
     "routeSegments_widthLeft", "routeSegments_widthLeftUom",
     "routeSegments_widthRight", "routeSegments_widthRightUom",
     "routeSegments_turnDirection", "routeSegments_signalGap",
     "routeSegments_minimumEnrouteAltitude",      # JSON: AltitudeIndication[]
     "routeSegments_minimumCrossingAtEnd", "routeSegments_minimumCrossingAtEndUom",
     "routeSegments_minimumCrossingAtEndReference",
     "routeSegments_maximumCrossingAtEnd", "routeSegments_maximumCrossingAtEndUom",
     "routeSegments_maximumCrossingAtEndReference",
     "routeSegments_designatorSuffix"]
    + [f"routeSegments_start{f}" for f in _SEGMENT_POINT_FIELDS]
    + [f"routeSegments_end{f}" for f in _SEGMENT_POINT_FIELDS]
    + ["routeSegments_availability",              # JSON
       "routeSegments_cardinalDirectionLeft", "routeSegments_cardinalDirectionRight",
       "routeSegments_aircraftCapability",        # JSON
       "routeSegments_airspaceClass",             # JSON
       "routeSegments_designCriteria",            # virgülle ayrılmış
       # Route'tan devralınan alanlar (Route'un geometrisi yok, ayrı katman
       # değil). `route_` öneki BİLİNÇLİ OLARAK `routeSegments_`'ten farklıdır:
       # bu alanlar RouteSegment'in değil, bağlı Route feature'ının alanlarıdır
       # (kullanıcı düzeltmesi — aynı önek iki farklı kaynağı ayırt edilemez
       # kılıyordu).
       "route_designatorPrefix", "route_designatorSecondLetter",
       "route_designatorNumber", "route_multipleIdentifier",
       "route_locationDesignator", "route_name",
       "route_type", "route_flightRule",
       "route_internationalUse", "route_militaryUse",
       "route_militaryTrainingType"]
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + AIXM_COLUMNS
)

# ── changeOverPoints ────────────────────────────────────────────────────────
# COP'un geometrisi KENDI KONUMU DEGILDIR: AIP, COP'un koordinatini
# yayimlamiyor (bkz. docs/AIXM_ChangeOverPoint_Attributes.md §7.2). Onun
# yerine COP'un gecerli oldugu ROTA ARALIGI cizgi olarak yazilir ve cizgi
# `RoutePortion.start` ucundan baslar; QGIS sembolu bu cizgi boyunca
# `copSymbology_offsetPercent` kadar kaydirarak dogru yere koyar.
# Yon kritiktir: ters yonde bir cizgi sembolu yanlis uctan olcer.
CHANGE_OVER_POINTS = (
    ["changeOverPoints_distance", "changeOverPoints_distanceUom",
     "changeOverPoints_distanceFromEnd", "changeOverPoints_distanceFromEndUom"]
    + [f"changeOverPoints_startPoint{f}" for f in _COP_ENDPOINT_FIELDS]
    + [f"changeOverPoints_endPoint{f}" for f in _COP_ENDPOINT_FIELDS]
    + [f"changeOverPoints_intermediatePoint{f}" for f in _COP_REFERENCE_FIELDS]
    # `location`'in iki yuzu ayri tasinir: ham koordinat (`location_position`
    # verildiyse) ve cozulmus referans (`location_navaidSystem` vb.).
    # Koordinat referanstan TURETILMEZ — yalnizca AIXM'de yazilmissa dolar.
    + ["changeOverPoints_locationLatitude", "changeOverPoints_locationLongitude"]
    + [f"changeOverPoints_location{f}" for f in _COP_REFERENCE_FIELDS]
    + ASSOCIATED_ROUTE_COLUMNS
    + ASSOCIATED_ROUTE_SEGMENT_COLUMNS
    + COP_SYMBOLOGY_COLUMNS
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    # Nokta katmanlariyla ORTAK yedili (kullanici karari): COP cizgisini
    # seviye/tip ile filtrelemek icin. Kaynak, COP'un ARALIGINDAKI
    # segmentlerdir (`associatedRouteSegment_id`), bagli Route'un tamami
    # DEGIL — boylece bayraklar satirin kendi geometrisini tarif eder.
    + ATS_STATUS_ASSOCIATED_COLUMNS
    + AIXM_COLUMNS
)

LAYERS = {
    "designatedPoints": {"columns": DESIGNATED_POINTS, "geometry": "POINT"},
    "navaids": {"columns": NAVAIDS, "geometry": "POINT"},
    "navaidComponents": {"columns": NAVAID_COMPONENTS, "geometry": "POINT"},
    "routeSegments": {"columns": ROUTE_SEGMENTS, "geometry": "LINESTRING"},
    "changeOverPoints": {"columns": CHANGE_OVER_POINTS,
                         "geometry": "LINESTRING"},
}

# Sayısal olarak saklanacak sütunlar (diğerleri TEXT).
_REAL_SUFFIXES = (
    "Elevation", "GeoidUndulation", "HorizontalAccuracy", "magneticVariation",
    "frequency", "tuningFrequencyVHF", "declination", "magneticBearing",
    "trueBearing", "widthCourse", "slope", "rdh", "axisBearing", "displace",
    "angleProportionalLeft", "angleProportionalRight", "angleCoverLeft",
    "angleCoverRight", "angleNominal", "angleMinimum", "angleSpan",
    "trueTrack", "magneticTrack", "reverseTrueTrack", "reverseMagneticTrack",
    "length", "widthLeft", "widthRight", "TurnRadius", "upperLimit",
    "lowerLimit", "minimumObstacleClearanceAltitude", "minimumCrossingAtEnd",
    "maximumCrossingAtEnd",
    # navaidLabeling_* — `short` tam esitlikle yakalanir; mevcut "frequency"
    # girdisi "freq" icin eslesmez ("frequency".endswith("freq") yanlistir).
    "freq", "dmeElev",
    # navaidSymbology_* — mevcut "trueBearing" girdisi bunu yakalamaz.
    "TrueBrg",
    # changeOverPoints_* — COP mesafeleri ve konumu. `distanceFromEnd` ayrica
    # yazilir: "distanceFromEnd".endswith("distance") YANLIS'tir.
    "distance", "distanceFromEnd", "Latitude", "Longitude",
    # copSymbology_offsetPercent
    "Percent",
)


def column_type(name: str) -> str:
    if name in INTEGER_BASE_COLUMNS:
        return "INTEGER"
    if name in BOOLEAN_COLUMNS:
        return "BOOLEAN"                  # SQLite'ta 0/1 INTEGER olarak saklanır
    if name.endswith("Uom") or name.endswith("Reference"):
        return "TEXT"
    # Cozulmus referansin gpkg satir id'si. `…PointId` yerine genel `…Id`:
    # COP'ta `locationId` gibi "Point" icermeyen adlar da var. Kucuk harfli
    # `_id` (ornegin `associatedRouteSegment_id`) BU KURALA GIRMEZ — o bir
    # virgullu LISTE'dir ve TEXT kalmalidir.
    if name.endswith("Id") or name.endswith("navaidId"):
        return "INTEGER"
    short = name.split("_", 1)[-1]
    for suffix in _REAL_SUFFIXES:
        if short == suffix or short.endswith(suffix):
            return "REAL"
    return "TEXT"


# ── GeoPackage yazımı ───────────────────────────────────────────────────────
# Altyapı ortak pakettedir (`data_build_common.gpkg_writer`); burada yalnızca
# bu projenin katman sözlüğüyle bağlanır. Fonksiyon adları önceki API'yi korur.

def create_gpkg(path):
    return gpkg_writer.create_gpkg(path, LAYERS, column_type)


def insert_row(cur, layer: str, row: dict, geom: bytes | None) -> int:
    return gpkg_writer.insert_row(cur, LAYERS, layer, row, geom)


def finalize(con, log=None):
    """Satır sayaçları, tüm sütun index'leri ve mekânsal (RTree) index."""
    gpkg_writer.finalize(con, LAYERS, log)
