# AIXM 5.2 — Pist, Taksi Yolu ve Apron Yüzeyleri Nasıl Eklenir?

Kaynak: `AIXM_Features_annotated.xsd` + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> Önkoşul: meydan (`AirportHeliport`) zaten eklenmiş olmalı — bkz.
> `AIXM_AirportHeliport_How_To_Add.md`. Attribute anlamları için pist/taksi/apron
> `*_Attributes.md` dosyalarına bakın.
>
> **Örnek veri hayalidir:** `LTZZ`, pist `05/23` (3000 × 45 m, gerçek yön ≈050°),
> taksi yolu `A`, `APRON 1`, park yeri `12`. Koordinatlar yaklaşık hesaplanmıştır.
> Okunabilirlik için `xlink:href` değerlerinde gerçek UUID yerine **okunur yer tutucular**
> kullanılmıştır (`urn:uuid:RWY-0523`); gerçek kodlamada her biri ilgili feature'ın
> `gml:identifier` UUID'sidir.
>
> **Kısaltma:** Örneklerde `<aixm:Xxx>` ile `<aixm:XxxTimeSlice>` arasındaki
> `gml:identifier` ve `<aixm:timeSlice>` sarmalayıcısı, ayrıca timeslice içindeki
> `gml:validTime`, `interpretation`, `sequenceNumber`, `correctionNumber` alanları
> `<!-- başlık -->` yorumuyla kısaltılmıştır. Tam yapı `AIXM_AirportHeliport_How_To_Add.md`
> §3'teki gibidir:
> `<aixm:Runway gml:id><gml:identifier/><aixm:timeSlice><aixm:RunwayTimeSlice gml:id>
> <gml:validTime/>…<aixm:correctionNumber/> [attribute'lar] </aixm:RunwayTimeSlice></aixm:timeSlice></aixm:Runway>`.

---

## 0. Genel prensipler

1. **Mantıksal feature + fiziksel parçalar:** `Runway`/`Taxiway`/`Apron` kimlik ve özet
   bilgi taşır, geometri taşımaz. Çizilebilir yüzey `RunwayElement`/`TaxiwayElement`/
   `ApronElement` ile eklenir. En az **bir** element eklenmezse yüzey haritada görünmez.
2. **Referans yönü yukarıya:** her parça, ait olduğu feature'a işaret eder. Ebeveyn
   kaydında çocuk listesi tutulmaz, dolayısıyla çocuk eklemek ebeveyni değiştirmeyi
   gerektirmez.
3. **Sıra:** her feature'ın attribute'ları şemadaki `sequence` sırasıyla yazılır; türemiş
   feature'larda (ProtectArea, LightSystem, Marking) **üst sınıf attribute'ları önce** gelir.
4. **Yüzey özellikleri** (`surfaceProperties` → `SurfaceCharacteristics`) hem mantıksal
   feature'da (genel değer) hem element'te (parçaya özel değer) verilebilir.
5. **Koordinat:** `srsName="urn:ogc:def:crs:EPSG::4326"`, sıra **lat lon**; poligon halkası
   kapalı (ilk nokta = son nokta).

---

## 1. Ekleme sırası (özet akış)

```
PİST                                   TAKSİ                              APRON
─────                                  ─────                              ─────
1 Runway ───────────────┐              6 Taxiway                          10 Apron
2 RunwayElement(ler)    │              7 TaxiwayElement(ler)              11 ApronElement(ler)
3 RunwayDirection ×2 ◄──┘              8 GuidanceLine ──► Taxiway,        12 AircraftStand
   (startingElement ─► 2, ops.)          Apron, Stand, RCP                   (apronLocation ─► 11)
4 RunwayCentrelinePoint(ler)           9 TaxiHoldingPosition              13 (ops.) DeicingArea,
   + declared distances                   ─► GuidanceLine, Runway             PassengerLoadingBridge, Road
5 RunwayProtectArea (SWY/CWY/RESA),
  BlastPad, ArrestingGear              ─── sonra (ops.) ───
                                       Işık sistemleri, işaretler, tabelalar, VGSI, ALS, RVR
```

