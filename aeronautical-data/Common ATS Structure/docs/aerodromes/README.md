# AIXM 5.2 — Havalimanı (AirportHeliport) Dokümanları

Kaynak: `../AIXM_Features_annotated.xsd` + `../AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

Bu dizin, AIXM 5.2 şemasında bir havalimanının/helipadın ve altındaki tüm yüzey, ışık,
işaret ve yardımcı elemanların **nasıl modellendiğini** konu bağlamına göre anlatır.
Stil ve kapsam, üst dizindeki rota dokümanlarıyla (`AIXM_Route_*.md`) aynıdır: attribute
tabloları şemadan birebir çıkarılmıştır; yorum/çıkarım olan yerler ayrıca belirtilmiştir.

> **Proje notu:** Common ATS Structure pipeline'ının şu anki veri kaynaklarında (EAD-SDO,
> LT, TRNC, Jeppesen) **hiç `AirportHeliport`/`Runway`/`Taxiway`/`Apron` feature'ı yoktur**
> (yalnızca DesignatedPoint, Navaid ve ekipmanları, Route/RouteSegment). Bu dokümanlardaki
> XML örnekleri bu yüzden gerçek veriden değil şemadan türetilmiştir ve **temsili**
> değerler içerir (hayali `LTZZ` havalimanı). Kodlama biçimi (gml:id, `urn:uuid:`
> referansları, `BASELINE` timeSlice) projenin ürettiği `trnc-aixm-ats-structure.xml`
> dosyasıyla aynı tutulmuştur.

---

## Doküman listesi (okuma sırası)

| # | Dosya | Konu |
|---|---|---|
| 1 | [AIXM_Aerodrome_Model_Overview.md](AIXM_Aerodrome_Model_Overview.md) | Havalimanı modelinin genel mimarisi: feature hiyerarşisi, referans yönleri, geometri nerede taşınır, havalimanı dışından gelen referanslar |
| 2 | [AIXM_AirportHeliport_Attributes.md](AIXM_AirportHeliport_Attributes.md) | `AirportHeliport` feature'ının tüm attribute'ları + alt objeleri (Availability, Usage, ConditionCombination, ResponsibilityOrganisation, City, AltimeterSource) ve `AirportHeliportCollocation` |
| 3 | [AIXM_AirportHeliport_How_To_Add.md](AIXM_AirportHeliport_How_To_Add.md) | Bir havalimanını adım adım ekleme: bağımlılık sırası, minimum veri seti, tam XML örneği, kontrol listesi |
| 4 | [AIXM_Aerodrome_Components.md](AIXM_Aerodrome_Components.md) | Havalimanının altındaki **tüm** elemanların kataloğu (manevra alanı, apron alanı, ışık, işaret, tabela, koruma alanları, hidro/heli, çalışma alanı, hotspot...) |
| 5 | [AIXM_Runway_Attributes.md](AIXM_Runway_Attributes.md) | Pist ailesi: `Runway`, `RunwayDirection`, `RunwayCentrelinePoint`, declared distances, `RunwayElement`, `RunwayProtectArea`, `RunwayBlastPad`, `ArrestingGear`, RVR, VGSI, ALS, pist ışık/işaretleri |
| 6 | [AIXM_Taxiway_Attributes.md](AIXM_Taxiway_Attributes.md) | Taksi yolu ailesi: `Taxiway`, `TaxiwayElement`, `GuidanceLine`, `TaxiHoldingPosition`, taksi ışık/işaretleri, `AirportHotSpot` |
| 7 | [AIXM_Apron_Attributes.md](AIXM_Apron_Attributes.md) | Apron ailesi: `Apron`, `ApronElement`, `AircraftStand`, `DeicingArea`, `PassengerLoadingBridge`, `Road`, apron ışık/işaretleri |
| 8 | [AIXM_Heliport_TLOF_FATO.md](AIXM_Heliport_TLOF_FATO.md) | Helikopter alanları: FATO (`Runway.type=FATO`), `TouchDownLiftOff`, `TouchDownLiftOffSafeArea`, TLOF ışık/işaretleri |
| 9 | [AIXM_Surfaces_How_To_Add.md](AIXM_Surfaces_How_To_Add.md) | Pist, taksi yolu, apron ve park yeri yüzeylerini adım adım ekleme (geometri + ilişki + XML örnekleri) |
| 10 | [AIXM_Surface_Common_Objects.md](AIXM_Surface_Common_Objects.md) | Tüm yüzeylerin ortak kullandığı objeler: `SurfaceCharacteristics` (PCN/PCR), Availability/Usage, Contamination (SNOWTAM), geometri tipleri (`ElevatedPoint/Curve/Surface`), ışık ve işaret üst sınıfları |

---

## Tek paragrafta model

`AirportHeliport` bir "kap" değildir: kendi içinde pist/taksi yolu listesi tutmaz. Her alt
eleman kendi `associatedAirportHeliport` (veya `usedRunway`, `associatedTaxiway`...) alanıyla
**yukarıya** işaret eder — rota modelindeki `RouteSegment.routeFormed → Route` ile aynı
desen. `Runway`, `Taxiway` ve `Apron` **mantıksal** feature'lardır ve **geometri taşımaz**;
çizilebilir poligonlar `RunwayElement`, `TaxiwayElement`, `ApronElement`,
`RunwayProtectArea`, `AircraftStand.extent` vb. üzerindedir. Pistin eşik/son noktaları
`RunwayCentrelinePoint` feature'larıdır ve declared distance (TORA/TODA/ASDA/LDA) değerleri
bu noktaların üzerinde taşınır.

## Genel not (tüm dokümanlar için)

> Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Her `Code*`/`Val*`/`Text*Type` ayrıca
> `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u taşır. Tüm attribute'lar
> şemada `minOccurs="0"`'dır — AIXM şema düzeyinde **hiçbir alanı zorunlu tutmaz**;
> zorunluluk iş kurallarından (ICAO Annex 15 / PANS-AIM, AIXM Business Rules) gelir.
>
> Feature'ların ortak base tipleri (`AbstractAIXMFeatureType`, `AbstractAIXMTimeSliceType`)
> `AIXM_AbstractGML_ObjectTypes.xsd` dosyasında tanımlıdır; bu dosya elimizde olmadığından
> içerikleri şemadan teyit edilemedi. Projenin ürettiği XML'de kullanılan alanlar:
> `gml:identifier`, `gml:validTime`, `interpretation`, `sequenceNumber`, `correctionNumber`.
