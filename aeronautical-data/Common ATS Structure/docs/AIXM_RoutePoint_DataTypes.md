# AIXM 5.2 — RouteSegment start/end Noktalarında Kullanılan Veri Tipleri

Kaynak: `AIXM_Features_annotated.xsd` + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Her `Code*`/`Val*`/`Text*Type`, `complexType` olarak
> `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u da taşır.

**Ayrı bir "ara nokta"/"intermediate point" feature'ı yoktur.** `RouteSegment.start` ve
`RouteSegment.end` (tip: `EnRouteSegmentPointPropertyType`), iki katmanlı bir referans
zinciriyle mevcut nokta feature'larına bağlanır — mekanizmanın tam açıklaması için
`AIXM_Route_Network_Overview.md`'ye bakın. Bu doküman, o zincirdeki her katmanın tam
öznitelik listesini verir.

```
RouteSegment.start / end
   └─► EnRouteSegmentPoint  (Object — segmente özgü ek nitelikler)
          └─► SegmentPointPropertyGroup (ortak alanlar + 6 seçenekli "hangi nokta" choice'ı)
                 └─► DesignatedPoint | Navaid | Point | RunwayCentrelinePoint
                     | TouchDownLiftOff | AirportHeliport   (gerçek Feature, xlink:href ile)
```

---

## 1. EnRouteSegmentPoint (Object — Feature değil)

`AbstractSegmentPointType` → `AbstractAIXMObjectType`'ı genişletir (yani `DesignatedPoint`
gibi kendi `timeSlice`/`validTime` geçmişi olan bağımsız bir Feature değildir; segmentin
içine gömülü, segmente özgü bir "rol" objesidir).

### 1.1 EnRouteSegmentPointPropertyGroup (kendine özgü alanlar)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `roleFreeFlight` | `CodeFreeFlightType` | `PITCH` (free flight başlangıç noktası), `CATCH` (free flight bitiş noktası) (+OTHER) |
| `roleRVSM` | `CodeRVSMPointRoleType` | `IN` (RVSM giriş noktası), `OUT` (RVSM çıkış noktası), `IN_OUT` (giriş/çıkış) (+OTHER) |
| `turnRadius` | `ValDistanceType` | Sayı (≥0) + `uom`: `NM, KM, M, FT, MI, CM` — önceki/sonraki segmente devam ederken önerilen dönüş yarıçapı |
| `roleMilitaryTraining` | `CodeMilitaryRoutePointType` | `S` (giriş/başlangıç noktası), `T` (dönüş noktası), `X` (çıkış/bitiş noktası), `AS` (alternatif giriş), `AX` (alternatif çıkış), `ASX` (alternatif giriş/çıkış) (+OTHER) |

### 1.2 SegmentPointPropertyGroup (tüm segment-nokta tiplerinde ortak — `EnRouteSegmentPoint`, `TerminalSegmentPoint`, `AerialRefuellingPoint` bunu paylaşır)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `reportingATC` | `CodeATCReportingType` | `COMPULSORY, ON_REQUEST, NO_REPORT` (+OTHER) — ATC pozisyon raporu gereksinimi |
| `flyOver` | `CodeYesNoType` | `YES` (fly-over waypoint — üzerinden doğrudan geçilmesi zorunlu), `NO` (fly-by waypoint — dönüş öngörümlemesi ile geçilir) |
| `waypoint` | `CodeYesNoType` | `YES/NO` — RNAV (Area Navigation) prosedürü/rotası için kullanılan bir nokta mı |
| `radarGuidance` | `CodeYesNoType` | `YES/NO` — noktaya ulaşmak için radar yönlendirmesi mümkün mü |
| `facilityMakeup` (0..∞) | `PointReferencePropertyType` | Noktanın açı/mesafe referanslarıyla (DME, kesişim vb.) konumlandırılması → bkz. **3** |
| **choice** (6 seçenek) | — | → bkz. **2** — noktanın gerçek kimliği |

---

## 2. Nokta seçim choice'ı (6 alternatif)

Şema annotation'ı (tüm 6 seçenek için ortak):
> *"A link class that allows selecting between a navaid system, a runway point, an
> airport reference point, an aiming point or a fix designated point. SignificantPoint
> accounts for a specified geographical location used to define an ATS route, the
> flight path of an aircraft or for other navigation/ATS purposes."*

| Choice elemanı | Hedef tip | Hedef Feature |
|---|---|---|
| `pointChoice_fixDesignatedPoint` | `DesignatedPointPropertyType` | **DesignatedPoint** → bkz. **2.1** |
| `pointChoice_navaidSystem` | `NavaidPropertyType` | **Navaid** → bkz. **2.2** |
| `pointChoice_position` | `PointPropertyType` | **Point** (serbest koordinat) → bkz. **2.3** |
| `pointChoice_runwayPoint` | `RunwayCentrelinePointPropertyType` | **RunwayCentrelinePoint** → bkz. **2.4** |
| `pointChoice_aimingPoint` | `TouchDownLiftOffPropertyType` | **TouchDownLiftOff** → bkz. **2.5** |
| `pointChoice_airportReferencePoint` | `AirportHeliportPropertyType` | **AirportHeliport** → bkz. **2.6** |

Tüm `*PropertyType`'lar aynı boş kalıba sahiptir:
```xml
<complexType name="...PropertyType">
   <attributeGroup ref="gml:OwnershipAttributeGroup"/>
   <attributeGroup ref="gml:AssociationAttributeGroup"/>
</complexType>
```
Yani her biri, ayrı tanımlanmış bağımsız bir Feature'a **GML association**
(`xlink:href="#<gml:id>"`, by-reference) ya da — `OwnershipAttributeGroup` sayesinde —
teoride doğrudan iç içe gömme (by-value) imkanı sağlar. ATS rota verisinde pratikte
neredeyse her zaman **by-reference** kullanılır.

En yaygın kullanılan üç seçeneğin (**DesignatedPoint**, **Navaid**, **Point**) tam
öznitelik listeleri artık ayrı, kendi başına duran dokümanlarda —
[`aixm-point-types/`](aixm-point-types) klasörü altında; kalan 3 seçenek (SID/STAR ve
havaalanı prosedürlerinde daha sık görülür, enroute ATS rota ağında nadirdir) kısaca
tanımlanıyor.

---

### 2.1 DesignatedPoint

> *"A geographical location not marked by the site of a radio navigation aid, used in
> defining an ATS route, the flight path of an aircraft or for other navigation or ATS
> purposes."*

Tam öznitelik listesi → **[aixm-point-types/AIXM_DesignatedPoint_Attributes.md](aixm-point-types/AIXM_DesignatedPoint_Attributes.md)**
(`designator`, `type` [ICAO/COORD/CNF/TERMINAL/BRG_DIST/VRP], `name`, `location`,
`aimingPoint`, `airportHeliport`, `runwayPoint`, `annotation`, `codeICAOCountry`, `fix`).

---

### 2.2 Navaid

> *"A service providing guidance information or position data for the efficient and safe
> operation of aircraft supported by one or more radio navigation aids."*

Tam öznitelik listesi → **[aixm-point-types/AIXM_Navaid_Attributes.md](aixm-point-types/AIXM_Navaid_Attributes.md)**
(`type` [18 değerli `CodeNavaidServiceType`], `designator`, `name`, `flightChecked`,
`purpose`, `signalPerformance`, `courseQuality`, `integrityLevel`, `touchDownLiftOff`,
`navaidEquipment` [NavaidComponent alt-yapısı dahil], `location` [ElevatedPoint dahil],
`runwayDirection`, `servedAirport`, `availability` [NavaidOperationalStatus alt-yapısı
dahil], `annotation`, `codeICAOCountry`).

---

### 2.3 Point (serbest koordinat)

> *"A zero-dimensional object that specifies geometric location. One coordinate pair or
> triplet specifies the location."*

Bağımsız bir isimlendirilmiş/kimlikli nokta feature'ı **değildir** — sadece bir GML
koordinatıdır (`gml:Point`'i genişletir). Tam öznitelik listesi →
**[aixm-point-types/AIXM_Point_Attributes.md](aixm-point-types/AIXM_Point_Attributes.md)**
(`horizontalAccuracy`, `annotation`).

Kullanım amacı: rota segmentinin ucunun, tanımlı bir `DesignatedPoint`/`Navaid`'e değil,
doğrudan bir koordinata sabitlendiği (nadir) durumlar.

---

### 2.4 RunwayCentrelinePoint

> *"An operationally significant position on the centre line of a runway direction. A
> typical example is the runway threshold."*

Enroute ATS rota ağında nadir; asıl kullanım alanı SID/STAR/yaklaşım prosedürleridir.
Kendi öznitelik yapısı bu dokümanın kapsamı dışında.

### 2.5 TouchDownLiftOff

> *"A load bearing area on which a helicopter may touch down or lift-off."*

Helikopter TLOF alanları — enroute ağı için ilgisiz, SID/STAR/yaklaşım bağlamında
kullanılır. Kapsam dışı.

### 2.6 AirportHeliport

> *"A defined area on land or water (including any buildings, installations and
> equipment) intended to be used either wholly or in part for the arrival, departure and
> surface movement of aircraft/helicopters."*

Enroute ATS rota ağında nadir; asıl kullanım alanı SID/STAR referans noktalarıdır. Kendi
öznitelik yapısı (pist, taksi yolu, apron vb. içeren büyük bir feature) bu dokümanın
kapsamı dışında.

---

## 3. PointReference (facilityMakeup / DesignatedPoint.fix altında kullanılır)

> *"Defines the location of a designated point using a combination of angles and
> distances based on the guidance service. The set of angles and distances must not
> under specify the location."*

Bir noktanın (özellikle DME/DME kesişimi, bearing/distance fix gibi konvansiyonel
yöntemlerle tanımlanan noktaların) hangi tesis(ler)e göre, hangi açı/mesafe
kombinasyonuyla konumlandırıldığını tarif eder. Hem `SegmentPointPropertyGroup.facilityMakeup`
(bölüm 1.2) hem de `DesignatedPoint.fix` (bölüm 2.1) tarafından kullanılır.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `role` | `CodeReferenceRoleType` | `INTERSECTION` (iki açı/mesafe göstergesinin farklı navaid'lere referansla kesişimi), `RECNAV` (segment için önerilen/tavsiye edilen navaid), `ATD` (Along Track Distance — rehberlik güzergahı boyunca başka bir noktaya mesafe), `RAD_DME` (bir navaid'den bearing + DME mesafesi ile tanımlı) (+OTHER) |
| `priorFixTolerance` | `ValDistanceSignedType` | İşaretli mesafe (`xsd:decimal`) + `uom`: `NM, KM, M, FT, MI, CM` — fix'in erken alınabileceği durumlar için, uçuş rotasına dik referans hattından itibaren en erken alım noktasına olan hata mesafesi |
| `postFixTolerance` | `ValDistanceSignedType` | (yukarıdaki gibi) — fix'in en geç alınabileceği noktaya olan hata mesafesi |
| `fixToleranceArea` | `SurfacePropertyType` | Fix tolerance alanının boyutları (navaid sistem kullanım doğruluğu ve tesisten mesafeye göre belirlenir) — GML geometrisi, kapsam dışı |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |
| `minimumReceptionLimit` | `ValDistanceVerticalType` | En düşük sinyal alım irtifası |
| `minimumReceptionLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `maximumAuthorisedLimit` | `ValDistanceVerticalType` | En yüksek yetkili kullanım irtifası |
| `maximumAuthorisedLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `distanceReference` (0..∞) | `DistancePropertyType` | Fix'in temel alındığı navaid/designated point'ten mesafe göstergesi → bkz. **3.1** |
| `angleReference` (0..∞) | `AngleUsePropertyType` | Fix'in temel alındığı tesisten noktaya açı göstergesi → bkz. **3.2** |

---

### 3.1 `distanceReference` → Distance

> *"A distance reference from a navaid or with reference to a designated point."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `distance` | `ValDistanceType` | Sayı (≥0) + `uom`: `NM, KM, M, FT, MI, CM` — mesafe değeri |
| `minimumReceptionAltitude` | `ValDistanceVerticalType` | Sinyalin alınabildiği en düşük MSL irtifası |
| `type` | `CodeDistanceIndicationType` | `DME` (DME göstergesinden gelen mesafe), `GEODETIC` (geodezik hesaplamayla bulunan mesafe) (+OTHER) |
| **choice** (6 seçenek) | — | Mesafenin ölçüldüğü referans nokta — bölüm **2**'deki aynı 6 seçenek (`pointChoice_fixDesignatedPoint`, `pointChoice_navaidSystem`, `pointChoice_position`, `pointChoice_runwayPoint`, `pointChoice_aimingPoint`, `pointChoice_airportReferencePoint`) |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |

---

### 3.2 `angleReference` → AngleUse

> *"Indicates the role of the AngleIndication in the PointReference (for example, along
> track versus intersecting)."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `alongCourseGuidance` | `CodeYesNoType` | `YES/NO` — bu açı göstergesi segment için rota rehberliği (course guidance) sağlıyor mu |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |
| `theAngle` (0..1) | `AnglePropertyType` | → bkz. **3.2.1** |

#### 3.2.1 `theAngle` → Angle

> *"An angular reference from a navaid or with reference to a designated point."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `angle` | `ValBearingType` | 0-360 derece (ondalık) — kuzey referansına göre açı |
| `angleType` | `CodeBearingType` | `TRUE` (gerçek kerteriz), `MAG` (manyetik kerteriz), `RDL` (VOR radial), `TRK` (track), `HDG` (heading) (+OTHER) |
| `indicationDirection` | `CodeDirectionReferenceType` | `TO` (tesise doğru), `FROM` (tesisten itibaren) (+OTHER) |
| `trueAngle` | `ValBearingType` | 0-360 derece — gerçek kuzey referanslı açı |
| `cardinalDirection` | `CodeCardinalDirectionType` | 16 yön (`N, NE, E, SE, S, SW, W, NW, NNE, ENE, ESE, SSE, SSW, WSW, WNW, NNW` +OTHER) — açının pusula yönü olarak ifadesi |
| `minimumReceptionAltitude` | `ValDistanceVerticalType` | Sinyalin alınabildiği en düşük MSL irtifası |
| **choice** (6 seçenek) | — | Açının ölçüldüğü referans nokta — bölüm **2**'deki aynı 6 seçenek |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |

---

## Özet: "Ara nokta" sorusuna cevap

**Hayır, ayrı bir "ara nokta" veri tipi yoktur.** `RouteSegment.start`/`end`, mevcut
`DesignatedPoint` veya `Navaid` (ya da 4 diğer nadir seçenek) feature'larına, GML
association (`xlink:href` → hedef Feature'ın `gml:id`'si) ile bağlanır. Araya giren tek
ek katman, Feature değil bir **Object** olan `EnRouteSegmentPoint`'tir — bu da yalnızca
segmente özgü bağlamsal nitelikleri (RVSM rolü, dönüş yarıçapı, askeri rota rolü, ATC
raporlama, fly-over/fly-by, RNAV waypoint işareti) taşır; noktanın coğrafi/isimsel
kimliğini kendisi tanımlamaz.
