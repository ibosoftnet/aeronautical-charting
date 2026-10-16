# AIXM 5.2 — Bir Havalimanı Nasıl Eklenir?

Kaynak: `AIXM_Features_annotated.xsd` + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2).
Kodlama biçimi projenin ürettiği `data-sources/TRNC/trnc-aixm-ats-structure.xml` ile aynıdır.

> Bu doküman **ekleme sürecini** anlatır. Attribute anlamları için
> `AIXM_AirportHeliport_Attributes.md`, yüzeylerin eklenmesi için
> `AIXM_Surfaces_How_To_Add.md` dosyasına bakın. Örnekteki `LTZZ / ORNEK` hayalidir.

---

## 1. Bağımlılık sırası

AIXM referansları `xlink:href="urn:uuid:<UUID>"` ile kurulur. Referans verilen feature'ın
UUID'si önceden belli olmalıdır (aynı mesajda olması şart değildir, ama tutarlılık için
aynı mesajda göndermek önerilir). Referans yönü **çocuktan ebeveyne** olduğundan sıra:

```
1. OrganisationAuthority     (opsiyonel — responsibleOrganisation için)
2. WeatherSource             (opsiyonel — altimeterSource için)
3. AirportHeliport           ◄── merkez
4. AirportHeliportCollocation (varsa, iki meydan hazır olduktan sonra)
5. Runway → RunwayDirection → RunwayCentrelinePoint (+declared distances) → RunwayElement
   → RunwayProtectArea / BlastPad / ArrestingGear / ışık / işaret      (AIXM_Surfaces_How_To_Add.md §2)
6. Taxiway → TaxiwayElement → GuidanceLine → TaxiHoldingPosition        (§3)
7. Apron → ApronElement → AircraftStand → DeicingArea ...               (§4)
8. Havalimanı dışı bağlar: Unit(TWR).airportLocation, Navaid.servedAirport /
   Navaid.runwayDirection (ILS), Procedure.airportHeliport, DesignatedPoint.airportHeliport ...
```

Bir `AirportHeliport` kaydı **tek başına geçerlidir**; pist/taksi yolu eklemek zorunlu
değildir. Rota/prosedür dünyasında yalnızca "meydan noktası" gerekiyorsa (ör. segment
noktası olarak `pointChoice_airportReferencePoint`), `designator` + `locationIndicatorICAO`
+ `ARP` içeren minimal kayıt yeterlidir.

---

## 2. Veri seti — ne girilmeli?

Şema hiçbir alanı zorunlu tutmaz (tümü `minOccurs="0"`). Aşağıdaki gruplama, AIP AD 2
bölümlerinin AIXM karşılıklarına göre yapılmıştır (eşleme yorumdur, şemada yazmaz):

| Öncelik | Alan(lar) | AIP karşılığı |
|---|---|---|
| **Temel (her meydan)** | `designator`, `locationIndicatorICAO`, `name`, `type`, `ARP` (gml:pos + `elevation`), `fieldElevation` | AD 2.1, AD 2.2 (1-3) |
| **Yüksek** | `designatorIATA`, `controlType`, `magneticVariation` + `dateMagneticVariation` + `magneticVariationChange`, `referenceTemperature`, `timeZone`, `servedCity`, `transitionAltitude`, `verticalDatum` | AD 2.2 |
| **Operasyonel** | `availability` (çalışma saatleri, PPR, kısıtlamalar), `responsibleOrganisation`, `contact` | AD 2.2, AD 2.3 |
| **Opsiyonel** | `certifiedICAO`, `certificationDate`/`ExpirationDate`, `privateUse`, `abandoned`, `aviationBoundary`, `altimeterSource`, `windDirectionIndicator`, `landingDirectionIndicator`, `segmentedCircleMarker`, `secondaryPowerSupply`, `lowestTemperature`, `transitionLevel`, `annotation` | AD 2.2, 2.9, 2.14, 2.15 |
| **Dinamik (NOTAM/SNOWTAM)** | `contaminant`, `availability.warning` | — |

