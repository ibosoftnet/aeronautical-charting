# AIXM 5.2 — Bir Hava Sahası Nasıl Eklenir?

Bu doküman bir hava sahasını AIXM 5.2'ye elle ya da yeni bir üreticiyle
eklerken izlenecek sırayı, gereken veri setini ve XSD'den geçen XML
iskeletlerini verir. Model: [`AIXM_Airspace_Model_Overview.md`](AIXM_Airspace_Model_Overview.md),
tüm alanlar: [`AIXM_Airspace_Attributes.md`](AIXM_Airspace_Attributes.md).

> Bu projede `data-sources/TRNC` ve `data-sources/tailored-LT` kaynaklarının
> AIXM dosyaları **doğrudan elle düzenlenir** (JSON/üretici yok); bu doküman
> onları düzenlerken ve yeni üretici yazarken uyulacak kuralları anlatır.
> `ibosoft` kaynağı GeoJSON'dan üretilir (`data-airspace/tailored_geojson.py`).

## 1. Bağımlılık sırası

Bir Airspace tek başına yazılabilir — zorunlu bir referansı yoktur. Referans
verdiği feature'lar varsa onlar birleşik veride bulunmalıdır:

| Referans | Hedef feature | Ne zaman |
|---|---|---|
| `contributorAirspace/…/theAirspace` | başka bir `Airspace` | geometri başka sahadan alınıyorsa |
| `protectedRoute` | `Route` | saha bir rotayı koruyorsa |
| `associatedLevels/…/discreteLevelSeries` | `StandardLevelColumn` | seviyeler standart seviye kümesine bağlıysa |
| `activation/…/user`, `specialDateAuthority` | `OrganisationAuthority` | kullanıcı / özel gün kuruluşu belirtiliyorsa |

Referanslar `xlink:href="urn:uuid:<UUID>"` biçimindedir ve hedefin
`gml:identifier`'ına bakar.

## 2. Veri seti — ne girilmeli?

| Bilgi | AIXM alanı | Not |
|---|---|---|
| Tür | `type` | `CodeAirspaceType` listesi (CTR, TMA, R, D, P, FIR …) |
| Kod | `designator` | Yayımlanmış kod; yoksa yazılmaz |
| Ad | `name` | Yayımlandığı gibi |
| Yatay sınır | `geometryComponent/…/horizontalProjection` | Poligon (enlem boylam), kapalı halka |
| Dikey sınırlar | `upperLimit`/`lowerLimit` (+ `uom`, `…Reference`) | Volume'da |
| Sınıf | `class/…/classification` | Seviyeye bağlıysa `associatedLevels` |
| Kullanım | `activation` | Aktivite, durum, saatler |
| Notlar | `annotation` | Yayımlanmış açıklamalar |
| Kimlik | `gml:identifier` | Kalıcı UUID — aynı saha her güncellemede aynı UUID'i almalı |

### Dikkat edilecek biçim kuralları (şemadan)

| Kural | Kaynak |
|---|---|
| `name`, `localType`: 1-60 karakter, yalnız ASCII harf/rakam ve `, !"&#$%'()*+-./:;<=>?@[\]^_\|{}` | `TextNameBaseType` deseni |
| `designator`: 1-10 karakter; büyük harf, rakam, aynı işaretler | `CodeAirspaceDesignatorBaseType` (`Character3Type`) |
| Dikey değer: `[+-]` + en fazla 8 basamak + ondalık **veya** `UNL`/`GND`/`FLOOR`/`CEILING` | `ValDistanceVerticalBaseType` deseni |
| Dikey `uom`: `FT`, `M`, `FL`, `SM` (opsiyonel nitelik) | `UomDistanceVerticalType` |
| Kod listesi dışı değer: `OTHER:<KOD>` (1-58 karakter, harf/rakam/_) | her `Code*Type`'ın union deseni |
| Koordinat sırası `gml:posList`'te **enlem boylam** (EPSG:4326) | `srsName="urn:ogc:def:crs:EPSG::4326"` |
| Halka yönü: kaynakta serbest; birleşik AIXM'de birleştirici RFC 7946'ya getirir (dış saat yönünün tersi, delik saat yönü — harita düzleminde) | proje kuralı, `Common_Builder_Behaviour.md` §4.1 |
| Her nesne (`AirspaceGeometryComponent`, `AirspaceVolume`, `Surface`, `Note` …) belge içinde tekil `gml:id` taşır | GML |
| `gml:validTime` ve `interpretation` her TimeSlice'ta **zorunlu** | `AbstractAIXMTimeSliceType` |
| `extension` TimeSlice'ın **son** elemanıdır | `AirspaceTimeSliceType` dizisi |

