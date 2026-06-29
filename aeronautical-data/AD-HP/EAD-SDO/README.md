# EAD-SDO AD/HP GeoPackage

## Açıklama

Bu araç, EAD-SDO (European AIS Data Service - Standardized Data Only) kaynaklarından havalimanı/heliport (AD/HP) verilerini GeoPackage formatına dönüştürür. İki katman üretir:

- **`ad_hp_airports`** (spatial, POINT): ARP (Aerodrome Reference Point) konum verisi + usage (kullanım kısıtları) verisi.
- **`ad_hp_runways`** (aspatial): RWY-DIR (pist yönü: bearing) + RWY-INFO (pist çifti: boyut, yüzey, PCN/LCN, strip, ağırlık limitleri) verisi, birbirine eşleştirilmiş.

İki tablo, `match_id` sütunu üzerinden çapraz referanslanabilir (bkz. aşağıdaki bölüm).

## Katmanlar (Layers)

| Katman | Tip | Geometri | İçerik | Kayıt grain'i | Kayıt sayısı |
|---|---|---|---|---|---|
| `ad_hp_airports` | features (POINT) | ARP lat/lon, WGS84 | Havalimanı/heliport + usage join | 1 satır = 1 ICAO/code_id | ~38.000 |
| `ad_hp_runways` | aspatial | yok (koordinat kaynakta yok) | RWY-DIR (yön) + RWY-INFO (çift, 30+ alan) join | 1 satır = 1 pist YÖNÜ | ~55.000 |

## `ad_hp_airports` Şeması

| Sütun | Açıklama |
|---|---|
| `source_region` | Kaynak bölge: `afr` / `am-pac` / `asi-aus` / `eur` / `tailored` |
| `source_file` | Kaynak XML dosya adı |
| `join_key` | `code_icao` varsa o, yoksa `code_id` (usage eşleştirme anahtarı) |
| `mid` | EAD-SDO kayıt id'si |
| `code_id` | Aerodrome/Heliport - Identification (ICAO **değil**) |
| `code_icao` | ICAO 4-harf kodu (varsa) |
| `code_iata` | IATA 3-harf kodu (varsa) |
| `code_type` | AD / HP / AH |
| `name`, `city`, `country` | Ad, şehir/servis bölgesi, ülke |
| `datum` | Koordinat datumu (WGE = WGS84) |
| `lat_text`, `lon_text` | Ham koordinat metni (DMS/DDM/DD) |
| `lat_dd`, `lon_dd` | Ondalık derece (WGS84) |
| `dt_wef`, `arp_work_hr`, `sys_rmk`, `created_by` | ARP kaydının tarih/çalışma saati/not/oluşturan kurum bilgisi |
| `usage_*` (27 sütun) | `ad-hp-usage.xml`'den join edilen kullanım kısıtlaması alanları (limitasyon, çalışma saati, geçerlilik, uçak tipi/motor, vb.) |
| `usage_joined` | 0/1 — usage eşleşmesi bulundu mu |
| `match_id` | INTEGER — **Çapraz tablo eşleştirme anahtarı**, rastgele üretilir (bkz. aşağıda) |

## `ad_hp_runways` Şeması

