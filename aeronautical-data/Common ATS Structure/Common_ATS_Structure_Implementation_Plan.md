# Common ATS Structure — Uygulama Planı

İki aşamalı proje:

| Aşama | Kapsam | Durum |
|---|---|---|
| **1** | Her kaynağın ham verisini kendi AIXM 5.2 XML dosyasına çeviren üreticiler | ✅ **TAMAMLANDI** |
| **2** | Common builder: kaynakları tek AIXM dosyasında birleştir → oradan GeoPackage türet | ⬜ **YAPILACAK** |

---

## Bağlayıcı kural (her iki aşama için de geçerli)

> **Hiçbir AIXM özniteliği sessizce atlanamaz.** `docs/*.md` referans dosyalarındaki
> her öznitelik ya bir sütuna/elemana eşlenmeli, ya da "kaynakta yok" olarak
> (ham veriye bakılarak doğrulanmış şekilde, varsayımla değil) işaretlenmelidir.
> **Bir şeyi "kapsam dışı" ilan etmek asla uygulayıcının tek başına vereceği bir
> karar değildir** — her böyle durum bulgusu ve gerekçesiyle kullanıcıya
> getirilip onaylanmalıdır.
>
> **Uydurma eşleme/açıklama yok.** Her eşleme, enum karşılığı veya "bu alan
> kaynakta var/yok" iddiası gerçekten okunmuş bir şeye (XSD, ham XML külliyatı,
> legacy scriptler) dayanmalıdır.
>
> **Gerçekten bilinmeyen/belirsiz her alan, enum değeri veya davranış
> sorulmalıdır, varsayılmamalıdır.** Bu kural planlama görüşmesiyle sınırlı
> değildir, uygulama boyunca geçerlidir.

---

# 1. AŞAMA — Kaynak AIXM üreticileri ✅ TAMAMLANDI

## Mimari

Her veri sağlayıcı, ham verisini **kendi başına geçerli, bağımsız bir AIXM 5.2
XML dosyasına** çeviren kendi aracına sahiptir. Common builder hiçbir kaynağın
ham formatını tanımaz — yalnızca AIXM okur.

| Üretici | Konum | Çıktı | Durum |
|---|---|---|---|
| **LT** | `data-sources/LT/generate-aixm-data/` | `lt-route-data-aixm.xml` (4.368 feature) | Hazır |
| **Jeppesen NDB** | `data-sources/Jeppesen/generate-aixm-data/` | `jeppesen-ndb-aixm.xml` (6.146 feature) + `jeppesen-ndb-index.json` + `data.json` | Hazır |
| **EAD-SDO** | `data-sources/EAD-SDO/generate-aixm-data/` | `ead-sdo-aixm.xml` (274.933 feature, ~461 MB) + `ead-sdo-originators.json` | Hazır |
| TRNC | — | — | Kaynak veri yok |

## Doğrulanan sonuçlar

