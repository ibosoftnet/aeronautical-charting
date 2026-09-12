# AIXM 5.2 — ChangeOverPoint (COP) Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`ChangeOverPoint`/`ChangeOverPointType`/
`ChangeOverPointTimeSlice`, satır ~17528-17615; `RoutePortion`, satır ~17918-18050),
`AIXM_DataTypes_annotated.xsd` (`ValDistanceType`/`UomDistanceType`, satır ~22700-23280),
17 January 2025, AIXM 5.2.

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Her `Code*`/`Val*`/`Text*Type`, `complexType` olarak
> `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u da taşır.

> **Durum: LT üretecinde implemente edildi.** `data-sources/LT/lt-route-data-aixm.xml`
> içinde **100 `ChangeOverPoint`** vardır (AIP TÜRKİYE ENR 3.1'den, kaynak:
> `data-sources/LT/COP/turkiye_enr31_changeover_points.json`). Eşleme kararları,
> ölçümler ve implementasyon ayrıntısı: **7. Bu projedeki eşleme kararı**.
>
> Birleşik AIXM'de (`common-ats-structure-aixm.xml`) **100 COP** vardır ve
> XSD doğrulaması `GECERLI 0 hata` (282.567 feature) — bkz. **7.6**.
> GeoPackage'da `changeOverPoints` **beşinci katmandır** (44 sütun, 100 satır,
> LINESTRING) — bkz. **7.7**.

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

`RoutePortion`'ın şema annotation'ı bunu açıkça söyler: *"A group of **one or more
consecutive segments** of the same route"*. Şema seviyesinde iki yapı birbirine
referanslı **değildir**, yalnızca aynı noktalara işaret ederler.

> **Ölçüldü — COP genelde TEK segment üzerinde DEĞİLDİR.** Bu dokümanın eski bir
> sürümü "pratikte COP tek bir `RouteSegment` üzerinde olur" diyordu; LT kaynak
> verisi bunu çürüttü. 100 COP'un **92'si birden fazla segmenti kapsıyor** (2–9
> segment); yalnızca 8'i tek segment ve bu 8 kayıt aslında 4 fiziksel COP'un
> alt/üst rota çiftidir (`G12`/`UG12`, `G80`/`UG80`, `W715`/`UW715`, `W717`/`UW717`).
> Sebebi basit: COP iki **VOR** arasında tanımlıdır, o iki VOR arasında ise genellikle
> ara DesignatedPoint'ler vardır ve rota orada segmentlere bölünür. Yani `RoutePortion`
> burada bir kolaylık değil, **zorunluluktur** — `RouteSegment` bu aralığı ifade edemez.

---

## 1. ChangeOverPoint → ChangeOverPointTimeSlice (kendi attribute'ları)

| Attribute | Değer Tipi | Occurs | Açıklama |
|---|---|---|---|
| `distance` | `ValDistanceType` | 0..1 | `RoutePortion.start`'tan COP'un konumuna olan mesafe — bkz. **3** |
| **choice** (6 seçenek) | — | 0..1 | COP'un fiziksel konumu → bkz. **2** |
| `applicableRoutePortion` | `RoutePortionPropertyType` | 0..1 | COP'un geçerli olduğu rota aralığı → bkz. **4** |
| `annotation` | `NotePropertyType` | 0..∞ | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |
| `extension` | `AbstractChangeOverPointExtension` (soyut) | 0..∞ | Ulusal/kurumsal ek alanlar → bkz. **5**; bu projede kullanılıyor → bkz. **7** |

XSD sırası tam olarak yukarıdaki gibidir (`ChangeOverPointPropertyGroup` + TimeSlice'ın
`extension`'ı) ve yazımda bu sıraya uyulmak **zorundadır**.

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

`distance` **her zaman `RoutePortion.start`'tan** ölçülür ve **tekildir**
(`minOccurs="0"`, `maxOccurs` varsayılan 1 — XSD'den doğrulandı). `applicableRoutePortion`
da tekildir. Dolayısıyla **çekirdek AIXM 5.2'de tek bir COP feature'ı iki mesafe
taşıyamaz**; `end`'den ölçülen tamamlayıcı mesafe için çekirdekte alan yoktur.

Bu, haritacılık açısından bir eksikliktir: COP sembolünde genellikle **her iki VOR için
de** DME değeri gösterilir. Bu projede sorun, AIXM'in kendi `extension` mekanizmasıyla
çözülmüştür — bkz. **5. Genişletme noktası** ve **7. Bu projedeki eşleme kararı**.

> **Kontrol edildi — `RouteDME` bu işe yaramaz.** Rota üzerinde mesafe taşıyabilecek
> tek diğer aday `RouteDME` feature'ıdır; alanları `criticalDME`, `satisfactory`,
> `referencedDME`, `applicableRoutePortion`'dır — **mesafe alanı yoktur**. O feature
> DME/DME (RNAV) seyrüseferinde kritik DME'yi işaretlemek içindir, COP için değil.

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

## 5. Genişletme noktası (extension)

`ChangeOverPointTimeSliceType.extension` → soyut `AbstractChangeOverPointExtension`;
`RoutePortionType.extension` → soyut `AbstractRoutePortionExtension`.

**Extension, AIXM'in resmi ve sistematik bir parçasıdır** — sonradan uydurulan bir
kaçamak değil. XSD'den ölçüldü:

| | Adet |
|---|---:|
| `Abstract<X>Extension` soyut elemanı | **284** |
| Bunların ikame grubu | **hepsi** `aixm:AbstractExtension` |
| `timeSlice` içinde `extension` elemanı tanımlı yer | **266** |

Resmi kılavuzu da vardır ve bu projede duruyor:
`temporary-files/Scheme and Data AIXM 5.1/aixm_application_schema_generation_1.0 (1).pdf`,
**Bölüm 2 — "EXTENDING AIXM FEATURES / OBJECTS"** (2.1 UML Package for Extensions,
2.2 UML Extension Package, 2.3 Data Type Extension Package). Belgenin ifadesiyle
extension, *"…attributes or associations or define new features, which are only relevant
for that community"* içindir.

**Resmi olan / bize ait olan ayrımı:**

| | Durum |
|---|---|
| `extension` elemanı, `AbstractChangeOverPointExtension`, ikame grubu mekanizması | **Resmi AIXM** — standardın parçası |
| İçine konan somut eleman (ad, namespace, alanlar) | **Bize ait** — tasarım gereği öyle olmalı |

Extension kullanan bir belge, kendi extension şemasıyla **birlikte** doğrulanır; bu
standart dışı bir durum değil, öngörülen akıştır. Bu şemayı tanımayan dış tüketiciler
extension'ı görmezden gelir — yine tasarım gereği.

---

## 6. Örnek — yalnız ÇEKİRDEK AIXM ile bir COP

Bu bölüm, **hiç extension kullanmadan** çekirdek AIXM 5.2'nin neyi ifade edebildiğini
gösterir. Bu projenin fiilen üreteceği biçim için bkz. **7**.

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
| "60 DME" (XYZ'den) | — | **Çekirdekte alan yok** (tek `distance`, yalnızca `start`'tan). Bu örnekte yalnızca okunabilirlik için `annotation`'a metin olarak yazıldı — makine tarafından okunamaz. Bu projede bunun yerine extension kullanılır, bkz. **7** |
| ATSUB, ADASU | — | `RoutePortion`'da görünmez — `start`+`referencedRoute`+`end` aralarındaki segmentleri zaten kapsar |

Örnekteki `xlink:href` UUID'leri **placeholder** — gerçek Route/Navaid feature'larının
kendi `gml:id`/UUID'leriyle değiştirilmesi gerekir.

---

## 7. Bu projedeki eşleme kararı

### 7.1 Kaynak veri

`data-sources/LT/COP/turkiye_enr31_changeover_points.json` — AIP TÜRKİYE **ENR 3.1**
(Conventional Navigation Routes; alt: ENR 3.1.1, üst: ENR 3.1.2) tablolarındaki
"Change over point BTN" satırlarından çıkarılmıştır.

```json
{ "ilişkili_ats_yolu": "A4", "vor_1": "BUK", "vor_1_mesafe_nm": 80,
                             "vor_2": "SIV", "vor_2_mesafe_nm": 97 }
