# AIXM 5.2 — Rota Ağının İşlenmesi (Genel Bakış)

Kaynak: `AIXM_Features_annotated.xsd` + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

Bu doküman, ATS rota ağının AIXM 5.2 modelinde **kavramsal olarak** nasıl kurulduğunu
özetler — tam attribute listeleri için `AIXM_Route_Attributes.md`,
`AIXM_RouteSegment_Attributes.md` ve `AIXM_RoutePoint_DataTypes.md` dosyalarına bakın.

---

## 1. Üç temel eleman

| Eleman | Rolü |
|---|---|
| **Route** | Rotanın kimliği (designator, flightRule, type...). **Geometri taşımaz.** |
| **RouteSegment** | İki ardışık nokta arasındaki tek bir yol parçası. Geometriyi (`curveExtent`) ve uçuş özniteliklerini (irtifa, pathType, track...) taşıyan asıl feature. |
| **Nokta** (start/end) | Segmentin uç noktaları. Ayrı bir "ara nokta" tipi değil — mevcut `DesignatedPoint`/`Navaid` (veya 4 diğer seçenek) feature'larına referans. |

---

## 2. Route ↔ RouteSegment bağlantısı: yön tersine kuruludur

`Route`'un kendi içinde segment listesini tutan bir alan **yoktur**. Bağlantı tam tersi
yönde kurulur: her `RouteSegment`, kendi **`routeFormed`** alanıyla (tip:
`RoutePropertyType` — bir GML association) hangi Route'a ait olduğuna işaret eder.

```
RouteSegment.routeFormed  ──────►  Route
```

Bir "rota", pratikte aynı `routeFormed` değerine sahip tüm `RouteSegment` kayıtlarının
oluşturduğu zincirdir. Segmentlerin hangi sırayla dizileceği, her segmentin `start`/`end`
noktalarının birbirini takip etmesinden (bir sonraki segmentin `start`'ı, bir öncekinin
`end`'i ile aynı noktaya işaret eder) çıkarılır — ayrı bir "sıra numarası" alanı yoktur.

---

## 3. RouteSegment ↔ Nokta bağlantısı: iki katmanlı referans

Her segment, `start` ve `end` alanlarıyla (tip: `EnRouteSegmentPointPropertyType`) iki
uca bağlanır. Ancak bu doğrudan bir `DesignatedPoint`/`Navaid` referansı değildir — araya
ince bir **rol katmanı** girer:

```
RouteSegment.start / end
   └─► EnRouteSegmentPoint  (AIXM "Object", Feature değil — segmente özgü ek nitelikler taşır:
   │                          roleRVSM, roleMilitaryTraining, turnRadius, flyOver, waypoint...)
   │
   └─► pointChoice_* (6 seçenekli choice)
          └─► xlink:href (gml:id referansı) ──► gerçek DesignatedPoint / Navaid / ... Feature'ı
```

- **`EnRouteSegmentPoint`**, `AbstractSegmentPointType`'ı genişletir; bu tip
  `AbstractAIXMObjectType`'tan türer — yani gerçek bir zaman-dilimli (`timeSlice`) AIXM
  **Feature** değildir, segmentin içine gömülü bir yardımcı objedir.
- Asıl coğrafi/isimsel kimlik, bu objenin içindeki **6 seçenekli choice**'tan (`pointChoice_fixDesignatedPoint`,
  `pointChoice_navaidSystem`, `pointChoice_position`, `pointChoice_runwayPoint`,
  `pointChoice_aimingPoint`, `pointChoice_airportReferencePoint`) biriyle, sistemde
  **bağımsız olarak zaten tanımlı** bir `DesignatedPoint` veya `Navaid` (ya da diğer 4
  tip) Feature'ına GML association (`xlink:href` → hedef Feature'ın `gml:id`'si) ile
  bağlanır.
- Pratikte en yaygın kullanılan iki seçenek `DesignatedPoint` (fix/waypoint) ve `Navaid`
  (VOR/DME/NDB vb.) 'dır. Ayrıntılı liste ve öznitelikleri için
  `AIXM_RoutePoint_DataTypes.md`.
- Bu tasarımın sonucu: aynı nokta (örn. bir VOR), verisi tekrarlanmadan onlarca farklı
  rotada/segmentte/SID-STAR prosedüründe referans olarak kullanılabilir; segment sadece
  o noktaya *bağlama özgü* ek bilgi (RVSM giriş/çıkış rolü, dönüş yarıçapı, fly-over/fly-by
  vb.) ekler.