## 3. XML iskeletleri

Hepsi bir `message:hasMember` içinde yer alır. Namespace önekleri:
`aixm` = `http://www.aixm.aero/schema/5.2`, `gml` = `http://www.opengis.net/gml/3.2`,
`ibosoftais` = projenin extension namespace'i. Değerler **kurgusaldır**.

### 3.1 Basit CTR (tek hacim, tek sınıf)

```xml
<aixm:Airspace gml:id="EX_CTR">
  <gml:identifier codeSpace="urn:uuid:">4F1C0E6A-0000-5000-8000-000000000001</gml:identifier>
  <aixm:timeSlice>
    <aixm:AirspaceTimeSlice gml:id="EX_CTR_TS">
      <gml:validTime>
        <gml:TimePeriod gml:id="EX_CTR_TP">
          <gml:beginPosition indeterminatePosition="unknown"/>
          <gml:endPosition indeterminatePosition="unknown"/>
        </gml:TimePeriod>
      </gml:validTime>
      <aixm:interpretation>BASELINE</aixm:interpretation>
      <aixm:sequenceNumber>1</aixm:sequenceNumber>
      <aixm:correctionNumber>0</aixm:correctionNumber>
      <aixm:type>CTR</aixm:type>
      <aixm:designator>LTXX</aixm:designator>
      <aixm:name>EXAMPLE CTR</aixm:name>
      <aixm:class>
        <aixm:AirspaceLayerClass gml:id="EX_CTR_CLS">
          <aixm:classification>D</aixm:classification>
        </aixm:AirspaceLayerClass>
      </aixm:class>
      <aixm:geometryComponent>
        <aixm:AirspaceGeometryComponent gml:id="EX_CTR_GC">
          <aixm:operation>BASE</aixm:operation>
          <aixm:operationSequence>1</aixm:operationSequence>
          <aixm:theAirspaceVolume>
            <aixm:AirspaceVolume gml:id="EX_CTR_AV">
              <aixm:upperLimit uom="FT">4500</aixm:upperLimit>
              <aixm:upperLimitReference>MSL</aixm:upperLimitReference>
              <aixm:lowerLimit>GND</aixm:lowerLimit>
              <aixm:horizontalProjection>
                <aixm:Surface gml:id="EX_CTR_SF" srsName="urn:ogc:def:crs:EPSG::4326">
                  <gml:patches>
                    <gml:PolygonPatch>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList>40.0 32.0 40.0 33.0 39.5 33.0 39.5 32.0 40.0 32.0</gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:PolygonPatch>
                  </gml:patches>
                </aixm:Surface>
              </aixm:horizontalProjection>
            </aixm:AirspaceVolume>
          </aixm:theAirspaceVolume>
        </aixm:AirspaceGeometryComponent>
      </aixm:geometryComponent>
      <aixm:extension>
        <ibosoftais:AirspaceDataProvenance gml:id="EX_CTR_PROV">
          <ibosoftais:dataProvider>Ibosoft AIS</ibosoftais:dataProvider>
          <ibosoftais:dataOriginator>DHMI Turkiye</ibosoftais:dataOriginator>
          <ibosoftais:dataEffectivity>01 OCT 2026 (AIRAC 2610)</ibosoftais:dataEffectivity>
        </ibosoftais:AirspaceDataProvenance>
      </aixm:extension>
    </aixm:AirspaceTimeSlice>
  </aixm:timeSlice>
</aixm:Airspace>
```

