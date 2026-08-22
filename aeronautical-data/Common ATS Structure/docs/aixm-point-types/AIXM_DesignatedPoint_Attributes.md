# AIXM 5.2 — DesignatedPoint Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`DesignatedPointPropertyGroup`, satır ~11566-11635) +
`AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni (yani `OTHER:MY_CODE` gibi serbest bir uzatma).
> Ayrıca her `Code*`/`Val*`/`Text*Type`, `complexType` olarak `gml:NilReasonEnumeration`
> tipinde bir `nilReason` attribute'u da taşır.
>
> `DesignatedPoint`, AIXM'de bir **Feature**'dır (`DesignatedPointType` →
> `AbstractAIXMFeatureType`), yani kendi `gml:id`'si, `timeSlice`/`validTime` geçmişi
> vardır. `RouteSegment.start`/`end` içindeki nokta-seçim choice'ının bir alternatifi
> olarak, **id referansıyla (xlink:href)** bağlanır — bkz.
> `AIXM_RoutePoint_DataTypes.md` §2.

> *"A geographical location not marked by the site of a radio navigation aid, used in
> defining an ATS route, the flight path of an aircraft or for other navigation or ATS
> purposes."*

---

## 1. DesignatedPoint → DesignatedPointTimeSlice (kendi attribute'ları)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `designator` | `CodeDesignatedPointDesignatorType` | Enum değil — serbest alfanumerik, 1-5 karakter (örn. ICAO 5 harfli isim: TALAS, ATREX) |
| `type` | `CodeDesignatedPointType` | `ICAO` (ICAO 5 harfli isim kuralına göre), `COORD` (koordinattan türetilmiş isim), `CNF` (Computer Navigation Fix, FAA 8260.19I), `TERMINAL` (max 5 karakter, sadece terminal alanda benzersiz), `BRG_DIST` (ARINC 424'e göre bearing/distance waypoint), `VRP` (Visual Reference Point — VFR raporlama noktası) (+OTHER) |
| `name` | `TextNameType` | Enum değil — serbest metin, max 60 karakter — varsa noktanın tam adı |
| `location` (0..1) | `PointPropertyType` | Noktanın coğrafi konumu → bkz. `AIXM_Point_Attributes.md` |
| `aimingPoint` (0..1) | `TouchDownLiftOffPropertyType` | Nokta bir TLOF (helikopter iniş alanı) merkezinin üzerindeyse association — kapsam dışı (heliport'a özgü feature) |
| `airportHeliport` (0..∞) | `AirportHeliportPropertyType` | Nokta belirli bir havaalanı/heliportla ilişkiliyse (genelde RNAV prosedürlerinde, aynı ada sahip noktaları ayırt etmek için) association — kapsam dışı (büyük, ayrı feature) |
| `runwayPoint` (0..1) | `RunwayCentrelinePointPropertyType` | Nokta bir pist merkez hattı noktasının üzerindeyse association — kapsam dışı (SID/STAR'a özgü) |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) |
| `codeICAOCountry` | `CodeICAOCountryType` | Enum değil — serbest 1-2 karakter alfanumerik (`AlphanumericType`, maxLength 2), ICAO Doc 7910 ülke/alt-bölge harf kodu (örn. `TR`, `LT`). Sınırda kalan noktalarda, 5-harfli kodu ICAO ICARD sisteminde resmi olarak kaydetmiş devletin kodu kullanılır |
| `fix` (0..∞) | `PointReferencePropertyType` | Noktayı konumlandıran açı/mesafe referansı kombinasyonu → bkz. `AIXM_RoutePoint_DataTypes.md` §3 (PointReference) |

---

## Ortak (base) attribute'lar

`DesignatedPointType` → `AbstractAIXMFeatureType`, `DesignatedPointTimeSliceType` →
`AbstractAIXMTimeSliceType`'dan miras alır. Bu iki tip `AIXM_AbstractGML_ObjectTypes.xsd`
dosyasında tanımlı — bu dosya elimizde olmadığı için içeriği teyit edilemedi. Standart
AIXM davranışına göre muhtemelen şunları içerir: `gml:identifier`, `validTime`,
`sequenceNumber`, `correctionNumber`, `interpretation`, `featureLifetime`.

## Genişletme noktası

`extension` alanı → soyut `AbstractDesignatedPointExtension` (ulusal AIP'lerin kendi ek
alanlarını eklemesi için extension noktası, boş/soyut tanımlı).

---

## İlgili dokümanlar

- [AIXM_RoutePoint_DataTypes.md](../AIXM_RoutePoint_DataTypes.md) — DesignatedPoint'in
  `RouteSegment.start`/`end` içindeki 6 seçenekli nokta-seçim choice'ındaki yeri
- [AIXM_Navaid_Attributes.md](AIXM_Navaid_Attributes.md) — alternatif nokta türü
- [AIXM_Point_Attributes.md](AIXM_Point_Attributes.md) — `location` alanının hedef tipi