`RunwayDirection.startingElement` bir `RunwayElement`'e işaret ettiği için, kaydırılmış
eşik varsa element'i yönden önce tanımlamak (UUID'sini bilmek) gerekir. Pist ile taksi
bağlantısı `GuidanceLine.connectedRunwayCentrelinePoint` ve
`TaxiHoldingPosition.protectedRunway` üzerinden kurulduğu için taksi adımları pist
adımlarından sonra gelir.

---

## 2. Pist ekleme

### 2.1 Runway (mantıksal pist)

```xml
<aixm:Runway gml:id="RWY_0523">
  <!-- başlık: gml:identifier = RWY-0523 ... -->
  <aixm:RunwayTimeSlice gml:id="RWY_0523_TS">
    <!-- validTime / interpretation=BASELINE / sequenceNumber / correctionNumber -->
    <aixm:designator>05/23</aixm:designator>
    <aixm:type>RWY</aixm:type>
    <aixm:nominalLength uom="M">3000</aixm:nominalLength>
    <aixm:nominalWidth uom="M">45</aixm:nominalWidth>
    <aixm:widthShoulder uom="M">7.5</aixm:widthShoulder>
    <aixm:lengthStrip uom="M">3120</aixm:lengthStrip>
    <aixm:widthStrip uom="M">280</aixm:widthStrip>
    <aixm:surfaceProperties>
      <aixm:SurfaceCharacteristics gml:id="RWY_0523_SC">
        <aixm:composition>ASPH</aixm:composition>
        <aixm:preparation>GROOVED</aixm:preparation>
        <aixm:classPCN>80</aixm:classPCN>
        <aixm:pavementTypePCN>FLEXIBLE</aixm:pavementTypePCN>
        <aixm:pavementSubgradePCN>B</aixm:pavementSubgradePCN>
        <aixm:maxTyrePressurePCN>W</aixm:maxTyrePressurePCN>
        <aixm:evaluationMethodPCN>TECH</aixm:evaluationMethodPCN>
      </aixm:SurfaceCharacteristics>
    </aixm:surfaceProperties>
    <aixm:associatedAirportHeliport xlink:href="urn:uuid:AD-LTZZ"/>
    <aixm:referenceCodeFieldLength>4</aixm:referenceCodeFieldLength>
    <aixm:referenceCodeWingspan>E</aixm:referenceCodeWingspan>
  </aixm:RunwayTimeSlice>
</aixm:Runway>
```

AIP AD 2.12 eşlemesi: *Designations* → `designator`; *Dimensions of RWY* →
`nominalLength`/`nominalWidth`; *Strength (PCN) and surface* → `surfaceProperties`;
*Strip dimensions* → `lengthStrip`/`widthStrip`.

### 2.2 RunwayElement (pist yüzeyi)

Basit pist için tek `NORMAL` element yeterlidir. Kaydırılmış eşik, omuz, kesişim varsa
her biri ayrı element olur.

```xml
<aixm:RunwayElement gml:id="RWE_0523_1">
  <!-- başlık: gml:identifier = RWE-0523-1 -->
  <aixm:RunwayElementTimeSlice gml:id="RWE_0523_1_TS">
    <aixm:type>NORMAL</aixm:type>
    <aixm:length uom="M">3000</aixm:length>
    <aixm:width uom="M">45</aixm:width>
    <aixm:associatedRunway xlink:href="urn:uuid:RWY-0523"/>
    <aixm:extent>
      <aixm:ElevatedSurface gml:id="RWE_0523_1_ES" srsName="urn:ogc:def:crs:EPSG::4326">
        <gml:patches>
          <gml:PolygonPatch>
            <gml:exterior>
              <gml:LinearRing>
                <gml:posList>
                  40.089845 29.590170  40.107185 29.617160
                  40.107495 29.616820  40.090155 29.589830
                  40.089845 29.590170
                </gml:posList>
              </gml:LinearRing>
            </gml:exterior>
          </gml:PolygonPatch>
        </gml:patches>
      </aixm:ElevatedSurface>
    </aixm:extent>
  </aixm:RunwayElementTimeSlice>
</aixm:RunwayElement>
```

