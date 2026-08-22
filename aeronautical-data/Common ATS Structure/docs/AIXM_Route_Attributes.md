# AIXM 5.2 — Route Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`RoutePropertyGroup`, satır ~17662-17765) +
`AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni (yani `OTHER:MY_CODE` gibi serbest bir uzatma).
> Ayrıca her `Code*`/`Val*`/`Text*Type`, `complexType` olarak `gml:NilReasonEnumeration`
> tipinde bir `nilReason` attribute'u da taşır (nedeni bilinmeyen/uygulanmayan değerler için).
>
> `Route`, AIXM'de bir **Feature**'dır (`RouteType` → `AbstractAIXMFeatureType`), yani
> kendi `gml:id`'si, `timeSlice`/`validTime` geçmişi vardır. Route'un **hiçbir geometrisi
> yoktur** — geometri `RouteSegment.curveExtent` üzerinde taşınır (bkz.
> `AIXM_RouteSegment_Attributes.md`).

---

## 1. Route → RouteTimeSlice (kendi attribute'ları)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `designatorPrefix` | `CodeRouteDesignatorPrefixType` | `K` (Helicopter), `U` (Upper), `S` (Supersonic), `T` (TACAN Route/military) (+OTHER) |
| `designatorSecondLetter` | `CodeRouteDesignatorLetterType` | `A, B, G, H, J, L, M, N, P, Q, R, T, V, W, Y, Z` (+OTHER) |
| `designatorNumber` | `NoNumberType` | Sayısal (`unsignedInt`, pozitif tam sayı) |
| `multipleIdentifier` | `CodeUpperAlphaType` | Tek büyük harf `A`-`Z` — homonim (aynı isimli) rotaları ayırt etmek için (özellikle askeri eğitim rotalarında) |
| `locationDesignator` | `TextDesignatorType` | Enum değil — serbest metin, 1-16 karakter |
| `name` | `TextNameType` | Enum değil — serbest metin, max 60 karakter |
| `type` | `CodeRouteType` | `ATS` (ICAO Annex 11 ATS Route), `NAT` (North Atlantic Track) (+OTHER) |
| `flightRule` | `CodeFlightRuleType` | `IFR, VFR, ALL` (+OTHER) |
| `internationalUse` | `CodeRouteOriginType` | `INTL, DOM, BOTH` (+OTHER) |
| `militaryUse` | `CodeMilitaryStatusType` | `MIL, CIVIL, ALL` (+OTHER) |
| `militaryTrainingType` | `CodeMilitaryTrainingType` | `IR` (IFR Training route), `VR` (VFR Training Route), `SR` (Slow Speed Low Altitude Training Route) (+OTHER) |
| `userOrganisation` (0..1) | `OrganisationAuthorityPropertyType` | Askeri eğitim rotasında faaliyeti başlatan kuruluş — **Organisation/Authority** feature'ına association, kapsam dışı |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |
| `designCriteria` (0..∞) | `DesignStandardPropertyType` | Rotanın tasarımında uygulanan standart: `PANS_OPS, TERPS, CANADA_TERPS, NATO` (+OTHER) |
| `availability` (0..∞) | `RouteAvailabilityPropertyType` | → bkz. **2** |
| `aircraftCapability` (0..∞) | `AircraftCharacteristicPropertyType` | Rota sınıflandırmasını sağlayan uçak özellik/ekipman/kapasite kombinasyonu → bkz. `AIXM_RouteSegment_Attributes.md` §6 (aynı tip) |

---

## 2. `availability` → RouteAvailability

`RouteSegment.availability` ile birebir aynı yapı (bkz. `AIXM_RouteSegment_Attributes.md`).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `direction` | `CodeRouteDirectionType` | `FORWARD, BACKWARD` (+OTHER) — **not:** genel `CodeDirectionType`'ın aksine `BOTH` değeri yok |
| `cardinalDirection` | `CodeCardinalDirectionType` | → bkz. **3** |
| `status` | `CodeRouteAvailabilityType` | `OPEN` (rota tarifesine göre uçulabilir), `COND` (özel koşullara/izinlere bağlı), `CLSD` (kapalı) (+OTHER) |
| `levels` (0..∞) | `AirspaceLayerPropertyType` | Kullanılabilirliğin geçerli olduğu seviye/zaman bloğu → bkz. `AIXM_RouteSegment_Attributes.md` §5 (AirspaceLayer) |

---

## 3. `cardinalDirection` → CodeCardinalDirectionType (16 yön)

| Değer | Açıklama |
|---|---|
| `N, NE, E, SE, S, SW, W, NW` | Ana 8 yön |
| `NNE, ENE, ESE, SSE, SSW, WSW, WNW, NNW` | Ara 8 yön |

(+`OTHER`)

---

## Ortak (base) attribute'lar

`RouteType` → `AbstractAIXMFeatureType`, `RouteTimeSliceType` → `AbstractAIXMTimeSliceType`'dan
miras alır. Bu iki tip `AIXM_AbstractGML_ObjectTypes.xsd` dosyasında tanımlı — bu dosya
elimizde olmadığı için içeriği teyit edilemedi. Standart AIXM davranışına göre muhtemelen
şunları içerir: `gml:identifier`, `validTime`, `sequenceNumber`, `correctionNumber`,
`interpretation`, `featureLifetime`.

## Genişletme noktası

`extension` alanı → soyut `AbstractRouteExtension` (ulusal AIP'lerin kendi ek alanlarını
eklemesi için extension noktası, boş/soyut tanımlı).