| Sütun | Tip | Kaynak | Açıklama |
|---|---|---|---|
| `match_id` | INTEGER | rastgele üretilir | **Çapraz tablo eşleştirme anahtarı** |
| `source_region` | TEXT | — | `afr` / `am-pac` / `asi-aus` / `eur` (RWY-DIR kaynağı) |
| `source_file` | TEXT | — | RWY-DIR XML dosya adı |
| `ahp_code_id` | TEXT | RWY-DIR `Ahp/codeId` | Aerodrome/Heliport - Identification (ICAO **değil**) |
| `ahp_code_icao` | TEXT | RWY-DIR `Ahp/codeIcao` | ICAO kodu (varsa; bazı bölgelerde yok) |
| `rwy_designator` | TEXT | RWY-DIR `Rwy/txtDesig` | Pist **çifti** designator'ı (örn. "RWY 11/29") |
| `direction_designator` | TEXT | RWY-DIR `txtDesig` | Bu kaydın temsil ettiği **yön** (örn. "11") |
| `true_bearing` | REAL | RWY-DIR `valTrueBrg` | Gerçek (true) bearing, derece |
| `mag_bearing` | REAL | RWY-DIR `valMagBrg` | Manyetik bearing, derece |
| `dir_dt_wef` | TEXT | RWY-DIR `dtWef` | RWY-DIR kaydının geçerlilik tarihi |
| `dir_created_by` | TEXT | RWY-DIR `OrgCre/txtName` | RWY-DIR kaydını oluşturan kurum |
| `dir_mid` | TEXT | RWY-DIR `mid` | RWY-DIR kayıt id'si |
| `info_joined` | INTEGER | — | 0/1 — RWY-INFO eşleşmesi bulundu mu |
| `info_designator` | TEXT | RWY-INFO `txtDesig` | RWY-INFO'daki pist çifti designator'ı (ham, eşleşince) |
| `info_length` | REAL | RWY-INFO `valLen` | Pist uzunluğu (eşleşince; bazı kayıtlarda hiç yok) |
| `info_width` | REAL | RWY-INFO `valWid` | Pist genişliği (eşleşince; bazı kayıtlarda hiç yok) |
| `info_dim_unit` | TEXT | RWY-INFO `uomDimRwy` | Uzunluk/genişlik birimi (`FT` / `M`) |
| `info_dt_wef` | TEXT | RWY-INFO `dtWef` | RWY-INFO kaydının geçerlilik tarihi |
| `info_dt_com` | TEXT | RWY-INFO `dtCom` | RWY-INFO kaydının yayın/tamamlanma tarihi |
| `info_surface_composition` | TEXT | RWY-INFO `codeComposition` | Pist yüzey malzemesi (örn. `ASPH`, `CONC`) |
| `info_surface_condition` | TEXT | RWY-INFO `codeCondSfc` | Yüzey durumu (örn. `GOOD`) |
| `info_surface_preparation` | TEXT | RWY-INFO `codePreparation` | Yüzey hazırlığı (örn. `GROOVED`) |
| `info_status` | TEXT | RWY-INFO `codeSts` | Pist durumu (nadiren dolu, örn. `OTHER`) |
| `info_marking_rmk` | TEXT | RWY-INFO `txtMarking` | İşaretleme notu |
| `info_profile_rmk` | TEXT | RWY-INFO `txtProfile` | Profil/eğim notu (örn. "Rwy 35 up 0.56%") |
| `info_rmk` | TEXT | RWY-INFO `txtRmk` | Genel not |
| `info_pcn_class` | REAL | RWY-INFO `valPcnClass` | PCN (Pavement Classification Number) değeri |
| `info_pcn_pavement_type` | TEXT | RWY-INFO `codePcnPavementType` | PCN kaplama tipi (`F`=flexible / `R`=rigid) |
| `info_pcn_pavement_subgrade` | TEXT | RWY-INFO `codePcnPavementSubgrade` | PCN alttemel kategorisi (`A`/`B`/`C`/`D`) |
| `info_pcn_max_tire_pressure_code` | TEXT | RWY-INFO `codePcnMaxTirePressure` | PCN maks. lastik basıncı kategorisi (`W`/`X`/`Y`/`Z`) |
| `info_pcn_eval_method` | TEXT | RWY-INFO `codePcnEvalMethod` | PCN değerlendirme yöntemi (`T`=technical / `U`=using aircraft experience) |
| `info_pcn_note` | TEXT | RWY-INFO `txtPcnNote` | PCN standart formatta değilse açıklama notu |
| `info_lcn_class` | REAL | RWY-INFO `valLcnClass` | LCN (Load Classification Number) değeri |
| `info_length_offset` | REAL | RWY-INFO `valLenOffset` | Nadir alan (~6 kayıt); anlamı EAD-SDO dokümantasyonunda teyit edilmedi, muhtemelen displaced threshold offset |
| `info_strip_length` | REAL | RWY-INFO `valLenStrip` | Pist şeridi (graded strip) uzunluğu |
| `info_strip_width` | REAL | RWY-INFO `valWidStrip` | Pist şeridi genişliği |
| `info_strip_dim_unit` | TEXT | RWY-INFO `uomDimStrip` | Strip boyut birimi |
| `info_auw_weight` | REAL | RWY-INFO `valAuwWeight` | All-Up-Weight limiti |
| `info_auw_weight_unit` | TEXT | RWY-INFO `uomAuwWeight` | AUW birimi |
| `info_siwl_weight` | REAL | RWY-INFO `valSiwlWeight` | Single Isolated Wheel Load ağırlığı |
| `info_siwl_weight_unit` | TEXT | RWY-INFO `uomsiwlweight` | SIWL ağırlık birimi |
| `info_siwl_tire_pressure` | REAL | RWY-INFO `valSiwlTirePressure` | SIWL lastik basıncı |
| `info_siwl_tire_pressure_unit` | TEXT | RWY-INFO `uomSiwlTirePressure` | SIWL basınç birimi |
| `info_created_by` | TEXT | RWY-INFO `OrgCre/txtName` | RWY-INFO kaydını oluşturan kurum |
| `info_ahp_code_id` | TEXT | RWY-INFO `Ahp/codeId` | RWY-INFO tarafındaki codeId (doğrulama amaçlı) |
| `info_ahp_code_icao` | TEXT | RWY-INFO `Ahp/codeIcao` | RWY-INFO tarafındaki ICAO kodu (sıkça boş) |
| `info_mid` | TEXT | RWY-INFO `mid` | RWY-INFO kayıt id'si |
| `info_source_file` | TEXT | — | RWY-INFO XML dosya adı (`rwy-ad-hp-{a..z}.xml`) |