| Durum | Element seti |
|---|---|
| Basit pist | 1 × `NORMAL` |
| 05 eşiği 300 m kaydırılmış | `DISPLACED` (ilk 300 m) + `NORMAL` (kalan) ; `RunwayDirection(05).startingElement → DISPLACED` |
| Omuzlu | + 2 × `SHOULDER` (sol/sağ şerit) |
| Pist-pist veya pist-taksi kesişimi | Kesişim karesi `INTERSECTION`; `associatedRunway` iki pisti de gösterebilir (0..*) |
| Köprü üstünde bölüm | `gradeSeparation=OVERPASS` |

### 2.3 RunwayDirection ×2

```xml
<aixm:RunwayDirection gml:id="RDN_05">
  <!-- başlık: gml:identifier = RDN-05 -->
  <aixm:RunwayDirectionTimeSlice gml:id="RDN_05_TS">
    <aixm:designator>05</aixm:designator>
    <aixm:trueBearing>50.00</aixm:trueBearing>
    <aixm:magneticBearing>44.00</aixm:magneticBearing>
    <aixm:patternVFR>LEFT</aixm:patternVFR>
    <aixm:elevationTDZ uom="FT">318</aixm:elevationTDZ>
    <aixm:approachMarkingType>PRECISION</aixm:approachMarkingType>
    <aixm:classLightingJAR>FALS</aixm:classLightingJAR>
    <aixm:usedRunway xlink:href="urn:uuid:RWY-0523"/>
    <aixm:availability>
      <aixm:ManoeuvringAreaAvailability gml:id="RDN_05_AV1">
        <aixm:operationalStatus>NORMAL</aixm:operationalStatus>
      </aixm:ManoeuvringAreaAvailability>
    </aixm:availability>
    <aixm:slope>0.2</aixm:slope>
    <aixm:approachGuidance>PRECISION_CAT_I</aixm:approachGuidance>
  </aixm:RunwayDirectionTimeSlice>
</aixm:RunwayDirection>
```

`RDN_23` aynı yapıda: `designator=23`, `trueBearing=230.00`, `usedRunway` yine
`RWY-0523`. Yön-özel kısıtlar (ör. "RWY 23 yalnızca iniş") o yönün `availability.usage`
alanına yazılır (`usage{type=FORBID, operation=TAKEOFF}`).

### 2.4 RunwayCentrelinePoint + declared distances

Her yön için en az `THR` ve `END` noktası önerilir. 05 yönü için (eşik kaydırılmamış;
kalkış koşusu eşikten başlıyor):

```xml
<aixm:RunwayCentrelinePoint gml:id="RCP_05_THR">
  <!-- başlık: gml:identifier = RCP-05-THR -->
  <aixm:RunwayCentrelinePointTimeSlice gml:id="RCP_05_THR_TS">
    <aixm:role>THR</aixm:role>
    <aixm:designator>THR05</aixm:designator>
    <aixm:location>
      <aixm:ElevatedPoint gml:id="RCP_05_THR_EP" srsName="urn:ogc:def:crs:EPSG::4326">
        <gml:pos>40.090000 29.590000</gml:pos>
        <aixm:elevation uom="FT">312</aixm:elevation>
        <aixm:geoidUndulation uom="M">36.5</aixm:geoidUndulation>
      </aixm:ElevatedPoint>
    </aixm:location>

    <!-- declared distances: her tip ayrı RunwayDeclaredDistance -->
    <aixm:associatedDeclaredDistance>
      <aixm:RunwayDeclaredDistance gml:id="RCP_05_THR_TORA">
        <aixm:type>TORA</aixm:type>
        <aixm:declaredValue>
          <aixm:RunwayDeclaredDistanceValue gml:id="RCP_05_THR_TORA_V">
            <aixm:distance uom="M">3000</aixm:distance>
          </aixm:RunwayDeclaredDistanceValue>
        </aixm:declaredValue>
      </aixm:RunwayDeclaredDistance>
    </aixm:associatedDeclaredDistance>
    <aixm:associatedDeclaredDistance>
      <aixm:RunwayDeclaredDistance gml:id="RCP_05_THR_TODA">
        <aixm:type>TODA</aixm:type>
        <aixm:declaredValue>
          <aixm:RunwayDeclaredDistanceValue gml:id="RCP_05_THR_TODA_V">
            <aixm:distance uom="M">3300</aixm:distance>
          </aixm:RunwayDeclaredDistanceValue>
        </aixm:declaredValue>
      </aixm:RunwayDeclaredDistance>
    </aixm:associatedDeclaredDistance>
    <!-- ASDA 3060, LDA 3000 aynı desenle -->

    <aixm:onRunwayDirection xlink:href="urn:uuid:RDN-05"/>
  </aixm:RunwayCentrelinePointTimeSlice>
</aixm:RunwayCentrelinePoint>
```