```

**Ölçülen veri özellikleri** (100 kayıt):

| Ölçüm | Sonuç |
|---|---|
| Kayıt / rota sayısı | 100 COP, 67 farklı rota (45 rotada tek COP, en fazlası 4) |
| `(rota, vor_1, vor_2)` üçlüsü benzersiz mi | **100/100 benzersiz** → `gml:id` anahtarı olarak kullanılabilir |
| Aynı VOR çifti birden fazla rotada | **Evet** (alt/üst çiftleri: `G8` ve `UG8` gibi) → rota, kimliğin zorunlu parçası |
| İki VOR da LT verisinde var mı | **100/100** — eksik referans yok |
| İki VOR rota üzerinde bağlı mı | **100/100** |
| Kapsanan segment sayısı | **92/100 çoklu segment** (2–9); 8'i tek segment (= 4 fiziksel COP'un alt/üst çifti) |
| `vor_1` rota yönünde hep önce mi | **Hayır** — 80/100'de rota segment yönüne göre ters |
| `d1 + d2` ≈ gerçek VOR-VOR mesafesi | 98/100'ü ≤1 NM (maks 1,8 / ort 0,28 NM) |

`vor_1`'in rota yönüyle uyumsuz olması sorun **değildir**: `RoutePortion.start` bizim
seçimimizdir, şema onu rotanın kendi yönüne bağlamaz. `start = vor_1` seçilince
`distance = vor_1_mesafe_nm` kurgu gereği doğru olur.

> EAD-SDO ham verisinde COP **yoktur** (route segment raporunda böyle bir alan tanımlı
> bile değil), dolayısıyla dış emsal yok — eşleme kararı tümüyle bu projeye aittir.

### 7.2 Alınan kararlar

| Konu | Karar | Gerekçe |
|---|---|---|
| Feature sayısı | COP kaydı başına **tek** `ChangeOverPoint` (100 feature) | Fiziksel olarak tek nokta var; aynalı çift yazmak "bu rotada 2 COP var" diyen yanlış kardinalite üretirdi |
| `distance` | `vor_1_mesafe_nm`, `uom="NM"` | `start = vor_1` olduğu için çekirdek alanın tanımına birebir uyar |
| İkinci mesafe | `ibosoftais:distanceFromEnd` (extension) | Çekirdekte alan yok; annotation metni makine-okunur olmazdı (bkz. **3**) |
| `location_*` | **Yazılmaz** | AIP, COP'un koordinatını yayımlamıyor; hesaplayıp yazmak veri uydurmak olur. (İstenirse ileride `d1`/`d2`'den türetilebilir — tutarlılığı ölçüldü.) |
| `gml:id` | `LT_COP_<rota>_<vor1>_<vor2>` | Üçlünün 100/100 benzersiz olduğu ölçüldü |
| `gml:identifier` | Mevcut `feature_uuid()` desenine göre deterministik UUID5 | Projenin diğer feature'larıyla aynı kural |

### 7.3 Extension tanımı

| | |
|---|---|
| Önek | `ibosoftais` |
| Namespace | `https://cdn.ibosoft.net.tr/aviation-data/schema/aixm/5.2/extension` |
| Somut eleman | `ibosoftais:ChangeOverPointExtension` (→ `aixm:AbstractChangeOverPointExtension` ikame grubunda) |
| Alan | `ibosoftais:distanceFromEnd`, tipi **`aixm:ValDistanceType`** |

