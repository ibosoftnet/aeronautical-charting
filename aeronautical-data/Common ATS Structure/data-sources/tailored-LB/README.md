# `tailored-LB` — elle yazılmış Bulgaristan düzeltmesi

Bu kaynak, **EAD-SDO'nun almadığı** bir AIP değişikliğini birleşik veriye
taşımak için vardır. Üretici scripti yoktur; AIXM dosyası elle yazılır
(TRNC kaynağıyla aynı desen).

## Neden var

Bulgaristan AIP'sinde (**ENR 3.3**, RNAV rotalar, **AIRAC 2606 / 14 MAY 2026**)
**iki ayrı nokta değişikliği** var:

| # | Değişiklik | Rotalar |
|---|---|---|
| 1 | `BAKLO` kaldırıldı, yerine `EFCOM`; `T264` üzerinde `MYNDA` yayımlandı | N618, T889, T264 |
| 2 | `IBLAX` kaldırıldı, zincir `FENER → REZOV → UVUDA` oldu | P727, UP727 |

EAD-SDO **ikisini de almamış**: EAD kaydı 03 SEP 2026 (AIRAC 2609) tarihli
olmasına rağmen hâlâ `BAKLO`'yu ve `IBLAX`'i taşıyor. Yani bu kaynağın
`data_effectivity`'si (2606) bilerek EAD'ninkinden **eskidir** — düzeltilen veri
daha yeni tarihli ama içerik olarak yanlıştır.

## İki parçalı düzeltme

| Parça | Dosya |
|---|---|
| Eskimiş EAD kayıtlarının çıkarılması | `../excludes/bulatsa-baklo-efcom.json` (4 kural) · `../excludes/bulatsa-p727-iblax-rezov.json` (4 kural) |
| Yerlerine geçenlerin eklenmesi | `tailored-lb-aixm.xml` (9 feature) |

İptal mekanizması yalnızca **ana kaynaklara** uygulanır; BAKLO EAD'den geldiği
için bu yol kullanılabiliyor.

> **Kritik kontrol — kırık referans.** İptal kuralı `remap` girdisi üretmez:
> çıkarılan kaydın UUID'si yok olur ve ona referans veren her şey boşta kalır.
> `BAKLO` ve `IBLAX` birer `designatedPoints` kaydı olduğu için bu risk
> gerçekti. İkisi için de ölçüldü: her birine referans veren **tam olarak 3**
> segment var ve **üçü de** aynı anda iptal ediliyor. Bu yüzden boşluk
> oluşmuyor. Bu dosya güncellenirken aynı kontrol tekrarlanmalıdır.

## İçerik

| Feature | gml:id |
|---|---|
| DesignatedPoint | `TLB_DP_EFCOM`, `TLB_DP_MYNDA` |
| Route | `TLB_RTE_T264` |
| RouteSegment | `TLB_RS_N618_VADEN_EFCOM`, `TLB_RS_N618_EFCOM_GOL`, `TLB_RS_T889_EFCOM_DEDIN`, `TLB_RS_T264_TUDBU_MYNDA`, `TLB_RS_T264_MYNDA_UTEKA`, `TLB_RS_P727_REZOV_UVUDA` |

### P727 neden tek segment?

`IBLAX` kaldırıldığında zincir `FENER → IBLAX → UVUDA`'dan
`FENER → REZOV → UVUDA`'ya dönüşüyor. Ama **`FENER → REZOV` zaten LT
kaynağında var** (`LT_RS_1078`, üst hava sahası için `LT_RS_2349`) — DHMİ onu
kendi AIP'sinde yayımlıyor. Bu yüzden burada yalnızca eksik halka
`REZOV → UVUDA` yazıldı. `REZOV` noktası da zaten var (`LT_DP_REZOV`), AIP
koordinatıyla örtüşüyor; yeni nokta eklenmedi.

`UP727` tarafında Bulgaristan'a giren bir segment yok, bu yüzden o yönde yeni
segment de yok — yalnızca eskimiş `UP727 FENER → IBLAX` iptal ediliyor.