## `match_id` Çapraz Tablo Eşleştirme Sözleşmesi

- `match_id`, **codeId** (`ad_hp_airports.code_id` / `ad_hp_runways.ahp_code_id` — ICAO kodu **değil**) grubu başına `make_match_id_generator()` ile üretilen **rastgele bir tamsayıdır** (1 – 9.999.999.999 aralığında, çalıştırma-içi tekil).
- Aynı codeId'ye sahip airport satırı ve tüm pist satırları, **tek bir script çalıştırması içinde** aynı `match_id` değerini paylaşır.
- **Kalıcı/deterministik değildir**: script her çalıştırıldığında (`ad-hp.gpkg` yeniden üretildiğinde) tüm `match_id` değerleri sıfırdan, baştan rastgele üretilir — bir önceki çalıştırmadaki değerlerle eşleşmesi garanti değildir. Bu yüzden `match_id`'yi GeoPackage dışında (örn. başka bir veritabanında, harici bir referans listesinde) kalıcı bir anahtar olarak saklamayın; sabit/insan-okunur bir referans için `code_id`/`ahp_code_id` kullanın.
- QGIS'te kullanım: `ad_hp_runways` katmanını ekleyip **Properties → Joins → Join attributes by field value** ile `ad_hp_airports.match_id` ↔ `ad_hp_runways.match_id` üzerinden bağlayabilirsiniz; böylece pist satırlarına havalimanı adı/ülke/konum gibi alanlar da görünür hale gelir. Bu join, **aynı `ad-hp.gpkg` dosyası** içinde geçerlidir — dosya yeniden oluşturulursa join'i etkilemez (her iki tablo da aynı anda, aynı değerlerle yeniden yazılır), ama eski bir `.gpkg`'den alınmış `match_id` değerleri yeni dosyada anlamsız olur.

## RWY-DIR / RWY-INFO Join Mantığı