| Kontrol | Sonuç |
|---|---|
| AIXM 5.2 XSD (üç dosya da tam hâlleriyle) | **0 hata** |
| `gml:id` tekilliği | EAD 1.572.860 · JEPP 30.160 · LT 29.263 — hepsi farklı, **0 tekrar** |
| `gml:id` kaynaklar arası çakışma | **0** |
| `gml:identifier` (UUID) kaynaklar arası çakışma | **0** (EAD∩JEPP, EAD∩LT, JEPP∩LT) |
| `xlink:href` bütünlüğü | EAD 272.379 · JEPP 3.073 · LT 8.883 — **0 kırık** (2.901'i EAD→Jeppesen çapraz dosya) |
| Navaid eşleştirme motoru | Legacy `navaids.gpkg` ile **birebir aynı gruplama kararları** (tek fark: bu turda kapsam dışı olan tailored kayıtlar) |
| Uç nokta çözünürlüğü (EAD) | **%91,5** (169.323 / 185.080) |
| Segment uzunluğu makullüğü (EAD) | En uzun 966 NM; 1000 NM üstü **yok** |

## Kaynak önekleri

Üç kaynağın dosyaları 2. aşamada birleşeceği için her `gml:id` kaynak önekiyle
üretilir — önek `IdRegistry` içinde uygulandığından türetilmiş id'ler
(`_TS`, `_TP`, `_EP`, `_NC1`, `_C`, `_START` …) ve mesaj kökleri de öneki taşır:

| Kaynak | Önek | Örnek | Mesaj kökü |
|---|---|---|---|
| EAD-SDO | `EAD_` | `EAD_RS_001610` | `EAD_MSG_SDO` |
| Jeppesen | `JEPP_` | `JEPP_NAV_NDB_BBS_DA` | `JEPP_MSG_NDB` |
| LT | `LT_` | `LT_DP_ABDIK` | `LT_MSG_ROUTE_DATA` |

## 1. aşamada plandan sapan / eklenen kararlar (hepsi kullanıcı onaylı)

1. **Uç nokta eşleştirmesi coğrafi yakınlıkla yapılır** — segmentin iki ucu
   birlikte çözülür, aday çiftlerinden segment uzunluğunu en küçük yapan seçilir;
   originator yalnızca eşitlik bozucudur; en iyi çift 1000 NM'yi aşarsa eşleşme
   kabul edilmez. (Originator'ı zorunlu şart yapmak %64,6, tek ayıklama ölçütü
   yapmak %87,6 veriyordu ama coğrafi olarak yanlış seçebiliyordu — bkz. 2. aşama
   bölümündeki "Giderilen sorun".)
2. **NDB için yeni bir kaynak eklendi (Jeppesen).** EAD-SDO'da NDB raporu yok;
   NDB'ler ayrı dosyada üretilir, EAD kendi dosyasına NDB yazmaz, onlara çapraz
   dosya `xlink` referansı verir. Belirsizlikte rotanın `txtLocDesig` ICAO bölge
   kodu ile ayıklanır.
3. **AIXM designator desenine uymayan rota kodları** (%2,4) `Route.name` alanına
   yazılır, kayıt düşürülmez.
4. **`codeWorkHr=H24`** için tam AIXM `Timesheet` yapısı **+** annotation üretilir
   (`operationalStatus` yazılmaz — kaynak "çalışıyor mu"yu söylemiyor).
5. **`validTime/beginPosition`** her kaydın kendi `dtWef` değerinden gelir;
   `data.json`'daki `data_effectivity` üretilen veri setinin geçerliliğidir,
   feature'ın yürürlüğüyle ilgisizdir.
6. **Üreticiler `data-sources/<KAYNAK>/generate-aixm-data/` altında** (planın ilk
   hâlindeki `sources/ead_sdo/` yerine) — LT'nin zaten kullandığı yerleşim.
7. **Jeppesen `data.json` bir çıktıdır** — her çalıştırmada
   `Jeppesen Data/data.json`'dan birebir kopyalanır, elle düzenlenmez.
8. **Tekilleştirme iki yerde gerekti** (AIXM'de `gml:identifier` tekil olmak
   zorunda): bölge sınırını kesen 623 rota segmenti (`mid` bazında, kopyalar
   birebir aynı olduğu doğrulandı) ve birden fazla Navaid tarafından eşleştirilen
   ekipman (bir kez yazılır, çoklu referans verilir — **eşleştirme kararları
   değişmeden**).

## Ayrıntılı dokümanlar

- `data-sources/EAD-SDO/generate-aixm-data/EAD-SDO_Field_Mapping.md`
- `data-sources/Jeppesen/generate-aixm-data/Jeppesen_to_AIXM_Mapping.md`
- `data-sources/LT/generate-aixm-data/DHMI_to_AIXM_Mapping.md`

Her üreticide `validate.bat` ile yeniden doğrulanabilir (`lxml` gerekir; AIXM
şeması GML 3.2.1'i uzaktan import ettiği için ilk derleme ~11 dk sürer, ardından
460 MB'lik dosya akış modunda ~16 sn'de doğrulanır).

---

# 2. AŞAMA — Common builder ✅ TAMAMLANDI

> **Uygulama sırasında eklenen/değişen davranışlar** aşağıda ilgili
> bölümlerde işaretlendi. Builder'ın güncel davranışının tam anlatımı
> [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md)'de, katman/sütun
> eşlemesi [`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md)'dedir.
> Bu iki doküman güncel kaynaktır; aşağıdaki plan metni tarihsel kayıttır.
>
> Plandan sapan başlıca noktalar:
> - **1. aşama artık orkestratörden çalıştırılabiliyor** (`run_source_generators`
>   + `source_generators` sırası; `--sources`). Plan yazıldığında üreticiler elle
>   çalıştırılıyordu.
> - **Çakışma çözümü tek yönlü değil, katmana göre iki yönlü**
>   (`prefer_base_on_match` + `prefer_base_on_match_layers`) — aşağıdaki
>   "Override kuralları" bölümü bu yüzden eksiktir.
> - **`points` katmanı iptal edildi**; 5 katman değil **4 katman** var.
>   Antimeridyen kesişim noktaları `DesignatedPoint` (`type=OTHER`) olarak
>   üretiliyor.
> - **Mekânsal (RTree) index** eklendi; tüm sütunlar da indeksleniyor.
> - Üretilen her AIXM dosyasının başlığı:
>   `<!-- Generated by Ibosoft AIS - ais.ibosoft.net.tr -->`
> - **Provenance/`gmlId`/`annotation` sütunları katman önekisiz** — aşağıdaki
>   "Provenance sütunları katman önekli" ifadesi artık geçerli değil; güncel
>   davranış `AIXM_to_GeoPackage_Schema_Design.md` §2'dedir (kullanıcı kararı).
> - **LT'nin `designatedPoints` override'ında konum tabanlı yedek eşleştirme**
>   eklendi: EAD'de aynı nokta farklı originator yazımıyla geçtiğinde
>   (`EUROCONTROL NMOC`, `INITIAL`, ulusal sağlayıcı adları …) doğal anahtar
>   tutmuyordu ve 613 LT noktasının 153'ü mükerrer kalıyordu — bkz.
>   `Common_Builder_Behaviour.md` §4.4.

## Neden iki alt-aşama

Common builder **tek adımda GeoPackage üretmez**. Önce yapılandırmadaki tarife
göre tüm kaynakları **tek bir AIXM 5.2 XML dosyasında birleştirir**, sonra
*yalnızca o dosyadan* GeoPackage türetir.

```
ana kaynaklar ───┬─ ead-sdo-aixm.xml      (+ originators)
                 └─ jeppesen-ndb-aixm.xml
ek kaynaklar ────┬─ lt-route-data-aixm.xml
                 └─ (trnc — henüz yok)
                        │
                        ▼
            AŞAMA 2A — BİRLEŞTİRME
            ana kaynaklar (EAD + Jeppesen) → iptal
            → ek kaynaklar (LT/TRNC, override) → antimeridyen bölme
                        │
                        ▼
        common-ats-structure-aixm.xml          ← kendi başına geçerli AIXM 5.2
        common-ats-structure-originators.json  ← gml:id → originator (AIXM'de alan yok)
                        │
                        ▼
            AŞAMA 2B — GEOPACKAGE TÜREVİ
            AIXM_to_GeoPackage_Schema_Design.md'ye göre saf eşleme
                        │
                        ▼
            common_ats_structure.gpkg  +  errored-features.csv
```

Bu ayrımın faydası: 2A çıktısı **XSD ile doğrulanabilir bir AIXM dosyasıdır**
(birleştirme/override/bölme mantığının doğruluğu bağımsız olarak sınanabilir),
2B ise saf bir şema eşlemesine indirgenir — kaynak bilgisi, override kuralları
veya geometri hesabı içermez.

## Modül yerleşimi

```
Common ATS Structure/
├── config.json                              # tarife: base + ek kaynaklar + seçenekler
├── build_common_ats.py                      # orkestratör (2A → 2B)
├── AIXM_to_GeoPackage_Schema_Design.md       # teslimat: şema/eşleme dokümanı
├── common-ats-structure-aixm.xml             # 2A ÇIKTISI
├── common-ats-structure-originators.json     # 2A ÇIKTISI
├── common_ats_structure.gpkg                 # 2B ÇIKTISI
├── errored-features.csv                      # 2B ÇIKTISI
├── merge/                                    # AŞAMA 2A
│   ├── aixm_reader.py      # jenerik message/hasMember/Feature/timeSlice okuyucu
│   ├── aixm_writer.py      # birleşik dosyayı akış modunda yazar
│   ├── exclude.py          # data-sources/excludes/*.json
│   ├── override.py         # ek kaynakların base kayıtları geçersiz kılması
│   └── antimeridian.py     # antimeridyen bölme (seçenek)
└── gpkg/                                     # AŞAMA 2B
    ├── schema.py           # 4 katman DDL, insert, index
    ├── mapper.py           # AIXM feature → katman satırı
    ├── validation_rules.py # docs/*.md'den alan kuralları
    └── validate.py         # validate_record(), severity, hata logu
```

`data-sources/excludes/` klasörü 2A için oluşturulur (şimdilik boş).

---

## AŞAMA 2A — Birleştirme

### Tarife (config.json)

**Ana kaynaklar: EAD-SDO ve Jeppesen. Ek kaynaklar: yalnızca LT ve TRNC.**

Jeppesen'in ana kaynak olmasının teknik bir zorunluluğu da var: EAD-SDO rota
segmentleri NDB uç noktaları için **doğrudan Jeppesen feature'larına** `xlink`
veriyor (2.901 çapraz referans). Jeppesen ek kaynak sayılıp isteğe bağlı hâle
getirilseydi, o referanslar birleşik dosyada kırık kalırdı.

```jsonc
{
  "base_sources": [
    { "name": "ead_sdo",  "file": "data-sources/EAD-SDO/ead-sdo-aixm.xml",
      "originators_file": "data-sources/EAD-SDO/ead-sdo-originators.json" },
    { "name": "jeppesen", "file": "data-sources/Jeppesen/jeppesen-ndb-aixm.xml",
      "data_json": "data-sources/Jeppesen/data.json" }
  ],
  "additional_sources": [
    { "name": "lt", "file": "data-sources/LT/lt-route-data-aixm.xml",
      "data_json": "data-sources/LT/data.json",
      "override_enabled": true,
      "override_base_originator": "DHMI TURKIYE" },
    { "name": "trnc", "file": "data-sources/TRNC/trnc-aixm-ats-structure.xml",
      "data_json": "data-sources/TRNC/data.json",
      "enabled": false, "override_enabled": false }
  ],
  "excludes_dir": "data-sources/excludes",
  "split_antimeridian": true,
  "merged_aixm": "common-ats-structure-aixm.xml",
  "merged_originators": "common-ats-structure-originators.json",
  "output_gpkg": "common_ats_structure.gpkg"
}
```

### İşlem sırası

1. **Ana kaynaklar** (`ead_sdo`, `jeppesen`) okunur; tüm feature'lar birleşik
   çıktıya geçer. `data_originator`, kaynağın `originators_file`'ı varsa
   `gml:id` ile oradan, yoksa `data.json`'daki sabit değerden gelir.
   Ana kaynaklar arasında override uygulanmaz — birbirlerini tamamlıyorlar,
   çakışmıyorlar (doğrulandı: `gml:id` ve UUID düzeyinde sıfır çakışma).
2. **İptal (exclude) modülü** — `data-sources/excludes/*.json` içindeki kurallara
   uyan kayıtlar çıkarılır. Kural biçimi `{"layer": …, "match": {…}}` — yalnızca
   rota segmentine özel değil, jenerik. Şimdilik dosya yok, no-op.
3. **Ek kaynaklar** (`lt`, `trnc`) sırayla eklenir; `override_enabled` olanlar
   aşağıdaki kurallara göre ana kaynak kayıtlarının yerine geçer, diğerleri
   salt-ekleme yapar.
4. **Antimeridyen bölme** (seçenek açıksa) — aşağıdaki bölüm.
5. Birleşik AIXM + originator yan dosyası yazılır.

### Override kuralları (`override_enabled: true` olan kaynaklar için)

Kaynaklar arası UUID uzayları bağımsız olduğundan eşleştirme **doğal anahtarla**
yapılır, UUID eşitliğiyle değil:

| Feature | Eşleşme anahtarı | Sonuç |
|---|---|---|
| RouteSegment | rota kimliği + start/end nokta kombinasyonu + originator | Ana kaynak segmentinin yerine geçer |
| DesignatedPoint | designator + originator | Ana kaynak kaydının yerine geçer |
| Point | designator/konum + originator | Ana kaynak kaydının yerine geçer |
| Navaid | type + ident + originator | Ana kaynak kaydının yerine geçer. `navaidComponents`'a **dokunmaz** — LT/TRNC gibi kaynaklarda ekipman ayrıntısı yoktur |

`override_base_originator` **her ek kaynak için ayrı ayarlanır**, koda gömülmez:
kaynağın kendi provenance originator'ı ile ana kaynak tarafında aranacak dize farklı
olabilir. LT için doğrulandı: kendi `data.json`'ı `"DHMİ Türkiye"` derken EAD
tarafındaki karşılığı `"DHMI TURKIYE"` yazımıyla geçiyor.

> **Uygulamada değişti — ters yön eklendi.** Yukarıdaki tablo yalnızca
> `override_enabled` yönünü (ek kaynak kazanır) anlatır. Uygulamada bir ek
> kaynak için **iki yön aynı anda** geçerli olabilir ve **katmana göre** ayrışır:
> `prefer_base_on_match_layers` listesindeki katmanlarda **ana kaynak kazanır**
> (ek kaynağın kaydı yazılmaz, ona referans veren her şey ana kaynağın
> UUID'sine yönlendirilir); diğer tüm katmanlarda `override_enabled` yönü işler.
>
> LT'de bu, `["navaids", "navaidComponents"]` olarak ayarlıdır: DesignatedPoint
> ve RouteSegment'te LT kazanır, navaid tarafında EAD kazanır. Gerekçe: LT'de
> ekipman ayrıntısı yok; LT bir Navaid'i override ettiğinde EAD'nin ona bağlı
> fiziksel VOR/DME/TACAN bileşenleri boşta kalıyordu (ölçüldü: 116 bağlanmamış
> bileşen). Ters yönde bu sayı 0'a indi.
>
> Ayrıca **tipsiz navaid'ler için gevşek eşleşme** eklendi: `type` taşımayan bir
> ek kaynak navaid'i `designator + originator` ile aranır; tek aday varsa
> devredilir, birden fazla aday varsa **seçim yapılmaz** ve belirsizlik loglanır.
>
> **Karşılaştırma tablosu ana kaynakla sınırlı değildir:** ek kaynaklar config
> sırasıyla işlenir ve her kaynağın yazılacak kayıtları tabloya eklenir; sonraki
> bir ek kaynak kendinden önce okunmuş bir ek kaynağa da devredebilir. TRNC bu
> yüzden `designatedPoints`'te LT'ye devreder (LT listede TRNC'den önce gelir).
> Ayrıntı: [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md) §4.3, §8.

### Antimeridyen bölme (yeni — `split_antimeridian` seçeneği)

`split_antimeridian: true` iken, antimeridyeni (±180° boylam) aşan her
`RouteSegment` kesişim noktasından **iki ayrı segmente** bölünür. Amaç: web
haritalarında segmentin tüm dünyayı boydan boya kat eder gibi çizilmesini
önlemek.

**Bu işlem 2A'da (AIXM düzeyinde) yapılır**, 2B'de değil — çünkü bölme yeni
`Point` feature'ları ve yeni `RouteSegment` feature'ları üretir; bunların AIXM
dosyasında gerçek `gml:identifier`'ları ve `xlink` referansları olmalıdır ki
birleşik dosya kendi içinde tutarlı ve XSD-geçerli kalsın.

**Tespit:** segmentin iki ucu arasındaki boylam farkının mutlak değeri 180°'den
büyükse, kısa geodesic yol antimeridyeni aşıyor demektir.

**Kesişim enlemi (kullanıcı kararı: WGS84 elipsoidi üzerinde geodesic):**
küresel büyük daire yaklaşımı değil, **WGS84 elipsoidi üzerinde gerçek geodesic**
kullanılır. Bağımlılık olarak `pyproj` eklenir (`pyproj.Geod(ellps="WGS84")` —
PROJ/GeographicLib sarmalayıcısı, C tabanlı, hızlı).

Yöntem: `Geod.inv()` ile iki uç arasındaki azimut ve mesafe bulunur, ardından
mesafe boyunca `Geod.fwd()` ile ikili arama (bisection) yapılarak boylamın tam
±180° olduğu nokta çözülür (tolerans ~1e-9°). Basit, sağlam ve segment sayısı
düşük olduğu için maliyeti önemsiz — ölçüldü: mevcut veride antimeridyeni aşan
segment sayısı **53** (83.444 geometrili segmentin %0,06'sı; LT'de 0).

> Bu 53 geçişin tamamı gerçek (Bering Boğazı, Aleutlar, Pasifik ekvatoru, bir
> kutup rotası; 40-587 NM). Ölçümün ilk hâlinde 96 görünüyordu; aradaki fark
> yanlış çözülmüş uç noktalardan kaynaklanıyordu ve aşağıdaki "Giderilen sorun"
> bölümündeki düzeltmeyle ortadan kalktı.

**Üretilenler:**

- **Bir adet `DesignatedPoint` feature** — konumu (kesişim enlemi, 180°).
  `-180°` aynı meridyendir; tutarlılık için `+180` yazılır.
  `type = OTHER`, `designator`/`name` **boş** bırakılır; tanımlayıcı bilgi
  annotation'dadır.

  > **Neden `Point` değil (şema kısıtı, XSD'den doğrulandı):** `aixm:Point`,
  > `gml:Point` substitution group'undadır — `AbstractAIXMFeature` değildir,
  > dolayısıyla `message:hasMember` olarak yazılamaz. Ayrıca
  > `PointPropertyType`, `<element ref="aixm:Point"/>` ile noktayı **satır içine
  > gömer** (`DesignatedPointPropertyType`/`NavaidPropertyType`'ın aksine, ki
  > onlar boş xlink association tipidir). Yani `pointChoice_position` paylaşılan
  > bir noktaya referans veremez. Tek paylaşılan ara nokta üretebilmek için
  > `DesignatedPoint` kullanılır (kullanıcı kararı).

  Bu noktanın `annotation/Note/translatedNote/LinguisticNote/note` alanı **tam
  olarak** şu metni taşır:

  > `Automatically generated by the AIS system to display antimeridian crossings on web maps.`

- **İki adet `RouteSegment`**, orijinalin yerine geçer:
  - **A**: orijinal `start` → yeni Point
  - **B**: yeni Point → orijinal `end`
  - İkisi de orijinalin diğer tüm özniteliklerini (level, dikey limitler,
    `routeFormed`, `validTime`, originator …) aynen devralır.
  - Geometri (`curveExtent`): A segmenti kesişimde **+180** veya **-180**
    boylamıyla biter, B segmenti **karşı işaretle** başlar (yön hangi taraftan
    geçildiğine göre belirlenir) — böylece her iki çizgi de haritada kendi
    yarısında kalır.
  - Her iki segmentin `annotation/Note/translatedNote/LinguisticNote/note`
    alanı **tam olarak** şu metni taşır:

    > `Route segment automatically split by the AIS system at the antimeridian for display on web maps.`

    Orijinal segmentin kendi annotation'ı varsa korunur; bu not **ek bir
    `annotation` olarak** yazılır (AIXM'de `annotation` 0..∞'dur), mevcut notun
    üzerine yazılmaz. GeoPackage tarafında `annotation` dört sabit sütuna
    (`Description`/`Remark`/`Warning`/`Disclaimer`) düzleştirildiği için, aynı
    `purpose` altında birden fazla not birleştirilerek yazılır — bu, planın
    "aynı purpose'a düşen notlar birleştirilir" kuralının doğrudan bir sonucudur.

- Yeni feature'ların `gml:id`/`gml:identifier` değerleri orijinalinkinden
  türetilir (örn. `…_AM_A`, `…_AM_B`, `…_AM_PT`) — deterministik, her çalıştırmada
  aynı.

**Not:** üretilen ara noktalar `designatedPoints` katmanına düşer
(`type=OTHER`), iki segment de aynı noktaya `pointChoice_fixDesignatedPoint`
ile xlink verir.

### ✅ Giderilen sorun — uç nokta çözümlemesi (1. aşama revizyonu, tamamlandı)

Antimeridyen özelliğinin kaç segmenti etkileyeceği ölçülürken, 1. aşamanın uç
nokta çözümleme stratejisinin (ident + tip, belirsizlikte rotanın originator'ı
ile ayıklama) bazı durumlarda **coğrafi olarak yanlış** nokta seçtiği bulundu:
233 segment 2000 NM'den uzundu, en uzunu **10.287 NM** (dünyanın yarısı).
Örn. `UL210` rotasında Bahamalar'daki `UMIMI`den **Tayvan'daki** `BORDO`ya —
kaynakta iki `BORDO` var, rotanın originator'ı `EUROCONTROL NMOC` olduğu için
ayıklama coğrafi olarak yanlış olanı seçmişti.

**Kök neden:** rotanın `OrgCre/txtName` değeri *rotayı* yayımlayan kurumdur,
*noktayı* değil — originator'ın zorunlu şart olmaktan çıkarılma gerekçesinin ta
kendisi; aynı sebeple **ayıklama ölçütü** olarak da güvenilir değil.

**Uygulanan düzeltme (kullanıcı onaylı):** segmentin iki ucu **birlikte** çözülür,
aday çiftleri arasından **segment uzunluğunu en küçük yapan** çift seçilir;
originator yalnızca eşitlik bozucudur. Seçilen en iyi çift **1000 NM**'yi
aşıyorsa (doğru nokta kaynakta hiç yok demektir) eşleşme kabul edilmez, çözümsüz
bırakılır ve loglanır.

| Ölçüt | Önce | Sonra |
|---|---|---|
| Uç nokta çözünürlüğü | %87,6 | **%91,5** |
| Belirsiz kalan uç nokta | 8.356 | **577** |
| Yalnızca yakınlık sayesinde ayıklanan | — | **9.936** |
| 1000 NM üstü segment | 279 (233'ü >2000 NM) | **0** (en uzun 966 NM) |
| Antimeridyeni aşan segment | 96 | **53** |

Kalan 53 geçiş gerçek: Bering Boğazı, Aleutlar, Pasifik ekvatoru, bir kutup
rotası — 40-587 NM arası (ortalama 220 NM). Antimeridyen bölme artık sağlıklı
geometri üzerinde çalışacak.

---

## AŞAMA 2B — GeoPackage türevi

Girdi **yalnızca** 2A çıktısıdır (birleşik AIXM + originator yan dosyası).
Eşleme kuralları `AIXM_to_GeoPackage_Schema_Design.md`'de tanımlıdır; bu aşama
o dokümanın birebir uygulamasıdır — kaynak bilgisi veya override mantığı içermez.

### Dört katman

> **`points` katmanı iptal edildi (kullanıcı kararı).** AIXM `Point` bağımsız
> bir feature değildir (yukarıdaki şema kısıtı) — `message:hasMember` olarak
> yazılamaz, yalnızca başka bir feature'ın içine gömülü geometri olarak bulunur.
> Bağımsız satırları olacak bir katman kurulamaz. Kaynakların hiçbirinde
> `pointChoice_position` (gömülü Point) kullanımı da yok; ileride çıkarsa
> loglanır.

1. **`designatedPoints`** — AIXM `DesignatedPoint`. Antimeridyen bölme açıksa
   üretilen ara noktalar da burada (`type=OTHER`).
2. **`navaids`** — AIXM `Navaid` (bileşik kimlik: `VOR_DME`, `VORTAC`, `ILS_DME`
   veya tekil `VOR`/`DME`/`TACAN`/`NDB`…). Kendi `location`'ı vardır; rota uç
   noktaları **bu katmana** çözülür.
3. **`navaidComponents`** — `Navaid.navaidEquipment` → `NavaidComponent` →
   `theNavaidEquipment` → `AbstractNavaidEquipment` zinciri. Her satırın **kendi
   gerçek konumu** vardır (bir ILS'in LOC/GP/DME'si havaalanında üç ayrı
   noktadadır). Rota çözümlemesinde kullanılmaz.
4. **`routeSegments`** — start/end doğrudan `designatedPoints`/`navaids`
   satırlarına çözülür.

### `navaidComponents` düzleştirmesi

`NavaidComponent` kendi başına anlamı olmayan ince bir Object olduğu için, kendi
alanları ile bağlı olduğu `AbstractNavaidEquipment`'ın alanları **tek satırda**
birleştirilir:

- `NavaidComponent`'tan: `collocationGroup`, `markerPosition`,
  `providesNavigableLocation`, `annotation*`
- Ekipman ortak tabanından: `designator`, `name`, `emissionClass`, `mobile`,
  `magneticVariation`, `dateMagneticVariation`, `flightChecked`, `location`
  (bu katmanın geometrisi), `monitoring`, `availability`, `annotation*`
  (`authority` kapsam dışı — büyük Organisation/Authority feature'ı)
- `navaidComponents_equipmentType` — 11 somut alt-türden hangisi
  (`VOR`/`DME`/`TACAN`/`Localizer`/`Glidepath`/`MarkerBeacon`/`NDB`/`SDF`/
  `Azimuth`/`Elevation`/`DirectionFinder`)
- Alt-türe özgü alanlar, yalnızca eşleşen `equipmentType` için doldurulur
  (`frequency`, `channel`, `magneticBearing`, `slope`, `rdh` … — tam liste
  `docs/aixm-point-types/AIXM_NavaidEquipment_Attributes.md` §2.1-2.11)
- `navaidComponents_navaidId` — üst `navaids.id` satırına FK

`CodeDMEChannelType`/`CodeMLSChannelType` (352 ve 200 değerlik kapalı enum'lar)
elle kopyalanmaz; biçim `AIXM_NavaidEquipment_Attributes.md` §2.2.1/§2.9.1'e göre
doğrulanır.

### Alan adlandırma

- Her sütun `<katman>_<AIXM öznitelik adı, camelCase>` (örn. `navaids_type`)
- UOM: `<alan>Uom` (+ gerekiyorsa `<alan>Reference`)
- `annotation` → 4 sabit sütun: `annotationDescription/Remark/Warning/Disclaimer`
- Provenance sütunları katman önekli: `<katman>_data_provider`,
  `_data_originator`, `_data_effectivity`, `_add_date`
- `routeSegments` üzerindeki Route kökenli sütunlar `routeSegments_route<Attr>`
  biçiminde yazılır (`route_designatedPoints` gibi katman adlarıyla karışmasın)

### Tekrarlanan (0..∞) yapılar — kullanıcı onaylı

| AIXM alanı | Katman | Saklama |
|---|---|---|
| `designCriteria` | routeSegments | virgülle ayrılmış metin |
| `availability` | routeSegments, navaids, navaidComponents | TEXT içinde JSON dizisi (iç içe `levels[]` dahil) |
| `aircraftCapability` | routeSegments | TEXT içinde JSON dizisi (25 alt-alan + `radioNavigationEquipment[]`) |
| `airspaceClass` | routeSegments | TEXT içinde JSON dizisi (`associatedLevels[]` dahil) |
| `facilityMakeup` | routeSegments start/end | TEXT içinde JSON dizisi (`distanceReference[]`/`angleReference[]` dahil) |
| `fix` | designatedPoints | aynı PointReference yapısı, JSON dizisi |
| `navaidEquipment` | — | Ayrı `navaidComponents` katmanı + FK olarak modellenir |

### Referans çözümleme

Birleşik AIXM dosyasında her `xlink:href` zaten aynı dosya içindeki bir
`gml:identifier`'a işaret ettiği için (1. aşamada ve 2A'da doğrulanır), 2B'de
çözümleme **doğrudan sözlük araması**dır: `{uuid → (katman, satır id)}`.
`routeSegments_startPointLayer` + `routeSegments_startPointId` çiftleri buradan
doldurulur. Çözülemeyen referans `errored-features.csv`'ye yazılır.

### Validasyon

`gpkg/validation_rules.py`: katman başına `alan → FieldRule(type, max_length,
enum, allow_other, pattern)` — `docs/*.md` tablolarından bire bir aktarılır.
`allow_other`, AIXM'in evrensel `OTHER(:…)?` union desenini karşılar.

Severity politikası:
- Enum ihlali veya tip uyumsuzluğu → `error`, alan null'lanır, **kayıt yine yazılır**
- Serbest metin `max_length` aşımı → `warning`, değer kırpılır, tam değer logda
- Kaynağın hiç sağlamadığı alanlar → hiç loglanmaz

`errored-features.csv` sütunları: `layer, record_identifier, field, value,
violation, severity`.

---

## Teslimatlar (2. aşama)

1. **`AIXM_to_GeoPackage_Schema_Design.md`** — mimari (iki alt-aşama ve gerekçesi),
   katman başına tam sütun tablosu (4 katman, `navaidComponents`'ın alt-tür
   kırılımı dahil), sapmalar tablosu, referans çözümleme modeli, override ve
   antimeridyen bölme mekanizmaları, validasyon politikası. 1. aşama mapping
   dokümanlarına **bağlantı verir**, içeriklerini tekrarlamaz.
2. Çalışan `build_common_ats.py` + `merge/` + `gpkg/` modülleri ve `config.json`.

## Doğrulama (2. aşama)

1. `python build_common_ats.py` istisnasız tamamlanır; `common-ats-structure-aixm.xml`,
   `common-ats-structure-originators.json`, `common_ats_structure.gpkg`,
   `errored-features.csv` üretilir.
2. **Birleşik AIXM dosyası XSD'ye karşı 0 hata** (1. aşamadaki üreticilerle aynı
   çıta) ve dosya içi `xlink:href` bütünlüğü 0 kırık.
3. Feature sayısı tutarlılığı: birleşik dosya = ana kaynaklar + ek kaynaklar − iptal edilen
   − override ile değiştirilen + antimeridyen bölmesinden gelen fazladan
   feature'lar. Her bileşen ayrı ayrı raporlanır.
4. **Antimeridyen kontrolü** (seçenek açıkken): bölünen segment sayısı raporlanır;
   QGIS'te dünya haritasında hiçbir rota segmenti haritayı boydan boya kat etmez;
   üretilen `points` satırlarının annotation'ı tam olarak istenen metni taşır.
5. GeoPackage QGIS'te açılır: 4 katman yüklenir, nokta katmanları nokta,
   `routeSegments` çizgi olarak çizilir. Bilinen bir ILS: `navaids`'de tek
   `ILS`/`ILS_DME` satırı, `navaidComponents`'ta LOC/GP/(DME) ayrı ve kendi doğru
   konumlarında, `navaidComponents_navaidId` ile bağlı.
6. Uçtan uca örnek: bir EAD rotası (`UA14`) ve bir LT rotası (`UA 285` →
   `ERHAN`/`TIRMA`, `LEVEL=UPPER`, `lowerLimit=285 FL`, `upperLimit=660 FL`).
7. En az bir LT override'ının gerçekten tetiklendiği (veya hiç tetiklenmediyse
   bunun beklenen olduğu) doğrulanır — mekanizmanın sessizce ölü olmadığı
   gösterilir.
8. `errored-features.csv` incelenir: `unresolved_xlink_href` sıfıra yakın olmalı.

## Açık konular

1. **Koordinatla verilmiş segment ucu** — hiçbir kaynakta yok (tarandı: 0), bu
   yüzden desteklenmiyor. Böyle bir kaynak gelirse mevcut kod ne geometri ne uç
   kimliği üretir. Veri gelmeden uygulanması önerilmedi.

### Kapanan konular

- **LT'nin 2 stub `Navaid` kaydı** (`MEN`, `AYR`) — tipsiz navaid'ler için
  gevşek eşleşme eklendi (`designator + originator`). `MEN`'de EAD'de iki aday
  bulundu (`VOR_DME` "IZMIR", `TACAN` "ADNAN MENDERES"); kullanıcı kararı **stub
  kalsın**, belirsizlik loglanır. `AYR`'nin EAD'de hiç karşılığı yok; kullanıcı
  kararı **NULL geometriyle katmanda kalsın**.
- **`points` katmanı** — `aixm:Point` Feature olmadığı için katman iptal edildi;
  antimeridyen kesişim noktaları `DesignatedPoint` (`type=OTHER`) olarak
  üretiliyor.

- **Antimeridyen kesişim hesabı** — WGS84 elipsoidi üzerinde geodesic, `pyproj`
  bağımlılığıyla (kullanıcı kararı).
- **Uç nokta ayıklaması** — coğrafi yakınlık + 1000 NM eşiği; 1. aşamada
  uygulandı ve doğrulandı (yukarıdaki "Giderilen sorun").