### 3.2 Çok sınıflı TMA (seviyeye bağlı sınıf)

Yalnız TimeSlice'ın `class` kısmı (diğer alanlar §3.1 gibi). Volume
sahanın bütün dikey aralığını (4500 FT MSL – FL195) taşır; her sınıf kendi
bandını `associatedLevels` ile söyler:

```xml
<aixm:class>
  <aixm:AirspaceLayerClass gml:id="EX_TMA_CLS_C">
    <aixm:classification>C</aixm:classification>
    <aixm:associatedLevels>
      <aixm:AirspaceLayer gml:id="EX_TMA_LYR_C">
        <aixm:upperLimit uom="FL">195</aixm:upperLimit>
        <aixm:upperLimitReference>STD</aixm:upperLimitReference>
        <aixm:lowerLimit uom="FL">95</aixm:lowerLimit>
        <aixm:lowerLimitReference>STD</aixm:lowerLimitReference>
      </aixm:AirspaceLayer>
    </aixm:associatedLevels>
  </aixm:AirspaceLayerClass>
</aixm:class>
<aixm:class>
  <aixm:AirspaceLayerClass gml:id="EX_TMA_CLS_D">
    <aixm:classification>D</aixm:classification>
    <aixm:associatedLevels>
      <aixm:AirspaceLayer gml:id="EX_TMA_LYR_D">
        <aixm:upperLimit uom="FL">95</aixm:upperLimit>
        <aixm:upperLimitReference>STD</aixm:upperLimitReference>
        <aixm:lowerLimit uom="FT">4500</aixm:lowerLimit>
        <aixm:lowerLimitReference>MSL</aixm:lowerLimitReference>
      </aixm:AirspaceLayer>
    </aixm:associatedLevels>
  </aixm:AirspaceLayerClass>
</aixm:class>
```

### 3.3 Bileşik saha: `BASE` + `SUBTR` (TMA, CTR hariç)

Yalnız `geometryComponent` kısmı. İkinci bileşenin hacmi ya kendi
poligonunu taşır ya da (burada) CTR feature'ına `contributorAirspace` ile
bağlanır:

```xml
<aixm:geometryComponent>
  <aixm:AirspaceGeometryComponent gml:id="EX_TMA_GC1">
    <aixm:operation>BASE</aixm:operation>
    <aixm:operationSequence>1</aixm:operationSequence>
    <aixm:theAirspaceVolume>
      <aixm:AirspaceVolume gml:id="EX_TMA_AV1">
        <aixm:upperLimit uom="FL">195</aixm:upperLimit>
        <aixm:upperLimitReference>STD</aixm:upperLimitReference>
        <aixm:lowerLimit uom="FT">4500</aixm:lowerLimit>
        <aixm:lowerLimitReference>MSL</aixm:lowerLimitReference>
        <aixm:horizontalProjection>
          <aixm:Surface gml:id="EX_TMA_SF1" srsName="urn:ogc:def:crs:EPSG::4326">
            <gml:patches>
              <gml:PolygonPatch>
                <gml:exterior>
                  <gml:LinearRing>
                    <gml:posList>41.0 31.0 41.0 34.0 39.0 34.0 39.0 31.0 41.0 31.0</gml:posList>
                  </gml:LinearRing>
                </gml:exterior>
              </gml:PolygonPatch>
            </gml:patches>
          </aixm:Surface>
        </aixm:horizontalProjection>
      </aixm:AirspaceVolume>
    </aixm:theAirspaceVolume>
  </aixm:AirspaceGeometryComponent>
</aixm:geometryComponent>
<aixm:geometryComponent>
  <aixm:AirspaceGeometryComponent gml:id="EX_TMA_GC2">
    <aixm:operation>SUBTR</aixm:operation>
    <aixm:operationSequence>2</aixm:operationSequence>
    <aixm:theAirspaceVolume>
      <aixm:AirspaceVolume gml:id="EX_TMA_AV2">
        <aixm:contributorAirspace>
          <aixm:AirspaceVolumeDependency gml:id="EX_TMA_DEP">
            <aixm:dependency>FULL_GEOMETRY</aixm:dependency>
            <aixm:theAirspace xlink:href="urn:uuid:4F1C0E6A-0000-5000-8000-000000000001"/>
          </aixm:AirspaceVolumeDependency>
        </aixm:contributorAirspace>
      </aixm:AirspaceVolume>
    </aixm:theAirspaceVolume>
  </aixm:AirspaceGeometryComponent>
</aixm:geometryComponent>
```

