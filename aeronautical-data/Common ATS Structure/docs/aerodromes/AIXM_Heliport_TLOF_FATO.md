# AIXM 5.2 — Helikopter Alanları: FATO, TLOF, Safe Area

Kaynak: `AIXM_Features_annotated.xsd` (satır ~2722-2925 TLOF; ~3783 ışık; ~4500 işaret;
~4866 Runway) + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> AIXM'de ayrı bir "FATO" feature'ı **yoktur**. Annex 14 Vol II kavramları şöyle eşlenir:
>
> | Annex 14 kavramı | AIXM karşılığı |
> |---|---|
> | Heliport | `AirportHeliport.type = HP` (veya meydanda heli alanı varsa `AH`) |
> | FATO | `Runway.type = FATO` + iki `RunwayDirection` (yaklaşma/kalkış yönleri) |
> | FATO eşik/nişan noktası | `RunwayCentrelinePoint` (`role = THR`, `HEL_AIMING_PT`...) |
> | FATO yüzeyi | `RunwayElement.extent` (FATO Runway'ine bağlı) |
> | TLOF | `TouchDownLiftOff` |
> | Safety area | `TouchDownLiftOffSafeArea` |
> | TODAH / RTODAH / LDAH | `RunwayDeclaredDistance.type` (FATO'nun centreline point'lerinde) |
> | Heli yaklaşma yolu göstergesi | `VisualGlideSlopeIndicator.type = HAPI` |
> | Hava taksi yolu | `Taxiway.type = AIR` / `GuidanceLine.type = AIR_TLANE` |

---

## 1. TouchDownLiftOff (TLOF)

Helikopterin teker koyabileceği veya kalkabileceği yük taşıyan alan.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `designator` | `TextDesignatorType` | 1-16 karakter | TLOF adı (ör. `H1`) |
| `length` | `ValDistanceType` | ≥0 + `uom` | Fiziksel uzunluk |
| `width` | `ValDistanceType` | ≥0 + `uom` | Fiziksel genişlik |
| `slope` | `ValSlopeType` | `-100..100` | Yüzey eğimi |
| `abandoned` | `CodeYesNoType` | `YES, NO` | |
| `extent` | `ElevatedSurfacePropertyType` | poligon | **Geometri** |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | → `AIXM_Surface_Common_Objects.md` §1 | |
| `associatedAirportHeliport` | `AirportHeliportPropertyType` | xlink | **Bağlı meydan** |
| `approachTakeOffArea` | `RunwayPropertyType` | xlink | İçinde bulunduğu FATO — **yalnızca `type=FATO` olan Runway** (DO-272 Rule 14) |
| `contaminant` (0..∞) | `TouchDownLiftOffContaminationPropertyType` | → §4 ortak | |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ManoeuvringAreaAvailabilityPropertyType` | → §3 ortak | |
| `aircraft` (0..∞) | `AircraftCharacteristicPropertyType` | ortak tip | TLOF'u kullanabilecek helikopter özellikleri (D-value, max ağırlık...) |
| `geometricCentre` | `ElevatedPointPropertyType` | nokta | TLOF geometrik merkezi |

> TLOF, significant point choice'larında **`aimingPoint`** seçeneği olarak kullanılır
> (`pointChoice_aimingPoint`, `DesignatedPoint.aimingPoint`,
> `FinalLeg.finalPathAlignmentPoint_aimingPoint` ...) — heli prosedürlerinde nişan noktası.
> Bu referanslarda hangi konumun kullanılacağı (muhtemelen `geometricCentre`) şemada
> belirtilmez.

---

## 2. TouchDownLiftOffSafeArea

TLOF çevresinde, helikopteri manevra/kalkış/iniş sırasında korumak için mâniasız alan.
`AbstractAirportHeliportProtectionArea`'dan türer.

| Attribute | Değer Tipi | Açıklama |
|---|---|---|
| *(miras)* `width`, `length` | `ValDistanceType` | |
| *(miras)* `lighting` | `CodeYesNoType` | |
| *(miras)* `obstacleFree` | `CodeYesNoType` | |
| *(miras)* `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | |
| *(miras)* `extent` | `ElevatedSurfacePropertyType` | **Geometri** |
| *(miras)* `annotation` (0..∞) | `NotePropertyType` | |
| `protectedTouchDownLiftOff` | `TouchDownLiftOffPropertyType` | **Bağlı TLOF** |

---

## 3. TouchDownLiftOffLightSystem

`AbstractGroundLightSystem`'dan türer (miras: `emergencyLighting`, `intensityLevel`,
`colour`, `element`, `availability`, `annotation`).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `position` | `CodeTLOFSectionType` | `AIM` (nişan noktası), `EDGE` (kenar) |
| `lightedTouchDownLiftOff` | `TouchDownLiftOffPropertyType` | **Bağlı TLOF** |

FATO ışıkları FATO bir `Runway` olduğu için `RunwayDirectionLightSystem` ile kodlanır.

---

## 4. TouchDownLiftOffMarking

`AbstractMarking`'den türer (miras: `markingICAOStandard`, `condition`, `element`,
`annotation`).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `markingLocation` | `CodeTLOFSectionType` | `AIM, EDGE` |
| `markedTouchDownLiftOff` | `TouchDownLiftOffPropertyType` | **Bağlı TLOF** |

Safe area kenar işaretleri `AirportProtectionAreaMarking.markedProtectionArea` →
`TouchDownLiftOffSafeArea` ile verilir.

---

## 5. Minimum heliport kaydı (sıra)

```
1. AirportHeliport            type=HP, ARP, fieldElevation
2. Runway                     type=FATO, designator, nominalLength/Width, associatedAirportHeliport
3. RunwayDirection ×2         designator (ör. "09"/"27" veya FATO yön adları), trueBearing, usedRunway
4. RunwayCentrelinePoint      role=THR / HEL_AIMING_PT, location, onRunwayDirection
                              + associatedDeclaredDistance: TODAH, RTODAH, LDAH
5. RunwayElement              extent (FATO poligonu), associatedRunway
6. TouchDownLiftOff           extent, geometricCentre, associatedAirportHeliport, approachTakeOffArea → FATO
7. TouchDownLiftOffSafeArea   extent, protectedTouchDownLiftOff
8. (ops.) TLOF/FATO ışık, işaret, HAPI (VisualGlideSlopeIndicator), Navaid.touchDownLiftOff
```

Genel ekleme prensipleri ve XML biçimi için `AIXM_Surfaces_How_To_Add.md`'ye bakın;
heli için tek fark `Runway.type=FATO` ve heli-özel declared distance tipleridir.
