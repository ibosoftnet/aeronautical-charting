# AIXM 5.2 — Point (serbest koordinat): Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`PointPropertyGroup`, satır ~8420-8460) +
`AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Ayrıca her `Code*`/`Val*`/`Text*Type`, `complexType`
> olarak `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u da taşır.
>
> `Point`, AIXM'de bir **Feature değildir** — kendi `gml:id`'si/`timeSlice` geçmişi
> yoktur. `PointType` doğrudan `gml:PointType`'ı genişletir (yani temelde saf bir GML
> koordinatıdır), üzerine sadece 2 ek alan eklenir. `RouteSegment.start`/`end` içindeki
> nokta-seçim choice'ının bir alternatifi olarak kullanıldığında (`pointChoice_position`),
> isimlendirilmemiş/kimliksiz bir koordinat noktasını temsil eder — bkz.
> `AIXM_RoutePoint_DataTypes.md` §2.3.

> *"A zero-dimensional object that specifies geometric location. One coordinate pair or
> triplet specifies the location."*

---

## 1. Point (kendi attribute'ları)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| *(gml:Point)* | `gml:PointType` | Temel GML koordinatı — `pos`/`coordinates` (enlem/boylam çifti veya üçlüsü) — pure geometri, kapsam dışı |
| `horizontalAccuracy` | `ValDistanceType` | Sayı (≥0) + `uom`: `NM, KM, M, FT, MI, CM` — kaydedilen yatay koordinatların gerçek konumdan (aynı jeodezik datuma göre) sapması, ICAO PANS-AIM (Doc 10066) güven seviyesine göre dairesel hata olarak ifade edilir |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) |

---

## Kullanım bağlamları

`Point`/`PointPropertyType`, AIXM şemasında birden fazla yerde temel geometri tipi olarak
kullanılır — hepsi aynı 3 alana sahiptir:

| Kullanıldığı yer | Anlamı |
|---|---|
| `RouteSegment.start`/`end` → `pointChoice_position` | Rota segmentinin ucu, tanımlı bir `DesignatedPoint`/`Navaid`'e değil, doğrudan bir koordinata sabitlenmiş (nadir durum) |
| `DesignatedPoint.location` | Bir `DesignatedPoint`'in coğrafi konumu → bkz. `AIXM_DesignatedPoint_Attributes.md` §1 |
| `Navaid.location` (`ElevatedPointPropertyType` üzerinden, irtifa eklenerek) | Bir `Navaid`'in significant point olarak konumu → bkz. `AIXM_Navaid_Attributes.md` §6 |
| `PointReference.distanceReference`/`angleReference` içindeki 6 seçenekli choice | Bir fix'in referans alındığı noktanın koordinatı (nadiren doğrudan `Point`, genelde `DesignatedPoint`/`Navaid`) → bkz. `AIXM_RoutePoint_DataTypes.md` §3.1/§3.2 |

---

## Genişletme noktası

`extension` alanı → soyut `AbstractPointExtension` (ulusal AIP'lerin kendi ek alanlarını
eklemesi için extension noktası, boş/soyut tanımlı).

---

## İlgili dokümanlar

- [AIXM_RoutePoint_DataTypes.md](../AIXM_RoutePoint_DataTypes.md) — Point'in
  `RouteSegment.start`/`end` içindeki 6 seçenekli nokta-seçim choice'ındaki yeri (§2.3)
- [AIXM_DesignatedPoint_Attributes.md](AIXM_DesignatedPoint_Attributes.md) — isimlendirilmiş/kimlikli nokta alternatifi
- [AIXM_Navaid_Attributes.md](AIXM_Navaid_Attributes.md) — seyrüsefer yardımcısı nokta alternatifi, `location` alanında `ElevatedPoint` (Point + irtifa) kullanır