| Nokta | `role` | Declared distances (öneri) | `relativeDistance` |
|---|---|---|---|
| 05 eşik | `THR` | TORA, TODA, ASDA, LDA (kalkış eşikten başlıyorsa hepsi burada) | 0 |
| 05 kaydırılmış eşik varsa | `START` + `DISTHR` | TORA/TODA/ASDA → `START`; LDA → `DISTHR` | `DISTHR`: kaydırma mesafesi |
| 05 kesişimden kalkış | `START_RUN` | İkinci TORA/TODA/ASDA seti | kesişime mesafe |
| 05 pist sonu | `END` | — | 3000 |
| 23 için | aynıları, `onRunwayDirection → RDN-23` | | |

> Declared distance'ın hangi noktaya asılacağı şemada kesin tanımlı değildir (bkz.
> `AIXM_Runway_Attributes.md` §4 notu); yukarıdaki tablo "mesafenin başladığı nokta"
> yorumuna dayanır. Veri sağlayıcının (ör. EAD) kodlama kuralı varsa o kullanılmalıdır.

### 2.5 Koruma alanları (stopway, clearway, RESA)

```xml
<aixm:RunwayProtectArea gml:id="RPA_05_SWY">
  <!-- başlık -->
  <aixm:RunwayProtectAreaTimeSlice gml:id="RPA_05_SWY_TS">
    <!-- önce üst sınıf (AirportHeliportProtectionArea) alanları -->
    <aixm:width uom="M">45</aixm:width>
    <aixm:length uom="M">60</aixm:length>
    <aixm:extent>
      <aixm:ElevatedSurface gml:id="RPA_05_SWY_ES" srsName="urn:ogc:def:crs:EPSG::4326">
        <!-- 23 eşiğinin ötesindeki 60 m'lik poligon -->
      </aixm:ElevatedSurface>
    </aixm:extent>
    <!-- sonra kendi alanları -->
    <aixm:type>STOPWAY</aixm:type>
    <aixm:status>NORMAL</aixm:status>
    <aixm:protectedRunwayDirection xlink:href="urn:uuid:RDN-05"/>
  </aixm:RunwayProtectAreaTimeSlice>
</aixm:RunwayProtectArea>
```

> **Hangi yöne bağlanır?** RWY 05 kalkışı için stopway ve clearway pistin **23 ucunun
> ötesindedir** ama `protectedRunwayDirection` = **05**'tir (koruduğu operasyonun yönü).
> RESA da aynı şekilde iniş/kalkış yönüne bağlanır.

Aynı desen: `type=CWY` (clearway, `obstacleFree=YES`), `type=RESA`, `type=OFZ`, `type=ILS`.

### 2.6 Opsiyonel pist ekipmanları

