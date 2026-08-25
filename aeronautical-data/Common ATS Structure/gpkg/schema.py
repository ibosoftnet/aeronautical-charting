"""AŞAMA 2B — GeoPackage şeması: 4 katmanın sütun listeleri ve DDL.

Sütun adlandırma (plan kararı):
  * `<katman>_<AIXM öznitelik adı, camelCase>`
  * ölçü birimi → `<alan>Uom`, dikey referans → `<alan>Reference`
  * `annotation` → 4 sabit sütun (purpose değerlerine göre), katman ÖNEKİSİZ
  * provenance (`data_provider`/`data_originator`/`data_effectivity`/`add_date`)
    ve `gmlId` de katman ÖNEKİSİZ — bu alanlar her katmanda birebir aynı yapıyı
    taşır, tabloya özgü bir anlamları yoktur (kullanıcı kararı)

`points` katmanı YOKTUR: AIXM `Point` bağımsız bir feature değildir
(`gml:Point` substitution group'unda, `AbstractAIXMFeature` değil), bu yüzden
bağımsız satırları olan bir katman kurulamaz — kullanıcı kararıyla iptal edildi.
"""

import sqlite3
import struct

SRS_ID = 4326

ANNOTATION_PURPOSES = ("Description", "Remark", "Warning", "Disclaimer")


#: `annotation` ve provenance sütunları katman önekisiz — bu yapılar her
#: katmanda birebir aynı 4 alana indirgenir, tabloya özgü bir anlamı yoktur
#: (kullanıcı kararı). `_annotation_columns`/`_provenance_columns` artık
#: parametresiz: tüm katmanlar aynı sabit listeyi kullanır.
ANNOTATION_COLUMNS = [f"annotation{p}" for p in ANNOTATION_PURPOSES]
PROVENANCE_COLUMNS = ["data_provider", "data_originator",
                      "data_effectivity", "add_date"]

