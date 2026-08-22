# AIXM 5.2 — `annotation` (Note / LinguisticNote): Ortak Yapı

Kaynak: `AIXM_Features_annotated.xsd` (`Note`/`NoteType`/`NotePropertyType`, satır
~12726-12780; `LinguisticNote`/`LinguisticNoteType`/`LinguisticNotePropertyType`, satır
~12689-12723), 17 January 2025, AIXM 5.2

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Ayrıca her `Code*`/`Val*`/`Text*Type`, `complexType`
> olarak `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u da taşır.

## Bu doküman neden ayrı

`annotation` alanı, bu proje dokümantasyonundaki **her tek dokümanda** (Route,
RouteSegment, DesignatedPoint, Navaid, Point, PointReference, AircraftCharacteristic,
AirspaceLayer, vb.) tekrar tekrar görünür. Şemada bu, kopya/benzer tipler değil,
**tek ve aynı** `NotePropertyType` → `Note` tanımına referanstır (XSD'de bir kez
tanımlanır, tüm feature/object'ler bu tek tanıma `element ref`'ler). Bu yüzden tekrar
tekrar aynı tabloyu yazmak yerine, tüm dokümanlar buraya işaret eder.

`Note`, AIXM'de bir **Object**'tir (`NoteType` → `AbstractAIXMObjectType`; `Feature`
değil — kendi `gml:id`/`timeSlice` geçmişi yoktur, gömülü olduğu feature'ın bir parçası
olarak var olur).

> *"A general text note for a feature or for one of its properties."*

---

## 1. annotation → Note

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `propertyName` (0..1) | `TextPropertyNameType` | Enum değil — serbest metin, lowerCamelCase, max 60 karakter, desen: `[A-Za-z\-_]*`. Notun hangi feature özniteliğiyle ilgili olduğunu belirtir; boşsa not feature'ın tamamı için geçerlidir |
| `purpose` (0..1) | `CodeNotePurposeType` | `DESCRIPTION` (açıklayıcı ek bilgi), `REMARK` (genel not), `WARNING` (dikkat/uyarı), `DISCLAIMER` (sorumluluk reddi) (+OTHER) |
| `translatedNote` (0..∞) | `LinguisticNotePropertyType` | Notun farklı dillerdeki çevirisi → bkz. **2** |

---

## 2. `translatedNote` → LinguisticNote

`LinguisticNoteType` → `AbstractAIXMObjectType` (Object, Feature değil).

> *"The Note written linguistically."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `note` | `TextNoteType` | Enum değil — serbest metin; `xml:lang` attribute'u ile dil etiketlenmiş not metni |

---

## Genişletme noktası

`Note.extension` → soyut `AbstractNoteExtension`; `LinguisticNote.extension` → soyut
`AbstractLinguisticNoteExtension` (ulusal AIP'lerin kendi ek alanlarını eklemesi için
extension noktası, boş/soyut tanımlı).

---

## Bu yapıyı kullanan dokümanlar

- [AIXM_Route_Attributes.md](AIXM_Route_Attributes.md) — `Route.annotation`
- [AIXM_RouteSegment_Attributes.md](AIXM_RouteSegment_Attributes.md) — `RouteSegment.annotation`, `AirspaceLayer.annotation`, `AircraftCharacteristic.annotation`, `AircraftNavigationEquipment.annotation`
- [AIXM_RoutePoint_DataTypes.md](AIXM_RoutePoint_DataTypes.md) — `PointReference.annotation`, `Distance.annotation`, `AngleUse.annotation`, `Angle.annotation`
- [aixm-point-types/AIXM_DesignatedPoint_Attributes.md](aixm-point-types/AIXM_DesignatedPoint_Attributes.md) — `DesignatedPoint.annotation`
- [aixm-point-types/AIXM_Navaid_Attributes.md](aixm-point-types/AIXM_Navaid_Attributes.md) — `Navaid.annotation`, `NavaidComponent.annotation`, `ElevatedPoint.annotation`
- [aixm-point-types/AIXM_Point_Attributes.md](aixm-point-types/AIXM_Point_Attributes.md) — `Point.annotation`
