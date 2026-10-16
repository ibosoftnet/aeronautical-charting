# AIXM 5.2 — Hava Sahası Aktivasyonu ve Zaman Çizelgesi

Kaynak: AIXM 5.2 XSD (`AirspaceActivation`, `PropertiesWithSchedule`,
`Timesheet`) ve açıklamalı XSD'deki tanımlar.

## 1. AirspaceActivation

"Sahanın operasyonel durumu hakkında bilgi." Bir Airspace 0..∞ aktivasyon
taşır; her biri bir kullanım nedenini ve durumunu, isteğe bağlı olarak
seviyelerini, kullanıcısını, uçağını ve saatlerini anlatır.

| Alan | Çokluk | Anlamı (AIXM) |
|---|---|---|
| `timeInterval` | 0..∞ | Çizelgenin bileşeni — `Timesheet` (§2) |
| `annotation` | 0..∞ | Not |
| `specialDateAuthority` | 0..∞ | Bu kuruluşun özel günleri (bayram vb.) çizelgeye uygulanır |
| `activity` | 0..1 | Sahanın kullanımını etkileyen, yerde ya da havadaki asıl durum veya neden (`TRAINING`, `PARACHUTE`, `MILOPS`, `BALLOON` …; tam liste: [`AIXM_Airspace_Attributes.md`](AIXM_Airspace_Attributes.md) §5) |
| `status` | 0..1 | Aktivasyon durumu (aşağıda) |
| `levels` | 0..∞ | Bu kullanıma ait saha katmanı (`AirspaceLayer`: üst/alt limit + referans) |
| `user` | 0..∞ | Katmanı kullanan kuruluş (`OrganisationAuthority`'ye `xlink:href`) |
| `aircraft` | 0..∞ | Aktivasyon süresince sahayı kullanan uçak tipi (`AircraftCharacteristic`) |

`status` (`CodeStatusAirspaceType`):

| Değer | AIXM tanımı |
|---|---|
| `AVBL_FOR_ACTIVATION` | Saha aktive edilebilir |
| `ACTIVE` | Saha aktif (ama henüz kullanımda olmayabilir) |
| `IN_USE` | Saha aktivasyon süresi içinde fiilen kullanılıyor |
| `INACTIVE` | Saha aktif değil |
| `INTERMITTENT` | Saha aktif ama gerçek kullanımın olmadığı aralıklarla |

Eleman sırası: önce `timeInterval`, `annotation`, `specialDateAuthority`
(`PropertiesWithSchedulePropertyGroup`), sonra `activity`, `status`, `levels`,
`user`, `aircraft`, en sonda `extension`.

> `AirspaceLayerClass` da bir `PropertiesWithSchedule`'dır: sahanın **sınıfı**
> da `timeInterval` ile saate bağlanabilir (§3.3).

## 2. Timesheet

"Bir çizelgenin parçası olarak tekrar eden tek bir zaman aralığının tanımı."

| Alan | Değer Tipi | Anlamı (AIXM) |
|---|---|---|
| `timeReference` | `CodeTimeReferenceType` | Çizelgedeki saat/gün/tarihlerin zaman referansı: `UTC`, `UTC-12` … `UTC+14` ve yarım/çeyrek saatlik ofsetler |
| `startDate` | `DateMonthDayType` | Yılsız başlangıç tarihi `GG-AA` (ör. `15-05`) ya da `SDLST`/`EDLST` |
| `endDate` | `DateMonthDayType` | Yılsız bitiş tarihi; `startDate` ile "15 Mayıs–15 Kasım" gibi tekrarlı dönemler |
| `day` | `CodeDayType` | Çizelgenin ilgili olduğu gün (aşağıda) |
| `dayTil` | `CodeDayType` | Boşsa bitiş değerleri `day`'de geçer; doluysa aralık `day`'den `dayTil`'e uzanır |
| `startTime` | `TimeType` | `day`'deki başlangıç saati `SS:DD` (`00:00`–`23:59`, `24:00`) |
| `startEvent` | `CodeTimeEventType` | Başlangıcı belirleyen olay: `SR` (gün doğumu), `SS` (gün batımı), `BMCT`, `EECT` |
| `startTimeRelativeEvent` | `ValDurationType` | Olaydan önce/sonra dakika |
| `startEventInterpretation` | `CodeTimeEventCombinationType` | `startTime` ile `startEvent` birlikteyse hangisi geçerli: `EARLIEST`, `LATEST` |
| `endTime` | `TimeType` | Bitiş saati |
| `endEvent` | `CodeTimeEventType` | Bitişi belirleyen olay |
| `endTimeRelativeEvent` | `ValDurationType` | Olaydan önce/sonra dakika |
| `endEventInterpretation` | `CodeTimeEventCombinationType` | `EARLIEST`, `LATEST` |
| `daylightSavingAdjust` | `CodeYesNoType` | Yaz saatinde `startTime`/`endTime` bir saat azaltılır |
| `excluded` | `CodeYesNoType` | Bu blok, diğer çizelgelerin tanımladığı toplam süreden **çıkarılır** |
| `annotation` | `NotePropertyType` | Not |

`day` (`CodeDayType`): `MON` … `SUN`, `WORK_DAY` (resmi tatil ve haftalık
tatil olmayan gün), `BEF_WORK_DAY`, `AFT_WORK_DAY`, `HOL` (resmi tatil;
haftalık tatil günleri dahil değil), `BEF_HOL`, `AFT_HOL`, `ANY`, `BUSY_FRI`,
`MON_FRI`, `SUN_THU`, `SAT_WED`, `SAT_THU` (son dördü resmi tatilleri de
kapsar).

## 3. Örnekler (kurgusal değerlerle, yapıyı göstermek için)

`gml:id`'ler örnektir; her nesne belge içinde tekil bir `gml:id` taşımalıdır.

### 3.1 Belirli saatlerde aktif (hafta içi 06:00–15:00 UTC, eğitim)

```xml
<aixm:activation>
  <aixm:AirspaceActivation gml:id="EX_ACT1">
    <aixm:timeInterval>
      <aixm:Timesheet gml:id="EX_TS1">
        <aixm:timeReference>UTC</aixm:timeReference>
        <aixm:day>MON_FRI</aixm:day>
        <aixm:startTime>06:00</aixm:startTime>
        <aixm:endTime>15:00</aixm:endTime>
        <aixm:daylightSavingAdjust>NO</aixm:daylightSavingAdjust>
        <aixm:excluded>NO</aixm:excluded>
      </aixm:Timesheet>
    </aixm:timeInterval>
    <aixm:activity>TRAINING</aixm:activity>
    <aixm:status>ACTIVE</aixm:status>
  </aixm:AirspaceActivation>
</aixm:activation>
```

### 3.2 NOTAM ile aktive edilebilir (saat yok)

Saat belli değilse `timeInterval` yazılmaz, durum `AVBL_FOR_ACTIVATION`
olur; koşul bir notla anlatılır:

```xml
<aixm:activation>
  <aixm:AirspaceActivation gml:id="EX_ACT2">
    <aixm:annotation>
      <aixm:Note gml:id="EX_ACT2_N">
        <aixm:purpose>REMARK</aixm:purpose>
        <aixm:translatedNote>
          <aixm:LinguisticNote gml:id="EX_ACT2_N_LN">
            <aixm:note>Activated by NOTAM.</aixm:note>
          </aixm:LinguisticNote>
        </aixm:translatedNote>
      </aixm:Note>
    </aixm:annotation>
    <aixm:activity>MILOPS</aixm:activity>
    <aixm:status>AVBL_FOR_ACTIVATION</aixm:status>
  </aixm:AirspaceActivation>
</aixm:activation>
```

### 3.3 Sınıfın saate bağlı değişmesi (gündüz D, gece G)

İki `class` yazılır; her biri kendi `timeInterval`'ını taşır. Gece aralığı
gündüz çizelgesinin `excluded=YES` ile tersidir ya da ayrı bir çizelgedir:

```xml
<aixm:class>
  <aixm:AirspaceLayerClass gml:id="EX_CLS_DAY">
    <aixm:timeInterval>
      <aixm:Timesheet gml:id="EX_CLS_DAY_TS">
        <aixm:timeReference>UTC</aixm:timeReference>
        <aixm:day>ANY</aixm:day>
        <aixm:startEvent>SR</aixm:startEvent>
        <aixm:endEvent>SS</aixm:endEvent>
      </aixm:Timesheet>
    </aixm:timeInterval>
    <aixm:classification>D</aixm:classification>
  </aixm:AirspaceLayerClass>
</aixm:class>
<aixm:class>
  <aixm:AirspaceLayerClass gml:id="EX_CLS_NIGHT">
    <aixm:timeInterval>
      <aixm:Timesheet gml:id="EX_CLS_NIGHT_TS">
        <aixm:timeReference>UTC</aixm:timeReference>
        <aixm:day>ANY</aixm:day>
        <aixm:startEvent>SS</aixm:startEvent>
        <aixm:endEvent>SR</aixm:endEvent>
      </aixm:Timesheet>
    </aixm:timeInterval>
    <aixm:classification>G</aixm:classification>
  </aixm:AirspaceLayerClass>
</aixm:class>
```

Bu örnekler bir `AirspaceTimeSlice` içinde XSD doğrulamasından geçirildi
(bkz. [`AIXM_Airspace_How_To_Add.md`](AIXM_Airspace_How_To_Add.md) §5).

## 4. Bu projede

GeoPackage'ta `activation` tek bir sütuna indirgenmez: tamamı (seviyeler,
kullanıcı, uçak, çizelge, notlar dahil) `airspaces_activation` sütununda JSON
dizisi olarak durur; `class` da `airspaces_class` sütununda JSON'dur
(bkz. [`../AIXM_to_GeoPackage_Schema_Design.md`](../AIXM_to_GeoPackage_Schema_Design.md)).
Bugünkü kaynaklardan yalnızca elle tutulan TRNC / tailored-LT / tailored-LC kayıtları
`activity`/`status` taşır; çizelge (`timeInterval`) yalnız tailored-LC LCP1'de
var (H24: `ANY` 00:00–24:00 UTC).