### Dikkat edilecek biçim kuralları (şemadan)

| Alan | Kural |
|---|---|
| `locationIndicatorICAO` | **tam 4** büyük harf (`minLength=maxLength=4`, `[A-Z]*`) — rakam kabul etmez |
| `designatorIATA` | **tam 3** büyük harf |
| `designator` | 3-6 karakter, büyük harf veya rakam |
| `name` | max 60 karakter; küçük harf **kabul eder** (`TextNameType`) — `TextDesignatorType` alanları ise küçük harf **kabul etmez** |
| Mesafe/yükseklik | Değer + zorunlu `uom` attribute'u: `<aixm:fieldElevation uom="FT">325</aixm:fieldElevation>` |
| Manyetik sapma | Derece, `-180..180`, **uom yok** |
| Boş ama bilinçli alan | `<aixm:xxx xsi:nil="true" nilReason="unknown"/>` (tüm alanlar `nillable="true"`) |

---

## 3. XML iskeleti

Her feature `message:hasMember` altında durur; `gml:id`'ler mesaj içinde benzersiz olmalı,
`gml:identifier` feature'ın kalıcı UUID'sidir. Timeslice `BASELINE` olarak kodlanır.

```xml
<message:hasMember>
  <aixm:AirportHeliport gml:id="AD_LTZZ">
    <gml:identifier codeSpace="urn:uuid:">1B3C5E7A-0000-4000-8000-00000000A001</gml:identifier>
    <aixm:timeSlice>
      <aixm:AirportHeliportTimeSlice gml:id="AD_LTZZ_TS">
        <gml:validTime>
          <gml:TimePeriod gml:id="AD_LTZZ_TP">
            <gml:beginPosition>2026-10-01T00:00:00Z</gml:beginPosition>
            <gml:endPosition indeterminatePosition="unknown"/>
          </gml:TimePeriod>
        </gml:validTime>
        <aixm:interpretation>BASELINE</aixm:interpretation>
        <aixm:sequenceNumber>1</aixm:sequenceNumber>
        <aixm:correctionNumber>0</aixm:correctionNumber>

        <!-- §1.1 kimlik — sıra şemadaki sequence ile aynı olmalı -->
        <aixm:designator>LTZZ</aixm:designator>
        <aixm:name>ORNEK HAVALIMANI</aixm:name>
        <aixm:locationIndicatorICAO>LTZZ</aixm:locationIndicatorICAO>
        <aixm:designatorIATA>ZZZ</aixm:designatorIATA>
        <aixm:type>AD</aixm:type>
        <aixm:certifiedICAO>YES</aixm:certifiedICAO>
        <aixm:privateUse>NO</aixm:privateUse>
        <aixm:controlType>CIVIL</aixm:controlType>
        <aixm:fieldElevation uom="FT">325</aixm:fieldElevation>
        <aixm:verticalDatum>EGM96</aixm:verticalDatum>
        <aixm:magneticVariation>6.2</aixm:magneticVariation>
        <aixm:dateMagneticVariation>2025</aixm:dateMagneticVariation>
        <aixm:magneticVariationChange>0.1</aixm:magneticVariationChange>
        <aixm:referenceTemperature uom="C">29.5</aixm:referenceTemperature>
        <aixm:transitionAltitude uom="FT">10000</aixm:transitionAltitude>
        <aixm:transitionLevel uom="FL">110</aixm:transitionLevel>

        <!-- gömülü objeler -->
        <aixm:servedCity>
          <aixm:City gml:id="AD_LTZZ_CITY1">
            <aixm:name>ORNEKKENT</aixm:name>
          </aixm:City>
        </aixm:servedCity>
        <aixm:responsibleOrganisation>
          <aixm:AirportHeliportResponsibilityOrganisation gml:id="AD_LTZZ_RO1">
            <aixm:role>OPERATE</aixm:role>
            <aixm:theOrganisationAuthority xlink:href="urn:uuid:1B3C5E7A-0000-4000-8000-0000000000F1"/>
          </aixm:AirportHeliportResponsibilityOrganisation>
        </aixm:responsibleOrganisation>

        <!-- ARP: ElevatedPoint (lat lon sırası, EPSG:4326) -->
        <aixm:ARP>
          <aixm:ElevatedPoint gml:id="AD_LTZZ_ARP" srsName="urn:ogc:def:crs:EPSG::4326">
            <gml:pos>40.123456 29.654321</gml:pos>
            <aixm:elevation uom="FT">325</aixm:elevation>
            <aixm:verticalDatum>EGM96</aixm:verticalDatum>
          </aixm:ElevatedPoint>
        </aixm:ARP>

        <!-- Çalışma saatleri: H24 açık (timeInterval yok = sürekli) -->
        <aixm:availability>
          <aixm:AirportHeliportAvailability gml:id="AD_LTZZ_AV1">
            <aixm:operationalStatus>NORMAL</aixm:operationalStatus>
          </aixm:AirportHeliportAvailability>
        </aixm:availability>

        <aixm:timeZone>UTC+3</aixm:timeZone>
      </aixm:AirportHeliportTimeSlice>
    </aixm:timeSlice>
  </aixm:AirportHeliport>
</message:hasMember>
```