| Eklenecek | Feature | Bağ |
|---|---|---|
| PAPI | `VisualGlideSlopeIndicator{type=PAPI, position=LEFT, numberBox=4, slopeAngle=3.0, minimumEyeHeightOverThreshold}` | `runwayDirection → RDN-05` |
| Yaklaşma ışıkları | `ApproachLightingSystem{classICAO=CAT1, length=900 M}` | `servedRunwayDirection → RDN-05` |
| Kenar / eşik / TDZ / eksen / son ışıkları | Her biri ayrı `RunwayDirectionLightSystem{position=EDGE / THR / TDZ / CL / END}` | `associatedRunwayDirection` |
| RVR | `RunwayVisualRangeEquipment{readingPosition=TDZ}` | `associatedRunwayDirection` (0..*) |
| Blast pad | `RunwayBlastPad` | `usedRunwayDirection` |
| Arresting gear / EMAS | `ArrestingGear{engageDevice=EMAS, extent_surfaceExtent}` | `runwayDirection` |
| Pist işaretleri | `RunwayMarking{markingLocation=DESIG / THR / AIM / TDZ / CL}` | `markedRunway → RWY-0523` (yön değil pist!) |
| ILS | `Navaid{type=ILS...}.runwayDirection → RDN-05` (navaid tarafında) | — |

---

## 3. Taksi yolu ekleme

### 3.1 Taxiway (mantıksal)

```xml
<aixm:Taxiway gml:id="TWY_A">
  <!-- başlık: gml:identifier = TWY-A -->
  <aixm:TaxiwayTimeSlice gml:id="TWY_A_TS">
    <aixm:designator>A</aixm:designator>
    <aixm:type>PARALLEL</aixm:type>
    <aixm:width uom="M">23</aixm:width>
    <aixm:widthShoulder uom="M">10.5</aixm:widthShoulder>
    <aixm:surfaceProperties>
      <aixm:SurfaceCharacteristics gml:id="TWY_A_SC">
        <aixm:composition>ASPH</aixm:composition>
        <aixm:classPCN>80</aixm:classPCN>
        <aixm:pavementTypePCN>FLEXIBLE</aixm:pavementTypePCN>
        <aixm:pavementSubgradePCN>B</aixm:pavementSubgradePCN>
        <aixm:maxTyrePressurePCN>W</aixm:maxTyrePressurePCN>
        <aixm:evaluationMethodPCN>TECH</aixm:evaluationMethodPCN>
      </aixm:SurfaceCharacteristics>
    </aixm:surfaceProperties>
    <aixm:associatedAirportHeliport xlink:href="urn:uuid:AD-LTZZ"/>
  </aixm:TaxiwayTimeSlice>
</aixm:Taxiway>
```

Bağlantı taksi yolları (`A1`, `A2`...) ayrı `Taxiway` kayıtlarıdır (`type=EXIT`,
`FASTEXIT`, `STUB`...).

### 3.2 TaxiwayElement

```xml
<aixm:TaxiwayElement gml:id="TWE_A_1">
  <!-- başlık -->
  <aixm:TaxiwayElementTimeSlice gml:id="TWE_A_1_TS">
    <aixm:type>NORMAL</aixm:type>
    <aixm:associatedTaxiway xlink:href="urn:uuid:TWY-A"/>
    <aixm:extent>
      <aixm:ElevatedSurface gml:id="TWE_A_1_ES" srsName="urn:ogc:def:crs:EPSG::4326">
        <!-- gml:patches / PolygonPatch / LinearRing / posList -->
      </aixm:ElevatedSurface>
    </aixm:extent>
  </aixm:TaxiwayElementTimeSlice>
</aixm:TaxiwayElement>
```

Uzun taksi yolları genelde kavşaklardan bölünür: kavşaklar arası `NORMAL`, kavşak
kareleri `INTERSECTION` (birden çok taksi yoluna `associatedTaxiway` ile bağlanır), yan
şeritler `SHOULDER`, bekleme cepleri `HOLDING_BAY`. Parça bazında kapatma (NOTAM) bu
bölmeyle mümkün olur.

### 3.3 GuidanceLine (taksi merkez hattı)