- **Join key**: `(normalize_code(Ahp/codeId), normalize_designator(pist çifti designator))`. ICAO kodu (`codeIcao`) **kullanılmaz** — RWY-INFO'da sıkça eksik olduğu için (örn. NAV CANADA kayıtları).
- **RWY-INFO kaynağı**: `rwy-ad-hp-{a..z}.xml` (CODE ID ilk harfine göre 26 dosya). Eski `rwy-info-{afr,am,asi-aus,eur}.xml` ile **aynı kayıtlar** (mid bazında %100 örtüşme doğrulandı) ama ~25 ek alanla (yüzey, PCN/LCN, strip, AUW/SIWL) export edilmiş — script artık eski dosyaları okumuyor (diskte duruyorlar, kullanılmıyorlar).
- **`normalize_designator()`**: büyük harfe çevirir, `"RWY"`, `"-"`, `" "`, `"/"` karakterlerini temizler. Böylece RWY-DIR'in `"RWY 11/29"` (boşluklu) formatı ile RWY-INFO'nun `"RWY-03/21"` (tireli) formatı aynı anahtara (`"1129"`, `"0321"`) indirgenir.
- **Grain kararı**: tablo **yön-bazlı** — her RWY-DIR kaydı (örn. "11" veya "29") kendi satırını alır; RWY-INFO'dan gelen uzunluk/genişlik bilgisi eşleşen her iki yön satırına da kopyalanır (pist çifti başına RWY-INFO'da zaten tek kayıt var).
- RWY-INFO'da RWY-DIR'de hiç karşılığı bulunamayan kayıtlar çıktıya **dahil edilmez** — satır üretimini RWY-DIR sürüklüyor, RWY-INFO sadece zenginleştiriyor (aynı mantık: usage verisi de `ad_hp_airports`'u zenginleştiriyor, sürüklemiyor).

## Tailored Veri (Manuel Override/Ekleme)

Tek dosya: **`tailored-data.jsonc`** — hem `ad_hp_airports` hem `ad_hp_runways` için manuel override/ek kayıt burada tanımlanır (iki ayrı dosya değil, tek dosyada iki ayrı liste). Format ve davranış airport/runway için ortak:

- `"airports": [...]` — `join_key`/`code_icao`/`code_id` ile eşleşir, `ad_hp_airports` çıktı alan adlarını kullanır.
- `"runways": [...]` — `ahp_code_id` + `direction_designator` ile eşleşir, `ad_hp_runways` çıktı alan adlarını kullanır. **Grain gerçek RWY-DIR verisiyle aynıdır: 1 kayıt = 1 pist YÖNÜ.** Pist çiftleri her zaman 2 yönlü olmak zorunda değildir (tek taraf kullanımlı/yayınlı pistler de var) — bu yüzden script otomatik "çifte bölme" yapmaz; iki yönü olan bir pist için iki ayrı giriş yazmanız gerekir (ortak alanları — uzunluk, yüzey, PCN vb. — her ikisine de tekrarlayın).
- Her iki listede de: aynı anahtar mevcutsa kayıt **TAM override** sayılır (kaynak veriden alan mirası yapılmaz, vermediğiniz alanlar boş kalır); anahtar yoksa **yeni kayıt** eklenir; `enabled: false` ile geçici devre dışı bırakılabilir.
- `match_id` bu dosyada **hiçbir zaman yazılmaz** — script otomatik atar. Aynı `ahp_code_id`/`code_id` değerine sahip airport ve runway tailored kayıtları, gerçek veriden gelen kayıtlarla aynı şekilde otomatik olarak aynı `match_id`'yi paylaşır.
- Detaylı alan listesi ve örnekler için dosya içi yorumlara bakın.

## Bilinen Sınırlamalar

- **`match_id` kalıcı değil**: her script çalıştırmasında yeniden, rastgele üretilir. Aynı havalimanı için bugünkü ve yarınki `ad-hp.gpkg`'deki `match_id` değeri farklı olabilir — sadece **tek bir build içinde** geçerli bir eşleştirme anahtarıdır.
- **Designator sıra uyuşmazlığı**: `"RWY-04/22"` ile `"RWY-22/04"` farklı normalize edilir (sıra korunur, sayılar sort edilmez). Bölgeler arası pist çifti sırası tutarsız yazılmışsa nadir bir eşleşme kaçırma riski var — bilinçli bir basitleştirme, ihtiyaç olursa sort eklenebilir.
- **Eksik boyut/yüzey verisi**: `info_joined=1` olsa da çoğu `info_*` alanı NULL olabilir — kaynakta gerçekten yok (örn. PCN sadece ~3.500/55.430 satırda dolu, AUW/SIWL alanları ~20-40 satırda).
- **`info_length_offset` anlamı teyit edilmedi**: çok nadir bir alan (~6 kayıt), EAD-SDO dokümantasyonunda doğrulanmadı — kullanırken dikkatli olun.
- **Malformed designator**: RWY-DIR'de bazı nadir kayıtlarda pist çifti designator'ı sadece `"RWY"` gibi sayısız/eksik gelebilir; bu durumda `normalize_designator()` boş string üretir ve eşleşme aranmaz (`info_joined=0`). Gözlemde ~55.000 kayıttan sadece 2'si bu durumda.
- **Havalimanı ↔ pist kapsama farkı**: Her havalimanının `ad_hp_runways`'te karşılığı yok — RWY-DIR/RWY-INFO veri seti, ARP veri setinden daha sınırlı kapsamlı (özellikle küçük heliport'lar için pist verisi hiç yayınlanmamış olabilir).
- Usage tablosu (`ad_hp_usage`) hâlâ `EXPORT_RAW_USAGE_TABLE = False` ile devre dışı; script çalıştığında bu ham tablo yazılmaz, sadece `ad_hp_airports`'a join edilmiş haliyle görünür.

