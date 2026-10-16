# Ibosoft AIS — AIXM 5.2 extension şeması

Şema: [`../schemas/ibosoftais-extension.xsd`](../schemas/ibosoftais-extension.xsd)
Namespace: `https://cdn.ibosoft.net.tr/aviation-data/schema/aixm/5.2/extension`
Önek: `ibosoftais` (Python'da tek tanım yeri: `data_build_common.aixm_reader.NS_IBOSOFTAIS`)
Şema sürümü: **1.0.0** (`<schema version="1.0.0">` ve başlık yorumu)

> Şema dosyası **public paylaşılacak**: içindeki yorum ve `documentation`
> metinleri İngilizcedir ve sistemin iç yapısına (dizinler, betikler,
> doğrulayıcı) değinmez. İç ayrıntılar yalnızca bu dokümanda tutulur.
> Şemada geriye uyumsuz değişiklik ana sürümü, yeni opsiyonel eleman ara
> sürümü artırır.

Namespace URI bir adres değil, kimliktir: ayrıştırıcılar onu indirmez.
Karşılaştırma birebir dizgi karşılaştırmasıdır (`http`/`https`, sondaki `/`
farklı namespace sayılır).

## 1. Mekanizma

AIXM 5.2'nin resmi genişletme noktası kullanılır: her feature'ın TimeSlice'ı
**sonunda** 0..∞ `aixm:extension` elemanı taşıyabilir
(`AIXM_Features.xsd`, `maxOccurs="unbounded"`). Her `extension`, o feature'a
özgü soyut başlığın (`aixm:Abstract<F>Extension`) ikame grubundaki **bir**
elemanı içerir. Bizim elemanlarımız bu başlıklara bağlanır ve
`aixm:AbstractExtensionType`'tan türer (dolayısıyla `gml:id` zorunludur).

XSD 1.0'da bir eleman yalnızca **tek** bir soyut başlığa bağlanabildiği için
aynı içerik farklı feature'larda **farklı adlı** elemanlarla taşınır
(`DesignatedPointDataProvenance`, `RouteDataProvenance` …); içerikleri aynı
tipi (`DataProvenanceType`) kullanır. Doğrulayıcı (`lxml`) XSD 1.0 kullanır.

Extension elemanlarının bir feature'da birden fazla olması geçerlidir; her
amaç kendi kutusundadır (kullanıcı kararı, "ayrı kutu" düzeni).

## 2. Provenance kutusu — `<F>DataProvenance`

AIXM'de veriyi kimin sağladığı / yayımladığı ve veri setinin geçerliliği için
alan yoktur. Birden çok kaynaktan birleşen veride bu bilgi feature başına
gerekir.

| Eleman | Tip | Zorunlu | Anlamı |
|---|---|---|---|
| `dataProvider` | `DataTextType` (boş olmayan metin) | evet | Veri setini sağlayan kurum/servis (`EUROCONTROL EAD SDO`, `Jeppesen`, `Ibosoft AIS`, `ICAO GIS`, `soaringweb.org`) |
| `dataOriginator` | `DataTextType` | hayır | Feature'ı asıl yayımlayan otorite (`DHMI TURKIYE`, `BULATSA` …). Kaynak vermiyorsa **yazılmaz** |
| `dataEffectivity` | `DataTextType` | evet | KAYNAK VERİ SETİNİN geçerliliği, serbest metin (`01 OCT 2026 (AIRAC 2610)`). Feature'ın kendi yürürlüğü değildir — o `gml:validTime`'dadır |

Kutunun `gml:id`'si: `<feature gml:id>_PROV`. Kutu TimeSlice'ın **son**
`aixm:extension`'ıdır.

Kutu tanımlı feature tipleri (17): `DesignatedPoint`, `Navaid`, `VOR`, `DME`,
`TACAN`, `NDB`, `Localizer`, `Glidepath`, `MarkerBeacon`, `SDF`, `Azimuth`,
`Elevation`, `DirectionFinder`, `Route`, `RouteSegment`, `ChangeOverPoint`,
`Airspace`. Yeni bir feature tipi üretilecekse şemaya önce onun elemanı
eklenir.

```xml
<aixm:DesignatedPointTimeSlice gml:id="EAD_DP_X_TS">
  …feature alanları…
  <aixm:extension>
    <ibosoftais:DesignatedPointDataProvenance gml:id="EAD_DP_X_PROV">
      <ibosoftais:dataProvider>EUROCONTROL EAD SDO</ibosoftais:dataProvider>
      <ibosoftais:dataOriginator>DHMI TURKIYE</ibosoftais:dataOriginator>
      <ibosoftais:dataEffectivity>01 OCT 2026 (AIRAC 2610)</ibosoftais:dataEffectivity>
    </ibosoftais:DesignatedPointDataProvenance>
  </aixm:extension>
</aixm:DesignatedPointTimeSlice>
```

**Kim yazar.** Kutuyu yazan kod üreticilerde değil
`data_build_common.provenance.append_box()`'tadır; tüm üreticiler bunu
çağırır. Değerler:

| Proje / kaynak | `dataProvider`, `dataEffectivity` | `dataOriginator` |
|---|---|---|
| ATS EAD-SDO | `data.json` | kaydın kendi `OrgCre/txtName`'i (kayıt başına) |
| ATS Jeppesen (NDB), ATS LT | `data.json` | `data.json` (Jeppesen'de boş → yazılmaz) |
| ATS TRNC, ATS tailored-LB | dosyanın içinde (elle) | dosyanın içinde |
| ATS MarkerBeacon (birleştiricide üretilir) | marker kaynağının `data.json`'ı | aynı (boş → yazılmaz) |
| ATS antimeridyen ara noktası | bölünen segmentin kutusu | aynı |
| Airspace Jeppesen, LT, LH, ICAO-FIR-UIR | `data.json` | `data.json` (Jeppesen ve ICAO-FIR-UIR'de yok → yazılmaz) |
| Airspace TRNC, tailored-LT, ibosoft | kayıt başına GeoJSON özelliklerinden | aynı |

**Kim okur.** Birleştiriciler (iptal/override doğal alanı `originator`) ve
GeoPackage (`data_provider`, `data_originator`, `data_effectivity` sütunları).
Kutusu olmayan feature **hata**dır: build durur, varsayılan değer atanmaz.

## 3. `ChangeOverPointExtension` (data-ats)

| Eleman | Tip | Anlamı |
|---|---|---|
| `distanceFromEnd` | `aixm:ValDistanceType` (`uom`, `nilReason` çekirdek `distance` ile aynı) | COP'un geçerli olduğu rota aralığının **SONUNDAN** mesafe. Çekirdek `distance` başlangıçtan ölçülür ve tek değerlidir; haritalar iki navaid'e olan mesafeyi birden gösterir |

`gml:id`: `<feature gml:id>_EXT`. Provenance kutusu bunun ARDINDAN ayrı bir
`aixm:extension` olarak gelir. Gerekçe ve değerlendirilen alternatifler:
[`data-ats/docs/AIXM_ChangeOverPoint_Attributes.md`](../../data-ats/docs/AIXM_ChangeOverPoint_Attributes.md) §5, §7.

## 4. `AirspaceExtension` (data-airspace)

| Eleman | Tip | Anlamı |
|---|---|---|
| `regionIcao` | `DataTextType`, opsiyonel | Hava sahasının ICAO hava seyrüsefer bölgesi. Bölgeler ICAO Doc 8144'te (Directives to Regional Air Navigation Meetings and Rules of Procedure for their Conduct) tanımlıdır. Değer kaynağın yazdığı gibidir — ICAO FIR veri setindeki `REGION` (ölçüldü: `EUR`, `ASIA`, `AFI`, `CARSAM`, `NAM`, `MID`, `NAT`) |
| `regionSupProc` | `DataTextType`, opsiyonel | ICAO Doc 7030 (Regional Supplementary Procedures) bölgesi. Değer kaynağın yazdığı gibidir — ICAO FIR veri setindeki `SUPP_REGIO` (ölçüldü: `EUR`, `ASIAPAC`, `AFI`, `CARSAM`, `NAM`, `MID`, `NAT`) |

Çekirdek AIXM'de bu bilgiler için alan yoktur. Bugün yalnız ICAO-FIR-UIR
kaynağı yazar (kullanıcı kararı). `gml:id`: `<feature gml:id>_EXT`.

## 5. Doğrulama

`data_build_common/validate_aixm.py` AIXM 5.2 setini ve bu şemayı tek bir
"schema assembly" sarmalayıcısıyla birlikte derler. Şema `aixm` namespace'ini
schemaLocation'sız import eder; asıl AIXM dosyasının yerini sarmalayıcı verir
(makineye özgü yol tek yerde kalır).