Önek **proje düzeyindedir**, kaynak düzeyinde değil: ileride EAD/Jeppesen/TRNC
tarafında da bir ek alan gerekirse aynı namespace kullanılır ve "bizim eklediğimiz"
işareti tek yerde toplanır.

> **Namespace URI'si bir adres değil, kimliktir** — XML ayrıştırıcıları onu hiçbir
> zaman indirmez (AIXM'in kendi `http://www.aixm.aero/schema/5.2` namespace'i gibi).
> Bir dosyanın yayımlanması gerekmez. Seçilen URI, ileride şema dışarıya açılırsa
> konulacağı yere göre belirlenmiştir (kullanıcı kararı).
>
> **Dikkat:** namespace karşılaştırması **birebir dizgi** karşılaştırmasıdır.
> `http://` ile `https://`, ya da sondaki `/` farkı **ayrı namespace** sayılır.
> Bu yüzden yukarıdaki dizgi, üreteçte, extension XSD'sinde ve doğrulayıcıda
> **harfi harfine aynı** yazılmak zorundadır.

Doğrulamada gerçekten okunan dosya namespace değil, **`schemaLocation`**'dır; bizim
extension XSD'miz proje içinde **yerel** bir dosya olarak duracak ve `validate_aixm.py`
onu yerel yoldan derleyecektir (AIXM setini şu an nasıl derliyorsa öyle). Bu adım
internet gerektirmez.