```xml
<aixm:GuidanceLine gml:id="GL_A_1">
  <!-- başlık -->
  <aixm:GuidanceLineTimeSlice gml:id="GL_A_1_TS">
    <aixm:designator>A</aixm:designator>
    <aixm:type>TWY</aixm:type>
    <aixm:connectedRunwayCentrelinePoint xlink:href="urn:uuid:RCP-05-THR"/>
    <aixm:connectedApron xlink:href="urn:uuid:APN-1"/>
    <aixm:extent>
      <aixm:ElevatedCurve gml:id="GL_A_1_EC" srsName="urn:ogc:def:crs:EPSG::4326">
        <gml:segments>
          <gml:LineStringSegment>
            <gml:posList>40.0895 29.5920 40.0960 29.6020 40.1040 29.6140</gml:posList>
          </gml:LineStringSegment>
        </gml:segments>
      </aixm:ElevatedCurve>
    </aixm:extent>
    <aixm:connectedTaxiway xlink:href="urn:uuid:TWY-A"/>
  </aixm:GuidanceLineTimeSlice>
</aixm:GuidanceLine>
```

> Sıra dikkat: `connectedTaxiway`, `extent`'ten **sonra** gelir (şema sırası:
> `designator, type, connectedTouchDownLiftOff, connectedRunwayCentrelinePoint,
> connectedApron, connectedStand, extent, connectedTaxiway, annotation, availability`).
>
> Ground-routing ağı için guidance line'lar düğüm noktalarında (kavşak, bekleme noktası,
> park yeri girişi) bölünmelidir; şema bölmeyi zorunlu kılmaz ama tek yönlü kullanım
> (`availability.direction`) ve bekleme noktası bağı ancak bölünmüş hatlarla anlamlıdır.

### 3.4 TaxiHoldingPosition

```xml
<aixm:TaxiHoldingPosition gml:id="THP_A1_CAT1">
  <!-- başlık -->
  <aixm:TaxiHoldingPositionTimeSlice gml:id="THP_A1_CAT1_TS">
    <aixm:landingCategory>CAT_I</aixm:landingCategory>
    <aixm:status>NORMAL</aixm:status>
    <!-- A1 bağlantı taksi yolunun guidance line'ı (§3.3 desenindeki ayrı bir kayıt) -->
    <aixm:associatedGuidanceLine xlink:href="urn:uuid:GL-A1"/>
    <aixm:protectedRunway xlink:href="urn:uuid:RWY-0523"/>
    <aixm:location>
      <aixm:ElevatedPoint gml:id="THP_A1_CAT1_EP" srsName="urn:ogc:def:crs:EPSG::4326">
        <gml:pos>40.089200 29.591100</gml:pos>
      </aixm:ElevatedPoint>
    </aixm:location>
    <aixm:type>RUNWAY_HOLDING_POSITION</aixm:type>
  </aixm:TaxiHoldingPositionTimeSlice>
</aixm:TaxiHoldingPosition>
```

Stop bar → `TaxiHoldingPositionLightSystem{type=STOP_BAR, taxiHolding → THP-A1-CAT1}`;
yer işareti → `TaxiHoldingPositionMarking{markedTaxiHold}`; tabela →
`AirportSign{type=CAT_HOLD / RWY_INT_HOLD, location}`.

---

## 4. Apron ve park yeri ekleme

### 4.1 Apron

```xml
<aixm:Apron gml:id="APN_1">
  <!-- başlık: gml:identifier = APN-1 -->
  <aixm:ApronTimeSlice gml:id="APN_1_TS">
    <aixm:name>APRON 1</aixm:name>
    <aixm:surfaceProperties>
      <aixm:SurfaceCharacteristics gml:id="APN_1_SC">
        <aixm:composition>CONC</aixm:composition>
        <aixm:classPCN>90</aixm:classPCN>
        <aixm:pavementTypePCN>RIGID</aixm:pavementTypePCN>
        <aixm:pavementSubgradePCN>B</aixm:pavementSubgradePCN>
        <aixm:maxTyrePressurePCN>W</aixm:maxTyrePressurePCN>
        <aixm:evaluationMethodPCN>TECH</aixm:evaluationMethodPCN>
      </aixm:SurfaceCharacteristics>
    </aixm:surfaceProperties>
    <aixm:associatedAirportHeliport xlink:href="urn:uuid:AD-LTZZ"/>
  </aixm:ApronTimeSlice>
</aixm:Apron>
```

### 4.2 ApronElement