> Bu projenin GeoPackage aşaması `contributorAirspace` ile tanımlanan (kendi
> poligonu olmayan) bir bileşenin geometrisini **hesaplamaz**: satır yazılmaz,
> hata loglanır (poligon uydurulmaz). Bileşik sahayı GeoPackage'a geçirmek
> için her bileşenin kendi `horizontalProjection`'ı olmalıdır.

### 3.4 FIR / UIR + projenin extension kutuları

`type=FIR`, dikey limit yok (kaynak vermiyorsa yazılmaz), ICAO bölge kodları
`AirspaceExtension`'da; provenance kutusu ayrı `extension`'da ve en sonda:

```xml
<aixm:extension>
  <ibosoftais:AirspaceExtension gml:id="EX_FIR_EXT">
    <ibosoftais:regionIcao>EUR</ibosoftais:regionIcao>
    <ibosoftais:regionSupProc>EUR</ibosoftais:regionSupProc>
  </ibosoftais:AirspaceExtension>
</aixm:extension>
<aixm:extension>
  <ibosoftais:AirspaceDataProvenance gml:id="EX_FIR_PROV">
    <ibosoftais:dataProvider>ICAO GIS</ibosoftais:dataProvider>
    <ibosoftais:dataEffectivity>2021 (Non-AIRAC)</ibosoftais:dataEffectivity>
  </ibosoftais:AirspaceDataProvenance>
</aixm:extension>
```

## 4. Kontrol listesi

- [ ] `gml:identifier` kalıcı (aynı saha her koşuda aynı UUID) ve belgede tekil
- [ ] Her nesnenin `gml:id`'si belgede tekil
- [ ] `name`/`localType` ASCII ve ≤ 60, `designator` ≤ 10
- [ ] Poligon halkası kapalı (ilk = son nokta), koordinatlar **enlem boylam**
- [ ] Dikey değer sayı ya da `UNL`/`GND`/`FLOOR`/`CEILING`; `uom` ve referans kaynaktaki gibi (uydurulmadı)
- [ ] Liste dışı kod değeri `OTHER:<KOD>` biçiminde
- [ ] Çok bileşenli sahada tek `BASE`, sıra numaraları tekil
- [ ] Çok sınıflı sahada her sınıfın `associatedLevels`'ı var
- [ ] `extension`'lar TimeSlice'ın en sonunda; provenance kutusu var
- [ ] Dosya `common/data_build_common/validate_aixm.py` ile **0 hata**

## 5. Bu dokümandaki örneklerin doğrulanması

§3.1'in tamamı ve §3.2–§3.4 parçaları ile
[`AIXM_Airspace_Activation_Schedule.md`](AIXM_Airspace_Activation_Schedule.md)
§3 örnekleri, geçerli `AirspaceTimeSlice`'lara yerleştirilip ortak doğrulayıcıyla
(AIXM 5.2 + extension şeması) **0 hata** ile doğrulandı.