#: `atsStatus_*` — noktanın ATS rota ağındaki rolünün TÜRETİLMİŞ özeti.
#: Yalnızca nokta katmanlarında (`designatedPoints`, `navaids`) bulunur;
#: `navaidComponents` rota uç noktası olarak çözümlenmez, orada anlamsızdır.
#: AIXM'de karşılığı YOKTUR — `routeSegments` tablosu yazıldıktan SONRA ondan
#: türetilir (bkz. build_common_ats.py `compute_ats_status`). Amaç: QGIS'te
#: "yalnızca rota noktaları" gibi filtreleri sanal katman kurmadan, mevcut
#: RTree/B-tree indekslerini bozmadan yapabilmek.
#: Katman öneki taşımazlar (annotation/provenance ile aynı kural).
ATS_STATUS_COLUMNS = [
    "atsStatus_isElementOfRouteSegment",   # BOOLEAN — kapı alanı
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
#: cizimini besler. Yalnizca `navaidComponents`'te bulunur; katman oneki
#: tasimaz (annotation/provenance/atsStatus/navaidLabeling ile ayni kural).
#:
#: `GPAssociatedLOCTrueBrg`: Glidepath sembolu haritada bir HUZME olarak
#: cizilir ve yonu olmalidir, ama `GlidepathPropertyGroup`'ta yon alani
#: YOKTUR. Yon ayni ILS'in Localizer bileseninde durur; bu sutun o degeri
#: Glidepath satirina tasir (bkz. gpkg/navaid_symbology.py).
NAVAID_SYMBOLOGY_COLUMNS = [
    "navaidSymbology_GPAssociatedLOCTrueBrg",
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
    + ["gmlId"]
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
    + ASSOCIATED_COMPONENT_COLUMNS
    + ["gmlId"]
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
    + ["gmlId"]
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
    + ["gmlId"]
)

LAYERS = {
    "designatedPoints": {"columns": DESIGNATED_POINTS, "geometry": "POINT"},
    "navaids": {"columns": NAVAIDS, "geometry": "POINT"},
    "navaidComponents": {"columns": NAVAID_COMPONENTS, "geometry": "POINT"},
    "routeSegments": {"columns": ROUTE_SEGMENTS, "geometry": "LINESTRING"},
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
)


def column_type(name: str) -> str:
    if name in BOOLEAN_COLUMNS:
        return "BOOLEAN"                  # SQLite'ta 0/1 INTEGER olarak saklanır
    if name.endswith("Uom") or name.endswith("Reference"):
        return "TEXT"
    if name.endswith("PointId") or name.endswith("navaidId"):
        return "INTEGER"
    short = name.split("_", 1)[-1]
    for suffix in _REAL_SUFFIXES:
        if short == suffix or short.endswith(suffix):
            return "REAL"
    return "TEXT"


# ── GeoPackage yazımı ───────────────────────────────────────────────────────

def point_blob(lon: float, lat: float) -> bytes:
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", SRS_ID)
    return header + struct.pack("<BI2d", 1, 1, lon, lat)


def linestring_blob(points) -> bytes:
    """points: [(lat, lon), …] — GeoPackage WKB'de sıra (lon, lat)."""
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", SRS_ID)
    wkb = struct.pack("<BII", 1, 2, len(points))
    for lat, lon in points:
        wkb += struct.pack("<2d", lon, lat)
    return header + wkb


def create_gpkg(path):
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.executescript(
        """
        PRAGMA application_id = 0x47504B47;
        PRAGMA user_version = 10300;
        CREATE TABLE gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL, srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL, organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL, description TEXT);
        INSERT INTO gpkg_spatial_ref_sys VALUES
            ('Undefined Cartesian', -1, 'NONE', -1, 'undefined', 'undefined cartesian'),
            ('Undefined Geographic', 0, 'NONE', 0, 'undefined', 'undefined geographic'),
            ('WGS84', 4326, 'EPSG', 4326, 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]', 'WGS 84 geographic 2D');
        CREATE TABLE gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL,
            identifier TEXT UNIQUE, description TEXT DEFAULT '',
            last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            min_x REAL, min_y REAL, max_x REAL, max_y REAL, srs_id INTEGER);
        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT NOT NULL, column_name TEXT NOT NULL,
            geometry_type_name TEXT NOT NULL, srs_id INTEGER NOT NULL,
            z TINYINT NOT NULL, m TINYINT NOT NULL,
            PRIMARY KEY (table_name, column_name));
        CREATE TABLE gpkg_ogr_contents (
            table_name TEXT NOT NULL PRIMARY KEY, feature_count INTEGER DEFAULT 0);
        CREATE TABLE gpkg_extensions (
            table_name TEXT, column_name TEXT, extension_name TEXT NOT NULL,
            definition TEXT NOT NULL, scope TEXT NOT NULL,
            CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name));
        """
    )

    for name, spec in LAYERS.items():
        cols = ",\n  ".join(
            f'"{c}" {column_type(c)}' for c in spec["columns"])
        cur.execute(
            f'CREATE TABLE "{name}" (\n'
            f'  id INTEGER PRIMARY KEY AUTOINCREMENT,\n'
            f'  geom BLOB,\n  {cols}\n)')
        cur.execute(
            "INSERT INTO gpkg_contents "
            "(table_name, data_type, identifier, srs_id) VALUES (?,?,?,?)",
            (name, "features", name, SRS_ID))
        cur.execute(
            "INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,0,0)",
            (name, "geom", spec["geometry"], SRS_ID))
        cur.execute("INSERT INTO gpkg_ogr_contents VALUES (?, 0)", (name,))

    con.commit()
    return con


def insert_row(cur, layer: str, row: dict, geom: bytes | None) -> int:
    columns = LAYERS[layer]["columns"]
    placeholders = ",".join("?" * (len(columns) + 1))
    names = ",".join(['geom'] + [f'"{c}"' for c in columns])
    values = [geom] + [row.get(c) for c in columns]
    cur.execute(f'INSERT INTO "{layer}" ({names}) VALUES ({placeholders})', values)
    return cur.lastrowid


def geometry_envelope(blob: bytes):
    """GeoPackage geometri blob'unun sınırlayıcı kutusu → (minx, maxx, miny, maxy).

    Yalnızca bu modülün ürettiği iki tipi çözer (Point, LineString); başka bir
    tip gelirse None döner ve satır mekânsal index'e girmez.
    """
    if not blob or len(blob) < 8 or blob[:2] != b"GP":
        return None
    flags = blob[3]
    # bit 1-3: envelope göstergesi (0 = yok, 1 = XY, 2 = XYZ, 3 = XYM, 4 = XYZM)
    envelope_doubles = (0, 4, 6, 6, 8)[(flags >> 1) & 0x07]
    offset = 8 + envelope_doubles * 8
    if len(blob) < offset + 5:
        return None
    endian = "<" if blob[offset] == 1 else ">"
    wkb_type = struct.unpack(endian + "I", blob[offset + 1:offset + 5])[0]
    body = offset + 5

    if wkb_type == 1:                                     # Point
        if len(blob) < body + 16:
            return None
        x, y = struct.unpack(endian + "2d", blob[body:body + 16])
        return x, x, y, y

    if wkb_type == 2:                                     # LineString
        if len(blob) < body + 4:
            return None
        count = struct.unpack(endian + "I", blob[body:body + 4])[0]
        start = body + 4
        if count == 0 or len(blob) < start + count * 16:
            return None
        coords = struct.unpack(endian + f"{count * 2}d",
                               blob[start:start + count * 16])
        xs, ys = coords[0::2], coords[1::2]
        return min(xs), max(xs), min(ys), max(ys)

    return None


# GeoPackage 1.2 Ek F.3 — RTree index tetikleyicileri. `ST_*` fonksiyonları
# QGIS/GDAL tarafından sağlanır; düz SQLite'ta tanımsız olmaları sorun değildir
# çünkü tetikleyici gövdesi yalnızca çalıştırıldığında çözülür.
_RTREE_TRIGGERS = """
CREATE TRIGGER "rtree_{t}_geom_insert" AFTER INSERT ON "{t}"
  WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
BEGIN
  INSERT OR REPLACE INTO "rtree_{t}_geom" VALUES (NEW."id",
    ST_MinX(NEW."geom"), ST_MaxX(NEW."geom"),
    ST_MinY(NEW."geom"), ST_MaxY(NEW."geom"));
END;
CREATE TRIGGER "rtree_{t}_geom_update1" AFTER UPDATE OF "geom" ON "{t}"
  WHEN OLD."id" = NEW."id"
   AND (NEW."geom" NOTNULL AND NOT ST_IsEmpty(NEW."geom"))
BEGIN
  INSERT OR REPLACE INTO "rtree_{t}_geom" VALUES (NEW."id",
    ST_MinX(NEW."geom"), ST_MaxX(NEW."geom"),
    ST_MinY(NEW."geom"), ST_MaxY(NEW."geom"));
END;
CREATE TRIGGER "rtree_{t}_geom_update2" AFTER UPDATE OF "geom" ON "{t}"
  WHEN OLD."id" = NEW."id"
   AND (NEW."geom" ISNULL OR ST_IsEmpty(NEW."geom"))
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id = OLD."id";
END;
CREATE TRIGGER "rtree_{t}_geom_update3" AFTER UPDATE ON "{t}"
  WHEN OLD."id" != NEW."id"
   AND (NEW."geom" NOTNULL AND NOT ST_IsEmpty(NEW."geom"))
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id = OLD."id";
  INSERT OR REPLACE INTO "rtree_{t}_geom" VALUES (NEW."id",
    ST_MinX(NEW."geom"), ST_MaxX(NEW."geom"),
    ST_MinY(NEW."geom"), ST_MaxY(NEW."geom"));
END;
CREATE TRIGGER "rtree_{t}_geom_update4" AFTER UPDATE ON "{t}"
  WHEN OLD."id" != NEW."id"
   AND (NEW."geom" ISNULL OR ST_IsEmpty(NEW."geom"))
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id IN (OLD."id", NEW."id");
END;
CREATE TRIGGER "rtree_{t}_geom_delete" AFTER DELETE ON "{t}"
  WHEN OLD."geom" NOT NULL
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id = OLD."id";
END;
"""


def _build_spatial_index(cur, name: str) -> tuple[int, tuple | None]:
    """Katman için RTree sanal tablosunu kurar, doldurur, tetikleyicileri ekler.

    Dönen: (indekslenen satır sayısı, katmanın toplam sınırlayıcı kutusu).
    """
    cur.execute(f'CREATE VIRTUAL TABLE "rtree_{name}_geom" '
                f'USING rtree(id, minx, maxx, miny, maxy)')

    rows, bounds = [], None
    read = cur.connection.cursor()
    read.execute(f'SELECT id, geom FROM "{name}" WHERE geom IS NOT NULL')
    for row_id, blob in read:
        envelope = geometry_envelope(blob)
        if envelope is None:
            continue
        rows.append((row_id, *envelope))
        bounds = envelope if bounds is None else (
            min(bounds[0], envelope[0]), max(bounds[1], envelope[1]),
            min(bounds[2], envelope[2]), max(bounds[3], envelope[3]))
    read.close()

    cur.executemany(f'INSERT INTO "rtree_{name}_geom" VALUES (?,?,?,?,?)', rows)
    cur.executescript(_RTREE_TRIGGERS.format(t=name))
    cur.execute(
        "INSERT INTO gpkg_extensions VALUES (?,'geom','gpkg_rtree_index',"
        "'http://www.geopackage.org/spec120/#extension_rtree','write-only')",
        (name,))
    return len(rows), bounds


def _build_column_indexes(cur, name: str, columns) -> list[tuple[str, str]]:
    """Her sütunda B-tree index kurar; kurulamayanların listesini döndürür.

    Hata **yutulmaz**. Eskiden burada `except OperationalError: pass` vardı ve
    ekrana sütun listesinin uzunluğu basılıyordu — yani bir index kurulamasa
    bile çıktı "hepsi kuruldu" diyordu. "Her sütunda index olacak" kuralının
    doğrulanabilir olması için başarısızlık görünür olmalı.
    """
    failed = []
    for column in columns:
        try:
            cur.execute(f'CREATE INDEX "idx_{name}_{column}" '
                        f'ON "{name}"("{column}")')
        except sqlite3.OperationalError as exc:
            failed.append((column, str(exc)))
    return failed


def _indexed_columns(cur, name: str) -> set[str]:
    """Katmanda GERÇEKTEN index'lenmiş sütunların kümesi.

    Niyetten değil **diskteki durumdan** üretilir ve index SAYMAZ, index'in
    hangi sütunu kapsadığına bakar. Salt sayım kandırılabilir: doğru sayıda
    ama yanlış sütuna bakan bir index "tamam" görünürdü.
    """
    covered = set()
    for row in cur.execute(f'PRAGMA index_list("{name}")').fetchall():
        index = row[1]
        for info in cur.execute(f'PRAGMA index_info("{index}")').fetchall():
            if info[2] is not None:
                covered.add(info[2])
    return covered


def finalize(con, log=None):
    """Satır sayaçları, tüm sütun index'leri ve mekânsal (RTree) index."""
    cur = con.cursor()
    eksik_toplam = 0
    for name in LAYERS:
        cur.execute(f'SELECT COUNT(*) FROM "{name}"')
        cur.execute("UPDATE gpkg_ogr_contents SET feature_count=? WHERE table_name=?",
                    (cur.fetchone()[0], name))
        failed = _build_column_indexes(cur, name, LAYERS[name]["columns"])

        indexed, bounds = _build_spatial_index(cur, name)
        if bounds:
            cur.execute(
                "UPDATE gpkg_contents SET min_x=?, max_x=?, min_y=?, max_y=? "
                "WHERE table_name=?", (*bounds, name))

        # Rapor NIYETTEN degil, diskteki durumdan uretilir.
        beklenen = LAYERS[name]["columns"]
        covered = _indexed_columns(cur, name)
        indexsiz = [c for c in beklenen if c not in covered]
        eksik_toplam += len(indexsiz)
        uyari = "" if not indexsiz else f"  !! {len(indexsiz)} EKSIK"
        print(f"    {name:18} sutun_index={len(beklenen) - len(indexsiz):>3}"
              f"/{len(beklenen)}{uyari} mekansal_index={indexed}")
        for column in indexsiz:
            print(f"        INDEXSIZ SUTUN: {column}")
            if log is not None:
                log.error("2B", name, column, "index", "-", "sutun_indexsiz")

        for column, hata in failed:
            print(f"        index kurulamadi: {column} -> {hata}")
            if log is not None:
                log.error("2B", name, column, "index", hata,
                          "sutun_indexi_kurulamadi")

    if eksik_toplam:
        print(f"    UYARI: toplam {eksik_toplam} sutun indexsiz kaldi")
    con.commit()
    cur.execute("ANALYZE")
    con.commit()
