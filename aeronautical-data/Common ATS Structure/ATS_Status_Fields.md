# `atsStatus_*` Alanları — Noktaların ATS Rota Ağındaki Rolü

`designatedPoints` ve `navaids` katmanlarına eklenen **on üç türetilmiş** alan.
Bir noktanın ATS rota ağıyla ilişkisini, ona referans veren `routeSegments`
satırlarından özetler.

- Katman/sütun eşlemesinin tamamı:
  [`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md)
- Builder'ın genel davranışı:
  [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md)

---

## 1. Neden var

QGIS'te "yalnızca rota noktalarını göster" gibi bir filtre iki yolla kurulabilir:

| Yol | Sorun |
|---|---|
| **Virtual layer** (`EXISTS (SELECT … FROM routeSegments …)`) | Sonuç katmanının kalıcı **RTree mekânsal indeksi olmaz**; harita her pan/zoom'da 152.061 satırlık alt sorguyu yeniden tarar |
| **Kalıcı sütun** (bu çözüm) | Aynı fiziksel tablo, aynı `geom`, aynı RTree; sütun ayrıca B-tree index alır. QGIS'in Query Builder'ı filtreyi indekslerle birlikte native uygular |

İkincisi seçildi (kullanıcı kararı). Alanlar QGIS'e özel değildir — ArcGIS,
`ogr2ogr`, herhangi bir GIS aracı aynı sütunları kullanabilir.

## 2. Kapsam

| Katman | `atsStatus_*` var mı | Gerekçe |
|---|---|---|
| `designatedPoints` | ✅ | Rota segmenti ucu olarak çözümlenir |
| `navaids` | ✅ | Rota segmenti ucu olarak çözümlenir (14.214 start + 13.892 end referansı) |
| `navaidComponents` | ❌ | Rota ucu olarak **hiç çözümlenmez** — fiziksel ekipmandır, orada anlamsız olurdu |
| `routeSegments` | ❌ | Kaynağın kendisi |

Sütunlar **katman öneki taşımaz** (`annotation`/provenance ile aynı kural).

## 3. AIXM'de karşılığı yoktur

Bu alanlar AIXM'den okunmaz — **`routeSegments` tablosu yazıldıktan sonra**
ondan türetilir (`build_common_ats.py` → `compute_ats_status`, 2B aşamasının
[4] adımı). Bu yüzden birleşik AIXM dosyasında karşılıkları yoktur ve XSD
doğrulamasını etkilemezler.

Türetme sırası zorunludur: uç nokta çözümlemesi (`startPointId`/`endPointId`)
tamamlanmadan hangi noktanın hangi segmente bağlı olduğu bilinemez.

---

## 4. Alanlar

### 4.1 `atsStatus_isElementOfRouteSegment` — BOOLEAN, kapı alanı

Nokta en az bir rota segmentinin ucu mu? Her satırda **0 veya 1** doldurulur,
asla NULL kalmaz.

> **Kapı kuralı:** bu alan `0` ise diğer **on iki alanın tamamı** `NULL`'dur — `0` veya boş
> dize değil. Böylece "rota ağına bağlı değil" ile "bağlı ama o bilgi yok"
> ayrımı korunur (kullanıcı kararı). Doğrulandı: her iki katmanda da ihlal 0.

### 4.2 Seviye bayrakları — BOOLEAN × 4

| Sütun | Anlamı |
|---|---|
| `atsStatus_associatedLevelUpper` | ilişkili segmentlerden en az biri `level = UPPER` |
| `atsStatus_associatedLevelLower` | en az biri `level = LOWER` |
| `atsStatus_associatedLevelBoth` | en az biri `level = BOTH` |
| `atsStatus_associatedLevelOther` | en az biri `level` = **gerçek** `OTHER` veya `OTHER:<kod>` |

**Dördü de bağımsızdır, birbirini dışlamaz.** Bir nokta hem `UPPER` hem `LOWER`
segmente bağlıysa iki bayrak da `1` olur — ölçüldü: `designatedPoints`'te
**4.125**, `navaids`'te **703** nokta böyle.

İki nokta özellikle önemli:

- **`Both` türetilmez.** Yalnızca ham `level = BOTH` taşıyan bir segment varsa
  `1` olur; `UPPER` + `LOWER` birleşiminden **çıkarılmaz**. Bu yüzden veride
  çok nadirdir (tüm veri setinde `level = BOTH` olan yalnızca **2 segment**
  var → 3 designatedPoint, 1 navaid).
- **`Other` fallback değildir.** Yalnızca AIXM'in `OTHER(:(\w|_){1,58})?`
  desenine uyan gerçek bir değer varsa `1` olur (kullanıcı kararı). `level`
  alanı **boş** olan segmentler hiçbir bayrağa katkı vermez — böyle bir noktada
  dördü de `0` kalır (bağlı olduğu için `NULL` değil).

Ölçüldü: `designatedPoints`'te **181 nokta** rota ağına bağlı olduğu hâlde
hiçbir segmentinde `level` bulunmadığı için dört bayrağı da `0`
(`routeSegments_level` 212 satırda boş). Bu bir eksiklik değil, kaynakta o
alanın olmamasıdır.

> Mevcut veride `OTHER` desenli `level` **hiç geçmiyor**, bu yüzden
> `associatedLevelOther` tüm satırlarda `0`. Kural yine de enum'un tamamını
> karşılıyor; veri gelirse çalışır.

### 4.3 Rota tipi bayrakları — BOOLEAN × 3

| Sütun | Anlamı |
|---|---|
| `atsStatus_associatedTypeAts` | ilişkili segmentlerden en az biri `route_type = ATS` |
| `atsStatus_associatedTypeNat` | en az biri `route_type = NAT` |
| `atsStatus_associatedTypeOther` | en az biri `route_type` = **gerçek** `OTHER` veya `OTHER:<kod>` |

Seviye bayraklarıyla (§4.2) **birebir aynı mantık**: her biri bağımsızdır,
birbirini dışlamaz, `Other` bir fallback değildir ve `route_type` taşımayan bir
segment hiçbir bayrağa katkı vermez.

Tek farkı **kaynağı**: `route_type` sütunu RouteSegment'in değil, segmentin
bağlı olduğu **Route feature'ının** alanıdır (bu yüzden `routeSegments_` değil
`route_` önekini taşır). AIXM tipi `CodeRouteType`:

| Değer | Anlamı (XSD `CodeRouteBaseType`) |
|---|---|
| `ATS` | ICAO Annex 11'de tanımlı ATS rotası |
| `NAT` | North Atlantic Track (Organized Track System'in parçası) |
| `OTHER(:(\w|_){1,58})?` | açık liste uzantısı |

**Ölçülen kaynak dağılımı** (92.976 segment): `ATS` = **92.764**,
`OTHER` = **212**, `NAT` = **0**, boş = **0**.

> Veride `NAT` hiç geçmiyor, bu yüzden `associatedTypeNat` tüm satırlarda `0`.
> `associatedLevelOther`'da olduğu gibi kural yine de enum'un tamamını
> karşılıyor; veri gelirse çalışır.

> `OTHER` tipli 212 segment, `level` alanı boş olan **tam olarak aynı** 212
> segmenttir (ölçüldü, kesişim 212/212). §4.2'de "bağlı ama hiç `level` yok"
> diye sayılan 181 designatedPoint da bu segmentlerin uçlarıdır — yani o
> noktalarda dört seviye bayrağı `0` iken `associatedTypeOther` `1` olur.

### 4.4 `atsStatus_reportingAssociation` — TEXT (JSON)

Hangi segmentte hangi raporlama türünün işaretlendiği. Yalnızca raporlama türü
**dolu olan** uçlar listelenir (boş olanlar listeyi şişirirdi — 90.284 segment
ucu raporlama taşımıyor).

```json
[
  {"segmentId": 90274, "role": "END",   "reportingATC": "COMPULSORY"},
  {"segmentId": 90275, "role": "START", "reportingATC": "COMPULSORY"}
]
```

| Alan | Anlamı |
|---|---|
| `segmentId` | `routeSegments.id` — doğrudan JOIN edilebilir |
| `role` | `START` / `END` — noktanın o segmentteki ucu |
| `reportingATC` | AIXM `CodeATCReportingType`: `COMPULSORY` / `ON_REQUEST` / `NO_REPORT` |

`role` ayrı alan olarak taşınır çünkü bir nokta aynı segmentin hem başı hem
sonu olabilir; ayrıca raporlama türü uca göre okunur (nokta segmentin başıysa
`routeSegments_startReportingATC`, sonuysa `routeSegments_endReportingATC`).

### 4.5 `atsStatus_depictionCompulsory` — BOOLEAN

İlişkili segmentlerden **herhangi birinde** raporlama türü `COMPULSORY` mi?
Kaynak: `routeSegments_startReportingATC` / `_endReportingATC`.

Kapıya bağlıdır: nokta rota ağına bağlı değilse `NULL`.

> Önceki sürümlerde bunun yanında `depictionOnRequest` / `depictionNonCompulsory`,
> `depictionRNAV` / `depictionCONV` / `depictionNonRNAV` bayrakları vardı.
> Hepsi **kaldırıldı** (kullanıcı kararı); seyrüsefer sınıflandırması artık
> §4.6'daki `depictionNav` enum'uyla yapılıyor.

### 4.6 `atsStatus_depictionNav` — TEXT (enum)

Seyrüsefer gösterim sınıfı. **Sıralı** bir karar zinciridir; ilk uyan kazanır.

| Sıra | Değer | Koşul |
|---|---|---|
| 1 | `CONV` | Bağlı ATS rotalarından biri `CONV` veya `TACAN`. **Ancak `type=COORD` olan DesignatedPoint `CONV` OLAMAZ** — koordinattan türetilmiş nokta klasik seyrüsefer yardımcısıyla tanımlanmaz. Navaid'de bu istisna yoktur. |
| 2 | `RNAVFlyBy` | `type=COORD` DesignatedPoint **koşulsuz**; ayrıca DP/Navaid'de bağlı rotalardan biri `PBN` ise |
| 3 | `RNAVFlyOver` | **Şu an hiçbir koşula bağlanmadı.** Fly-over / fly-by ayrımını verecek kaynak alanı henüz yok; ileride kullanılacak. Uydurma sınıflandırma yapılmadığı için bilerek üretilmiyor. |
| 4 | `OTHER` | Son fallback |

`CONV`/`TACAN` ve `PBN` değerleri AIXM `CodeNavigationType` enum'undan gelir
(`routeSegments_aircraftCapability` JSON'undaki `navigationType`).

### 4.7 `atsStatus_depictionSIGPointBasicFunc` — TEXT (enum)

Önemli noktanın temel işlevi. Yine sıralı karar zinciri:

| Sıra | Değer | Koşul |
|---|---|---|
| 1 | `NAVAID` | Rota elemanı olan **her** navaid. DesignatedPoint asla almaz. |
| 2 | `VFR_REP` | DesignatedPoint `type=VRP` ise |
| 3 | `WPT` | `depictionNav` **`CONV` DEĞİLSE** ve (`type=COORD` koşulsuz **veya** bağlı **tüm** rota segmentleri `PBN` ise) |
| 4 | `INT` | `type=BRG_DIST` ise, **veya** bağlı rotalardan biri `CONV`/`TACAN` ise |
| 5 | `OTHER` | DesignatedPoint için son fallback |

"Bağlı tüm segmentler PBN" sayımında segment kimliği **küme** olarak tutulur —
bir nokta aynı segmentin hem başı hem sonu olabilir, sayım bozulmasın diye.

### 4.8 `atsStatus_depictionNavAndREP` — TEXT (enum)

`depictionNav` ile `depictionCompulsory`'nin **bileşkesi**. Tek sütunda hem
seyrüsefer sınıfını hem raporlama zorunluluğunu taşır; QGIS'te tek bir
kategorize alanından sembol üretmek için (kullanıcı kararı).

```
atsStatus_depictionNavAndREP = <depictionNav> + ("_Comp" | "_NonComp")
```

Sonek `depictionCompulsory = 1` ise `_Comp`, `0` ise `_NonComp`.

| | `_Comp` | `_NonComp` |
|---|---|---|
| `CONV` | `CONV_Comp` | `CONV_NonComp` |
| `RNAVFlyBy` | `RNAVFlyBy_Comp` | `RNAVFlyBy_NonComp` |
| `RNAVFlyOver` | `RNAVFlyOver_Comp` | `RNAVFlyOver_NonComp` |
| `OTHER` | `OTHER_Comp` | `OTHER_NonComp` |

Enum listesi **elle yazılmaz**, `DEPICTION_NAV` × `("Comp","NonComp")`
çarpımından türetilir (`gpkg/schema.DEPICTION_NAV_AND_REP`) — `depictionNav`
enum'u değişirse bu liste kendiliğinden güncellenir, iki yerde birbirinden
kopma riski olmaz.

Kapıya bağlıdır: nokta rota elemanı değilse `NULL`.

### 4.9 Alanlar arası doğrulama

İki tür denetim var; ikisinin de kural listesi `gpkg/validation_rules.py`'de
**tek yerde** tutulur, `compute_ats_status` oradan okuyup uygular.

**a) Çakışma denetimi** (`ATS_STATUS_CONFLICTS`)

`atsStatus_depictionNav = CONV` ile `atsStatus_depictionSIGPointBasicFunc = WPT`
**birlikte olamaz** — `WPT` kuralı zaten `CONV` dışlıyor. Yine de savunma
amaçlı denetlenir. Kod: `depictionNav_CONV_ile_WPT_birlikte_olamaz`.

**b) Bileşke denetimi — üç sütun** (`ATS_STATUS_COMPOSITES`)

`depictionNavAndREP`, iki bileşeniyle birebir uyuşmalıdır:

```
depictionNavAndREP == depictionNav + ("_Comp" if depictionCompulsory else "_NonComp")
```

Üç sütun birlikte karşılaştırılır; uyuşmazlık
`depictionNavAndREP_bilesenleriyle_uyusmuyor` koduyla **error** olarak
`errored-features.csv`'ye yazılır.

Her iki denetim de `validate_row`'da **değil** `compute_ats_status` içinde
yapılır: bu alanlar satır yazıldıktan **sonra** `UPDATE` ile doldurulduğu için
satır doğrulamasının göremeyeceği bir aşamadadırlar.

Ölçüldü: her iki katmanda çakışma **0**, bileşke uyuşmazlığı **0**.

### 4.10 Kapı kuralı istisnasızdır

`depictionNav` ve `depictionSIGPointBasicFunc` de **kapıya bağlıdır**:
`isElementOfRouteSegment = 0` olan satırlarda diğer alanlar gibi `NULL`
kalırlar.

Tip tabanlı kuralları (`COORD` / `VRP` olmak, navaid tablosunda bulunmak) rota
bağlantısı olmadan da teknik olarak çalışabilirdi — ama bir noktanın **rota
gösterim sınıfı ancak bir ATS rotasının parçasıysa anlamlıdır** (kullanıcı
kararı). Bu yüzden `NAVAID` de "navaids tablosundaki her satır" değil, "rota
elemanı olan her navaid" anlamına gelir.

Doğrulandı: her iki katmanda kapı ihlali **0**, bağlı olup boş kalan satır **0**.

---

## 5. Ölçülen dağılım (son koşu)

### `designatedPoints` (152.061 satır)

| Alan | Değer | Adet |
|---|---|---:|
| `isElementOfRouteSegment` | `1` | **41.165** |
| | `0` | 110.896 |
| `associatedLevelLower` | `1` | 38.309 |
| `associatedLevelUpper` | `1` | 6.800 |
| `associatedLevelBoth` | `1` | 3 |
| `associatedLevelOther` | `1` | 0 |
| — hem Upper hem Lower | | 4.125 |
| `associatedTypeAts` | `1` | 40.984 |
| `associatedTypeNat` | `1` | 0 |
| `associatedTypeOther` | `1` | 181 |
| — bağlı ama hiç level yok | dördü de `0` | 181 |
| `reportingAssociation` | dolu | 623 |
| `depictionCompulsory` | `1` | 448 |
| `depictionNav` | `OTHER` | 40.540 |
| | `CONV` | 353 |
| | `RNAVFlyBy` | 272 |
| | `RNAVFlyOver` | 0 (koşulu yok) |
| | `NULL` (bağlı değil) | 110.896 |
| `depictionSIGPointBasicFunc` | `OTHER` | 40.396 |
| | `INT` | 353 |
| | `WPT` | 235 |
| | `VFR_REP` | 181 |
| | `NAVAID` | 0 (DP asla almaz) |
| | `NULL` (bağlı değil) | 110.896 |
| `depictionNavAndREP` | `OTHER_NonComp` | 40.540 |
| | `CONV_Comp` | 267 |
| | `RNAVFlyBy_Comp` | 181 |
| | `RNAVFlyBy_NonComp` | 91 |
| | `CONV_NonComp` | 86 |
| | `NULL` (bağlı değil) | 110.896 |

### `navaids` (9.357 satır)

| Alan | Değer | Adet |
|---|---|---:|
| `isElementOfRouteSegment` | `1` | **3.296** |
| | `0` | 6.061 |
| `associatedLevelLower` | `1` | 3.255 |
| `associatedLevelUpper` | `1` | 757 |
| `associatedLevelBoth` | `1` | 1 |
| `associatedLevelOther` | `1` | 0 |
| — hem Upper hem Lower | | 717 |
| `associatedTypeAts` | `1` | 3.296 |
| `associatedTypeNat` | `1` | 0 |
| `associatedTypeOther` | `1` | 0 |
| `reportingAssociation` | dolu | 66 |
| `depictionCompulsory` | `1` | 63 |
| `depictionNav` | `OTHER` | 3.230 |
| | `CONV` | 54 |
| | `RNAVFlyBy` | 12 |
| | `NULL` (bağlı değil) | 6.061 |
| `depictionSIGPointBasicFunc` | `NAVAID` | **3.296** (rota elemanı olanlar) |
| | `NULL` (bağlı değil) | 6.061 |
| `depictionNavAndREP` | `OTHER_NonComp` | 3.230 |
| | `CONV_Comp` | 53 |
| | `RNAVFlyBy_Comp` | 10 |
| | `RNAVFlyBy_NonComp` | 2 |
| | `CONV_NonComp` | 1 |
| | `NULL` (bağlı değil) | 6.061 |

Noktaların çoğunun (110.896) rota ağına bağlı olmaması beklenen sonuçtur —
bunlar ağırlıkla prosedür noktalarıdır (yaklaşma/kalkış fix'leri, `type=OTHER`
16.912 kayıt) ve bir ATS rotasının ucu değildirler.

---

## 6. Kullanım

**Yalnızca rota noktaları** (QGIS → Layer Properties → Source → Query Builder):

```sql
atsStatus_isElementOfRouteSegment = 1
```

**Zorunlu raporlama noktaları:**

```sql
atsStatus_isElementOfRouteSegment = 1 AND atsStatus_depictionCompulsory = 1
```

**North Atlantic Track noktaları** (veride şu an yok, kural hazır):

```sql
atsStatus_associatedTypeNat = 1
```

**Üst saha RNAV noktaları:**

```sql
(atsStatus_associatedLevelUpper = 1 OR atsStatus_associatedLevelBoth = 1)
AND atsStatus_depictionNav = 'RNAVFlyBy'
```

**Kavşak (intersection) noktaları — klasik seyrüsefer sembolü için:**

```sql
atsStatus_depictionSIGPointBasicFunc = 'INT'
```

**VFR raporlama noktaları:**

```sql
atsStatus_depictionSIGPointBasicFunc = 'VFR_REP'
```

**Bir noktanın raporlama ayrıntısını segmentlerle birleştirmek:**

```sql
SELECT d.designatedPoints_designator,
       json_extract(j.value, '$.segmentId')    AS segmentId,
       json_extract(j.value, '$.role')         AS role,
       json_extract(j.value, '$.reportingATC') AS reportingATC
FROM designatedPoints d, json_each(d.atsStatus_reportingAssociation) j
WHERE d.atsStatus_reportingAssociation IS NOT NULL;
```

---

## 7. Doğrulama

| Kontrol | Sonuç |
|---|---|
| Kapı kuralı ihlali (`=0` iken diğerleri dolu) | **0** (her iki katman) |
| `isElementOfRouteSegment` NULL kalan satır | **0** |
| `designatedPoints` bağlı sayısı — bağımsız `EXISTS` sorgusuyla | 41.165 = 41.165 ✅ |
| Uçtan uca örnek (`ABDIK`, `type=ICAO`, 12 segment) | `Upper=1 Lower=1`, `Compulsory=1`, `Nav=CONV` (bağlı rotalarda CONV var), `SIGFunc=INT` (CONV olduğu için WPT olamaz), `NavAndREP=CONV_Comp` — zincirin tamamı elle yeniden hesaplandı, birebir ✅ |
| `associatedType*` kapı kuralı ihlali | **0** (her iki katman) |
| `associatedTypeAts` + `associatedTypeOther` toplamı = bağlı nokta sayısı | dP 40.984 + 181 = **41.165** ✅, navaids 3.296 + 0 = **3.296** ✅ |
| `COORD` → `RNAVFlyBy` + `WPT` (koşulsuz kural) | ihlal **0** |
| `COORD` → asla `CONV` | ihlal **0** |
| `VRP` → `VFR_REP` | ihlal **0** |
| `NAVAID` yalnızca navaids'te, rota elemanı olanların hepsinde | ihlal **0** (3.296/3.296) |
| `CONV` + `WPT` çakışması | **0** |
| Bileşke uyuşmazlığı (`NavAndREP` ≠ `Nav` + `Compulsory`) | **0** (her iki katman) |
| Kapı ihlali (`=0` iken `depictionNav`/`SIGPointBasicFunc` dolu) | **0** |
| Bağlı olup `depictionNav`/`SIGPointBasicFunc` boş kalan | **0** |

---

## 8. Karar geçmişi

**Seviye alanı iki kez değişti.** İlk sürümde tek bir TEXT sütundu
(`atsStatus_associatedRouteLevels`), değeri `{LOWER, UPPER}` küme birleşimiyle
`CodeLevelType` enum'una çökertiliyordu (`LOWER` / `UPPER` / `BOTH`).

Kullanıcı kararıyla dört bağımsız boolean'a çevrildi ve **birleştirme
kaldırıldı**: artık her bayrak ham `level` değerinin varlığını bildirir. Sonuç
olarak `Both`, `UPPER`+`LOWER` birleşiminden türetilmediği için nadir bir
değere dönüştü (3 + 1 kayıt) — bu beklenen davranıştır, bilgi kaybı değildir:
eski `BOTH` sayısına karşılık gelen noktalar artık `Upper=1, Lower=1` ile
işaretlidir (4.125 + 703).