`distanceFromEnd` adı, çekirdek `distance`'ın şema tanımının (*"from the **start** of
the route portion"*) birebir tümleyenidir: **`end`'den ölçülmüş mesafe**. Kendi sayı
tipimiz uydurulmaz, `aixm:ValDistanceType` yeniden kullanılır — böylece `uom` ve
`nilReason` çekirdek `distance` ile birebir aynı davranır.

### 7.4 Üretilecek biçim (gerçek kayıt: A4 / BUK 80 NM / SIV 97 NM)

```xml
<aixm:ChangeOverPoint gml:id="LT_COP_A4_BUK_SIV">
  <gml:identifier codeSpace="urn:uuid:">…</gml:identifier>
  <aixm:timeSlice>
    <aixm:ChangeOverPointTimeSlice gml:id="LT_COP_A4_BUK_SIV_TS">
      <gml:validTime>…</gml:validTime>
      <aixm:interpretation>BASELINE</aixm:interpretation>
      <aixm:sequenceNumber>1</aixm:sequenceNumber>
      <aixm:correctionNumber>0</aixm:correctionNumber>

      <aixm:distance uom="NM">80</aixm:distance>

      <aixm:applicableRoutePortion>
        <aixm:RoutePortion gml:id="LT_COP_A4_BUK_SIV_RP">
          <aixm:start_navaidSystem xlink:href="urn:uuid:…BUK…"/>
          <aixm:referencedRoute    xlink:href="urn:uuid:…A4…"/>
          <aixm:end_navaidSystem   xlink:href="urn:uuid:…SIV…"/>
        </aixm:RoutePortion>
      </aixm:applicableRoutePortion>

      <aixm:extension>
        <ibosoftais:ChangeOverPointExtension gml:id="LT_COP_A4_BUK_SIV_EXT">
          <ibosoftais:distanceFromEnd uom="NM">97</ibosoftais:distanceFromEnd>
        </ibosoftais:ChangeOverPointExtension>
      </aixm:extension>

    </aixm:ChangeOverPointTimeSlice>
  </aixm:timeSlice>
</aixm:ChangeOverPoint>
```