---

## 4. Ara noktalar (dallanma ayrımı): RoutePortion

`RouteSegment` seviyesinde ayrı bir "ara nokta" alanı yoktur — segment kavramı zaten iki
nokta arasındaki tek bir parçadır. Ancak **`RoutePortion`** adlı yardımcı obje (Route'un
ardışık bir veya daha fazla segmentini gruplayan, `RouteAvailability`/`RouteDME` gibi
feature'ların "hangi bölüme uygulandığını" belirtmekte kullanılan bir link sınıfı), bir
**`intermediatePoint_*`** alanı taşır:

> *"To be used when necessary to distinguish between alternative branches of a route."*
> (Rotanın alternatif dallanan kollarını ayırt etmek gerektiğinde kullanılır.)

Yani `intermediatePoint`, segment zincirinin kendisini tanımlamaz; aynı `start`/`end`
noktalarına sahip birden fazla olası segment kümesi (dallanma) varsa, hangisinden
bahsedildiğini netleştirmek için `RoutePortion.start_*` / `intermediatePoint_*` /
`end_*` üçlüsüyle birlikte kullanılır. `RoutePortion.referencedRoute` alanı da hangi
Route'a ait olduğunu belirtir.

`RoutePortion`'ı somut olarak kullanan bir feature örneği (VOR değişim noktası) için
bkz. [`AIXM_ChangeOverPoint_Attributes.md`](./AIXM_ChangeOverPoint_Attributes.md).

---

## 5. VFR/IFR ayrımı — ayrı bir şema değil, kod değeri

AIXM 5.2'de `VfrRoute` veya `VfrRoutePoint` gibi ayrı bir complexType **yoktur**. Aynı
`Route`/`RouteSegment`/`DesignatedPoint` şeması üzerinden, kod-listesi (enumeration)
değerleriyle ayrıştırılır:

| Yer | Alan | VFR ile ilgili değer |
|---|---|---|
| `Route` | `flightRule` (`CodeFlightRuleType`) | `VFR` (IFR / VFR / ALL) |
| `DesignatedPoint` | `type` (`CodeDesignatedPointType`) | `VRP` (Visual Reference Point) |
| `PointUsage` | `role` (`CodePointUsageType`) | `VFR` (noktanın VFR uçuşlarınca kullanıldığını belirtir) |
| `Route` | `militaryTrainingType` (`CodeMilitaryTrainingType`) | `VR` (VFR eğitim rotası) |

---

## 6. Uçtan uca örnek akış

```
Route "UN854" (flightRule=IFR, type=ATS)
   ▲
   │ routeFormed
   │
RouteSegment #1 ──start──► EnRouteSegmentPoint ──pointChoice_fixDesignatedPoint──► DesignatedPoint "ATREX"
   │
   └──end────────► EnRouteSegmentPoint ──pointChoice_navaidSystem────────► Navaid "TALAS" (VOR/DME)
   ▲
   │ routeFormed
   │
RouteSegment #2 ──start──► (yukarıdaki "TALAS" ile aynı EnRouteSegmentPoint/Navaid referansı)
   │
   └──end────────► EnRouteSegmentPoint ──pointChoice_fixDesignatedPoint──► DesignatedPoint "GOLOR"
```

Zincir, bir segmentin `end`'i ile bir sonrakinin `start`'ının aynı gerçek noktaya
(`gml:id`) işaret etmesiyle ilerler; her iki segment de aynı `routeFormed` (Route
"UN854") değerine sahiptir.

---

## İlgili dokümanlar

- [`AIXM_Route_Attributes.md`](./AIXM_Route_Attributes.md) — Route feature'ının tam öznitelik listesi
- [`AIXM_RouteSegment_Attributes.md`](./AIXM_RouteSegment_Attributes.md) — RouteSegment feature'ının tam öznitelik listesi
- [`AIXM_RoutePoint_DataTypes.md`](./AIXM_RoutePoint_DataTypes.md) — start/end noktalarında kullanılan veri tipleri (EnRouteSegmentPoint, DesignatedPoint, Navaid...)
- [`AIXM_ChangeOverPoint_Attributes.md`](./AIXM_ChangeOverPoint_Attributes.md) — ChangeOverPoint (COP) feature'ı ve RoutePortion'ın somut kullanımı
