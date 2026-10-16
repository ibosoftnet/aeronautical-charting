# Common Airspaces Builder — Davranış Dokümanı

`build_common_airspaces.py`'nin ne yaptığını, kaynakları nasıl birleştirdiğini
ve son koşunun ölçülen sonuçlarını anlatır. GeoPackage sütun eşlemesi:
[`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md).
AIXM airspace modeli: [`docs/`](docs/). Ortak altyapı: [`../common/README.md`](../common/README.md).

Akış ATS ile (`../data-ats/Common_Builder_Behaviour.md`) aynıdır; bu doküman
airspace'e özgü olanları anlatır.

## 1. Bağlayıcı kural

> **Hiçbir AIXM özniteliği sessizce atlanamaz; uydurma eşleme yok; bilinmeyen
> sorulur; izinsiz fallback yok.** Kaynakta olmayan değer boş kalır.

## 2. Genel akış

```
                     ┌──────────────── AŞAMA 1 ────────────────────────┐
ham veri ────────────▶ üreticiler, config SIRASIYLA:                   │
                     │  jeppesen · icao-fir-uir · lt · lh · ibosoft    │
                     │  (trnc, tailored-lt: AIXM elle düzenlenir)      │
                     └───────────────────────┬─────────────────────────┘
                                             ▼
                 data-sources/<kaynak>/<kaynak>-airspace-aixm.xml (XSD-geçerli)
                                             │
                     ┌───────────────────────▼─────────────────────────┐
                     │ AŞAMA 2A — ana kaynaklar → iptal kuralları →    │
                     │            ek kaynaklar (ekleme / override)     │
                     └───────────────────────┬─────────────────────────┘
                                             ▼
                       navdata/ibosoft-ais-navdata-airspaces-aixm.xml
                                             │
                     ┌───────────────────────▼─────────────────────────┐
                     │ AŞAMA 2B — geometri hesabı + şema eşlemesi +    │
                     │            index                                │
                     └───────────────────────┬─────────────────────────┘
                                             ▼
                       navdata/ibosoft-ais-navdata-airspaces.gpkg
                       logs/errored-features.csv
```

```bash
py build_common_airspaces.py            # config'de açıksa 1, sonra 2A + 2B
```

```bash
py build_common_airspaces.py --sources --merge --gpkg
```

`start-full-build.bat` tam akışı çalıştırır. `--sources`, `--merge`, `--gpkg`
aşamaları ayrı ayrı çalıştırır. `config.json`'da `run_source_generators: true`.

## 3. AŞAMA 1 — Kaynaklar ve üreticiler

| Rol | Kaynak | Girdi | Çıktı | Kimlik (`gml:identifier`) |
|---|---|---|---|---|
| ana | `jeppesen` | `aeronautical-data/Jeppesen Data/jeppesen.sqlite` → `boundary` + `data.json` | `jeppesen-airspace-aixm.xml` | uuid5(`JeppesenAirspace:<boundary_id>`) |
| ana | `icao-fir-uir` | `fir-2021-ibosoft-tailored.json` (kopya) + `data.json` | `icao-fir-uir-airspace-aixm.xml` | uuid5(`IcaoFirAirspace:<OBJECTID>`) |
| ek | `lt` | `raw-data/*.json` (lt-dhmi indirir) + `data.json` | `lt-airspace-aixm.xml` | kaynağın kendi `kid`'i |
| ek | `lh` | `data.txt` (TNP) + `data.json` | `lh-airspace-aixm.xml` | uuid5(`LhAirspace:<sıra>:<başlık>`) |
| ek | `trnc` | — (AIXM elle düzenlenir) | `trnc-airspace-aixm.xml` | dosyadaki `gml:identifier` |
| ek | `tailored-lt` | — (AIXM elle düzenlenir) | `tailored-lt-airspace-aixm.xml` | dosyadaki `gml:identifier` |
| ek | `ibosoft` | `ibosoft-airspace.json` (elle) | `ibosoft-airspace-aixm.xml` | dosyadaki `aixm_uuid` |

Airspace feature'ını yazan kod tektir: `airspace_aixm.py` (yedi üretici de
onu kullanır). Her saha tek `BASE` bileşeniyle yazılır; geometri
antimeridyene karşı güvenli MultiPolygon'dur (her poligon bir
`gml:PolygonPatch`). Koordinatlar `repr(float)` ile yazılır, değerler
bit düzeyinde korunur. Her feature'ın sonunda provenance kutusu
(`ibosoftais:AirspaceDataProvenance`) vardır.

Eşlemelerin ayrıntısı ve eşlenmeyen kaynak alanlarının gerekçeleri:
`data-sources/<kaynak>/generate-aixm-data/<Kaynak>_to_AIXM_Mapping.md`.

### Elle tutulan kaynaklar

Eski `Common Airspaces/data-sources/tailored/tailored.json` (125 kayıt)
originator'a göre üç kaynağa ayrıldı: TRNC (KKTC SHD, 11), tailored-LT
(DHMİ Türkiye, 113), ibosoft (Ibosoft AIS, 1 ATZ). Bu veride doğal anahtar
tekil değil (4 KKTC paraşüt sahası aynı tip+ad taşıyor), bu yüzden her kayda
bir kez **sabit UUID** atandı; mevcut kayıtta değiştirilmez.

- **TRNC ve tailored-LT:** JSON ve üretici **yok** (kullanıcı kararı). Bir kez
  üretilen AIXM dosyaları artık kaynağın kendisidir ve **elle düzenlenir**
  (ATS'deki TRNC / tailored-LB ile aynı düzen). Kurallar:
  [`docs/AIXM_Airspace_How_To_Add.md`](docs/AIXM_Airspace_How_To_Add.md) ve
  ilgili dizindeki `README.md`. 1. aşamada çalıştırılmazlar.
- **ibosoft:** GeoJSON (`aixm_uuid` alanlı) + üretici.

## 4. AŞAMA 2A — Birleştirme

### 4.1 Sıra

1. **Override indeksi** — yalnız `override_enabled: true` ek kaynaklar
   (bugün **hiçbiri**). Anahtar: `type` + `designator` + ana kaynaktaki
   originator yazımı (`override_base_originator`). Designator'sız saha
   eşleştirilemez.
2. **İptal kuralları** yüklenir (`data-sources/excludes/`).
3. **Ana kaynaklar** (jeppesen, icao-fir-uir) sırayla yazılır; her feature için
   önce iptal, sonra override kontrolü.
4. **Ek kaynaklar** (lt, lh, trnc, tailored-lt, ibosoft) olduğu gibi eklenir.
5. **Halka yönü** — yazılan HER feature'ın (ana ve ek) yüzey halkaları
   GeoJSON **RFC 7946 §3.1.6** kuralına getirilir: dış halka saat yönünün
   tersi, delikler saat yönü (kullanıcı kararı). Yön harita düzleminde
   (x = boylam, y = enlem) hesaplanır; `posList` "enlem boylam" sırasında
   olduğu için ham sayı sırasıyla hesaplanmaz. Yalnız nokta **sırası** ters
   çevrilir, koordinat metinleri değişmez. Kaynak dosyalara (elle düzenlenen
   TRNC / tailored-LT dahil) dokunulmaz; kural yalnız birleşik AIXM'dedir.
   Ters çevrilen halka sayısı özette `halka_ters_cevrildi` olarak basılır
   (kod: `airspace_geometry.orient_member`). Ölçüldü: 36.694 halka çevrildi;
   sonuçta 36.981 dış halkanın hepsi saat yönünün tersi, 15 deliğin hepsi
   saat yönü.

Airspace'ler arasında `xlink` yoktur (kaynakların hiçbiri
`contributorAirspace`/`protectedRoute` üretmiyor), bu yüzden ATS'deki `remap`
gerekmez.

### 4.2 Ekleme modu (kullanıcı kararı)

Override mekanizması desteklenir ama mevcut kaynakların **hepsi yalnızca
ekleme modundadır**: Airspace'te güvenilir bir doğal anahtar yoktur
(designator'ı olmayan sahalar, kaynaklar arası farklı adlandırma). Çakışan
Jeppesen sahaları bölgesel iptal kurallarıyla düşer (§4.3).

### 4.3 İptal kuralları

Ortak `data_build_common/exclude.py`. Airspace'te `match` alanları:
`layer` (= `airspaces`), `provider`, `originator`, `type`, `designator`,
`name`. Konum = sahanın **merkezi**; 2B ile aynı geometri hesabından
(antimeridyen güvenli) alınır — eski koddaki
`antimeridian_safe(geom).centroid` ile aynı yöntem.

| Dosya | Kural | İsabet (son koşu) | İstisnayla korunan |
|---|---|---:|---:|
| `jeppesen-lt.json` | `provider=Jeppesen`, merkez `lt-fir.geojson` (ANKARA LTAA + İSTANBUL LTBB) içinde, `FREE RT` hariç | 490 | 1 |
| `jeppesen-lh.json` | `provider=Jeppesen`, merkez `lh-fir.geojson` (BUDAPEST LHCC) içinde, `FREE RT` hariç | 162 | 1 |

Toplam **652** — eski `Common Airspaces` Jeppesen kaynağının `fir-exclude`
ile elediği sayıyla birebir aynı (ölçüldü: eski kod kuralsız 36.354, kurallı
35.702). Ayrıntı: [`data-sources/excludes/README.md`](data-sources/excludes/README.md).

Her isabet `errored-features.csv`'ye `iptal_kuraliyla_cikarildi` olarak
yazılır.

## 5. AŞAMA 2B — GeoPackage

Yalnızca birleşik AIXM'den: her `Airspace` için geometri bileşenlerden
hesaplanır (`airspace_geometry.py`; BASE → UNION/SUBTR/INTERS), satır
`gpkg_airspace.map_airspace` ile eşlenir, ortak `gpkg_writer` ile yazılır ve
index'lenir. Hesaplanamayan geometri → satır yazılmaz, hata loglanır.
Ayrıntı: şema dokümanı §4.

## 6. Son koşunun sayıları (2026-10-15)

**Aşama 1:**

| Kaynak | Okunan | Yazılan | Not |
|---|---:|---:|---|
| jeppesen | 36.354 | 36.354 | FIR/UIR ön elemesi 750 (eski kodla aynı fonksiyon) |
| icao-fir-uir | 344 | 344 | |
| lt | 482 | 482 | 483 GeoJSON feature; `LTIHAT1`'in iki parçası aynı `kid`'i taşıyor → tek Airspace (MultiPolygon) |
| lh | 263 | 263 | 5 `GSEC` sınıfı → `OTHER:GSEC` |
| trnc | 11 | 11 | 1 adda Türkçe harf ASCII'ye çevrildi |
| tailored-lt | 113 | 113 | |
| ibosoft | 1 | 1 | |

**2A:** 36.916 feature (ana 36.046 + ek 870); iptal 652; override 0.

**2B:** `airspaces` 36.916 satır, geometri hesaplanamayan 0; sütun index
55/55, mekânsal index 36.916.

**Dosyalar:** birleşik AIXM 149 MB, GeoPackage 78 MB (`navdata/`);
`jeppesen-airspace-aixm.xml` 131 MB. 100 MB üstü dosyalar
`.gitattributes`'ta LFS'tedir.

## 7. Doğrulama durumu

| Kontrol | Sonuç |
|---|---|
| 7 kaynak AIXM'i XSD'ye karşı (AIXM 5.2 + extension) | **0 hata** |
| Birleşik AIXM XSD'ye karşı | **0 hata**, 36.916 feature |
| `gml:id` tekilliği | 271.886 tekil, çift **0** |
| UUID tekilliği | çift **0** |
| Provenance kutusu | 36.916 feature'ın hepsinde |
| Eski `Common Airspaces` ile karşılaştırma (öznitelik + geometri WKB, kaynak başına çoklu küme) | Jeppesen 35.702, LH 263, tailored 125: **birebir aynı** (beklenen farklar dışında: Jeppesen designator öneki, `OTHER:GSEC`, Türkçe harf dönüşümü). LT: 483 → 482, tek fark `LTIHAT1` birleşmesi |
| Sentetik testler | iptal (`within` içeride/dışarıda/konumsuz, `except`, desteklenmeyen anahtar), geometri (BASE+SUBTR/UNION/INTERS alanları, 3 hata durumu), sınıf listesi `C,D`, JSON içerikleri — 17/17 |
| Eşleme tamlığı | XSD'den çıkarılan 45 doğrudan öğenin hepsi şema dokümanında; JSON'da taşınan yapıların üst öğeleri belgeli |
| Kılavuz örnekleri (`docs/`) | 6 örnek feature XSD'den **0 hata** |