> **İki Route feature'ı sorunu.** Veride P727 için hem `EAD_RTE_P727_EUR`
> (loc=`EUR`) hem `LT_RTE_P727` (loc yok) var; yeni segmentin iki komşusu
> bunların **farklı** olanlarına bağlı (`LT_RS_1078` → LT'ninki,
> `EAD_RS_039398` → EAD'ninki). Kullanıcı kararı: **EAD'ninki** kullanılır,
> çünkü yerine geçilen `IBLAX → UVUDA` ve hayatta kalan `UVUDA → BGS` ona
> bağlı. Zincirin iki Route nesnesi arasında bölünmüş kalması bu düzeltmenin
> yarattığı bir durum değil, veride hâlihazırda var olan bir mükerrerliktir.

`N618` ve `T889` için **EAD'nin mevcut Route feature'ları** yeniden kullanılır
(yeni segmentler, hayatta kalan `GOL→ETIDA` segmentiyle aynı rota nesnesine
bağlansın diye). `T264`'ün Bulgar Route'u veride yoktu — mevcut üç T264 rotası
Türkiye-içi, Pasifik ve LT'nin kendi kaydı — bu yüzden burada tanımlandı.

> Miras doğrulandı: birleşik GeoPackage'ta N618 segmentleri
> `route_locationDesignator = EUR`, T889 segmenti `LT-LB` taşıyor — yani
> `routeFormed` referansları EAD'nin doğru Route'larına çözülüyor.
> `TLB_RTE_T264`'ün `locationDesignator`'ı **boştur**: AIP ENR 3.3 tablosu bu
> alanı yayımlamıyor, uydurulmadı.

## Bu kaynağın veriye kattığı ilkler

`airspaceClass` ve `aircraftCapability/navigationAccuracy` bu korpusta ilk kez
bu kaynağın segmentleriyle doldu (ölçüldü: başka kaynakta 0 satır). İkisinin de
GeoPackage sütunu şemada zaten tanımlıydı, kod değişikliği gerekmedi.

## `availability` ne zaman yazılır

Kullanıcı kuralı: **segmentin bir kısmı CDR ise `status=COND` kodla**; farklı
seviyelere farklı saat atanmışsa saati işleme, remark yeterli.

| Segment | CDR mi | `availability` |
|---|---|---|
| N618 ×2, T889, T264 ×2 | Evet (AIP: `CDR 1 H24`) | `COND` + H24 Timesheet |
| P727 `REZOV → UVUDA` | **Hayır** — AIP remarks "PERM except: UVUDA-BGS, BGS-ARGES" diyor, bu segment istisna listesinde yok | **Yazılmıyor** |

Her iki durumda da AIP'nin remarks metni `annotation`'da birebir korunur.

## UUID üretimi

Projenin standart yardımcısıyla deterministik üretilir; **anahtarlar
`tailored-lb-aixm.xml` başındaki yorumda kayıtlıdır**, böylece yeniden
üretilebilir. (TRNC dosyasında bu kayıt yok ve UUID'leri bugün yeniden
türetilemiyor — aynı hata tekrarlanmasın.)

```python
uuid5(UUID("6f1c3b52-9d4a-5e77-b8c1-2a0e94f7d310"), f"{kind}:{key}").upper()
```

`kind` öneki kaynağa özgüdür (`TailoredLb…`), böylece kaynakların UUID uzayları
ayrı kalır — LT `DesignatedPoint`, EAD `EadDesignatedPoint` kullanıyor.

## AIRAC değişince ne yapılmalı

1. Yeni AIP tablosu ile `tailored-lb-aixm.xml` karşılaştırılır.
2. **EAD artık doğru veriyi taşıyor mu?** Taşıyorsa bu kaynak ve iptal
   kuralları **tamamen kaldırılmalıdır** — aksi halde aynı segment iki kez
   girer.
3. `data.json`'daki `data_effectivity` güncellenir.
4. Nokta ya da segment eklenip çıkarılıyorsa, iptal kuralı yazmadan önce
   yukarıdaki **kırık referans kontrolü** tekrarlanır.