> **Doğrulanmayı bekleyen tek nokta:** extension elemanının `gml:id` taşımak zorunda
> olup olmadığı `AbstractExtensionType`'ın tanımına bağlıdır ve o tip
> `AIXM_AbstractGML_ObjectTypes.xsd` içindedir — `docs/` altında yalnızca Features ve
> DataTypes annotated kopyaları var. Yukarıdaki `gml:id` bu yüzden **geçici**;
> implementasyonda resmi XSD setinden kesinleştirilecek.

### 7.5 Implementasyon (LT üreteci)

| Dosya | Rol |
|---|---|
| `data-sources/LT/generate-aixm-data/sources/cop.py` | Kaynak okuyucu — rota anahtarı Türkçe karakterli olduğu için sondan eşleşmeyle bulunur, elle yazılmaz |
| `data-sources/LT/generate-aixm-data/aixm/change_over_point.py` | Feature yazıcı (XSD sırası, extension) |
| `data-sources/LT/generate-aixm-data/aixm/writer.py` | `NS_IBOSOFTAIS` + `ibosoftais()` — namespace TEK yerde tanımlı |
| `data-sources/LT/generate-aixm-data/generate_aixm.py` | `_write_change_over_points()` — ATS rotaları yazıldıktan sonra (3b) |
| `schemas/ibosoftais-extension.xsd` | Extension şeması |
| `data-sources/EAD-SDO/generate-aixm-data/validate_aixm.py` | Stok AIXM seti + extension şemasını birlikte derler |

**Rota kodu normalizasyonu:** COP kaynağı kodu boşluksuz veriyor (`A4`), ham rota
verisi boşluklu (`A 4`). Eşleme iki taraftan da boşluk silinip büyük harfe
çevrilerek yapılır; 453 ham kodun normalize hâlinde çakışma olmadığı ölçüldü.

**Üretim sonucu:** 100/100 COP yazıldı — 67/67 rota ve 35/35 VOR çözüldü,
çözülemeyen referans **0**, `cop_*` hata kaydı **0**. Bağımsız doğrulama
(kaynak JSON'dan yeniden hesaplayıp XML ile karşılaştıran betik): **19/19 geçti**
— değerler birebir, `uom` hepsinde `NM`, `location_*` hiçbirinde yok, tüm
`xlink:href`'ler dosyadaki gerçek Navaid/Route feature'larına çözülüyor.

**XSD doğrulaması (ölçüldü, iki koşu):**

| Derlenen şema | Sonuç |
|---|---|
| Yalnız stok AIXM 5.2 seti | `GECERSIZ` — **tek** hata: `{…/extension}ChangeOverPointExtension: This element is not expected` (4448 feature işlendikten sonra) |
| Stok set **+** `schemas/ibosoftais-extension.xsd` | **`GECERLI 0 hata (4448 feature)`** |

İlk satır, COP'un çekirdek yapısının (`distance`, `RoutePortion`, `xlink`
sıralaması) stok AIXM'e göre zaten kusursuz olduğunu da kanıtlar: şemanın tek
itirazı bizim eklediğimiz elemandır.

### 7.6 Birleştirme (Aşama 2A)

COP, ana AIXM'e dahil edilmiştir. Ayarlar ve davranış:
[`Common_Builder_Behaviour.md`](../Common_Builder_Behaviour.md) §4.10.

**Doğal anahtar** (`merge/keys.py`):

```
("changeOverPoints", rota, *sorted((uçA, uçB)), originator)
```

Uç çifti **sıralanır** (kullanıcı kararı): iki VOR arasındaki geçiş noktası
fizikî olarak tektir, bir kaynak `BUK→SIV`, diğeri `SIV→BUK` yazmış olabilir —
sıralama sayesinde ikisi aynı COP olarak eşleşir. `RouteSegment`'te sıra
korunur çünkü orada yön kaydın anlamının parçasıdır; COP'ta değildir. Uçlardan
biri çözülemezse anahtar `None` olur ve kayıt eşleştirmeye girmez
(`routeSegments` kuralıyla birebir aynı).