## Script Kullanımı

### Windows Batch Launcher
```bash
convert_ad_hp.bat
```

### Doğrudan Python
```bash
python build_ad_hp_gpkg.py
```

### Çıktı
- **ad-hp.gpkg**: OGC-compliant GeoPackage (`ad_hp_airports` + `ad_hp_runways` katmanları)

## QGIS'te Kullanım

1. QGIS'te `ad-hp.gpkg` dosyasını açın — `ad_hp_airports` harita canvas'ında görünür, `ad_hp_runways` aspatial olduğu için sadece katman listesinde/attribute table'da görünür (canvas'ta çizilmez).
2. `ad_hp_runways`'i havalimanı konumuyla ilişkilendirmek için `match_id` üzerinden "Join attributes by field value" kullanın (yukarıdaki bölüm).
3. Attribute sorguları (pist uzunluğu, designator, vb.) her iki tabloda da doğrudan yapılabilir — tüm sütunlar index'li.

## Teknik Detaylar

### Koordinat Dönüşümü
- Input: DMS (derece/dakika/saniye), DDM (derece+ondalık dakika) veya doğrudan ondalık derece.
- Output: WGS84 (EPSG:4326) ondalık derece.
- Geometry: WKB Point blob (GeoPackage standardı), sadece `ad_hp_airports` için — `ad_hp_runways` kaynakta koordinat içermediği için aspatial.

### Field Type Konvansiyonu
- **REAL**: koordinatlar, bearing (`true_bearing`/`mag_bearing`), pist/strip boyutları, PCN/LCN sınıf değerleri, ağırlık/basınç limitleri (AUW/SIWL).
- **INTEGER**: join/eşleşme bayrakları (`usage_joined`, `info_joined`), rastgele üretilen `match_id`.
- **TEXT**: kodlar, designator'lar, tarihler (ham `DD/MM/YYYY` string), kurum adları, birim etiketleri, remark/not alanları, `mid` değerleri (büyük sayılar olabileceği için int'e çevrilmez).

### Index Stratejisi
- Her iki tabloda da, `geom`/`fid` hariç **tüm sütunlarda** index oluşturulur (`PRAGMA table_info` ile sütunlar dinamik keşfedilip `idx_{tablo}_{sütun}` adıyla index açılır) — havalimanı ve pist verisi farklı yerlerden zaman zaman arandığı için.

## Veri Kaynakları

- `arp-{afr,am-pac,asi-aus,eur}.xml` — ARP (havalimanı/heliport konum) verisi.
- `ad-hp-usage.xml` — kullanım kısıtlaması verisi.
- `tailored-data.jsonc` — manuel override/ek kayıt dosyası, **hem havalimanı hem pist verisi için** (`"airports"` + `"runways"` listeleri; bkz. "Tailored Veri" bölümü ve dosya içi yorumlar).
- `rwy-dir-{afr,am,asi-aus,eur}.xml` — pist YÖN verisi (bearing). Not: dosya adı bölge etiketi Americas/Pacific için `am`, script içinde `am-pac` olarak etiketlenir (ARP tablosuyla tutarlılık için).
- `rwy-ad-hp-{a..z}.xml` — pist ÇİFT verisi (boyut, yüzey, PCN/LCN, strip, ağırlık limitleri), `CODE ID` ilk harfine göre 26 dosyaya bölünmüş **aktif RWY-INFO kaynağı**.
- `rwy-info-{afr,am,asi-aus,eur}.xml` — **artık script tarafından okunmuyor** (kullanılmayan eski kaynak, diskte kalıyor). `rwy-ad-hp-{a..z}.xml` ile aynı kayıtları içeriyordu (mid bazında doğrulandı), yerini ona bıraktı.

## Notlar

- Tüm kayıtlar WGS84 (EPSG:4326) referans sisteminde depolanır (`ad_hp_airports` için).
- NULL değerler standart SQL NULL olarak tutulur (QGIS'te gri gösterilir).
- `ad_hp_runways`, GeoPackage `gdal_aspatial` extension'ı ile kayıtlıdır — GDAL/QGIS tarafından geçerli bir attribute tablosu olarak tanınır.
- Script, mevcut `ad-hp.gpkg` dosyasını her çalıştırmada siler ve sıfırdan yeniden oluşturur.
