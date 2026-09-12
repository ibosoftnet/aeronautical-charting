# Common Builder — Davranış Dokümanı

Bu doküman `build_common_ats.py`'nin **ne yaptığını** anlatır: aşamalar, kaynak
sırası, çakışma çözümü, üretilen dosyalar ve doğrulama politikası.

- Katman/sütun listeleri ve AIXM → GeoPackage eşlemesi:
  [`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md)
- Kaynak başına ham veri → AIXM eşlemesi: her kaynağın kendi mapping dokümanı
  (`data-sources/*/generate-aixm-data/*_Mapping.md`)
- Projenin bütün planı:
  [`Common_ATS_Structure_Implementation_Plan.md`](Common_ATS_Structure_Implementation_Plan.md)

---

## 1. Bağlayıcı kural

> **Hiçbir AIXM özniteliği sessizce atlanamaz.** Her öznitelik ya bir sütuna
> eşlenir, ya "kaynakta yok" olarak (ham veriye bakılarak doğrulanmış şekilde)
> işaretlenir. Bir şeyi "kapsam dışı" ilan etmek tek başına verilecek bir karar
> değildir — bulgusu ve gerekçesiyle kullanıcıya getirilip onaylanır.
>
> **Uydurma eşleme/açıklama yok.** Her iddia gerçekten okunmuş bir şeye (XSD,
> ham XML, üretilen AIXM) dayanır. Bilinmeyen/belirsiz her şey sorulur.

Bu kural yalnızca planlama için değil, uygulamanın tamamı için geçerlidir.

---

## 2. Genel akış

```
                     ┌──────────────── AŞAMA 1 (seçenek) ────────────────┐
ham veri ────────────▶ kaynak üreticileri, config'deki SIRAYLA           │
(sqlite, EAD XML,    │   1 jeppesen   2 ead_sdo   3 lt                  │
 LT raw, …)          │   4 trnc  5 tailored-lb  (elle yazılır)          │
                     │   6 ibosoft  7 tailored  (henüz yok)             │
                     └───────────────────────┬──────────────────────────┘
                                             ▼
                       kaynak başına kendi başına geçerli AIXM 5.2 dosyası
                       ead-sdo-aixm.xml · jeppesen-ndb-aixm.xml · lt-…-aixm.xml
                                             │
                     ┌───────────────────────▼──────────────────────────┐
                     │ AŞAMA 2A — BİRLEŞTİRME                           │
                     │  ana kaynaklar → marker beacon → iptal →         │
                     │  ek kaynaklar (çakışma çözümü) → antimeridyen    │
                     └───────────────────────┬──────────────────────────┘
                                             ▼
                       common-ats-structure-aixm.xml        (geçerli AIXM 5.2)
                       common-ats-structure-provenance.json (gml:id → 3 alan)
                                             │
                     ┌───────────────────────▼──────────────────────────┐
                     │ AŞAMA 2B — GEOPACKAGE                            │
                     │  saf şema eşlemesi + validasyon + index          │
                     └───────────────────────┬──────────────────────────┘
                                             ▼
                       common_ats_structure.gpkg
                       errored-features.csv
```

**Neden 2A ve 2B ayrı:** 2A çıktısı XSD ile bağımsız doğrulanabilen bir AIXM
dosyasıdır — birleştirme, çakışma çözümü ve bölme mantığı GeoPackage'a hiç
bakmadan sınanır. 2B ise kaynak bilgisi, çakışma kuralı veya geometri hesabı
içermeyen saf bir şema eşlemesine iner: hiçbir `data.json` okumaz, provenance'ı
yan dosyadan `gml:id` ile alır.

### Kullanım

```bash
py build_common_ats.py            # (1. aşama config'de açıksa onu da) 2A + 2B
```

```bash
py build_common_ats.py --sources  # yalnızca 1. aşama
```

```bash
py build_common_ats.py --merge    # yalnızca 2A
```

```bash
py build_common_ats.py --gpkg     # yalnızca 2B (diskteki birleşik dosyadan)
```

`--sources`, config'deki `run_source_generators` kapalı olsa bile 1. aşamayı
çalıştırır — ayarı elle geçersiz kılmanın yolu budur.

---

## 3. AŞAMA 1 — Kaynak üreticileri

`run_source_generators: true` ise birleştirmeye geçmeden önce her kaynağın
üreticisi çalıştırılır ve AIXM dosyaları tazelenir. Kapalıysa diskte hazır duran
dosyalar kullanılır (varsayılan: kapalı — EAD üreticisi uzun sürer).

```jsonc
"run_source_generators": false,
"source_generators": [
  { "name": "jeppesen", "script": "data-sources/Jeppesen/generate-aixm-data/generate_aixm.py", "enabled": true },
  { "name": "ead_sdo",  "script": "data-sources/EAD-SDO/generate-aixm-data/generate_aixm.py",  "enabled": true },
  { "name": "lt",       "script": "data-sources/LT/generate-aixm-data/generate_aixm.py",       "enabled": true },
  { "name": "trnc",        "script": null, "enabled": false, "_durum": "elle duzenleniyor" },
  { "name": "tailored-lb", "script": null, "enabled": false, "_durum": "elle duzenleniyor" },
  { "name": "ibosoft",  "script": null, "enabled": false, "_durum": "henüz yok" },
  { "name": "tailored", "script": null, "enabled": false, "_durum": "henüz yok" }
]
```

**Sıra config'den gelir ve önemlidir.** Jeppesen, EAD'den önce gelmelidir: EAD
üreticisi NDB uç noktaları için Jeppesen'in çıktısındaki indekse
(`jeppesen-ndb-index.json`) bakar ve kendi AIXM'inde NDB feature'ı üretmez,
doğrudan Jeppesen feature'larına `xlink` verir (2.901 çapraz referans).

`script: null` olan kaynaklar henüz yoktur; listedeki yerleri sıra korunsun diye
duruyor, çalıştırma sırasında "henüz yok" diye raporlanır ve atlanır.

**Hata davranışı:** bir üretici sıfırdan farklı bir kodla çıkarsa zincir
**durdurulur** ve birleştirmeye geçilmez. Yarım bir kaynak dosyasıyla
birleştirmek sessiz veri kaybı demektir.

### Kaynak dosyaların ortak özellikleri

Her üretici, kendi başına XSD'ye karşı **0 hata** ile doğrulanan bir AIXM 5.2
`message:AIXMBasicMessage` üretir. İkinci satır her dosyada aynı imzayı taşır:

```xml
<!-- Generated by Ibosoft AIS - ais.ibosoft.net.tr -->
```

`gml:id` değerleri kaynak önekiyle başlar — `EAD_`, `JEPP_`, `LT_` — böylece
birleşik dosyada karışma imkânsızdır. UUID'ler sabit namespace'li
(`6f1c3b52-9d4a-5e77-b8c1-2a0e94f7d310`) deterministik UUID5'tir: aynı girdi
her koşuda aynı kimlikleri üretir.

> **Bir kaynak dosyası, çekirdek AIXM'de karşılığı olmayan alan taşıyabilir.**
> LT'nin `ChangeOverPoint`'leri, AIXM'in resmi genişletme mekanizmasıyla
> (`aixm:extension` → `aixm:AbstractExtension` ikame grubu) `ibosoftais`
> önekli bir alan taşır. Böyle bir dosya **yalnızca** stok AIXM setiyle
> doğrulanırsa "geçersiz" görünür; doğrulayıcı `schemas/ibosoftais-extension.xsd`
> dosyasını da derlemeye katar. Birleştirme tarafında özel bir iş yoktur:
> namespace bildirimi parça kopyalanırken korunur.

---

## 4. AŞAMA 2A — Birleştirme

### 4.1 Ana kaynak / ek kaynak ayrımı

| Rol | Kaynak | Anlamı |
|---|---|---|
| **Ana kaynak** (`base_sources`) | `ead_sdo`, `jeppesen` | Birleşik veri setinin gövdesi |
| **Ek kaynak** (`additional_sources`) | `lt`, `trnc`, `tailored-lb` | Üzerine eklenir, çakışmada kurallara göre çözülür |

`tailored-lb` bunların en sadesi: **hiçbir çakışma ayarı taşımaz**
(`override_enabled` vb. yok). Bulgaristan AIP'sindeki BAKLO→EFCOM
değişikliğini EAD-SDO almadığı için elle yazılmış bir düzeltme kaynağıdır;
eklediği 8 feature'ın hiçbirinin birleşik veride karşılığı yoktur, dolayısıyla
doğal anahtar eşleşmesi hiç oluşmaz. Eskimiş EAD kayıtları ayrı bir **iptal
dosyasıyla** çıkarılır (§4.7). Ayrıntı: `data-sources/tailored-LB/README.md`.

Jeppesen'in ana kaynak olması teknik zorunluluktur: EAD segmentleri Jeppesen
NDB feature'larına `xlink` verir; Jeppesen isteğe bağlı olsaydı o referanslar
kırık kalırdı.

Ana kaynaklar arasında çakışma çözümü uygulanmaz — çakışmıyorlar (`gml:id` ve
UUID düzeyinde sıfır çakışma, ölçüldü).

### 4.2 İşlem sırası

1. Kaynak indeksleri kurulur (`uuid → designator/type/kind`) — doğal anahtar
   karşılaştırması için gerekir.
2. Ek kaynakların doğal anahtarları çıkarılır.
3. **Marker beacon modülü** kurulur (config'de açıksa) — §4.6.
4. **İptal (exclude)** kuralları yüklenir.
5. **Ön tarama**: hangi kaydın hangi yöne devredileceği ve `remap` tablosu
   belirlenir; marker'ların hedef LOC/ILS'leri de burada toplanıp eşleştirilir.
6. Ana kaynaklar yazılır (iptal + çakışma süzgeciyle; eşleşen marker'ların
   bileşenleri hedef Navaid'e enjekte edilir).
7. Eşleşen marker'ların `MarkerBeacon` ekipman feature'ları yazılır.
8. Ek kaynaklar yazılır.
9. Antimeridyen bölme uygulanır (seçenek açıksa).

Okuma sırası config'deki yapıyı izler:
`ead_sdo` → `jeppesen` → **`jeppesen-mkr`** → `excludes`.

Yazım **akış modundadır**: 470 MB'lik kaynak dosyası belleğe alınmaz. Geçen
feature'lar **birebir kopyalanır** — yeniden serileştirilip öznitelik sırası /
biçim hatası riskine girilmez. Bu kuralın tanımlı **iki istisnası** var:

  * **antimeridyen bölme** — yeni `DesignatedPoint` ve iki yeni `RouteSegment`
    üretir (§4.8),
  * **marker beacon enjeksiyonu** — var olan bir LOC/ILS Navaid'ine
    `navaidEquipment` ekler (§4.6).

İkisi de XSD eleman sırasına uyar; doğrulama bunu yakalar.

### 4.3 Çakışma çözümü — iki yön, katmana göre

Kaynakların UUID uzayları bağımsız olduğu için eşleştirme **doğal anahtarla**
yapılır, UUID eşitliğiyle değil:

| Feature | Eşleşme anahtarı |
|---|---|
| `DesignatedPoint` | designator + originator |
| `Navaid` | type + designator + originator |
| `RouteSegment` | rota kimliği + start/end designator + originator |
| `ChangeOverPoint` | rota kimliği + **sırasız** uç çifti + originator |
| `Route` | — (doğal anahtar tanımlı değil, eşleştirmeye girmez) |

> **`ChangeOverPoint`'in uç çifti neden sırasız?** İki VOR arasındaki geçiş
> noktası fizikî olarak **tektir**; bir kaynak onu `BUK→SIV`, diğeri `SIV→BUK`
> yönünde yazmış olabilir (mesafeler de buna göre yer değiştirir). Uçlar
> sıralanarak anahtara girdiği için bu iki kayıt **aynı** COP olarak eşleşir.
> `RouteSegment`'te sıra korunur, çünkü orada yön kaydın kendi anlamının
> parçasıdır. COP'un referansları gömülü `RoutePortion` nesnesinin içindedir
> (bkz. [`docs/AIXM_ChangeOverPoint_Attributes.md`](docs/AIXM_ChangeOverPoint_Attributes.md) §0).

Bir ek kaynak için **iki yön aynı anda** geçerli olabilir ve **katmana göre**
ayrışır:

| Ayar | Yön | Sonuç |
|---|---|---|
| `override_enabled: true` | **ek kaynak kazanır** | Ana kaynak kaydı yazılmaz; ona referans veren her şey ek kaynağın UUID'sine yönlendirilir |
| `prefer_base_on_match: true` + `prefer_base_on_match_layers` | **önceki kayıt kazanır** | Ek kaynağın kaydı yazılmaz; ona referans veren her şey önceki kaydın UUID'sine yönlendirilir |

`prefer_base_on_match` **asla kaynağın tamamına uygulanmaz** — yalnızca
`prefer_base_on_match_layers` listesindeki katmanlarda geçerlidir. O katmanlar
override'a hiç girmez; kaynağın diğer bütün katmanlarında `override_enabled`
yönü işler.

> **Karşılaştırma tablosu ana kaynakla sınırlı değildir.** Ek kaynaklar
> config'deki **sırayla** işlenir ve her kaynağın yazılacak kayıtları tabloya
> eklenir. Böylece sonraki bir ek kaynak, kendisinden **önce okunmuş bir ek
> kaynağa da** devredebilir. Ayarın adı tarihsel sebeple `prefer_base…` olarak
> kaldı; anlamı "o ana kadar yazılmaya karar verilmiş kayıt kazanır"dır.

### Kaynak başına ayarlar

```jsonc
{ "name": "lt",
  "override_enabled": true,
  "prefer_base_on_match": true,
  "prefer_base_on_match_layers": ["navaids", "navaidComponents"],
  "override_base_originator": "DHMI TURKIYE" }

{ "name": "trnc",
  "override_enabled": true,
  "prefer_base_on_match": true,
  "prefer_base_on_match_layers": ["navaids", "navaidComponents", "designatedPoints"],
  "override_base_originator": "CYPRUS DEPARTMENT OF CIVIL AVIATION",
  "prefer_base_originator": "DHMI TURKIYE" }
```

**İki yön farklı sağlayıcı hedefleyebilir.** `override_base_originator` override
yönünde, `prefer_base_originator` devretme yönünde aranan originator dizesidir.
İkincisi verilmezse birincisine düşer (LT'deki durum).

- **LT**: tek originator (`DHMI TURKIYE`). DesignatedPoint ve RouteSegment'te LT
  kazanır; navaid tarafında ana kaynak (EAD) kazanır.
- **TRNC**: iki yön farklı sağlayıcıya bakar ve **ikisi de çalışır**. Önce
  devretme denenir (`DHMI TURKIYE` → LT); tutmazsa override uygulanır
  (`CYPRUS DEPARTMENT OF CIVIL AVIATION` → EAD'nin Kıbrıs kayıtları).

```
1) ana kaynak (EAD/Jeppesen) kaydı oluşur
2) LT kendi noktalarını override eder                    → LT kazanır
3) TRNC okunur:
   a) nokta LT'de de varsa  → TRNC kaydı yazılmaz, LT kazanır
   b) yoksa ve EAD'de Cyprus DCA olarak varsa
                            → EAD kaydı düşer, TRNC kazanır
   c) ikisi de değilse      → TRNC kaydı normal yazılır
```

**Dolaylı yönlendirme (zincir çözümü).** (a) ile (b) aynı kayıtta birlikte
oluşabilir: nokta hem LT'de hem EAD-Cyprus DCA'da varsa TRNC kaydı LT'ye
devreder *ve* EAD kaydını override eder. Tek adımlık arama EAD'yi yazılmayan
TRNC kaydına gönderirdi; bu yüzden `remap` tablosu yazımdan önce sonuna kadar
izlenir (EAD → TRNC → LT ⇒ EAD → LT). Döngüye karşı ziyaret kümesiyle korunur.

**Ölçülen sonuç** (TRNC: 80 feature, originator `KKTC SHD`):

| Nokta | Durum | Sonuç |
|---|---|---|
| `DOREN`, `TOMBI`, `VESAR` | LT'de **ve** EAD-Cyprus DCA'da | Tek kayıt: **LT**. TRNC devretti, EAD override ile düştü ve zincirle LT'ye yönlendi |
| `ALSUS`, `BALMA`, `DASNI`, `EVENO`, `NIKAS`, `VADUS` | yalnızca EAD-Cyprus DCA'da | Tek kayıt: **TRNC**. EAD kaydı override edildi |
| `BARIS`, `MEDIT`, `MURAT` | yalnızca EUROCONTROL NMOC'ta | **İki ayrı kayıt** — aynı kodu taşıyan farklı noktalar (2.004 / 4.409 / 4.481 NM uzakta), ayrılmaları doğru |

Son koşuda: TRNC 77 feature yazıldı, 3'ü devredildi, 9 EAD kaydını override etti,
3 dolaylı yönlendirme çözüldü. Bağlanmamış bileşen 0.

> Anahtardaki **originator bileşeni şarttır**: yalnızca designator'a bakan bir
> eşleştirme TRNC'nin `MEDIT`'ini 4.409 NM ötedeki EUROCONTROL noktasıyla
> birleştirirdi.

### 4.4 Yakınlık eşleştirmesi (originator yoksa)

Originator anahtarı her zaman kullanılamaz: **Jeppesen kayıtlarında originator
alanı hiç yoktur** (`data.json`'ında yok — doğrulanmış yokluk) ve EAD'de aynı
tesis kaynağa göre farklı originator yazımıyla geçebilir. Bu durumlar için
hedef kaynak **adıyla** belirtilir, aday ise **mesafeyle** ayıklanır:

```jsonc
// LT — bu kaynakların kaydı kazanır, LT'ninki düşer
"match_by_proximity_nm": 1.0,
"prefer_base_sources": ["jeppesen", "ead_sdo"]

// TRNC — bu kaynağın kaydı düşer, TRNC'ninki kazanır
"match_by_proximity_nm": 1.0,
"override_sources": ["jeppesen"]
```

Kaynak adı tek başına yetmez: aynı designator birden çok bölgede geçiyor
(`LU` Jeppesen'de **5 kez**, `ORI` 2 kez). Bu yüzden aday, aynı
`type + designator`'ı taşıyan yazılmış kayıtlar arasından `pyproj` geodesic
mesafesiyle süzülür. **Eşik içinde birden fazla aday varsa seçim yapılmaz** —
kayıt korunur, `yakinlik_esiginde_birden_fazla_aday` olarak loglanır.

Eşiğin 1 NM seçilmesi ölçüme dayanır: gerçek mükerrerler 0,000–0,007 NM, en
yakın yanlış aday 918,9 NM (`KAM`, Yunanistan). Aradaki marj ~130.000 kat.

| designator | eski | yeni |
|---|---|---|
| `CTP`, `GZP`, `HAY` | LT + Jeppesen | tek kayıt: Jeppesen |
| `LU` | LT + 5 Jeppesen | 5 Jeppesen (LT devretti; uzak 4'ü korundu) |
| `ORI` | LT + 2 Jeppesen | 2 Jeppesen (İtalya'daki 1.310 NM ayrı kaldı) |
| `LSV` | LT + EAD | tek kayıt: EAD |
| `GKE` | TRNC + Jeppesen | tek kayıt: **TRNC** (Jeppesen düştü) |

**Düşen Navaid'in ekipmanı da düşer** — ama yalnızca o ekipmanı kullanan bütün
Navaid'ler düşmüşse. EAD'de bir ekipman birden fazla Navaid tarafından
paylaşılabiliyor; hâlâ kullanılan bir ekipmanı düşürmek kırık referans
üretirdi. (`GKE`'de Jeppesen Navaid'i düşünce 1:1 bağlı NDB ekipmanı boşta
kalıyordu; bağlanmamış bileşen 1 → 0.)

**Neden navaid tarafında ters yön:** LT'de navaid ekipman ayrıntısı yok. LT bir
`Navaid`'i override ettiğinde EAD'nin o navaid'e bağlı fiziksel VOR/DME/TACAN
bileşenleri boşta kalıyordu (ölçüldü: 116 bağlanmamış bileşen — ADA, ARI, AYT).
Ters yönde ise EAD'nin zengin kaydı bileşenleriyle birlikte korunur ve LT'nin o
navaid'e verdiği referanslar EAD'nin UUID'sine çevrilir. Sonuç: bağlanmamış
bileşen = 0.

**Bunun bedeli:** eşleşen kayıtta kazanan kaynağın kaydı bir **bütün olarak**
geçerlidir; alan bazında birleştirme yapılmaz. Kaybeden kaynakta dolu olup
kazananda boş olan bir alan varsa o değer birleşik veriye girmez.

`override_base_originator` her ek kaynak için ayrı ayarlanır, koda gömülmez:
kaynağın kendi originator yazımı ile ana kaynaktaki karşılığı farklı olabilir.
LT'de doğrulandı — kendi `data.json`'ı `"DHMİ Türkiye"` derken EAD tarafındaki
karşılığı `"DHMI TURKIYE"` yazımıyla geçiyor.

### 4.5 Referans yönlendirmesi (`remap`)

Bir kayıt düşünce ona referans veren **başka** feature'lar boşta kalır. Bu
yüzden yazımdan önce bir ön tarama yapılır ve `remap` tablosu kurulur
(`düşen UUID → yerine geçen UUID`); yazım sırasında her `xlink:href` bu tabloya
göre çevrilir.

**Yönlendirme derinlikten bağımsızdır.** Çevrim, yazılan `hasMember`
parçasının **bütün** alt elemanlarını gezer (`member.iter()`) ve `urn:uuid:`
ile başlayan her `xlink:href`'i tablodan geçirir — eleman adına göre bir beyaz
liste **yoktur**. Bu, referansları doğrudan TimeSlice altında durmayan
feature'lar için belirleyicidir: `ChangeOverPoint`'in üç referansı gömülü bir
`RoutePortion` **nesnesinin** içindedir ve hiçbir ek kod olmadan yönlendirilir.

> **`remap` girdisi ÜRETMEYEN tek düşme yolu iptal (exclude) kuralıdır**
> (§4.7). Override, devretme ve yakınlık yollarının üçü de girdi üretir.
> İptal edilen kaydın UUID'si dosyadan yok olur ve ona giden referans boşta
> kalır — bu yüzden COP referansları yazımdan sonra ayrıca denetlenir (§4.10).

### 4.6 Marker beacon eşleştirmesi (`special_sources`)

Normal base/additional kaynaklardan farklı, **bu işe özgü** bir adım. Config'de
`special_sources` altında tanımlanır ve yalnızca `marker_beacon_matching: true`
olduğunda çalışır:

```jsonc
"special_sources": [
  { "name": "jeppesen-mkr",
    "enabled": true,
    "marker_beacon_matching": true,
    "file": "data-sources/Jeppesen/jeppesen-marker.json",
    "data_json": "data-sources/Jeppesen/data.json",
    "match_by_proximity_nm": 25.0,
    "target_navaid_types": ["ILS", "ILS_DME", "LOC", "LOC_DME"] }
]
```

**Neden ayrı bir modül.** Bir marker beacon tek başına anlamlı değildir;
ilişkili olduğu LOC/ILS navaid'inin `navaidComponent`'i olarak yer almalıdır.
Hangi LOC/ILS'e bağlanacağı ancak **birleşik** veride bilinebilir — marker
Jeppesen'den, hedef navaid EAD-SDO'dan gelir. Bu yüzden Jeppesen üreticisi
marker'ı kendi AIXM dosyasına yazmaz, yalnızca kimlikleriyle birlikte
`jeppesen-marker.json` yan dosyasına döker; eşleştirme ve AIXM üretimi
`merge/marker_beacon.py`'de yapılır.

**Eşleştirme: designator + yakınlık.** "Ülke kodu" kullanılamıyor — birleşik
verideki 550 LOC/ILS'in **548'inde `codeICAOCountry` boş** (EAD bu alanı hiç
doldurmuyor). Yakınlık bu boşluğu kapatıyor ve ölçümle doğrulandı: eşleşen
mesafeler **1,41–6,89 NM** (medyan 2,62) — outer/middle marker için tam
beklenen aralık; eşik içinde **birden fazla aday olan hiç yok**; aynı ident'i
taşıyıp uzakta olan **88 yanlış aday** doğru şekilde eleniyor.

**Eşleşemeyen marker yazılmaz** (kullanıcı kararı), `errored-features.csv`'ye
`marker_ebeveyn_loc_ils_bulunamadi` olarak loglanır. Ayrı `MKR` navaid
üretilmez: veride tek bir enroute marker (FAN/Z) yok, 913'ün tamamı ILS
yaklaşma marker'ı — "enroute" demek uydurma sınıflandırma olurdu.

**Ölçülen sonuç:** 913 marker → **77 eşleşti**, 836 eşleşemedi, belirsiz **0**.
Düşük oranın nedeni coğrafi kapsam: EAD-SDO'nun ILS raporunda ABD hiç yok
(FAA kaynaklı LOC/ILS = 0), Jeppesen marker verisi ise ağırlıklı ABD
(eşleşemeyenlerin 380'i K3–K7 bölgeleri). **Türkiye'nin 7 marker'ının 7'si de
eşleşiyor.** Eşik kısıt değil — 15/25/40 NM hepsi 77 veriyor.

**XSD sırası korunur.** `navaidEquipment`, `NavaidPropertyGroup` içinde
`location`'dan **önce** gelmelidir; modül yeni bileşeni, kendisinden sonra
gelmesi gereken ilk elemanın önüne yerleştirir. Enjeksiyon var olan bir
feature'ı değiştirdiği için bu, akış yazıcısının "birebir kopyala" kuralına
tanımlı tek istisnadır.

**`gml:validTime` boştur.** Jeppesen kayıtlarında feature başına yürürlük
tarihi yok; `data.json`'daki AIRAC effectivity **veri setinin** geçerliliğidir,
feature'ın kendi yürürlüğü değil. Bu yüzden `beginPosition` ve `endPosition`
`indeterminatePosition="unknown"` ile yazılır (NDB feature'ları da aynı
şekilde — kullanıcı kararı).

Alan eşlemeleri: `data-sources/Jeppesen/generate-aixm-data/Jeppesen_to_AIXM_Mapping.md` §6.

### 4.7 İptal (exclude)

`data-sources/excludes/*.json` içindeki kurallara uyan kayıtlar birleşik veriden
çıkarılır. Kural biçimi jeneriktir, yalnızca rota segmentine özel değildir:

```jsonc
{ "layer": "designatedPoints", "match": { "designator": "XXXXX" } }
```

Her isabet `errored-features.csv`'ye `iptal_kuraliyla_cikarildi` olarak yazılır —
sessiz düşürme yoktur.

Dört dosya var, toplam **16 kural / 32 isabet**:

| Dosya | Kural | İsabet | Neden |
|---|---|---:|---|
| `trnc-cyprus-overlap.json` | 5 | 5 | Kıbrıs DCA kayıtlarının TRNC ile örtüşen segmentleri |
| `bulatsa-baklo-efcom.json` | 4 | 4 | Bulgaristan AIP'sinde (ENR 3.3, AIRAC 2606) kaldırılan `BAKLO` ve ona bağlı üç segment; yerlerine geçenler `tailored-lb` kaynağından gelir (§4.1) |
| `bulatsa-p727-iblax-rezov.json` | 4 | 4 | Aynı AIP'de kaldırılan `IBLAX`; P727 zinciri `FENER → REZOV → UVUDA` oldu |
| `lt-kular.json` | 3 | 19 | `KULAR` (DHMİ) ve ona bağlı **18** segment |

> **Kural sayısı ≠ isabet sayısı.** `matches()` **kısmi** eşleşme yapar —
> yalnızca `match` içinde yazılı alanlar karşılaştırılır
> (`merge/exclude.py:71`). `lt-kular.json` bunu kullanır: tek bir
> `{"start": "KULAR", "originator": "DHMI TURKIYE"}` kuralı 8 segmenti,
> `end` karşılığı 10 segmenti yakalar. Rota rota yazmak gerekmez, ama kuralın
> ne kadarını süpürdüğü **önceden ölçülmelidir**.

> **Bilinen boşluk — iptal, `remap` girdisi üretmez.** Override/devretme/yakınlık
> yolları düşen kaydın UUID'sini kazanana bağlar; iptal kuralı bağlamaz, kaydın
> UUID'si dosyadan yok olur. Referans **verilen** bir katmanı hedefleyen kural,
> geride kırık `xlink` bırakabilir.
>
> Üç `designatedPoints` kuralı bu boşluğu **fiilen sınadı**. Her biri için
> kural yazılmadan önce referans sayımı yapıldı:
>
> | Nokta | Referans veren | Aynı kural kümesiyle iptal edilen |
> |---|---:|---:|
> | `BAKLO` | 3 | 3 |
> | `IBLAX` | 3 | 3 |
> | `KULAR` | **18** | **18** |
>
> Üçünde de referans veren her şey aynı anda düştüğü için geride boşluk
> kalmadı. Koşu sonrası bağımsız tarama bunu doğruladı: birleşik dosyadaki
> 277.694 `xlink`'in hedefi de mevcut, kırık **0**.
>
> **Referanslanabilir bir katmanda (`designatedPoints`, `navaids`, `routes`,
> navaid ekipmanı) iptal kuralı yazan herkes aynı sayımı önce yapmalıdır.**
> Üreteç bu kontrolü kendiliğinden yapmaz; yalnızca COP referansları §4.10'daki
> denetimle otomatik görünür olur.

> **Yan etki — segmentsiz kalan Route'lar.** Bir noktayı çıkarmak, ona bağlı
> tüm segmentleri de çıkardığı için bazı Route feature'ları segmentsiz kalır:
> `KULAR` iptali 6 rotayı (`L854`, `T39`, `T44`, `UL854`, `UT39`, `UT44`)
> tamamen boşalttı, `IBLAX` iptali `EAD_RTE_UP727_EUR`'u. Bu bir hata değil —
> veride bu iptallerden **önce de** 312 segmentsiz Route vardı (EAD'de yaygın
> bir durum) ve Route'un kendisi geçerli bir feature olarak kalır. Ama
> `N131`, `T54`, `UN131`, `UT54` gibi kısmen boşalan rotalarda zincir
> **ortadan kopar**; bu, iptali isteyenin bilerek kabul ettiği sonuçtur.

### 4.8 Antimeridyen bölme (`split_antimeridian`)

Antimeridyeni (±180°) aşan her `RouteSegment` kesişim noktasından **iki ayrı
segmente** bölünür; yoksa web haritalarında segment dünyayı boydan boya kat eder
gibi çizilir.

**2A'da (AIXM düzeyinde) yapılır**, 2B'de değil: bölme yeni feature'lar üretir ve
bunların gerçek `gml:identifier`'ları ile `xlink` referansları olmalıdır ki
birleşik dosya kendi içinde tutarlı ve XSD-geçerli kalsın.

- **Tespit:** iki uç arasındaki boylam farkının mutlak değeri > 180°.
- **Kesişim enlemi:** WGS84 elipsoidi üzerinde geodesic —
  `pyproj.Geod(ellps="WGS84")` ile azimut/mesafe, ardından mesafe boyunca ikili
  arama (bisection) ile boylamın tam ±180° olduğu nokta (tolerans ~1e-9°).
- **Üretilenler:**
  - Kesişimde bir **`DesignatedPoint`** (`type = OTHER`), konumu (kesişim
    enlemi, ±180). Diğer öznitelikleri boştur; `annotation` notu tam olarak:
    `Automatically generated by the AIS system to display antimeridian crossings on web maps.`
  - Orijinalin yerine **iki `RouteSegment`**: A = orijinal start → yeni nokta,
    B = yeni nokta → orijinal end. İkisi de orijinalin diğer tüm özniteliklerini
    (level, dikey limitler, `routeFormed`, `validTime`, originator …) aynen
    devralır. A kesişimde +180 veya −180 ile biter, B karşı işaretle başlar —
    her çizgi kendi yarısında kalır. İkisinin de ek `annotation` notu tam olarak:
    `Route segment automatically split by the AIS system at the antimeridian for display on web maps.`
    Orijinal segmentin kendi annotation'ı **korunur** (AIXM'de 0..∞); GeoPackage
    tarafında aynı feature içindeki aynı `purpose`'lu notlar `" | "` ile,
    farklı feature'lardan gelenler (segment + bağlı `Route`) araya bir **boş
    satır** konarak birleştirilir.
- Yeni `gml:id`/`gml:identifier` değerleri orijinalinkinden deterministik
  türetilir (`…_AM_A`, `…_AM_B`, `…_AM_PT`) ve kaynak önekini korur.

Mevcut veride **53 segment** bölünüyor (geometrili segmentlerin %0,06'sı; LT'de
0). Hepsi gerçek geçiş: Bering Boğazı, Aleutlar, Pasifik ekvatoru, bir kutup
rotası; 40–587 NM.

`aixm:Point` bir Feature değil (`gml:Point` ikame grubunda) — `hasMember`
olamaz. Bu yüzden kesişim noktası `Point` değil `DesignatedPoint` olarak
üretilir.

### 4.9 Provenance yan dosyası

AIXM'de provenance alanı **yoktur**; birleşik dosyada her feature farklı bir
kaynaktan geldiği için tek bir `data.json` da yeterli değildir. 2A bu yüzden
`gml:id` anahtarlı bir yan dosya üretir ve **üç alanı birden** taşır:

```jsonc
{
  "EAD_RS_001610": { "data_provider": "EUROCONTROL EAD SDO",
                     "data_originator": "HELLENIC AVIATION SERVICE PROVIDER (HASP)",
                     "data_effectivity": "06 AUG 2026 (AIRAC 2608)" },
  "LT_DP_ABDIK":   { "data_provider": "Ibosoft AIS",
                     "data_originator": "DHMİ Türkiye",
                     "data_effectivity": "06 AUG 2026 (AIRAC 2608)" }
}
```

- `data_provider`, `data_effectivity` → kaynağın `data_json`'ından (kaynak
  başına sabit)
- `data_originator` → kaynağın `originators_file`'ı varsa `gml:id` ile oradan
  (EAD-SDO: her feature farklı olabilir), yoksa `data_json`'daki sabit değerden

Antimeridyen bölmesiyle üretilen feature'lar, türetildikleri orijinal segmentin
provenance kaydını aynen devralır.

### 4.10 ChangeOverPoint

COP (`aixm:ChangeOverPoint`) şu an yalnızca **LT** kaynağından gelir (ölçüldü:
EAD-SDO 0, Jeppesen 0, TRNC 0). Buna rağmen diğer katmanlarla **aynı** çakışma
makinesine bağlıdır; `changeOverPoints` bir katman adıdır, dolayısıyla davranış
config'den ayarlanır:

| Durum | Bugünkü sonuç | Nasıl değiştirilir |
|---|---|---|
| Ek kaynak ile base kaynak aynı COP'u yayımlarsa | **Ek kaynak kazanır** (`override_enabled: true`, `changeOverPoints` prefer-base listesinde değil) | LT'nin `prefer_base_on_match_layers` listesine `"changeOverPoints"` eklenirse base kazanır |
| İptal kuralı | Kural `"layer": "changeOverPoints"` ile yazılabilir | — |

> `changeOverPoints`'in GeoPackage karşılığı **yoktur** (Aşama 2B henüz
> planlanmadı). Bu bir tutarsızlık değil: `routes` da aynı durumda — katman adı
> çakışma çözümünün dilidir, GeoPackage şemasına verilmiş bir söz değildir.

**Referans denetimi.** COP, referansları doğrudan TimeSlice altında değil gömülü
bir `RoutePortion` **nesnesinin** içinde duran ilk feature'dır; doğruluğu
tamamen yönlendirmenin derinlikten bağımsız olmasına dayanır (§4.5). Bu örtük
sözleşmeyi ölçülebilir kılmak için yazım bittiğinde her COP'un üç referansı
(`start_*`, `referencedRoute`, `end_*`) birleşik dosyaya gerçekten yazılmış
UUID'lerle uzlaştırılır:

- Çözülemeyen referans → `cop_referansi_birlesik_dosyada_yok` (severity `error`)
- **COP yine yazılır** — kayıt düşürülmez, boşluk görünür kılınır (§1'deki
  bağlayıcı kural ve §5.1'deki çözülemeyen uç nokta emsaliyle aynı çizgi)
- Sayaçlar: `cop_referansi_denetlendi`, `cop_referansi_kirik`

Ayrıntı ve AIXM gerekçeleri:
[`docs/AIXM_ChangeOverPoint_Attributes.md`](docs/AIXM_ChangeOverPoint_Attributes.md).

---

## 5. AŞAMA 2B — GeoPackage

Girdi **yalnızca** 2A çıktısıdır. Dört katman üretilir:

> **`changeOverPoints` beşinci katmandır ve geometrisi ÇİZGİDİR.** COP bir
> noktadır ama koordinatı AIXM'de yazılmaz (AIP yayımlamıyor); bu yüzden katman,
> COP'un geçerli olduğu **rota aralığını** çizgi olarak taşır ve çizgi
> `RoutePortion.start` ucundan başlar. QGIS sembolü bu çizgi boyunca
> `copSymbology_offsetPercent` kadar kaydırır. Ayrıntı: §5.5.

| Katman | Geometri | Sütun |
|---|---|---:|
| `designatedPoints` | POINT | 24 |
| `navaids` | POINT | 55 |
| `navaidComponents` | POINT | 98 |
| `routeSegments` | LINESTRING | 82 |

Sütun listeleri ve eşlemeler:
[`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md).

### 5.1 Uç nokta çözümlemesi

Birleşik dosyada her `xlink:href` aynı dosyadaki bir `gml:identifier`'a işaret
ettiği için çözümleme **doğrudan sözlük aramasıdır**: `uuid → (katman, satır id)`.
`routeSegments_startPointLayer` + `_startPointId` çiftleri buradan doldurulur.

Kaynaklarda segment ucu **hiçbir zaman koordinatla** verilmez — ham EAD kaydı
yalnızca `codeId` + `codeType` taşır (`WPT` → DesignatedPoint, `VOR/DME`,
`VORTAC`, `NDB`, `VOR`, `DME`, `DME/VOR`, `TACAN`, `TACVOR` → Navaid). Birleşik
dosyada da inline `Point` uçlu tek bir segment yoktur (tarandı: 0).

Bunun sonucu: **segment geometrisi uç noktalar çözülerek üretilir.** İki ucu da
çözülen segment geometrili olur; çözülemeyen uçlu segment `NULL` geometriyle
yazılır ve uç kimlikleri boş kalır. Kayıt **düşürülmez** — görünür boşluk
bırakılır.

> **Bilinen boşluk:** ileride bir kaynak segment ucunu koordinatla verirse
> mevcut kod bunu işlemez (ne geometri ne uç kimliği üretir). Şu an hiçbir
> kaynakta böyle bir kayıt olmadığı için tetiklenmiyor.

### 5.2 Validasyon ve severity politikası

`gpkg/validation_rules.py`, katman başına `alan → FieldRule(type, max_length,
enum, allow_other, pattern)` taşır ve `docs/*.md` tablolarından bire bir
aktarılmıştır. `allow_other`, AIXM'in evrensel `OTHER(:(\w|_){1,58})?` union
desenini karşılar.

| İhlal | Severity | Davranış |
|---|---|---|
| Enum dışı değer | `error` | Alan null'lanır, **kayıt yine yazılır** |
| Tip uyumsuzluğu / aralık dışı sayı | `error` | Alan null'lanır, kayıt yazılır |
| Serbest metin `max_length` aşımı | `warning` | Değer kırpılır, tam değer logda |
| Kaynağın hiç sağlamadığı alan | — | Loglanmaz (boş değer ihlal değildir) |

`navaidComponents_type` ve `_class` sütunları `equipmentType`'a göre farklı enum
taşır; doğrulama alt-türe göre yapılır.

`errored-features.csv` sütunları: `stage, layer, record_identifier, field,
value, violation, severity`.

### 5.3 Türetilmiş alanlar

Katmanlar yazıldıktan sonra, index kurulmadan **önce** iki türetme geçişi
çalışır. İkisinin de AIXM'de karşılığı yoktur; ikisi de kaynak veriyi
değiştirmez, yalnızca yeni sütun doldurur.

| Adım | Alanlar | Katman | Neyden türetilir |
|---|---|---|---|
| `[4]` | `atsStatus_*` (13 sütun) | `designatedPoints`, `navaids` | `routeSegments` — noktanın ATS rota ağındaki rolü |
| `[5]` | `navaidLabeling_*` (9 sütun) | `navaids`, `navaidComponents` | Tip bazlı geçerlilik kapıları, ICAO frekans/kanal eşleştirmesi ve ITU mors alfabesi |
| `[6]` | `navaidSymbology_*` (2 sütun) | `declination`: `navaids`+`navaidComponents`; `GPAssociatedLOCTrueBrg`: `navaidComponents` | `declination`: VOR/TACAN bileşeninin kendi AIXM `declination`'ı (pusula gülü dönüşü); `GPAssociatedLOCTrueBrg`: Glidepath hüzmesinin yönü — kardeş `Localizer`'ın `trueBearing`'i |

**Neden index'ten önce:** yeni sütunların B-tree index'i `finalize()` içinde
kuruluyor; sonra çalışsalardı indekssiz kalırlardı.

`navaidLabeling_*` etiket üretimini QGIS ifadelerinden tamamen devralır:
tip kısaltması (`VOR DME`, `GP`, `OM`) ve ident'in ITU mors karşılığı da
burada üretilir; QGIS tarafında 20 dallı `CASE` ifadesine gerek kalmaz.
Mors alfabesi koda gömülü değil, [`gpkg/morse-itu.json`](gpkg/morse-itu.json)
veri dosyasındadır (ITU-R M.1677-1).

Adım **üç geçişlidir**. Önce `navaidComponents`, sonra `navaids`
(bileşenlerin çözülmüş değerlerini devralır), en son MLS `Elevation`
bileşenleri (değerlerini kardeş `Azimuth`'tan alırlar, bu bağ ancak ilk geçiş
bittiğinde bilinir).

İlk iki geçişin sebebi: AIXM'de frekans ve kanal Navaid
feature'ında değil **bağlı ekipmanda** durur (`NavaidPropertyGroup`'ta ikisi de
yoktur), oysa harita etiketi navaid düzeyinde çizilir. Bu yüzden önce
`navaidComponents` çözülür, sonra `navaids` bileşenlerin sonucunu devralır.
Bir ekipman ya frekans ya kanal taşır; eksik olan
[`gpkg/frequency-pairing.csv`](gpkg/frequency-pairing.csv)'den türetilir.

Ayrıntılar: [`ATS_Status_Fields.md`](ATS_Status_Fields.md),
[`Navaid_Labeling_Fields.md`](Navaid_Labeling_Fields.md) ve
[`Navaid_Symbology_Fields.md`](Navaid_Symbology_Fields.md).

### 5.4 Index

`finalize()` üç şey kurar:

1. **Her sütunda B-tree index** — beş katmanda toplam 315 sütun.
2. **Mekânsal index (RTree)** — katman başına `rtree_<katman>_geom` sanal
   tablosu, GeoPackage 1.2 Ek F.3'teki altı tetikleyici (insert / update1-4 /
   delete) ve `gpkg_extensions` kaydı (`gpkg_rtree_index`, scope `write-only`).
   QGIS'te büyük katmanlarda asıl performansı bu verir.
3. `gpkg_contents` içindeki `min_x/min_y/max_x/max_y` sınırlayıcı kutuları ve
   `gpkg_ogr_contents` satır sayaçları; sonda `ANALYZE`.

Sınırlayıcı kutular geometri blob'undan Python tarafında hesaplanır
(`geometry_envelope`) — SpatiaLite gerekmez. Tetikleyiciler `ST_MinX` gibi
fonksiyonlara başvurur; düz SQLite'ta tanımsız olmaları sorun değildir çünkü
tetikleyici gövdesi yalnızca çalıştırıldığında çözülür, bu fonksiyonları
QGIS/GDAL sağlar.

### 5.5 `changeOverPoints` — rota aralığı çizgisi

COP'un GeoPackage geometrisi **kendi konumu değildir**: AIP, COP'un
koordinatını yayımlamıyor (bkz.
[`docs/AIXM_ChangeOverPoint_Attributes.md`](docs/AIXM_ChangeOverPoint_Attributes.md)
§7.2). Katman, COP'un geçerli olduğu **rota aralığını** çizgi olarak taşır;
sembol bu çizgi boyunca kaydırılarak yerine konur.

Çizgi, `gpkg/route_portion.py` tarafından kurulur:

1. Bağlı Route'un segmentlerinden komşuluk grafiği (her segment iki yönde de
   gezilebilir).
2. `intermediatePoint` **varsa** yol onun üzerinden geçer (`start→ara` +
   `ara→end`); yoksa `start→end` en kısa zincir aranır.
3. Her segment gerekiyorsa **ters çevrilerek** eklenir — çizgi `start` ucundan
   başlamak zorundadır, yoksa sembol yanlış uçtan ölçülür. (Ölçüldü: örnek bir
   COP'ta zincirdeki 7 segmentin tamamı kaynakta ters yöndeydi.)
4. Uzunluk `pyproj.Geod(ellps="WGS84")` ile ölçülür ve
   `copSymbology_offsetPercent = distance / uzunluk × 100` hesaplanır.

**Belirsizlik sessizce çözülmez.** Rota dallanıyor ve ara nokta verilmemişse —
yani aynı uzunlukta birden fazla yol varsa — **seçim yapılmaz**: satır yazılır,
geometri `NULL` kalır, `cop_rota_araliginda_birden_fazla_yol` loglanır. Zincir
hiç kurulamazsa `cop_rota_araligi_cozulemedi`. İkisinde de kayıt düşürülmez
(§5.1 emsali).

Bu geçiş 3. geçişten (`routeSegments`) **sonra** çalışır: çizgi ancak segment
geometrileri okunduktan sonra kurulabilir. Bellek için yalnızca COP'u olan
rotaların (67) segment topolojisi saklanır, 93.000 segmentin tamamı değil.

**Son koşu:** 100 COP, **100'ü geometrili**; birden fazla yol 0, çözülemeyen 0.

---

## 6. Üretilen dosyalar

| Dosya | Aşama | Son koşu |
|---|---|---|
| `data-sources/*/…-aixm.xml` | 1 | EAD 472,3 MB · Jeppesen 9,0 MB · LT 10,1 MB |
| `data-sources/Jeppesen/jeppesen-ndb-index.json` | 1 | 3.073 kayıt — EAD'nin NDB referans çözümlemesi için |
| `data-sources/Jeppesen/jeppesen-marker.json` | 1 | 913 kayıt — marker yan dosyası, AIXM'den bağımsız (§4.6) |
| `common-ats-structure-aixm.xml` | 2A | 485,3 MB · 282.549 feature |
| `common-ats-structure-provenance.json` | 2A | 282.549 kayıt |
| `common_ats_structure.gpkg` | 2B | 261,0 MB |
| `errored-features.csv` | 2A + 2B | 14.394 kayıt (tek koşu; 9.189'u yalnızca-sayaç) |

> **Yalnızca-sayaç kayıtlar.** `dme_yuksekligi_kaynakta_yok` (9.189) dosyaya
> satır yazmaz, sadece sayılır (`log.info_count`) — EAD'nin DME raporunda
> yükseklik alanı hiç olmadığı için bu boşluk ~9.200 satırı ilgilendiriyor ve
> dosyayı okunamaz hale getirirdi. Konsoldaki özet **sayaçları** gösterir,
> dosyadaki satır sayısı ise yalnızca gerçekten yazılan satırları.

> `errored-features.csv` her koşuda **sıfırdan yazılır**. Aşamaları ayrı ayrı
> çalıştırırsanız (`--merge`, sonra `--gpkg`) ikinci koşu birincinin kayıtlarını
> siler; tam log için tek komutla çalıştırın.

### Son koşunun sayıları

**2A:** toplam **282.549** feature; marker beacon 77; LT lehine düşen ana kaynak
kaydı 3.111, TRNC lehine 9; EAD/Jeppesen lehine yazılmayan LT navaid'i 64,
TRNC kaydı 3; bölünen segment 53; **iptal 32**.

Feature tipine göre: `DesignatedPoint` 152.042 · `RouteSegment` 92.959 ·
`Route` 14.767 · `Navaid` 9.338 · `DME` 4.667 · `VOR` 3.594 · `NDB` 3.054 ·
`TACAN` 877 · `Localizer` 550 · `Glidepath` 524 · **`ChangeOverPoint` 100** ·
`MarkerBeacon` 77.

COP referans denetimi (§4.10): **300 referans denetlendi, kırık 0**.

**2B:**

| Katman | Satır | Geometrili |
|---|---:|---:|
| `designatedPoints` | 152.042 | 152.042 |
| `navaids` | 9.338 | 9.336 |
| `navaidComponents` | 13.343 | 13.343 |
| `routeSegments` | 92.959 | 84.220 |
| `changeOverPoints` | 100 | 100 |

Bağlanmamış navaid bileşeni **0**.

Kaynak dağılımı (`data_provider` / `data_originator`'a göre sayıldı):

| Katman | EAD-SDO | Jeppesen | Ibosoft AIS / DHMİ | Ibosoft AIS / KKTC SHD | Ibosoft AIS / BULATSA |
|---|---:|---:|---:|---:|---:|
| `designatedPoints` | 151.159 | — | 855 | 26 | **2** |
| `navaids` | 6.277 | 3.053 | 3 | 5 | — |
| `navaidComponents` | 10.202 | 3.130 | — | 11 | — |
| `routeSegments` | 90.048 | — | 2.876 | 29 | **6** |
| `changeOverPoints` | — | — | 100 | — | — |

> Jeppesen'in `navaidComponents` payı 3.130 = 3.053 NDB + **77 marker beacon**.
> `navaids` payı 3.053'tür (3.054 değil): `GKE` NDB'si TRNC kaydıyla
> değiştirildi (§4.4).

> `BULATSA` originator'ı yalnızca `tailored-lb` kaynağından gelir (§4.1) —
> `data_provider` yine `Ibosoft AIS`'tir, çünkü kaydı biz yazdık; originator
> verinin sahibi otoriteyi gösterir.

**İlk kez dolan sütunlar.** `tailored-lb` ile birlikte iki GeoPackage sütunu
bu korpusta ilk kez değer aldı — ölçüldü, TLB dışı satır sayısı **0**:

| Sütun | Dolu satır | Not |
|---|---:|---|
| `routeSegments_airspaceClass` | 6 | Hepsi `tailored-lb` |
| `routeSegments_aircraftCapability` içinde `navigationAccuracy` | 6 | Hepsi `tailored-lb`; sütunun kendisi 2.698 satırda dolu, ama `navigationAccuracy` anahtarı yalnızca bu 6'sında var |

`routeSegments_availability` ise ilk kez **değil**: 12 satırda dolu, 7'si
`KKTC SHD`, 5'i `tailored-lb`. `tailored-lb`'nin 6 segmentinden biri
(`P727 REZOV→UVUDA`) AIP'ye göre PERM olduğu için `availability` taşımaz —
kural §4.1'deki kaynağın README'sinde.

---

## 7. Doğrulama durumu

| Kontrol | Sonuç |
|---|---|
| Birleşik AIXM XSD'ye karşı | **0 hata**, 282.549 feature (stok AIXM 5.2 seti **+** `schemas/ibosoftais-extension.xsd`) |
| `gml:id` tekilliği | 1.630.350 tekil (feature + iç nesneler), çift **0** |
| UUID tekilliği | 282.549 tekil, çift **0** |
| `xlink:href` bütünlüğü | 277.694 referans, **kırık 0** |
| COP `RoutePortion` referansı | 300 referans (200 `Navaid` + 100 `Route`), **kırık 0** |
| Provenance kapsamı | 282.549 kayıt, eksik anahtar 0 |
| Bağlanmamış navaid bileşeni | **0** |
| Mekânsal index | 4 RTree tablosu dolu, 24 tetikleyici, 4 `gpkg_extensions` kaydı |
| Antimeridyen | 53 kesişim noktası + 106 bölünmüş segment, notlar tam metin |
| Marker beacon | 77 eşleşti, belirsiz 0; enjekte edilen bileşenler **XSD sırasına uygun** (doğrulama bunu yakalar) |
| `errored-features.csv` | **877 satır**: 836 eşleşemeyen marker + 35 etiket türetmesi + 5 iptal + 1 MEN belirsizliği |

**XSD doğrulaması iki riski birden kapatıyor.** Bu koşuda şemaya iki yeni yapı
girdi ve ikisi de sınandı:

  * **Enjekte edilen `navaidEquipment`** — var olan bir Navaid'in içine
    eklendiği için eleman sırası bozulabilirdi (`location`'dan önce gelmeli).
    Yanlış yere eklenseydi şema hata verirdi.
  * **Boş `beginPosition`** — `indeterminatePosition="unknown"` ile yazılan
    değersiz `gml:TimePosition`'ın GML'de geçerli olduğu doğrulandı.

Provenance'ta boş `data_originator`: **6.221** feature — Jeppesen'in tamamı
(3.072 Navaid + 3.072 NDB ekipmanı + 77 MarkerBeacon). Jeppesen
`data.json`'ında originator alanı yok; doğrulanmış yokluk, sessiz düşürme
değil.

> Jeppesen NDB sayısı 3.073 değil **3.072**: `GKE` NDB'si TRNC kaydıyla
> değiştirildi ve ekipmanı da birlikte düştü (§4.4). `navaidComponents`
> katmanındaki 3.073 NDB satırının biri TRNC'den gelir.

### Kalan doğrulama işleri

- QGIS'te dört katmanın görsel kontrolü
- Bilinen bir ILS'in spot kontrolü (`navaids`'de tek satır, `navaidComponents`'ta
  LOC/GP/DME ayrı ve kendi konumlarında, `navaidId` ile bağlı)
- Uçtan uca rota kontrolü: bir EAD rotası (`UA14`) ve bir LT rotası (`UA 285`)
- Antimeridyen görsel kontrolü — hiçbir segment haritayı boydan boya kat etmemeli

---

## 8. LT'nin tipsiz stub navaid'leri (karar verildi)

LT'nin `MEN` ve `AYR` kayıtları, VFR `fix`/`PointReference` yapılarından
türetilmiş **stub**'lardır: ham LT verisinde tip ve konum tanımlı değildir.
Navaid doğal anahtarı `type + designator + originator` olduğu için tipsiz bir
kayıt tam anahtarla eşleşemez.

Bunun için **gevşek eşleşme** eklendi: tipsiz bir ek kaynak navaid'i,
`designator + originator` ile ana kaynakta aranır. Tek aday varsa ana kaynağa
devredilir; **birden fazla aday varsa seçim yapılmaz** — kayıt korunur ve
belirsizlik `tipsiz_navaid_birden_fazla_ana_kaynak_adayi` olarak loglanır.
Yanlış navaid'e yönlendirme sessiz bir veri hatası olurdu.

| Kayıt | EAD'deki durum | Sonuç |
|---|---|---|
| `MEN` | `DHMI TURKIYE` originator'lı **iki** aday: `VOR_DME` "IZMIR" ve `TACAN` "ADNAN MENDERES" | Belirsiz — kullanıcı kararı: **stub kalsın**. Loglanır. |
| `AYR` | Bu designator'la **hiç** navaid yok | Devredilecek kayıt yok — kullanıcı kararı: **NULL geometriyle katmanda kalsın** |

İkisi de `navaids` katmanında `type` ve `geom` NULL olarak durur; katmandaki
geometrisiz 2 satır bunlardır. LT'nin VFR raporlama noktaları (`LT_VRP_*`) bu
stub'lara referans vermeye devam eder — `xlink` bütünlüğü korunur.
