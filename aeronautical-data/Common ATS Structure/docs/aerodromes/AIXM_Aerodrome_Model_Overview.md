# AIXM 5.2 — Havalimanı Modeli (Genel Bakış)

Kaynak: `AIXM_Features_annotated.xsd` (satır ~498-7483, "AirportHeliport" paketi) +
`AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

Bu doküman havalimanı modelinin **kavramsal** yapısını anlatır. Attribute listeleri için
ilgili `*_Attributes.md` dosyalarına bakın.

---

## 1. Feature / Object ayrımı

AIXM'de iki tür eleman vardır; havalimanı modelinde bu ayrım çok önemlidir:

| Tür | Özellik | Havalimanı paketindeki örnekler |
|---|---|---|
| **Feature** (`AbstractAIXMFeatureType`) | Kendi `gml:identifier` (UUID) kimliği, kendi `timeSlice` geçmişi vardır; başka feature'lardan `xlink:href` ile referans alabilir. Mesajda `message:hasMember` altında **bağımsız** kayıt olarak durur. | `AirportHeliport`, `Runway`, `RunwayDirection`, `RunwayCentrelinePoint`, `RunwayElement`, `Taxiway`, `TaxiwayElement`, `Apron`, `ApronElement`, `AircraftStand`, `GuidanceLine`, `TaxiHoldingPosition`, tüm `*LightSystem` ve `*Marking`'ler... |
| **Object** (`AbstractAIXMObjectType`) | Kimliği yoktur; bir feature'ın timeSlice'ı **içine gömülü** yazılır, tek başına var olamaz. | `SurfaceCharacteristics`, `RunwayDeclaredDistance`, `*Availability`, `*Usage`, `*Contamination`, `City`, `AltimeterSource`, `LightElement`, `MarkingElement`, `ElevatedPoint/Curve/Surface` |

---

## 2. Referans yönü: her şey yukarıya işaret eder

`AirportHeliport`'un içinde "pistlerim", "taksi yollarım" gibi bir liste alanı **yoktur**.
Bağlantı, rota modelindeki `RouteSegment.routeFormed → Route` deseniyle aynı şekilde
**çocuktan ebeveyne** kurulur:

```
AirportHeliport  ◄── Runway.associatedAirportHeliport
                 ◄── Taxiway.associatedAirportHeliport
                 ◄── Apron.associatedAirportHeliport
                 ◄── TouchDownLiftOff.associatedAirportHeliport
                 ◄── Road.associatedAirport / AirportSign.associatedAirport
                 ◄── WorkArea / NonMovementArea / SurveyControlPoint .associatedAirportHeliport
                 ◄── SeaplaneLandingArea.associatedAirportHeliport
                 ◄── AirportHotSpot.affectedAirport
                 ◄── WaterBody.location (0..*)

Runway           ◄── RunwayDirection.usedRunway
                 ◄── RunwayElement.associatedRunway (0..* — kesişim elemanı birden çok piste ait olabilir)
                 ◄── RunwayMarking.markedRunway
                 ◄── TaxiHoldingPosition.protectedRunway (0..*)
                 ◄── TouchDownLiftOff.approachTakeOffArea (yalnızca type=FATO olan Runway)

RunwayDirection  ◄── RunwayCentrelinePoint.onRunwayDirection
                 ◄── RunwayProtectArea.protectedRunwayDirection   (stopway, clearway, RESA, OFZ...)
                 ◄── RunwayBlastPad.usedRunwayDirection
                 ◄── ArrestingGear.runwayDirection (0..*)
                 ◄── RunwayDirectionLightSystem.associatedRunwayDirection
                 ◄── ApproachLightingSystem.servedRunwayDirection
                 ◄── VisualGlideSlopeIndicator.runwayDirection
                 ◄── RunwayVisualRangeEquipment.associatedRunwayDirection (0..*)

Taxiway          ◄── TaxiwayElement.associatedTaxiway (0..*)
                 ◄── GuidanceLine.connectedTaxiway (0..*)
                 ◄── TaxiwayLightSystem.lightedTaxiway / TaxiwayMarking.markedTaxiway
                 ◄── DeicingArea.taxiwayLocation

Apron            ◄── ApronElement.associatedApron
                 ◄── DeicingArea.associatedApron
                 ◄── ApronLightSystem.lightedApron / ApronMarking.markedApron

ApronElement     ◄── AircraftStand.apronLocation
AircraftStand    ◄── PassengerLoadingBridge.associatedStand / Road.accessibleStand
                 ◄── StandMarking.markedStand / DeicingArea.standLocation
