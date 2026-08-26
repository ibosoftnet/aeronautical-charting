# AIXM 5.2 — ChangeOverPoint (COP) Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`ChangeOverPoint`/`ChangeOverPointType`/
`ChangeOverPointTimeSlice`, satır ~17528-17615; `RoutePortion`, satır ~17918-18050),
`AIXM_DataTypes_annotated.xsd` (`ValDistanceType`/`UomDistanceType`, satır ~22700-23280),
17 January 2025, AIXM 5.2.

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Her `Code*`/`Val*`/`Text*Type`, `complexType` olarak
> `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u da taşır.

> **Bu projede henüz implemente edilmedi.** Bu doküman şu an yalnızca AIXM şema
> referansıdır — `common-ats-structure-aixm.xml` içinde `ChangeOverPoint` kaydı **0**
> (tarandı), GeoPackage şemasında (`AIXM_to_GeoPackage_Schema_Design.md`) karşılığı yok.
> İleride eklenecekse, o dokümandaki "Hiçbir AIXM özniteliği sessizce atlanamaz" kuralına
> göre ayrı bir eşleme kararı gerekir.

`ChangeOverPoint`, AIXM'de bağımsız bir **Feature**'dır (`ChangeOverPointType` →
`AbstractAIXMFeatureType`). Şema annotation'ı:

> *"The distance from the start of the route portion to the position where change over
> occurs for VOR defined routes."*

Yani COP, VOR tanımlı (konvansiyonel) rotalarda, uçağın bir VOR'un radyalini takip etmeyi
bırakıp diğerininkini takip etmeye başladığı noktayı temsil eder.

---

## 0. Temel model — COP bir RouteSegment'i referans göstermez

COP, `RouteSegment`'e (veya doğrudan `Route`'a) bağlanmaz. Bunun yerine
`applicableRoutePortion` ile gömülü bir **`RoutePortion`** nesnesi kurar — bu nesne
`start` + `referencedRoute` + `end` üçlüsüyle rota üzerinde bir aralık tarif eder.

```
ChangeOverPoint
 ├─ distance ─────────────── RoutePortion.start'tan COP'a mesafe
 ├─ location_* (choice) ──── COP'un fiziksel konumu (opsiyonel)
 └─ applicableRoutePortion
       └─ RoutePortion (Object — Feature DEĞİL, kendi timeSlice'ı yok)
             ├─ start_*            (choice, 6 seçenek)
             ├─ intermediatePoint_* (choice, 6 seçenek, opsiyonel — dallanma belirsizliğini gidermek için)
             ├─ referencedRoute     → Route feature'ına association
             └─ end_*              (choice, 6 seçenek)
```

**`RoutePortion` neden `RouteSegment` değil:**

| | `RouteSegment` | `RoutePortion` |
|---|---|---|
| AIXM sınıfı | **Feature** (`AbstractAIXMFeatureType`) | **Object** (`AbstractAIXMObjectType`) |
| Kendi `gml:id`/`timeSlice` geçmişi | Var — bağımsız, kalıcı kayıt | Yok — yalnızca `gml:id` zorunlu niteliği var; gömülü olduğu feature'ın (burada `ChangeOverPoint`) parçası olarak var olur |
| Kapsam | Rota ağının gerçek yapı taşı — kendi `level`/`upperLimit`/`MEA` vb. operasyonel öznitelikleri var | Yalnızca "şu Route üzerinde, şu noktadan şu noktaya" ifadesi — tek bir segmenti veya birden fazla ardışık segmenti kapsayabilir |
| Kim kullanır | Route ağının kendisi (`routeFormed` ile `Route`'a bağlanır) | `ChangeOverPoint`, `RouteDME` (kritik DME), `RestrictionOnRoute` gibi başka feature'ların "bu rotanın filanca aralığında geçerli" demesi gerektiğinde — aynı desen tekrar tekrar kullanılır |

Pratikte COP tek bir `RouteSegment` üzerinde olur, bu yüzden `RoutePortion.start`/`end`
genelde o segmentin `start`/`end`'iyle aynı noktalara denk gelir — ama şema seviyesinde
iki yapı birbirine referanslı **değildir**, sadece aynı noktalara işaret ederler.

---

## 1. ChangeOverPoint → ChangeOverPointTimeSlice (kendi attribute'ları)

| Attribute | Değer Tipi | Occurs | Açıklama |
|---|---|---|---|
| `distance` | `ValDistanceType` | 0..1 | `RoutePortion.start`'tan COP'un konumuna olan mesafe — bkz. **3** |
| **choice** (6 seçenek) | — | 0..1 | COP'un fiziksel konumu → bkz. **2** |
| `applicableRoutePortion` | `RoutePortionPropertyType` | 0..1 | COP'un geçerli olduğu rota aralığı → bkz. **4** |
| `annotation` | `NotePropertyType` | 0..∞ | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |

Zorunlu (mandatory) tek bir alan yoktur — hepsi `minOccurs="0"`. Ortak taban alanlar
(`gml:id`, `validTime`, `interpretation`, `sequenceNumber`, `correctionNumber`,
`featureLifetime`) için bkz. **Ortak (base) attribute'lar**.

---

## 2. Konum choice'ı (6 alternatif)

`RoutePoint_DataTypes.md` §2'deki **aynı 6 seçenekli "SignificantPoint" link class**
deseni burada `location_` önekiyle tekrarlanır (RouteSegment'teki `pointChoice_` ve
RoutePortion'daki `start_`/`end_` ile aynı hedef tipler):

| Choice elemanı | Hedef tip | Hedef Feature |
|---|---|---|
| `location_fixDesignatedPoint` | `DesignatedPointPropertyType` | **DesignatedPoint** |
| `location_navaidSystem` | `NavaidPropertyType` | **Navaid** — pratikte en yaygın kullanım (COP genelde VOR/VOR arası hesaplanan bir nokta) |
| `location_position` | `PointPropertyType` | **Point** (serbest koordinat) |
| `location_runwayPoint` | `RunwayCentrelinePointPropertyType` | **RunwayCentrelinePoint** |
| `location_aimingPoint` | `TouchDownLiftOffPropertyType` | **TouchDownLiftOff** |
| `location_airportReferencePoint` | `AirportHeliportPropertyType` | **AirportHeliport** |

Hepsi opsiyonel (`minOccurs="0"`) — COP'un gerçek koordinatı hesaplanmamışsa bu alan
tamamen boş bırakılabilir; `distance` + `applicableRoutePortion` (start/end navaid'leri
ve referencedRoute) zaten konumu dolaylı olarak tarif eder.

---

## 3. `distance` → ValDistanceType

| Attribute | Değer Tipi | Format |
|---|---|---|
| (değer) | `ValDistanceBaseType` | Sayı (≥0) |
| `uom` | `UomDistanceType` | `NM, KM, M, FT, MI, CM` (+`OTHER`) |
| `accuracy` | `NumericalWithNilReason` | Ölçüm hassasiyeti (opsiyonel) |

**"DME" bir uom değildir.** DME (Distance Measuring Equipment), mesafenin nasıl
ölçüldüğünü anlatan operasyonel bir terimdir — AIXM'de bu bilgi için ayrı bir alan/enum
yoktur, yalnızca `uom="NM"` (deniz mili) girilir; DME'nin kendisi zaten mesafenin ait
olduğu navaid'in (`location_navaidSystem` veya `RoutePortion.start_navaidSystem`) VOR/DME
tipi olmasından ima edilir.

`distance` **her zaman `RoutePortion.start`'tan** ölçülür — `end`'den ölçülen tamamlayıcı
mesafe için ayrı bir alan yoktur (aşağıdaki örnekte olduğu gibi, gerekirse `annotation`'a
serbest metin olarak yazılabilir).

---

## 4. `applicableRoutePortion` → RoutePortion

| Attribute | Değer Tipi | Occurs | Açıklama |
|---|---|---|---|
| **choice** `start_*` (6 seçenek) | (bkz. **2**'deki aynı 6 tip) | 0..1 | Aralığın başlangıç noktası |
| **choice** `intermediatePoint_*` (6 seçenek) | (bkz. **2**'deki aynı 6 tip) | 0..1 | *"To be used when necessary to distinguish between alternative branches of a route."* — rota dallanıyorsa hangi koldan gidildiğini netleştirmek için, genelde gerekmez |
| `referencedRoute` | `RoutePropertyType` | 0..1 | *"The route referenced by the route portion."* — hangi **Route**'a ait olduğu |
| **choice** `end_*` (6 seçenek) | (bkz. **2**'deki aynı 6 tip) | 0..1 | Aralığın bitiş noktası |
| `annotation` | `NotePropertyType` | 0..∞ | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |

`RoutePortionType` → `AbstractAIXMObjectType` (Object, Feature değil — bkz. **0**).
Referanslar standart GML association mekanizmasıyla kurulur: hedef feature'ın `gml:id`'sine
`xlink:href` (bkz. **6. Örnek**).

---

## 5. Genişletme noktası

`ChangeOverPointTimeSliceType.extension` → soyut `AbstractChangeOverPointExtension`;
`RoutePortionType.extension` → soyut `AbstractRoutePortionExtension` (ulusal AIP'lerin
kendi ek alanlarını eklemesi için extension noktası, boş/soyut tanımlı).

---

## 6. Örnek — VOR-VOR aralığında ara noktalı bir COP

**Senaryo:** Route = `ABC VOR → ATSUB → ADASU → XYZ VOR`. Değişim noktası ABC VOR'dan
30 DME (= XYZ VOR'dan 60 DME) mesafede. `ATSUB`/`ADASU` ara noktaları `RoutePortion`'da
**görünmez** — `start` + `referencedRoute` + `end` üçlüsü, aralarındaki tüm segmentleri
zaten kapsar.

```xml
<message:hasMember>
  <aixm:ChangeOverPoint gml:id="EAD_COP_000001">
    <gml:identifier codeSpace="urn:uuid:">11111111-1111-1111-1111-111111111111</gml:identifier>
    <aixm:timeSlice>
      <aixm:ChangeOverPointTimeSlice gml:id="EAD_COP_000001_TS">
        <gml:validTime>
          <gml:TimePeriod gml:id="EAD_COP_000001_TP">
            <gml:beginPosition>2025-06-12T00:00:00Z</gml:beginPosition>
            <gml:endPosition indeterminatePosition="unknown"/>
          </gml:TimePeriod>
        </gml:validTime>
        <aixm:interpretation>BASELINE</aixm:interpretation>
        <aixm:sequenceNumber>1</aixm:sequenceNumber>
        <aixm:correctionNumber>0</aixm:correctionNumber>

        <!-- RoutePortion.start'tan (ABC VOR) itibaren mesafe -->
        <aixm:distance uom="NM">30</aixm:distance>

        <!-- location_* boş bırakıldı: COP'un hesaplanmış koordinatı yok, yalnızca
             mesafe bilgisi var. Koordinat üretilecekse location_position eklenir. -->

        <aixm:applicableRoutePortion>
          <aixm:RoutePortion gml:id="EAD_COP_000001_RP">
            <aixm:start_navaidSystem xlink:href="urn:uuid:AAAAAAAA-AAAA-AAAA-AAAA-ABCVORABCVOR"/>
            <aixm:referencedRoute xlink:href="urn:uuid:4608F50F-4F0E-5293-9AAA-DD34E05A2408"/>
            <aixm:end_navaidSystem xlink:href="urn:uuid:BBBBBBBB-BBBB-BBBB-BBBB-XYZVORXYZVOR"/>
          </aixm:RoutePortion>
        </aixm:applicableRoutePortion>

        <aixm:annotation>
          <aixm:Note gml:id="EAD_COP_000001_NOTE">
            <aixm:propertyName>ChangeOverPoint</aixm:propertyName>
            <aixm:translatedNote>
              <aixm:LinguisticNote gml:id="EAD_COP_000001_NOTE_LING">
                <aixm:note>ABC VOR 30 DME / XYZ VOR 60 DME</aixm:note>
              </aixm:LinguisticNote>
            </aixm:translatedNote>
          </aixm:Note>
        </aixm:annotation>

      </aixm:ChangeOverPointTimeSlice>
    </aixm:timeSlice>
  </aixm:ChangeOverPoint>
</message:hasMember>
```

**Alan eşleştirmeleri:**

| Girdi | AIXM alanı | Değer |
|---|---|---|
| "30 DME" (ABC'den) | `distance` (+`uom`) | `30` NM — `RoutePortion.start`'tan itibaren |
| "ABC VOR" (aralığın başı) | `applicableRoutePortion/RoutePortion/start_navaidSystem` | ABC VOR'un `gml:id`'sine `xlink:href` |
| Route (ABC-ATSUB-ADASU-XYZ) | `applicableRoutePortion/RoutePortion/referencedRoute` | İlgili `Route` feature'ının `gml:id`'sine `xlink:href` |
| "XYZ VOR" (aralığın sonu) | `applicableRoutePortion/RoutePortion/end_navaidSystem` | XYZ VOR'un `gml:id`'sine `xlink:href` |
| "60 DME" (XYZ'den) | — | Ayrı bir alan yok (schema tek `distance`, yalnızca `start`'tan). Tutarlılık/okunabilirlik için `annotation`'a metin olarak eklendi |
| ATSUB, ADASU | — | `RoutePortion`'da görünmez — `start`+`referencedRoute`+`end` aralarındaki segmentleri zaten kapsar |

Örnekteki `xlink:href` UUID'leri **placeholder** — gerçek Route/Navaid feature'larının
kendi `gml:id`/UUID'leriyle değiştirilmesi gerekir.

---

## Ortak (base) attribute'lar

`ChangeOverPointType` → `AbstractAIXMFeatureType`, `ChangeOverPointTimeSliceType` →
`AbstractAIXMTimeSliceType`'dan miras alır (`AIXM_AbstractGML_ObjectTypes.xsd`, AIXM 5.1
kopyasından doğrulandı — temel tipler versiyonlar arası değişmez):

- `gml:id` (zorunlu), `gml:validTime` (zorunlu)
- `interpretation` (zorunlu) — `BASELINE, TEMPDELTA, PERMDELTA, SNAPSHOT` (+OTHER)
- `sequenceNumber` (0..1), `correctionNumber` (0..1)
- `timeSliceMetadata` (0..1), `featureLifetime` (0..1)

`RoutePortionType` → `AbstractAIXMObjectType`: yalnızca zorunlu `gml:id` (bkz. **0**).

## İlgili dokümanlar

- [AIXM_Route_Attributes.md](AIXM_Route_Attributes.md) — `Route`
- [AIXM_RouteSegment_Attributes.md](AIXM_RouteSegment_Attributes.md) — `RouteSegment`, `RoutePortion` ile karşılaştırma (bkz. **0**)
- [AIXM_RoutePoint_DataTypes.md](AIXM_RoutePoint_DataTypes.md) — `location_*`/`start_*`/`end_*` choice'ının hedef tipleri (DesignatedPoint, Navaid, Point, ...)
- [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) — `annotation`/`Note` yapısı
