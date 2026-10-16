# AIXM 5.2 — Hava sahası (Airspace) dokümanları

Bu dizin AIXM 5.2'de bir hava sahasının nasıl modellendiğini anlatır.
Kaynak: AIXM 5.2 XSD seti (`AIXM_Features.xsd`, `AIXM_DataTypes.xsd`,
`AIXM_AbstractGML_ObjectTypes.xsd`) ve onun açıklamalı kopyaları
(`../../common/docs/AIXM_Features_annotated.xsd`,
`../../common/docs/AIXM_DataTypes_annotated.xsd`). Tanım cümleleri bu
dosyalardaki `documentation` metinlerinden çevrilmiştir; buradaki hiçbir
yapı ya da değer listesi şemada olmayan bir şeyi iddia etmez.

## Doküman listesi (okuma sırası)

| # | Doküman | Ne anlatır |
|---|---|---|
| 1 | [`AIXM_Airspace_Model_Overview.md`](AIXM_Airspace_Model_Overview.md) | Airspace → geometri bileşeni → hacim zinciri, bileşik geometri, sınıf katmanları, dikey limitlerin anlamı, koridor, başka sahadan geometri alma |
| 2 | [`AIXM_Airspace_Attributes.md`](AIXM_Airspace_Attributes.md) | Tüm öznitelikler ve değer listeleri (tam referans) |
| 3 | [`AIXM_Airspace_Activation_Schedule.md`](AIXM_Airspace_Activation_Schedule.md) | Aktivasyon (`activation`) ve zaman çizelgesi (`Timesheet`) |
| 4 | [`AIXM_Airspace_How_To_Add.md`](AIXM_Airspace_How_To_Add.md) | Bir hava sahası nasıl eklenir: veri seti, biçim kuralları, XML iskeletleri, kontrol listesi |

Bu projede AIXM'den GeoPackage'a eşleme:
[`../AIXM_to_GeoPackage_Schema_Design.md`](../AIXM_to_GeoPackage_Schema_Design.md).
Projenin kendi extension elemanları (provenance kutusu, `AirspaceExtension`):
[`../../common/docs/Ibosoft_AIS_Extension.md`](../../common/docs/Ibosoft_AIS_Extension.md).

## Tek paragrafta model

Bir **Airspace**, hava trafiği için anlamlı, tanımlı üç boyutlu bir bölgedir.
Kimliği (`type`, `designator`, `name` …) feature'ın kendisindedir; **şekli**
ise bir ya da daha çok `geometryComponent`'ten gelir. Her bileşen bir
**AirspaceVolume** taşır — yatay izdüşüm (`horizontalProjection`, poligon)
artı dikey limitler — ve bir **işlem** (`BASE`, `UNION`, `INTERS`, `SUBTR`)
ile **sıra numarası** taşır; sahanın gerçek şekli bileşenlerin sırayla
birleştirilmesidir. Saha **sınıfı** (`class`) ayrı bir yapıdır ve yükseklik
bantlarına (`associatedLevels`) bağlanabilir: aynı saha farklı seviyelerde
farklı sınıfta olabilir. Sahanın ne zaman/neden aktif olduğu `activation` ile,
o aktivasyonun saatleri `Timesheet`'lerle anlatılır.

## Genel notlar (tüm dokümanlar için)

- **`OTHER` deseni.** Her `Code…Type` sabit listesi bir `union`'dır: listedeki
  değerler **veya** `OTHER(:(\w|_){1,58})?` deseni (`OTHER`, `OTHER:GSEC` …).
  Listede olmayan bir değer bu desenle yazılır, kaybolmaz.
- **`nilReason`.** Her `Code*`/`Val*`/`Text*` tipi bir `nilReason` niteliği
  taşıyabilir: değerin neden boş olduğunu söyler (`unknown`, `withheld` …).
  Bilinmeyen değer uydurulmaz; ya hiç yazılmaz ya `nilReason` ile boş yazılır.
- **Metin tipleri.** `name` ve `localType` `TextNameType`'tır: 1-60 karakter,
  yalnızca ASCII harf/rakam ve belirli işaretler. Türkçe harf (Ş, İ …) şemaya
  aykırıdır. `designator` `CodeAirspaceDesignatorType`'tır: 1-10 karakter,
  büyük harf/rakam/işaret.
- **Nesne vs feature.** `Airspace` bir **feature**'dır (`gml:identifier`
  UUID'si ve `timeSlice`'ı olur, başka feature'lar ona `xlink:href` ile
  referans verir). `AirspaceVolume`, `AirspaceLayerClass`,
  `AirspaceActivation` gibi yapılar **nesne**dir: yalnızca `gml:id` taşır,
  feature'ın içine gömülür.