```

**Aşağıya doğru** (ebeveynden çocuğa) giden yalnızca birkaç referans vardır:

| Referans | Açıklama |
|---|---|
| `RunwayDirection.startingElement → RunwayElement` | Pist yönünün başladığı eleman (tipik: kaydırılmış eşik alanı / `DISPLACED`) |
| `SeaplaneLandingArea.rampSite / dockSite / assignedGangway` | Hidro-alanın kendi yardımcı tesislerine referansı |
| `PilotControlledLighting.activatedGroundLighting → AbstractGroundLightSystem` | Pilotun aktive ettiği ışık sistemleri |
| `AltimeterSource.altimeterData → WeatherSource` | AirportHeliport içine gömülü obje üzerinden |

**Pratik sonuç (GIS/sorgu):** "LTZZ'nin tüm pistleri" sorgusu, `Runway` kayıtları içinde
`associatedAirportHeliport` = LTZZ'nin UUID'si olanları filtreleyerek yapılır. Bazı
feature'ların havalimanına **doğrudan bağı yoktur** ve ancak zincirle ulaşılır:

| Feature | Havalimanına ulaşma yolu |
|---|---|
| `RunwayDirection` | `usedRunway → Runway.associatedAirportHeliport` |
| `RunwayCentrelinePoint` | `onRunwayDirection → usedRunway → associatedAirportHeliport` |
| `RunwayElement`, `RunwayProtectArea`, `RunwayBlastPad`, `ArrestingGear` | Runway / RunwayDirection üzerinden |
| `TaxiwayElement` | `associatedTaxiway → associatedAirportHeliport` |
| `GuidanceLine` | Doğrudan bağı yok; `connectedTaxiway/Apron/Stand/RunwayCentrelinePoint/TouchDownLiftOff` üzerinden |
| `TaxiHoldingPosition` | `protectedRunway` veya `associatedGuidanceLine` üzerinden |
| `ApronElement` | `associatedApron → associatedAirportHeliport` |
| `AircraftStand` | `apronLocation → ApronElement → associatedApron → Apron → associatedAirportHeliport` |
| Tüm `*LightSystem`, `*Marking` | İşaret/ışık verdiği feature üzerinden |

---

## 3. Geometri nerede taşınır?

**Kritik nokta:** `Runway`, `RunwayDirection`, `Taxiway` ve `Apron` feature'larının **hiçbir
geometri alanı yoktur** (tıpkı `Route` gibi). Bunlar mantıksal/kimlik feature'larıdır;
çizim için alt elemanlarına bakılır.

| Geometri tipi | Feature.attribute | Anlamı |
|---|---|---|
| **Nokta** (`ElevatedPoint`) | `AirportHeliport.ARP` | Havalimanı referans noktası |
| | `RunwayCentrelinePoint.location` | Eşik, kaydırılmış eşik, pist sonu, TDZ, orta nokta... |
| | `AircraftStand.location` | Park yeri referans noktası |
| | `TaxiHoldingPosition.location` | Bekleme noktası |
| | `TouchDownLiftOff.geometricCentre` | TLOF merkezi |
| | `RunwayVisualRangeEquipment.location`, `SurveyControlPoint.location`, `WeatherSource.position`, `AirportSign.location`, `MarkingBuoy.location`, `LightElement.location` | Nokta tesisler |
| **Çizgi** (`ElevatedCurve`) | `GuidanceLine.extent` | Taksi merkez hattı / lead-in / lead-out |
| | `SeaplaneRampSite.centreline` | Rampa ekseni |
| | `MarkingElement.extent_curveExtent`, `ArrestingGear.extent_curveExtent` | (choice) |
| **Alan** (`ElevatedSurface`) | `AirportHeliport.aviationBoundary` | Havalimanı sınırı |
| | `RunwayElement.extent` | Pist yüzeyi parçaları (normal, kesişim, kaydırılmış alan, omuz) |
| | `RunwayProtectArea.extent` | Stopway, clearway, RESA, OFZ, ILS koruma alanı... |
| | `RunwayBlastPad.extent` | Blast pad |
| | `TaxiwayElement.extent` | Taksi yolu yüzey parçaları |
| | `ApronElement.extent` | Apron yüzey parçaları |
| | `AircraftStand.extent`, `DeicingArea.extent`, `PassengerLoadingBridge.extent`, `Road.surfaceExtent` | |
| | `TouchDownLiftOff.extent`, `TouchDownLiftOffSafeArea.extent` | Heli alanları |
| | `WorkArea.extent`, `NonMovementArea.extent`, `AirportHotSpot.area` | |
| | `SeaplaneLandingArea.extent`, `FloatingDockSite.extent`, `SeaplaneRampSite.extent` | |
| | `WaterBody.extent` | **Dikkat:** `SurfacePropertyType` (Elevated değil) |

Yani **bir pistin çizilebilir poligonu = o `Runway`'e `associatedRunway` ile bağlı
`RunwayElement`'lerin `extent`'lerinin birleşimidir**; pist ekseni ise iki
`RunwayDirection`'ın `THR`/`END` rolündeki `RunwayCentrelinePoint`'leri arasındaki
doğrudur (şemada ayrı bir "centreline curve" alanı yoktur).

---

## 4. Havalimanı paketinin alt grupları

Şema paketi mantıksal olarak şu alt gruplara ayrılır (detay: `AIXM_Aerodrome_Components.md`):

| Grup | Feature'lar |
|---|---|
| **Havalimanı çekirdeği** | `AirportHeliport`, `AirportHeliportCollocation`, `AirportHotSpot`, `NonMovementArea`, `SurveyControlPoint`, `WaterBody`, `WeatherSource`, `WorkArea` |
| **Manevra alanı — pist** | `Runway`, `RunwayDirection`, `RunwayCentrelinePoint`, `RunwayElement`, `RunwayProtectArea`, `RunwayBlastPad`, `ArrestingGear`, `RunwayVisualRangeEquipment`, `VisualGlideSlopeIndicator` |
| **Manevra alanı — taksi** | `Taxiway`, `TaxiwayElement`, `GuidanceLine`, `TaxiHoldingPosition` |
| **Apron alanı** | `Apron`, `ApronElement`, `AircraftStand`, `DeicingArea`, `PassengerLoadingBridge`, `Road` |
| **Helikopter** | `TouchDownLiftOff`, `TouchDownLiftOffSafeArea` (+ FATO = `Runway.type=FATO`) |
| **Işıklandırma** (`AbstractGroundLightSystem`) | `ApproachLightingSystem`, `RunwayDirectionLightSystem`, `RunwayProtectAreaLightSystem`, `VisualGlideSlopeIndicator`, `TaxiwayLightSystem`, `TaxiHoldingPositionLightSystem`, `GuidanceLineLightSystem`, `ApronLightSystem`, `TouchDownLiftOffLightSystem`; ayrıca `PilotControlledLighting` |
| **İşaretleme** (`AbstractMarking`) | `RunwayMarking`, `TaxiwayMarking`, `TaxiHoldingPositionMarking`, `GuidanceLineMarking`, `ApronMarking`, `StandMarking`, `DeicingAreaMarking`, `TouchDownLiftOffMarking`, `AirportProtectionAreaMarking` |
| **Tabela** | `AirportSign` |
| **Hidro (deniz uçağı)** | `SeaplaneLandingArea`, `SeaplaneRampSite`, `FloatingDockSite`, `Gangway`, `MarkingBuoy` |
| **Kirlilik (SNOWTAM)** — Object | `AirportHeliportContamination`, `RunwayContamination`, `RunwaySectionContamination`, `TaxiwayContamination`, `ApronContamination`, `AircraftStandContamination`, `TouchDownLiftOffContamination` |

---

## 5. Kalıtım (soyut üst sınıflar)

Bazı feature'lar attribute'larının bir kısmını soyut bir üst gruptan alır. Şemada
`<xxxPropertyGroup>` içinde ilk eleman olarak `<group ref="aixm:ÜstGrupPropertyGroup"/>`
bulunur, yani **üst sınıfın attribute'ları XML'de önce yazılır**.

| Soyut üst sınıf | Ortak attribute'lar | Alt sınıflar |
|---|---|---|
| `AbstractAirportHeliportProtectionArea` | `width`, `length`, `lighting`, `obstacleFree`, `surfaceProperties`, `extent`, `annotation` | `RunwayProtectArea`, `TouchDownLiftOffSafeArea` |
| `AbstractGroundLightSystem` | `emergencyLighting`, `intensityLevel`, `colour`, `element` (LightElement), `availability`, `annotation` | Tüm `*LightSystem`'ler, `ApproachLightingSystem`, `VisualGlideSlopeIndicator` |
| `AbstractMarking` | `markingICAOStandard`, `condition`, `element` (MarkingElement), `annotation` | Tüm `*Marking`'ler |
| `AbstractSurfaceContamination` (Object) | `observationTime`, `depth`, `frictionCoefficient`, `frictionEstimation`, ... `layer` | Tüm `*Contamination`'lar |
| `AbstractPropertiesWithSchedule` (Object) | `timeInterval` (Timesheet), `specialDateAuthority`, `annotation` | Tüm `*Availability`, `RunwayDeclaredDistanceValue`, `ConditionCombination`, `WorkareaActivity`, `AirportSignStatus`... |
| `AbstractUsageCondition` (Object) | `type` (PERMIT/FORBID...), `priorPermission`, `contact`, `selection` | `AirportHeliportUsage`, `ManoeuvringAreaUsage`, `ApronAreaUsage` |

Detaylar: `AIXM_Surface_Common_Objects.md`.

---

## 6. Havalimanı dışından gelen referanslar

Havalimanı feature'ları AIXM'in diğer paketlerinden (navaid, prosedür, servis, hava sahası)
yoğun biçimde referans alır. Bu referanslar yine **dış feature → havalimanı** yönündedir;
havalimanı tarafında karşılık gelen bir liste alanı yoktur.

| Dış feature.attribute | Hedef | Anlamı |
|---|---|---|
| `Navaid.servedAirport` (0..*) | AirportHeliport | Navaid'in hizmet verdiği meydan |
| `Navaid.runwayDirection` (0..*) | RunwayDirection | ILS/LOC/GP gibi pist yönüne bağlı navaid |
| `Navaid.touchDownLiftOff` (0..*) | TouchDownLiftOff | Heli navaid'i |
| `GBAS.servedAirport`, `GBASService.servedApproach` | AirportHeliport / RunwayDirection | GBAS |
| `Unit.airportLocation` | AirportHeliport | TWR/APP gibi ATS birimlerinin bulunduğu meydan |
| `AirTrafficControlService.clientAirport`, `InformationService.clientAirport`, `GroundTrafficControlService.clientAirport`, `AirTrafficFlowManagementService.clientAirportHeliport`, `AirportGroundService.airportHeliport` | AirportHeliport | Servisler |
| `Procedure.airportHeliport` (0..*) | AirportHeliport | SID/STAR/IAP'nin ait olduğu meydan |
| `ProcedureTransition.airportTransition`, `LandingTakeoffAreaCollection.runwayDirection / TLOF` | AirportHeliport / RunwayDirection / TLOF | Prosedürün hangi pistlere uygulandığı |
| `DesignatedPoint.airportHeliport` (0..*), `DesignatedPoint.runwayPoint`, `DesignatedPoint.aimingPoint` | AirportHeliport / RunwayCentrelinePoint / TLOF | Terminal noktalarının meydan bağı |
| `SegmentPoint.pointChoice_runwayPoint / _aimingPoint / _airportReferencePoint` | RunwayCentrelinePoint / TLOF / AirportHeliport | **Rota/prosedür segment noktası olarak** pist eşiği veya ARP (bkz. `../AIXM_Route_Network_Overview.md` §3 — 6 seçenekli choice'ın 3'ü buraya işaret eder) |
| `RoutePortion.start/intermediatePoint/end_*`, `ChangeOverPoint.location_*`, `SignificantPointInAirspace.location_*`, `FinalLeg.finalPathAlignmentPoint_*`, `TerminalArrivalArea.IF_*/IAF_*`, `NavigationArea.centrePoint_*`, `MinimumAltitudeArea.centrePoint_*` | aynı üçlü | Aynı "significant point" choice deseni |
| `MinimumAltitudeArea.location` (0..*) | AirportHeliport | MSA/TAA'nın ait olduğu meydan |
| `ObstacleArea.reference_ownerAirport / _ownerRunway / _ownerRunwayDirection` | AirportHeliport / Runway / RunwayDirection | Mânia alanı (Area 2/3, TOD...) sahibi |
| `AeronauticalGroundLight.aerodromeBeacon` | AirportHeliport | Meydan bikını |
| `AltimeterCheckpoint.locationOnRunway / OnApron / OnStand`, `CheckpointINS.location` | RunwayCentrelinePoint / Apron / AircraftStand | Kontrol noktaları |
| `RadarSystem.airportHeliport`, `RadarSystem.PARRunway` | AirportHeliport / Runway | Radar / PAR |
| `RulesProcedures.affectedLocation`, `PointUsage.referenceAirportHeliport`, `FlightConditionElement.*`, `FlightRoutingElement.*` | AirportHeliport | Kurallar, akış kısıtlamaları |
| `SatelliteApproachOperation.theAirportHeliport`, `NavigationSystemCheckpoint.airportHeliport` | AirportHeliport | |

> **"Significant point" üçlüsü:** AIXM'de bir noktanın geçtiği her yerde (rota segmenti,
> COP, prosedür bacağı...) kullanılan choice'ın 6 seçeneğinden 3'ü havalimanı paketine
> aittir: `runwayPoint` → `RunwayCentrelinePoint`, `aimingPoint` → `TouchDownLiftOff`,
> `airportReferencePoint` → `AirportHeliport` (ARP'si kullanılır).