> **Sıra kuralı:** `AirportHeliportPropertyGroup` bir `sequence`'tir; XML'de elemanlar
> şemadaki sırayla yazılmalıdır: `designator, name, locationIndicatorICAO, designatorIATA,
> type, certifiedICAO, privateUse, controlType, fieldElevation, verticalDatum,
> magneticVariation, dateMagneticVariation, magneticVariationChange, referenceTemperature,
> altimeterCheckLocation, secondaryPowerSupply, windDirectionIndicator,
> landingDirectionIndicator, transitionAltitude, transitionLevel, lowestTemperature,
> abandoned, certificationDate, certificationExpirationDate, contaminant, servedCity,
> responsibleOrganisation, ARP, aviationBoundary, altimeterSource, contact, availability,
> annotation, timeZone, segmentedCircleMarker`. (`timeZone` ve `segmentedCircleMarker`
> şemada `annotation`'dan **sonra** gelir — alışılmadık ama şema böyle.)
>
> `ElevatedPoint` doğrudan `gml:PointType`'ı genişletir; sıra: önce `gml:pos`, sonra
> `elevation, geoidUndulation, verticalDatum, horizontalAccuracy, annotation`.

---

## 4. Çalışma saatleri / kısıtlama örnekleri

### 4.1 Belirli saatlerde açık, dışında PPR

```xml
<aixm:availability>
  <aixm:AirportHeliportAvailability gml:id="AD_LTZZ_AV1">
    <aixm:timeInterval>
      <aixm:Timesheet gml:id="AD_LTZZ_AV1_TS1">
        <aixm:timeReference>UTC</aixm:timeReference>
        <aixm:day>ANY</aixm:day>
        <aixm:startTime>05:00</aixm:startTime>
        <aixm:endTime>21:00</aixm:endTime>
      </aixm:Timesheet>
    </aixm:timeInterval>
    <aixm:operationalStatus>NORMAL</aixm:operationalStatus>
  </aixm:AirportHeliportAvailability>
</aixm:availability>
<aixm:availability>
  <aixm:AirportHeliportAvailability gml:id="AD_LTZZ_AV2">
    <aixm:timeInterval>
      <aixm:Timesheet gml:id="AD_LTZZ_AV2_TS1">
        <aixm:timeReference>UTC</aixm:timeReference>
        <aixm:day>ANY</aixm:day>
        <aixm:startTime>21:00</aixm:startTime>
        <aixm:endTime>24:00</aixm:endTime>
      </aixm:Timesheet>
    </aixm:timeInterval>
    <aixm:timeInterval>
      <aixm:Timesheet gml:id="AD_LTZZ_AV2_TS2">
        <aixm:timeReference>UTC</aixm:timeReference>
        <aixm:day>ANY</aixm:day>
        <aixm:startTime>00:00</aixm:startTime>
        <aixm:endTime>05:00</aixm:endTime>
      </aixm:Timesheet>
    </aixm:timeInterval>
    <aixm:operationalStatus>LIMITED</aixm:operationalStatus>
    <aixm:usage>
      <aixm:AirportHeliportUsage gml:id="AD_LTZZ_AV2_U1">
        <aixm:type>CONDITIONAL</aixm:type>
        <aixm:priorPermission uom="HR">24</aixm:priorPermission>
        <aixm:operation>ALL</aixm:operation>
      </aixm:AirportHeliportUsage>
    </aixm:usage>
  </aixm:AirportHeliportAvailability>
</aixm:availability>
```

> **`Timesheet` alanları** (`TimesheetPropertyGroup`, sırayla): `timeReference`
> (`CodeTimeReferenceType`: `UTC`, `UTC+3`...), `startDate`/`endDate` (`DateMonthDayType`,
> yıl içi dönem), `day`/`dayTil` (`CodeDayType`: `MON..SUN, WORK_DAY, BEF_WORK_DAY,
> AFT_WORK_DAY, HOL, BEF_HOL, AFT_HOL, ANY, BUSY_FRI, MON_FRI, SUN_THU, SAT_WED, SAT_THU`),
> `startTime` (`TimeType`: `HH:MM` veya `24:00`), `startEvent` (`SR`/`SS` gibi olay),
> `startTimeRelativeEvent`, `startEventInterpretation`, `endTime`, `endEvent`,
> `endTimeRelativeEvent`, `endEventInterpretation`, `daylightSavingAdjust`, `excluded`
> (`YES` → bu dilim hariç tutulur), `annotation`. Gece yarısını aşan aralık (21:00-05:00)
> için pratik olarak iki ayrı Timesheet (21:00-24:00 ve 00:00-05:00) kullanmak daha az
> yoruma açıktır.

### 4.2 Meydan kapalı (NOTAM benzeri, geçici)

Geçici değişiklikler BASELINE'ı değiştirmez; aynı feature'a yeni bir timeSlice
(`interpretation=TEMPDELTA`, kısıtlı `validTime`) eklenir ve yalnızca değişen alan
(`availability{operationalStatus=CLOSED}`) yazılır. (TEMPDELTA/PERMDELTA kuralları
`AbstractAIXMTimeSliceType` içindedir; bu XSD elimizde yok — genel AIXM Temporality Model.)

---

## 5. Kontrol listesi

- [ ] `gml:identifier` UUID kalıcı ve tekrarlanabilir mi? (Projede diğer feature'lar gibi
      deterministik UUID üretimi önerilir — aynı meydan her build'de aynı UUID'yi almalı,
      yoksa pist/prosedür referansları kopar.)
- [ ] `locationIndicatorICAO` 4 harf, `designatorIATA` 3 harf mi?
- [ ] `designator` ile `locationIndicatorICAO` birbirinin yerine **fallback olarak**
      doldurulmadı mı? (İkisi farklı alandır; ICAO kodu olmayan meydanda
      `locationIndicatorICAO` boş kalır.)
- [ ] `ARP` konumu `lat lon` sırasında mı (`EPSG::4326` eksen sırası)?
- [ ] Tüm `Val*` alanlarında `uom` var mı?
- [ ] Elemanlar şema `sequence` sırasında mı?
- [ ] `servedCity`, `availability` gibi gömülü objelerin `gml:id`'leri mesaj içinde benzersiz mi?
- [ ] Pist/taksi yolu/apron eklenecekse, bunların `associatedAirportHeliport`'u bu
      feature'ın `urn:uuid:`'sine işaret ediyor mu?
- [ ] TWR/APP `Unit`'leri, ILS `Navaid`'leri ve prosedürler bu meydana bağlandı mı?
