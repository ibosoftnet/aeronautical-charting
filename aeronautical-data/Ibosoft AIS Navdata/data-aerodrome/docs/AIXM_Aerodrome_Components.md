# AIXM 5.2 — Havalimanının Altındaki Elemanlar (Katalog)

Kaynak: `AIXM_Features_annotated.xsd` (satır ~498-7483) + `AIXM_DataTypes_annotated.xsd`
(17 January 2025, AIXM 5.2)

Bu doküman havalimanı paketindeki **tüm** feature'ları tek listede toplar: ne işe yarar,
kime bağlanır, geometrisi nedir. Pist, taksi yolu, apron ve helikopter aileleri kendi
dokümanlarında detaylıdır; burada **tam attribute listesi yalnızca başka dokümanda
anlatılmayan** elemanlar için verilmiştir (§3-§6).

Kısaltmalar: **F** = Feature (kendi UUID'si var), **O** = Object (gömülü). "Bağ" sütunu,
elemanın yukarıya işaret eden alanıdır.

---

## 1. Hiyerarşi ağacı

Ok yönü = XML'deki referans yönü (çocuk → ebeveyn). Girinti "mantıksal olarak altında"
anlamındadır.

```
AirportHeliport (F)  ── ARP (nokta), aviationBoundary (alan)
│
├── Runway (F)                         ← associatedAirportHeliport          [geometri YOK]
│   ├── RunwayDirection (F) ×2         ← usedRunway                         [geometri YOK]
│   │   ├── RunwayCentrelinePoint (F)  ← onRunwayDirection                  [nokta]
│   │   │   └── RunwayDeclaredDistance (O) → RunwayDeclaredDistanceValue (O)
│   │   ├── RunwayProtectArea (F)      ← protectedRunwayDirection           [alan]  (CWY, STOPWAY, RESA, OFZ...)
│   │   │   ├── RunwayProtectAreaLightSystem (F) ← lightedArea
│   │   │   └── AirportProtectionAreaMarking (F) ← markedProtectionArea
│   │   ├── RunwayBlastPad (F)         ← usedRunwayDirection                [alan]
│   │   ├── ArrestingGear (F)          ← runwayDirection (0..*)             [nokta|çizgi|alan]
│   │   ├── RunwayDirectionLightSystem (F) ← associatedRunwayDirection
│   │   ├── ApproachLightingSystem (F) ← servedRunwayDirection
│   │   ├── VisualGlideSlopeIndicator (F) ← runwayDirection                 (PAPI/VASIS)
│   │   └── RunwayVisualRangeEquipment (F) ← associatedRunwayDirection (0..*) [nokta]
│   ├── RunwayElement (F)              ← associatedRunway (0..*)            [alan]
│   └── RunwayMarking (F)              ← markedRunway
│
├── Taxiway (F)                        ← associatedAirportHeliport          [geometri YOK]
│   ├── TaxiwayElement (F)             ← associatedTaxiway (0..*)           [alan]
│   ├── TaxiwayLightSystem (F)         ← lightedTaxiway
│   └── TaxiwayMarking (F)             ← markedTaxiway / markedElement
│
├── GuidanceLine (F)                   → connectedTaxiway/Apron/Stand/RunwayCentrelinePoint/TLOF (0..*) [çizgi]
│   ├── GuidanceLineLightSystem (F)    ← lightedGuidanceLine
│   ├── GuidanceLineMarking (F)        ← markedGuidanceLine
│   └── TaxiHoldingPosition (F)        ← associatedGuidanceLine, → protectedRunway (0..*) [nokta]
│       ├── TaxiHoldingPositionLightSystem (F) ← taxiHolding              (stop bar, RGL...)
│       └── TaxiHoldingPositionMarking (F)     ← markedTaxiHold
│
├── Apron (F)                          ← associatedAirportHeliport          [geometri YOK]
│   ├── ApronElement (F)               ← associatedApron                    [alan]
│   │   └── AircraftStand (F)          ← apronLocation                      [nokta + alan]
│   │       ├── StandMarking (F)       ← markedStand
│   │       ├── PassengerLoadingBridge (F) ← associatedStand (0..*)         [alan]
│   │       └── DeicingArea (F)        ← standLocation (veya associatedApron / taxiwayLocation) [alan]
│   │           └── DeicingAreaMarking (F) ← markedDeicingArea
│   ├── ApronLightSystem (F)           ← lightedApron
│   └── ApronMarking (F)               ← markedApron
│
├── TouchDownLiftOff (F)               ← associatedAirportHeliport, → approachTakeOffArea (FATO Runway) [alan + nokta]
│   ├── TouchDownLiftOffSafeArea (F)   ← protectedTouchDownLiftOff          [alan]
│   ├── TouchDownLiftOffLightSystem (F)← lightedTouchDownLiftOff
│   └── TouchDownLiftOffMarking (F)    ← markedTouchDownLiftOff
│
├── Road (F)                           ← associatedAirport, → accessibleStand (0..*) [alan]
├── AirportSign (F)                    ← associatedAirport                  [nokta]
├── AirportHotSpot (F)                 ← affectedAirport                    [alan]
├── WorkArea (F)                       ← associatedAirportHeliport          [alan]
├── NonMovementArea (F)                ← associatedAirportHeliport          [alan]
├── SurveyControlPoint (F)             ← associatedAirportHeliport          [nokta]
├── WaterBody (F)                      ← location (0..*)                    [alan, Elevated değil]
├── SeaplaneLandingArea (F)            ← associatedAirportHeliport          [alan]
│   ├── → rampSite: SeaplaneRampSite (F)   [alan + eksen çizgisi]
│   ├── → dockSite: FloatingDockSite (F)   [alan]
│   ├── → assignedGangway: Gangway (F)     [geometri YOK]
│   └── MarkingBuoy (F)                ← theSeaplaneLandingArea             [nokta]
│
├── PilotControlledLighting (F)        → activatedGroundLighting (0..*)  (havalimanına doğrudan bağı yok)
├── AirportHeliportCollocation (F)     → hostAirport, dependentAirport
└── (gömülü) servedCity, responsibleOrganisation, availability, altimeterSource→WeatherSource (F), contaminant
```

---

## 2. Katalog tablosu

| Feature | Tür | Ne işe yarar | Bağ (yukarı) | Geometri | Detay |
|---|---|---|---|---|---|
| `AirportHeliport` | F | Meydan | — | `ARP` nokta, `aviationBoundary` alan | `AIXM_AirportHeliport_Attributes.md` |
| `AirportHeliportCollocation` | F | İki meydanın tesis paylaşımı | `hostAirport`, `dependentAirport` | — | `AIXM_AirportHeliport_Attributes.md` §4 |
| `Runway` | F | Pist / FATO / su pisti (mantıksal) | `associatedAirportHeliport` | — | `AIXM_Runway_Attributes.md` |
| `RunwayDirection` | F | Pistin bir iniş/kalkış yönü (ör. 05, 23) | `usedRunway` | — | 〃 |
| `RunwayCentrelinePoint` | F | Eksen üzerindeki önemli nokta (THR, END, TDZ...) | `onRunwayDirection` | nokta | 〃 |
| `RunwayElement` | F | Pist yüzey parçası | `associatedRunway` (0..*) | alan | 〃 |
| `RunwayProtectArea` | F | Stopway, clearway, RESA, OFZ, ILS/VGSI koruma alanı | `protectedRunwayDirection` | alan | 〃 |
| `RunwayBlastPad` | F | Blast pad | `usedRunwayDirection` | alan | 〃 |
| `ArrestingGear` | F | Durdurma sistemi (kablo, ağ, EMAS) | `runwayDirection` (0..*) | nokta/çizgi/alan (choice) | 〃 |
| `RunwayVisualRangeEquipment` | F | RVR sensörü | `associatedRunwayDirection` (0..*) | nokta | 〃 |
| `VisualGlideSlopeIndicator` | F | PAPI/VASIS/APAPI... | `runwayDirection` | (LightElement noktaları) | 〃 |
| `ApproachLightingSystem` | F | Yaklaşma ışıkları (ALS) | `servedRunwayDirection` | (LightElement noktaları) | 〃 |
| `RunwayDirectionLightSystem` | F | Pist kenar/eşik/TDZ/eksen ışıkları | `associatedRunwayDirection` | 〃 | 〃 |
| `RunwayProtectAreaLightSystem` | F | Stopway vb. ışıkları | `lightedArea` | 〃 | 〃 |
| `RunwayMarking` | F | Pist işaretleri | `markedRunway` | (MarkingElement) | 〃 |
| `Taxiway` | F | Taksi yolu (mantıksal) | `associatedAirportHeliport` | — | `AIXM_Taxiway_Attributes.md` |
| `TaxiwayElement` | F | Taksi yolu yüzey parçası | `associatedTaxiway` (0..*) | alan | 〃 |
| `GuidanceLine` | F | Taksi merkez hattı / lead-in / lead-out | `connected*` (0..*) | çizgi | 〃 |
| `TaxiHoldingPosition` | F | Pist/ara bekleme noktası | `associatedGuidanceLine`, `protectedRunway` | nokta | 〃 |
| `TaxiwayLightSystem`, `GuidanceLineLightSystem`, `TaxiHoldingPositionLightSystem` | F | Taksi ışıkları, stop bar | ilgili feature | (LightElement) | 〃 |
| `TaxiwayMarking`, `GuidanceLineMarking`, `TaxiHoldingPositionMarking` | F | Taksi işaretleri | ilgili feature | (MarkingElement) | 〃 |
| `AirportHotSpot` | F | Çarpışma/pist ihlali riski yüksek nokta | `affectedAirport` | alan | §3.1 + `AIXM_Taxiway_Attributes.md` |
| `Apron` | F | Apron (mantıksal) | `associatedAirportHeliport` | — | `AIXM_Apron_Attributes.md` |
| `ApronElement` | F | Apron yüzey parçası | `associatedApron` | alan | 〃 |
| `AircraftStand` | F | Park yeri / gate | `apronLocation` → ApronElement | nokta + alan | 〃 |
| `DeicingArea` | F | Buz çözme alanı | `associatedApron` / `taxiwayLocation` / `standLocation` | alan | 〃 |
| `PassengerLoadingBridge` | F | Körük / merdiven | `associatedStand` (0..*) | alan | 〃 |
| `Road` | F | Servis/kamu yolu | `associatedAirport` | alan (`surfaceExtent`) | 〃 |
| `ApronLightSystem`, `ApronMarking`, `StandMarking`, `DeicingAreaMarking` | F | Apron ışık/işaretleri | ilgili feature | — | 〃 |
| `TouchDownLiftOff` | F | Heli TLOF | `associatedAirportHeliport`, `approachTakeOffArea` | alan + merkez nokta | `AIXM_Heliport_TLOF_FATO.md` |
| `TouchDownLiftOffSafeArea` | F | TLOF/FATO güvenlik alanı | `protectedTouchDownLiftOff` | alan | 〃 |
| `TouchDownLiftOffLightSystem`, `TouchDownLiftOffMarking` | F | TLOF ışık/işaret | ilgili feature | — | 〃 |
| `AirportProtectionAreaMarking` | F | Koruma alanı kenar işaretleri | `markedProtectionArea` (RunwayProtectArea veya TLOFSafeArea) | — | `AIXM_Surface_Common_Objects.md` §6 |
| `AirportSign` | F | Havalimanı tabelası | `associatedAirport` | nokta | §3.2 |
| `WorkArea` | F | İnşaat/çalışma alanı | `associatedAirportHeliport` | alan | §3.3 |
| `NonMovementArea` | F | Kuleden görülmeyen, hareketi kısıtlı alan | `associatedAirportHeliport` | alan | §3.4 |
| `SurveyControlPoint` | F | Ölçme kontrol noktası (nirengi) | `associatedAirportHeliport` | nokta | §3.5 |
| `WaterBody` | F | Manevra alanı yakınındaki su kütlesi | `location` (0..*) | alan (`Surface`) | §3.6 |
| `WeatherSource` | F | Meteoroloji sensörü (altimetre, rüzgâr, kamera) | — (AltimeterSource'tan) | nokta | `AIXM_AirportHeliport_Attributes.md` §3 |
| `PilotControlledLighting` | F | Mikrofon tıklamasıyla aktive edilen ışık servisi | — | — | §4 |
| `SeaplaneLandingArea` ve ilgili 4 feature | F | Deniz uçağı alanları | `associatedAirportHeliport` | çeşitli | §5 |

---

## 3. Diğer bağımsız feature'lar (tam attribute listesi)

### 3.1 AirportHotSpot

Havalimanı hareket alanında çarpışma veya pist ihlali geçmişi/riski olan ve pilot/sürücü
dikkatinin artırılması gereken yer (AD 2.24 chart'larındaki "HS1, HS2...").

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `designator` | `TextDesignatorType` | 1-16 karakter — haritadaki etiketi (ör. `HS1`) |
| `instruction` | `TextInstructionType` | Serbest metin, max 10000 — yaklaşırken yapılacaklar |
| `area` | `ElevatedSurfacePropertyType` | Hotspot alanı (poligon) |
| `affectedAirport` | `AirportHeliportPropertyType` | Bağlı meydan |
| `annotation` (0..∞) | `NotePropertyType` | |

### 3.2 AirportSign

Tabela gövdesi, reflektif panel, yazı, elektrik ve montaj bileşenlerinden oluşan tam
tabela ünitesi.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeAirportSignType` | → bkz. aşağıdaki tablo |
| `frontMessageText` | `TextNoteType` | Ön yüz yazısı |
| `backMessageText` | `TextNoteType` | Arka yüz yazısı |
| `frontSignBearing` | `ValBearingType` | 0-360 — ön yüzün baktığı gerçek kerteriz |
| `height` | `ValDistanceType` | Tepe yüksekliği + `uom` |
| `lighted` | `CodeYesNoType` | `YES, NO` |
| `direction` | `CodeCardinalDirectionType` | 16 yön — okun gösterdiği yön |
| `side` | `CodeSideType` | `LEFT, RIGHT, BOTH, CENTRE` — pistin hangi tarafında |
| `location` | `ElevatedPointPropertyType` | Konum |
| `signStatus` (0..∞) | `AirportSignStatusPropertyType` | → `AirportSignStatus{status: CodeStatusOperationsType}` (+ Timesheet) |
| `associatedAirport` | `AirportHeliportPropertyType` | Bağlı meydan |
| `annotation` (0..∞) | `NotePropertyType` | |

**`CodeAirportSignType` değerleri:**

| Grup | Değerler |
|---|---|
| Zorunlu talimat (kırmızı) | `RWY_INT_HOLD` (taksi/pist kesişim bekleme), `RWY_APCH_DEP_HOLD` (yaklaşma/kalkış alanı bekleme), `CAT_HOLD` (CAT I/II/III bekleme), `RWY_CRITICAL` (ILS kritik alan / POFZ sınırı), `MIL_HOLD`, `NO_ENTRY` |
| Konum | `TWY_LOCATION`, `RWY_LOCATION` |
| Yön / varış | `TWY_DIRECTION`, `OUTBOUND_DEST`, `APRON`, `CARGO`, `CIVIL`, `FBO`, `FUEL`, `INTL`, `MIL`, `PAX`, `TERM` |
| Pist bilgi | `RWY_EXIT`, `RWY_VACATED`, `RWY_DIST_REMAIN`, `INT_TKOF` (kesişimden kalkış kalan mesafe), `TWY_END` |
| Diğer | `INFO_NAVAID` (VOR kontrol noktası tabelası), `INFO_VEH`, `VEH_STOP`, `VEH_YIELD` |

(+`OTHER`)

### 3.3 WorkArea (+ WorkareaActivity)

Hareket alanının inşaat altındaki kısmı.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeWorkAreaType` | `CONSTRUCTION` (AMDB Construction Area), `SURFACEWORK` (yüzey iyileştirme), `PARKED` (park etmiş/arızalı uçak veya makine) |
| `plannedOperational` | `DateType` | Alanın operasyonel olması beklenen tarih |
| `associatedAirportHeliport` | `AirportHeliportPropertyType` | |
| `extent` | `ElevatedSurfacePropertyType` | Alan |
| `activation` (0..∞) | `WorkareaActivityPropertyType` | → `WorkareaActivity{isActive: YES/NO}` + Timesheet (hangi saatlerde aktif) |
| `annotation` (0..∞) | `NotePropertyType` | |

### 3.4 NonMovementArea

Kontrol kulesinden görülemeyen ve bu yüzden hareketin kısıtlandığı alan.

| Attribute | Değer Tipi |
|---|---|
| `associatedAirportHeliport` | `AirportHeliportPropertyType` |
| `extent` | `ElevatedSurfacePropertyType` |
| `annotation` (0..∞) | `NotePropertyType` |

### 3.5 SurveyControlPoint

Kalıcı işaretle tesis edilmiş ölçme referans noktası.

| Attribute | Değer Tipi | Not |
|---|---|---|
| `designator` | `TextNameType` | **Dikkat:** designator olmasına rağmen tipi `TextNameType` (max 60, küçük harf kabul eder) |
| `associatedAirportHeliport` | `AirportHeliportPropertyType` | |
| `location` | `ElevatedPointPropertyType` | |
| `annotation` (0..∞) | `NotePropertyType` | |

### 3.6 WaterBody

Meydan hareket alanına yakın su kütlesi.

| Attribute | Değer Tipi | Not |
|---|---|---|
| `extent` | `SurfacePropertyType` | **Elevated değil** — düz `Surface` (yükseklik/datum alanı yok) |
| `location` (0..∞) | `AirportHeliportPropertyType` | Birden çok meydana bağlanabilir |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 4. PilotControlledLighting (+ LightActivation)

Mikrofon tuşlamasıyla ışıkların havadan kontrolü (genelde kulesiz veya kulenin kapalı
olduğu saatlerde). **Havalimanına doğrudan bağı yoktur**; aktive ettiği ışık
sistemlerine (`activatedGroundLighting`) işaret eder, meydan bağı bu sistemler üzerinden
kurulur.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodePilotControlledLightingType` | `STANDARD_FAA, NON_STANDARD` |
| `duration` | `ValDurationType` | Işığın açık kalma süresi (tipik 15 dk) + `uom` (`HR, MIN, SEC`) |
| `intensitySteps` | `NoNumberType` | Yoğunluk kademesi sayısı |
| `standByIntensity` | `CodeIntensityStandByType` | `OFF, LOW` — kullanılmadığında |
| `radioFrequency` | `ValFrequencyType` | Aktivasyon frekansı + `uom` |
| `activationInstruction` | `TextInstructionType` | Talimat metni |
| `controlledLightIntensity` (0..∞) | `LightActivationPropertyType` | → **LightActivation** (O): `clicks` (tıklama sayısı), `intensityLevel` (`LIL, LIM, LIH, LIL_LIH, PREDETERMINED`), `activation` (`ON, ON_OR_OFF, OFF`) |
| `activatedGroundLighting` (0..∞) | `GroundLightSystemPropertyType` | → herhangi bir `*LightSystem` feature'ı |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 5. Deniz uçağı (seaplane) elemanları

Su pistleri `Runway.type=WATER_RWY`, su taksi yolları `Taxiway.type=CHANNEL` /
`TURNING_BASIN` ile ifade edilir (bkz. pist/taksi dokümanları; `Runway.depth`,
`Taxiway.depth/diameter` su alanlarına özgü alanlardır). Bunlara ek olarak:

### 5.1 SeaplaneLandingArea

| Attribute | Değer Tipi | Açıklama |
|---|---|---|
| `rampSite` (0..∞) | `SeaplaneRampSitePropertyType` | Bağlı rampa(lar) — **aşağı yönlü referans** |
| `dockSite` (0..∞) | `FloatingDockSitePropertyType` | Bağlı yüzer iskele(ler) |
| `extent` | `ElevatedSurfacePropertyType` | Alan |
| `annotation` (0..∞) | `NotePropertyType` | |
| `availability` (0..∞) | `ManoeuvringAreaAvailabilityPropertyType` | Operasyonel durum (manevra alanı tipi) |
| `assignedGangway` (0..∞) | `GangwayPropertyType` | Bağlı iskele geçidi |
| `associatedAirportHeliport` | `AirportHeliportPropertyType` | Bağlı meydan |

### 5.2 SeaplaneRampSite / FloatingDockSite / Gangway / MarkingBuoy

| Feature | Attribute'lar |
|---|---|
| `SeaplaneRampSite` | `extent` (ElevatedSurface), `centreline` (ElevatedCurve), `annotation` |
| `FloatingDockSite` | `extent` (ElevatedSurface), `annotation` |
| `Gangway` | `width`, `length` (ValDistance), `type` (`WATER, GROUND`), `mobility` (YES=mobil / NO=sabit), `annotation` — **geometrisi yok** |
| `MarkingBuoy` | `designator` (`CodeBuoyDesignatorType`: `([A-Z]\|\d)*`), `type` (`CodeBuoyType`), `colour` (`CodeColourType`), `theSeaplaneLandingArea` (→ SeaplaneLandingArea), `location` (ElevatedPoint), `annotation` |

**`CodeBuoyType`:** `BLACK_RED_FL2` (izole tehlike), `GREEN` / `RED` (lateral — kanal
kenarı), `GREEN_RED_GFL` / `RED_GREEN_RFL` (tercihli kanal), `Q_VQ` / `Q3_VQ3` / `Q6_VQ6` /
`Q9_VQ9` (kardinal — kuzey/doğu/güney/batı), `RED_WHITE` (güvenli su), `WHITE` (renk
belirtilmemiş), `YELLOW` (özel amaçlı).