**Çakışma yönü:** ek kaynak kazanır (`designatedPoints`/`routeSegments` ile
aynı). `changeOverPoints` bir katman adı olduğu için bu, config'den
`prefer_base_on_match_layers` listesine eklenerek tersine çevrilebilir — ayrı
bir config alanı gerekmez.

**İkame senaryolarında referansların akıbeti.** COP'un referans verdiği hedefe
ne olursa olsun bağ korunur; tek istisna iptal kuralıdır:

| Hedefin başına gelen | `remap` | COP referansı |
|---|---|---|
| Hayatta kalır | — | Değişmez |
| Base kayıt override edildi (ek kaynak kazandı) | var | Kazanana yönlenir |
| Ek kaynak kaydı devretti (`prefer_base`) | var | Kazanana yönlenir |
| Yakınlıkla override edildi | var | Kazanana yönlenir |
| Öksüz ekipman zinciri düştü | — | İlgisiz (COP ekipmana referans vermez) |
| **İptal (exclude) kuralıyla çıkarıldı** | **YOK** | **Kırılır** → COP yazılır, loglanır |

Bu, yönlendirmenin derinlikten bağımsız olmasıyla mümkündür: COP'un referansları
gömülü `RoutePortion` nesnesinin içindedir ve yönlendirme yazılan parçanın bütün
alt elemanlarını gezer. COP bu özelliğe dayanan **ilk** feature olduğu için,
yazım sonrası ayrı bir denetim üç referansı da birleşik dosyayla uzlaştırır;
çözülemeyen referans `cop_referansi_birlesik_dosyada_yok` olarak loglanır ve
**COP yine yazılır** (kayıt düşürülmez, boşluk görünür kılınır).

### 7.7 GeoPackage (Aşama 2B)

`changeOverPoints`, GeoPackage'ın **beşinci katmanıdır** (44 sütun, 100 satır).
Tam sütun listesi ve adlandırma kuralları:
[`AIXM_to_GeoPackage_Schema_Design.md`](../AIXM_to_GeoPackage_Schema_Design.md)
§1.0 ve §2.1.

**Geometri çizgidir, nokta değil.** COP bir noktadır ama koordinatı yazılmaz
(§7.2); bu yüzden katman COP'un geçerli olduğu **rota aralığını** taşır ve
çizgi `RoutePortion.start` ucundan başlar. QGIS sembolü çizgi boyunca
`copSymbology_offsetPercent` kadar kaydırarak yerine koyar:

```
copSymbology_offsetPercent = distance / çizginin geodezik uzunluğu × 100
```

Payda çizginin **kendi uzunluğudur** — QGIS kaydırmayı çizgi üzerinde yaptığı
için başka bir payda anlamsız olurdu. `distanceFromEnd` bu hesaba girmez.

Çizgi, aralığı kapsayan `RouteSegment`'lerin geometrileri **sırayla ve doğru
yönde** birleştirilerek kurulur (`gpkg/route_portion.py`). `intermediatePoint`
verilmişse yol onun üzerinden geçer — bu alanın AIXM'deki tek işlevi budur ve
yok sayılırsa dallanan bir rotada yanlış kol çizilir. Rota dallanıyor ve ara
nokta yoksa **seçim yapılmaz**: geometri boş kalır ve loglanır.

**Ölçülen sonuç:** 100/100 COP geometrili; çizgilerin tamamı doğru uçta
başlıyor (<0,5 NM); çizgi uzunluğu ile `distance + distanceFromEnd` farkı
medyan 0,28 NM (maks 1,56); zincir uzunluğu 1-9 segment.

Katman ayrıca eşleştirme için hem gpkg satır id'lerini hem AIXM uuid'lerini
taşır (`…PointUuid`, `associatedRoute_uuid`, `associatedRouteSegment_uuid`) —
`…Uuid` sütun ailesi şemaya bu katmanla girdi.

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