```xml
<aixm:ApronElement gml:id="APE_1_PARK">
  <!-- başlık -->
  <aixm:ApronElementTimeSlice gml:id="APE_1_PARK_TS">
    <aixm:type>PARKING</aixm:type>
    <aixm:jetwayAvailability>YES</aixm:jetwayAvailability>
    <aixm:groundPowerAvailability>YES</aixm:groundPowerAvailability>
    <aixm:associatedApron xlink:href="urn:uuid:APN-1"/>
    <aixm:extent>
      <aixm:ElevatedSurface gml:id="APE_1_PARK_ES" srsName="urn:ogc:def:crs:EPSG::4326">
        <!-- poligon -->
      </aixm:ElevatedSurface>
    </aixm:extent>
  </aixm:ApronElementTimeSlice>
</aixm:ApronElement>
```

Bir apron fonksiyonel bölgelere ayrılabilir: `PARKING`, `TAXILANE`, `CARGO`, `FUEL`,
`MAINT`... Basit durumda tek `NORMAL` element (apronun tüm poligonu) yeterlidir.

### 4.3 AircraftStand

```xml
<aixm:AircraftStand gml:id="STD_12">
  <!-- başlık -->
  <aixm:AircraftStandTimeSlice gml:id="STD_12_TS">
    <aixm:designator>12</aixm:designator>
    <aixm:type>NI</aixm:type>
    <aixm:visualDockingSystem>A_VDGS</aixm:visualDockingSystem>
    <aixm:location>
      <aixm:ElevatedPoint gml:id="STD_12_EP" srsName="urn:ogc:def:crs:EPSG::4326">
        <gml:pos>40.098100 29.611200</gml:pos>
      </aixm:ElevatedPoint>
    </aixm:location>
    <aixm:apronLocation xlink:href="urn:uuid:APE-1-PARK"/>
    <aixm:availability>
      <aixm:ApronAreaAvailability gml:id="STD_12_AV1">
        <aixm:operationalStatus>NORMAL</aixm:operationalStatus>
      </aixm:ApronAreaAvailability>
    </aixm:availability>
  </aixm:AircraftStandTimeSlice>
</aixm:AircraftStand>
```

> `apronLocation` **ApronElement**'e işaret eder, Apron'a değil. Park yeri → meydan bağı
> `AircraftStand → ApronElement → Apron → AirportHeliport` zinciriyle kurulur; bu yüzden
> en az bir `ApronElement` olmadan park yeri meydana bağlanamaz.

Park yerine giriş/çıkış hattı: `GuidanceLine{type=LI_TLANE / LO_TLANE, connectedStand → STD-12}`.
Köprü: `PassengerLoadingBridge{type=ARM, associatedStand → STD-12}`.

---

## 5. Kontrol listesi

- [ ] Her `Runway`/`Taxiway`/`Apron` için en az bir `*Element` (geometri) var mı?
- [ ] Her `Runway` için iki `RunwayDirection` var ve ikisi de `usedRunway` ile aynı piste mi bağlı?
- [ ] Her yön için en az `THR` ve `END` `RunwayCentrelinePoint`'i var mı? THR konumunda
      `elevation` ve `geoidUndulation` dolu mu (AD 2.12)?
- [ ] Declared distances (TORA/TODA/ASDA/LDA) her iki yön için girildi mi?
- [ ] Stopway/clearway `RunwayElement` olarak **değil**, `RunwayProtectArea` olarak mı eklendi,
      ve `protectedRunwayDirection` koruduğu operasyonun yönü mü?
- [ ] `RunwayMarking.markedRunway` pist (Runway) feature'ına mı işaret ediyor?
- [ ] `AircraftStand.apronLocation` bir `ApronElement`'e mi işaret ediyor?
- [ ] `GuidanceLine` eleman sırası şemaya uygun mu (`connectedTaxiway` `extent`'ten sonra)?
- [ ] Türemiş feature'larda (ProtectArea, LightSystem, Marking) üst sınıf alanları önce mi yazıldı?
- [ ] Tüm poligon halkaları kapalı ve koordinatlar `lat lon` sırasında mı?
- [ ] Tüm `Val*` alanlarında `uom` var mı?
